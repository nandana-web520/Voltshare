from django.contrib import admin
from .models import UserProfile, ChargingStation, AvailabilitySlot, Booking

admin.site.register(UserProfile)
admin.site.register(ChargingStation)
admin.site.register(AvailabilitySlot)
admin.site.register(Booking)
