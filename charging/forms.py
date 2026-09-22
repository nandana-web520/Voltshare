import datetime
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, ChargingStation, AvailabilitySlot

class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

class ChargingStationForm(forms.ModelForm):
    class Meta:
        model = ChargingStation
        fields = ['station_name', 'location', 'plug_type', 'power_output', 'price_per_hour']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class AvailabilitySlotForm(forms.Form):
    RECURRENCE_CHOICES = (
        ('single', 'Single Date'),
        ('daily', 'Daily (Every Day in Range)'),
        ('weekdays', 'Weekdays Only (Mon - Fri)'),
        ('weekends', 'Weekends Only (Sat - Sun)'),
        ('custom', 'Specific Days of the Week'),
    )

    DAY_CHOICES = (
        ('0', 'Mon'),
        ('1', 'Tue'),
        ('2', 'Wed'),
        ('3', 'Thu'),
        ('4', 'Fri'),
        ('5', 'Sat'),
        ('6', 'Sun'),
    )

    recurrence_type = forms.ChoiceField(
        choices=RECURRENCE_CHOICES,
        initial='single',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_recurrence_type'})
    )
    single_date = forms.DateField(
        required=False,
        label="Date",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_single_date'})
    )
    start_date = forms.DateField(
        required=False,
        label="Start Date",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_start_date'})
    )
    end_date = forms.DateField(
        required=False,
        label="End Date",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_end_date'})
    )
    days_of_week = forms.MultipleChoiceField(
        required=False,
        choices=DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'day-checkbox'}),
        label="Select Days"
    )
    start_time = forms.TimeField(
        label="Start Time",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'id': 'id_start_time'})
    )
    end_time = forms.TimeField(
        label="End Time",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'id': 'id_end_time'})
    )

    def clean(self):
        cleaned_data = super().clean()
        rec_type = cleaned_data.get('recurrence_type')
        single_date = cleaned_data.get('single_date')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        days = cleaned_data.get('days_of_week')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if rec_type == 'single':
            if not single_date:
                self.add_error('single_date', 'Please select a date.')
        else:
            if not start_date:
                self.add_error('start_date', 'Please select a start date.')
            if not end_date:
                self.add_error('end_date', 'Please select an end date.')
            if start_date and end_date:
                if start_date > end_date:
                    self.add_error('end_date', 'End date cannot be earlier than start date.')
                elif (end_date - start_date).days > 90:
                    self.add_error('end_date', 'Date range cannot exceed 90 days.')

            if rec_type == 'custom' and not days:
                self.add_error('days_of_week', 'Please select at least one day of the week.')

        if start_time and end_time and start_time >= end_time:
            self.add_error('end_time', 'End time must be after start time.')

        return cleaned_data

    def get_target_dates(self):
        rec_type = self.cleaned_data.get('recurrence_type')
        if rec_type == 'single':
            return [self.cleaned_data['single_date']]

        start_date = self.cleaned_data['start_date']
        end_date = self.cleaned_data['end_date']
        target_dates = []
        curr = start_date
        while curr <= end_date:
            weekday = curr.weekday()  # 0 is Mon, 6 is Sun
            if rec_type == 'daily':
                target_dates.append(curr)
            elif rec_type == 'weekdays' and weekday in [0, 1, 2, 3, 4]:
                target_dates.append(curr)
            elif rec_type == 'weekends' and weekday in [5, 6]:
                target_dates.append(curr)
            elif rec_type == 'custom':
                selected_days = [int(x) for x in self.cleaned_data.get('days_of_week', [])]
                if weekday in selected_days:
                    target_dates.append(curr)
            curr += datetime.timedelta(days=1)
        return target_dates
