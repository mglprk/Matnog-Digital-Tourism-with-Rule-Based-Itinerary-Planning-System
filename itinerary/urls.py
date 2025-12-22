from django.urls import path
from . import views

app_name = 'itinerary'

urlpatterns = [
    # Function-based view (recommended for simple use)
    path('generate/', views.generate_itinerary, name='generate'),

    # Class-based view (alternative)
    # path('generate/', views.GenerateItineraryView.as_view(), name='generate'),

    path('', views.home, name='home'),
    path('destinations/', views.destinations, name='public-destinations'),
    path('destinations/<int:pk>/', views.destination_detail, name='public-destination-detail'),

    path('accommodations/', views.accommodations, name='public-accommodations'),
    path('accommodations/<int:pk>/', views.accommodation_detail, name='public-accommodation-detail'),

    path('transportations/', views.transportation, name='public-transportations'),
    path('announcements/', views.announcements, name='public-announcements'),
    path('announcements/<int:pk>/', views.announcement_detail, name='public-announcement_detail'),
    path('about/', views.about, name='about'),
    path('plan-trip/', views.plan_trip, name='plan_trip'),
]

