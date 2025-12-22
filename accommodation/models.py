from django.db import models
from django.utils import timezone
from destination.models import Destination  # assuming you already have a Destination model


class Accommodation(models.Model):
    ACCOMMODATION_TYPES = [
        ('hotel', 'Hotel'),
        ('resort', 'Resort'),
        ('inn', 'Inn'),
        ('homestay', 'Homestay'),
        ('hostel', 'Hostel'),
        ('bnb', 'Bed & Breakfast'),
        ('others', 'Others'),
    ]

    BUDGET_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('closed', 'Temporarily Closed'),
    ]

    # --- Basic Info ---
    name = models.CharField(max_length=255, )
    type = models.CharField(max_length=50, choices=ACCOMMODATION_TYPES)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='accommodations/', blank=True, null=True)
    contact_number = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    budget_category = models.CharField(max_length=10, choices=BUDGET_CHOICES, default='low')


    # --- Location ---
    address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=17, decimal_places=15, blank=True, null=True)
    longitude = models.DecimalField(max_digits=17, decimal_places=14, blank=True, null=True)


    # --- Facilities & Accessibility ---
    parking_available = models.BooleanField(default=False)
    wifi_available = models.BooleanField(default=False)
    breakfast_included = models.BooleanField(default=False)
    air_conditioned = models.BooleanField(default=False)
    wheelchair_friendly = models.BooleanField(default=False)
    pet_friendly = models.BooleanField(default=False)

    # --- Management ---
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Accommodation"
        verbose_name_plural = "Accommodations"

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class AccommodationImage(models.Model):
    accommodation = models.ForeignKey(
        Accommodation,
        on_delete=models.CASCADE,
        related_name='additional_images'
    )
    image = models.ImageField(upload_to="accommodations/gallery/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Image for {self.accommodation.name}"