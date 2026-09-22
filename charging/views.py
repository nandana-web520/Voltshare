from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Sum
import datetime
from django.urls import reverse
from .forms import UserRegisterForm, ChargingStationForm, AvailabilitySlotForm
from django.contrib.auth.forms import AuthenticationForm
from .models import UserProfile, ChargingStation, AvailabilitySlot

def is_admin_user(user):
    return user.is_authenticated and (
        user.is_staff or 
        user.is_superuser or 
        (hasattr(user, 'userprofile') and user.userprofile.role == 'Admin')
    )

def home(request):
    total_chargers = ChargingStation.objects.count()
    from .models import Booking
    total_bookings = Booking.objects.count()
    
    return render(request, 'home.html', {
        'total_chargers': total_chargers,
        'total_bookings': total_bookings
    })

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            # Create the User
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Create the UserProfile
            role = form.cleaned_data.get('role')
            UserProfile.objects.create(user=user, role=role)
            
            messages.success(request, f'Account created for {user.username}! You can now log in.')
            return redirect('login')
    else:
        initial_role = request.GET.get('role', 'Driver')
        if initial_role not in ['Host', 'Driver']:
            initial_role = 'Driver'
        form = UserRegisterForm(initial={'role': initial_role})
    
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        if is_admin_user(request.user):
            return redirect('admin_dashboard')
        elif hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'Host':
            return redirect('host_dashboard')
        return redirect('driver_dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                if is_admin_user(user):
                    return redirect('admin_dashboard')
                elif hasattr(user, 'userprofile') and user.userprofile.role == 'Host':
                    return redirect('host_dashboard')
                elif hasattr(user, 'userprofile') and user.userprofile.role == 'Driver':
                    return redirect('driver_dashboard')
                return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
        
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')

@login_required
def host_dashboard(request):
    # Ensure user is a host
    if hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'Host':
        stations = request.user.charging_stations.all()
        
        from .models import Booking
        from datetime import date
        from django.db.models import Sum
        
        upcoming_bookings = Booking.objects.filter(
            charging_station__host=request.user,
            availability_slot__date__gte=date.today(),
            status='Confirmed'
        ).order_by('availability_slot__date', 'availability_slot__start_time')
        
        expected_revenue = upcoming_bookings.aggregate(Sum('total_cost'))['total_cost__sum'] or 0.00
        
        return render(request, 'host_dashboard.html', {
            'stations': stations,
            'upcoming_bookings': upcoming_bookings,
            'expected_revenue': expected_revenue
        })
    else:
        messages.error(request, 'Unauthorized access. Only Hosts can view this page.')
        return redirect('home')

@login_required
def add_station(request):
    if hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'Host':
        if request.method == 'POST':
            form = ChargingStationForm(request.POST)
            if form.is_valid():
                station = form.save(commit=False)
                station.host = request.user
                station.save()
                messages.success(request, 'Charging station added successfully!')
                return redirect('host_dashboard')
        else:
            form = ChargingStationForm()
        return render(request, 'add_station.html', {'form': form})
    else:
        messages.error(request, 'Unauthorized access. Only Hosts can add stations.')
        return redirect('home')
def delete_past_available_slots(station=None, host=None):
    """
    Deletes unbooked availability slots (status='Available') whose date/time is in the past.
    Preserves booked slots to protect booking transactions and driver records.
    Returns the count of deleted slots.
    """
    now = timezone.localtime() if timezone.is_aware(timezone.now()) else timezone.now()
    today = now.date()
    current_time = now.time()

    slots = AvailabilitySlot.objects.filter(status='Available')
    if station is not None:
        slots = slots.filter(charging_station=station)
    elif host is not None:
        slots = slots.filter(charging_station__host=host)

    past_slots = slots.filter(
        Q(date__lt=today) |
        Q(date=today, end_time__lte=current_time)
    )
    deleted_count, _ = past_slots.delete()
    return deleted_count

@login_required
def delete_past_slots(request, station_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'Host':
        messages.error(request, 'Unauthorized access. Only Hosts can manage slots.')
        return redirect('home')
    station = get_object_or_404(ChargingStation, id=station_id, host=request.user)

    deleted_count = delete_past_available_slots(station=station)
    if deleted_count > 0:
        messages.success(request, f'Successfully deleted {deleted_count} expired available slot(s).')
    else:
        messages.info(request, 'No expired available slots found to delete.')

    return redirect('manage_availability', station_id=station.id)

@login_required
def manage_availability(request, station_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'Host':
        messages.error(request, 'Unauthorized access. Only Hosts can manage availability.')
        return redirect('home')
    station = get_object_or_404(ChargingStation, id=station_id, host=request.user)

    now = timezone.localtime() if timezone.is_aware(timezone.now()) else timezone.now()
    today = now.date()
    current_time = now.time()

    if request.method == 'POST':
        form = AvailabilitySlotForm(request.POST)
        if form.is_valid():
            target_dates = form.get_target_dates()
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']

            created_count = 0
            skipped_count = 0

            for target_date in target_dates:
                t_start = datetime.datetime.combine(target_date, start_time)
                t_end = datetime.datetime.combine(target_date, end_time)

                current_t = t_start
                while current_t < t_end:
                    next_t = current_t + datetime.timedelta(hours=1)
                    if next_t > t_end:
                        next_t = t_end

                    slot_start = current_t.time()
                    slot_end = next_t.time()

                    # Prevent duplicate slots
                    exists = AvailabilitySlot.objects.filter(
                        charging_station=station,
                        date=target_date,
                        start_time=slot_start,
                        end_time=slot_end
                    ).exists()

                    if not exists:
                        AvailabilitySlot.objects.create(
                            charging_station=station,
                            date=target_date,
                            start_time=slot_start,
                            end_time=slot_end,
                            status='Available'
                        )
                        created_count += 1
                    else:
                        skipped_count += 1

                    current_t = next_t

            msg = f'Successfully created {created_count} time slot(s) across {len(target_dates)} day(s)!'
            if skipped_count > 0:
                msg += f' ({skipped_count} existing slot(s) skipped).'
            messages.success(request, msg)
            return redirect('manage_availability', station_id=station.id)
    else:
        form = AvailabilitySlotForm(initial={
            'single_date': today,
            'start_date': today,
            'end_date': today + datetime.timedelta(days=6),
            'start_time': '09:00',
            'end_time': '18:00',
            'recurrence_type': 'single'
        })

    all_slots = station.availability_slots.all().order_by('date', 'start_time')

    # Count expired available slots
    past_available_count = station.availability_slots.filter(
        status='Available'
    ).filter(
        Q(date__lt=today) |
        Q(date=today, end_time__lte=current_time)
    ).count()

    upcoming_count = all_slots.filter(
        Q(date__gt=today) |
        Q(date=today, end_time__gt=current_time)
    ).count()
    past_total_count = all_slots.filter(
        Q(date__lt=today) |
        Q(date=today, end_time__lte=current_time)
    ).count()

    # Filter tab
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'upcoming':
        slots = all_slots.filter(
            Q(date__gt=today) |
            Q(date=today, end_time__gt=current_time)
        )
    elif filter_type == 'past':
        slots = all_slots.filter(
            Q(date__lt=today) |
            Q(date=today, end_time__lte=current_time)
        )
    else:
        slots = all_slots
        filter_type = 'all'

    return render(request, 'manage_availability.html', {
        'station': station,
        'slots': slots,
        'form': form,
        'filter_type': filter_type,
        'total_count': all_slots.count(),
        'upcoming_count': upcoming_count,
        'past_total_count': past_total_count,
        'past_available_count': past_available_count,
        'today': today,
        'current_time': current_time,
    })

@login_required
def delete_slot(request, slot_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'Host':
        messages.error(request, 'Unauthorized access.')
        return redirect('home')
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, charging_station__host=request.user)
    
    if slot.status == 'Booked':
        messages.error(request, 'Cannot delete a slot that is already booked.')
    else:
        slot.delete()
        messages.success(request, 'Slot deleted successfully.')
        
    return redirect('manage_availability', station_id=slot.charging_station.id)

def search_chargers(request):
    stations = ChargingStation.objects.all()
    
    # Simple search functionality
    location_query = request.GET.get('location')
    plug_type_query = request.GET.get('plug_type')
    
    if location_query:
        stations = stations.filter(location__icontains=location_query)
        
    if plug_type_query and plug_type_query != 'All':
        stations = stations.filter(plug_type=plug_type_query)
        
    # Pass plug choices to populate the dropdown
    plug_choices = ChargingStation.PLUG_CHOICES
    
    return render(request, 'search_chargers.html', {
        'stations': stations,
        'plug_choices': plug_choices,
        'location_query': location_query,
        'plug_type_query': plug_type_query
    })

def charger_details(request, station_id):
    station = get_object_or_404(ChargingStation, id=station_id)
    # Only show future slots that are Available
    from datetime import date
    available_slots = station.availability_slots.filter(status='Available', date__gte=date.today()).order_by('date', 'start_time')
    
    return render(request, 'charger_details.html', {
        'station': station,
        'available_slots': available_slots
    })

@login_required
def book_slot(request, slot_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'Driver':
        messages.error(request, 'Only Drivers can book slots.')
        return redirect('search_chargers')
        
    slot = get_object_or_404(AvailabilitySlot, id=slot_id)
    
    # Double-booking prevention
    if slot.status == 'Booked':
        messages.error(request, 'Sorry, this slot is already booked.')
        return redirect('charger_details', station_id=slot.charging_station.id)
        
    # Cost calculation
    import datetime
    from decimal import Decimal
    t1 = datetime.datetime.combine(datetime.date.today(), slot.start_time)
    t2 = datetime.datetime.combine(datetime.date.today(), slot.end_time)
    duration_hours = Decimal((t2 - t1).total_seconds() / 3600.0)
    total_cost = duration_hours * slot.charging_station.price_per_hour
    
    # Create booking and update slot status
    from .models import Booking
    Booking.objects.create(
        driver=request.user,
        charging_station=slot.charging_station,
        availability_slot=slot,
        total_cost=total_cost
    )
    
    slot.status = 'Booked'
    slot.save()
    
    messages.success(request, f'Successfully booked {slot.charging_station.station_name} for ₹{total_cost:.2f}!')
    return redirect('charger_details', station_id=slot.charging_station.id)

@login_required
def cancel_booking(request, booking_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'Driver':
        messages.error(request, 'Unauthorized access.')
        return redirect('home')
        
    from .models import Booking
    booking = get_object_or_404(Booking, id=booking_id, driver=request.user)
    
    if booking.status == 'Confirmed':
        booking.status = 'Cancelled'
        booking.save()
        
        # Free up the slot
        slot = booking.availability_slot
        slot.status = 'Available'
        slot.save()
        
        messages.success(request, 'Booking cancelled successfully.')
    else:
        messages.error(request, 'This booking is already cancelled.')
        
    return redirect('driver_dashboard')

@login_required
def delete_booking(request, booking_id):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'Driver':
        messages.error(request, 'Unauthorized access.')
        return redirect('home')
        
    from .models import Booking
    booking = get_object_or_404(Booking, id=booking_id, driver=request.user)
    
    if booking.status == 'Cancelled':
        booking.delete()
        messages.success(request, 'Cancelled booking deleted from history.')
    else:
        messages.error(request, 'Only cancelled bookings can be deleted.')
        
    return redirect('driver_dashboard')

@login_required
def driver_dashboard(request):
    if hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'Driver':
        from .models import Booking
        from datetime import date
        
        all_bookings = request.user.bookings.all().order_by('-availability_slot__date', '-availability_slot__start_time')
        
        upcoming_bookings = all_bookings.filter(status='Confirmed', availability_slot__date__gte=date.today())
        past_bookings = all_bookings.exclude(id__in=upcoming_bookings.values_list('id', flat=True))
        
        total_bookings = all_bookings.count()
        
        return render(request, 'driver_dashboard.html', {
            'upcoming_bookings': upcoming_bookings,
            'past_bookings': past_bookings,
            'total_bookings': total_bookings
        })
    else:
        messages.error(request, 'Unauthorized access. Only Drivers can view this page.')
        return redirect('home')

@login_required
def admin_dashboard(request):
    if not is_admin_user(request.user):
        messages.error(request, 'Unauthorized access. Only Administrators can view this page.')
        return redirect('home')

    from .models import Booking, ChargingStation, AvailabilitySlot, UserProfile
    from django.contrib.auth.models import User

    all_users = User.objects.all().select_related('userprofile').order_by('-date_joined')
    total_users_count = all_users.count()
    host_count = UserProfile.objects.filter(role='Host').count()
    driver_count = UserProfile.objects.filter(role='Driver').count()
    admin_count = total_users_count - (host_count + driver_count)

    all_stations = ChargingStation.objects.all().select_related('host').order_by('-id')
    total_stations_count = all_stations.count()

    all_bookings = Booking.objects.all().select_related('driver', 'charging_station', 'availability_slot').order_by('-booking_time')
    total_bookings_count = all_bookings.count()
    confirmed_bookings = all_bookings.filter(status='Confirmed')
    confirmed_bookings_count = confirmed_bookings.count()
    cancelled_bookings_count = all_bookings.filter(status='Cancelled').count()

    total_revenue = confirmed_bookings.aggregate(Sum('total_cost'))['total_cost__sum'] or 0.00

    now = timezone.localtime() if timezone.is_aware(timezone.now()) else timezone.now()
    today = now.date()
    current_time = now.time()

    total_slots_count = AvailabilitySlot.objects.count()
    past_available_slots_count = AvailabilitySlot.objects.filter(
        status='Available'
    ).filter(
        Q(date__lt=today) |
        Q(date=today, end_time__lte=current_time)
    ).count()

    active_tab = request.GET.get('tab', 'stations')

    return render(request, 'admin_dashboard.html', {
        'total_revenue': total_revenue,
        'total_users_count': total_users_count,
        'host_count': host_count,
        'driver_count': driver_count,
        'admin_count': admin_count,
        'total_stations_count': total_stations_count,
        'total_bookings_count': total_bookings_count,
        'confirmed_bookings_count': confirmed_bookings_count,
        'cancelled_bookings_count': cancelled_bookings_count,
        'total_slots_count': total_slots_count,
        'past_available_slots_count': past_available_slots_count,
        'stations': all_stations,
        'bookings': all_bookings,
        'users': all_users,
        'active_tab': active_tab,
    })

@login_required
def admin_delete_station(request, station_id):
    if not is_admin_user(request.user):
        messages.error(request, 'Unauthorized access.')
        return redirect('home')
    station = get_object_or_404(ChargingStation, id=station_id)
    station_name = station.station_name
    station.delete()
    messages.success(request, f'Charging station "{station_name}" has been removed.')
    return redirect(f"{reverse('admin_dashboard')}?tab=stations")

@login_required
def admin_cleanup_past_slots(request):
    if not is_admin_user(request.user):
        messages.error(request, 'Unauthorized access.')
        return redirect('home')
    count = delete_past_available_slots()
    if count > 0:
        messages.success(request, f'Successfully cleared {count} expired past availability slot(s) across all stations.')
    else:
        messages.info(request, 'No expired availability slots found across the platform.')
    return redirect('admin_dashboard')

