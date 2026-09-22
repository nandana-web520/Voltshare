from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile, ChargingStation, AvailabilitySlot, Booking
import datetime

class RoleAndLogicalFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create Host
        self.host_user = User.objects.create_user(username='testhost', password='password123')
        self.host_profile = UserProfile.objects.create(user=self.host_user, role='Host')

        # Create Driver
        self.driver_user = User.objects.create_user(username='testdriver', password='password123')
        self.driver_profile = UserProfile.objects.create(user=self.driver_user, role='Driver')

        # Create Station & Slot
        self.station = ChargingStation.objects.create(
            host=self.host_user,
            station_name="GreenCharge Central",
            location="Downtown",
            plug_type="Type 2",
            power_output=22.0,
            price_per_hour=150.00
        )
        self.slot = AvailabilitySlot.objects.create(
            charging_station=self.station,
            date=datetime.date.today(),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),
            status="Available"
        )

    def test_guest_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Register as Host')
        self.assertContains(response, 'Find a Charger')

    def test_host_home_view(self):
        self.client.login(username='testhost', password='password123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Host Dashboard')
        self.assertNotContains(response, 'Become a Host')
        self.assertNotContains(response, 'Register as Host')
        self.assertNotContains(response, 'Find Chargers')
        self.assertNotContains(response, 'Browse Chargers')

    def test_driver_home_view(self):
        self.client.login(username='testdriver', password='password123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Find EV Chargers')
        self.assertContains(response, 'My Bookings')
        self.assertNotContains(response, 'Become a Host')
        self.assertNotContains(response, 'Register as Host')

    def test_login_redirection_by_role(self):
        # Host login redirection
        response_host = self.client.post(reverse('login'), {'username': 'testhost', 'password': 'password123'})
        self.assertRedirects(response_host, reverse('host_dashboard'))

        # Logout before testing driver login
        self.client.logout()

        # Driver login redirection
        response_driver = self.client.post(reverse('login'), {'username': 'testdriver', 'password': 'password123'})
        self.assertRedirects(response_driver, reverse('driver_dashboard'))

    def test_driver_cannot_access_host_pages(self):
        self.client.login(username='testdriver', password='password123')
        # Cannot access host dashboard
        resp1 = self.client.get(reverse('host_dashboard'))
        self.assertRedirects(resp1, reverse('home'))

        # Cannot access add station
        resp2 = self.client.get(reverse('add_station'))
        self.assertRedirects(resp2, reverse('home'))

        # Cannot access manage availability
        resp3 = self.client.get(reverse('manage_availability', args=[self.station.id]))
        self.assertRedirects(resp3, reverse('home'))

    def test_host_cannot_book_slot(self):
        self.client.login(username='testhost', password='password123')
        response = self.client.get(reverse('book_slot', args=[self.slot.id]))
        self.assertRedirects(response, reverse('search_chargers'))
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.status, 'Available')

    def test_driver_booking_and_cancellation(self):
        self.client.login(username='testdriver', password='password123')
        # Book slot
        book_resp = self.client.get(reverse('book_slot', args=[self.slot.id]))
        self.assertRedirects(book_resp, reverse('charger_details', args=[self.station.id]))
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.status, 'Booked')

        # Cancel booking
        booking = Booking.objects.get(driver=self.driver_user, availability_slot=self.slot)
        cancel_resp = self.client.post(reverse('cancel_booking', args=[booking.id]))
        self.assertRedirects(cancel_resp, reverse('driver_dashboard'))
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.status, 'Available')

    def test_delete_cancelled_booking(self):
        self.client.login(username='testdriver', password='password123')
        booking = Booking.objects.create(
            driver=self.driver_user,
            charging_station=self.station,
            availability_slot=self.slot,
            total_cost=150.00,
            status='Cancelled'
        )
        del_resp = self.client.post(reverse('delete_booking', args=[booking.id]))
        self.assertRedirects(del_resp, reverse('driver_dashboard'))
        self.assertFalse(Booking.objects.filter(id=booking.id).exists())

    def test_delete_past_available_slots_function(self):
        from charging.views import delete_past_available_slots
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        future_date = today + datetime.timedelta(days=2)

        # Past available slot (should be deleted)
        past_slot = AvailabilitySlot.objects.create(
            charging_station=self.station,
            date=yesterday,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(10, 0),
            status="Available"
        )
        # Past booked slot (should NOT be deleted to preserve booking history)
        past_booked_slot = AvailabilitySlot.objects.create(
            charging_station=self.station,
            date=yesterday,
            start_time=datetime.time(11, 0),
            end_time=datetime.time(12, 0),
            status="Booked"
        )
        # Future available slot (should NOT be deleted)
        future_slot = AvailabilitySlot.objects.create(
            charging_station=self.station,
            date=future_date,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(10, 0),
            status="Available"
        )

        deleted = delete_past_available_slots(station=self.station)
        self.assertGreaterEqual(deleted, 1)
        self.assertFalse(AvailabilitySlot.objects.filter(id=past_slot.id).exists())
        self.assertTrue(AvailabilitySlot.objects.filter(id=past_booked_slot.id).exists())
        self.assertTrue(AvailabilitySlot.objects.filter(id=future_slot.id).exists())

    def test_delete_past_slots_view_by_host(self):
        self.client.login(username='testhost', password='password123')
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        past_slot = AvailabilitySlot.objects.create(
            charging_station=self.station,
            date=yesterday,
            start_time=datetime.time(8, 0),
            end_time=datetime.time(9, 0),
            status="Available"
        )
        resp = self.client.get(reverse('delete_past_slots', args=[self.station.id]))
        self.assertRedirects(resp, reverse('manage_availability', args=[self.station.id]))
        self.assertFalse(AvailabilitySlot.objects.filter(id=past_slot.id).exists())

    def test_add_daily_recurring_availability(self):
        self.client.login(username='testhost', password='password123')
        start_d = datetime.date.today() + datetime.timedelta(days=5)
        end_d = start_d + datetime.timedelta(days=2) # 3 days total
        
        post_data = {
            'recurrence_type': 'daily',
            'start_date': start_d.strftime('%Y-%m-%d'),
            'end_date': end_d.strftime('%Y-%m-%d'),
            'start_time': '10:00',
            'end_time': '13:00', # 3 hours per day = 3 slots per day * 3 days = 9 slots
        }
        resp = self.client.post(reverse('manage_availability', args=[self.station.id]), post_data)
        self.assertRedirects(resp, reverse('manage_availability', args=[self.station.id]))

        created_slots = AvailabilitySlot.objects.filter(
            charging_station=self.station,
            date__gte=start_d,
            date__lte=end_d
        )
        self.assertEqual(created_slots.count(), 9)

    def test_add_specific_days_availability(self):
        self.client.login(username='testhost', password='password123')
        # Pick next Monday
        today = datetime.date.today()
        days_ahead = (0 - today.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        monday = today + datetime.timedelta(days=days_ahead)
        sunday = monday + datetime.timedelta(days=6) # 1 full week

        post_data = {
            'recurrence_type': 'custom',
            'start_date': monday.strftime('%Y-%m-%d'),
            'end_date': sunday.strftime('%Y-%m-%d'),
            'days_of_week': ['0', '2'], # Monday (0) and Wednesday (2)
            'start_time': '14:00',
            'end_time': '16:00', # 2 hours per day = 2 slots per day * 2 days = 4 slots
        }
        resp = self.client.post(reverse('manage_availability', args=[self.station.id]), post_data)
        self.assertRedirects(resp, reverse('manage_availability', args=[self.station.id]))

        created_slots = AvailabilitySlot.objects.filter(
            charging_station=self.station,
            date__gte=monday,
            date__lte=sunday,
            start_time=datetime.time(14, 0)
        )
        self.assertEqual(created_slots.count(), 2) # One on Monday, one on Wednesday

    def test_admin_dashboard_access_control(self):
        # Driver cannot access admin dashboard
        self.client.login(username='testdriver', password='password123')
        resp_driver = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(resp_driver, reverse('home'))

        # Host cannot access admin dashboard
        self.client.login(username='testhost', password='password123')
        resp_host = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(resp_host, reverse('home'))

        # Create Admin user
        admin_user = User.objects.create_user(username='testadmin', password='password123', is_staff=True)
        UserProfile.objects.create(user=admin_user, role='Admin')

        self.client.login(username='testadmin', password='password123')
        resp_admin = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(resp_admin.status_code, 200)
        self.assertContains(resp_admin, 'VoltShare Admin Dashboard')
        self.assertContains(resp_admin, 'Platform Revenue')
        self.assertContains(resp_admin, 'GreenCharge Central')

    def test_admin_delete_station(self):
        admin_user = User.objects.create_user(username='superadmin', password='password123', is_superuser=True)
        self.client.login(username='superadmin', password='password123')

        resp = self.client.get(reverse('admin_delete_station', args=[self.station.id]))
        self.assertRedirects(resp, f"{reverse('admin_dashboard')}?tab=stations")
        self.assertFalse(ChargingStation.objects.filter(id=self.station.id).exists())


