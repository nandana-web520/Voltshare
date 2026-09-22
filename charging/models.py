from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('Host', 'Host (Charger Owner)'),
        ('Driver', 'Driver'),
        ('Admin', 'Admin (Platform Manager)'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Driver')

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class ChargingStation(models.Model):
    PLUG_CHOICES = (
        ('Type 1', 'Type 1'),
        ('Type 2', 'Type 2'),
        ('CCS', 'CCS'),
        ('CHAdeMO', 'CHAdeMO'),
    )
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charging_stations')
    station_name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    plug_type = models.CharField(max_length=20, choices=PLUG_CHOICES)
    power_output = models.DecimalField(max_digits=5, decimal_places=1, help_text="Power in kW")
    price_per_hour = models.DecimalField(max_digits=6, decimal_places=2, help_text="Price in ₹")

    def __str__(self):
        return f"{self.station_name} - {self.location}"

class AvailabilitySlot(models.Model):
    STATUS_CHOICES = (
        ('Available', 'Available'),
        ('Booked', 'Booked'),
    )
    charging_station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='availability_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Available')

    def __str__(self):
        return f"{self.charging_station.station_name} - {self.date} ({self.start_time} to {self.end_time})"

class Booking(models.Model):
    STATUS_CHOICES = (
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
    )
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    charging_station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE)
    availability_slot = models.ForeignKey(AvailabilitySlot, on_delete=models.CASCADE)
    booking_time = models.DateTimeField(auto_now_add=True)
    total_cost = models.DecimalField(max_digits=7, decimal_places=2, default=0.00)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Confirmed')

    def __str__(self):
        return f"Booking {self.id} by {self.driver.username}"

