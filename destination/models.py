from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Destination(models.Model):
    CATEGORY_CHOICES = [
        ('nature', 'Nature'),
        ('cultural', 'Cultural'),
        ('historical', 'Historical'),
        ('food', 'Food'),
        ('adventure', 'Adventure'),
        ('shopping', 'Shopping'),
        ('other', 'Other'),
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
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="destinations/", blank=True, null=True)

    # --- Location ---
    address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=17, decimal_places=15, blank=True, null=True)
    longitude = models.DecimalField(max_digits=17, decimal_places=14, blank=True, null=True)

    # --- Time Info ---
    opening_time = models.TimeField(blank=True, null=True)
    closing_time = models.TimeField(blank=True, null=True)
    best_time_to_visit = models.CharField(max_length=100, blank=True, null=True)
    avg_duration_minutes = models.PositiveIntegerField(default=60)

    # --- Budget Info ---
    entrance_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    other_costs = models.TextField(blank=True, null=True)
    budget_category = models.CharField(max_length=10, choices=BUDGET_CHOICES, default='low')

    # --- Travel Info ---
    nearest_transport = models.CharField(max_length=255, blank=True, null=True)
    estimated_travel_time_minutes = models.PositiveIntegerField(blank=True, null=True)

    # --- Facilities & Accessibility ---
    parking_available = models.BooleanField(default=False)
    wheelchair_friendly = models.BooleanField(default=False)
    kid_friendly = models.BooleanField(default=False)
    senior_friendly = models.BooleanField(default=False)

    # --- Management ---
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_all_images(self):
        """Returns list of all images (primary + additional)"""
        images = []
        if self.image:
            images.append({
                'url': self.image.url,
                'is_primary': True,
                'id': None
            })
        for img in self.additional_images.all():
            images.append({
                'url': img.image.url,
                'is_primary': False,
                'id': img.id
            })
        return images


class DestinationImage(models.Model):
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name='additional_images'
    )
    image = models.ImageField(upload_to="destinations/gallery/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Image for {self.destination.name}"