from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('host/dashboard/', views.host_dashboard, name='host_dashboard'),
    path('host/add-station/', views.add_station, name='add_station'),
    path('host/station/<int:station_id>/availability/', views.manage_availability, name='manage_availability'),
    path('host/station/<int:station_id>/delete-past-slots/', views.delete_past_slots, name='delete_past_slots'),
    path('host/slot/<int:slot_id>/delete/', views.delete_slot, name='delete_slot'),
    path('search/', views.search_chargers, name='search_chargers'),
    path('charger/<int:station_id>/', views.charger_details, name='charger_details'),
    path('book/<int:slot_id>/', views.book_slot, name='book_slot'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('booking/<int:booking_id>/delete/', views.delete_booking, name='delete_booking'),
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/station/<int:station_id>/delete/', views.admin_delete_station, name='admin_delete_station'),
    path('admin-dashboard/cleanup-slots/', views.admin_cleanup_past_slots, name='admin_cleanup_past_slots'),
]
