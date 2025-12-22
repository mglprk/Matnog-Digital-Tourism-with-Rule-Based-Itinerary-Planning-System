from django.db import models
from django.conf import settings


class Feedback(models.Model):
    """User feedback and suggestions for the tourism portal."""

    CATEGORY_CHOICES = [
        ('general', 'General Feedback'),
        ('suggestion', 'Suggestion'),
        ('bug', 'Bug Report'),
        ('complaint', 'Complaint'),
        ('praise', 'Praise'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
        ('archived', 'Archived'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedbacks'
    )
    name = models.CharField(max_length=100, blank=True)  # For anonymous feedback
    email = models.EmailField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Internal notes for administrators")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Feedbacks'

    def __str__(self):
        return f"{self.subject} - {self.get_category_display()}"


class Announcement(models.Model):
    """Public announcements and news for the tourism portal."""

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    excerpt = models.TextField(max_length=500, blank=True, help_text="Short summary for listings")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    publish_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True, help_text="Leave blank for no expiry")
    author = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-publish_date', '-created_at']

    def __str__(self):
        return self.title



class Guest(models.Model):
    """Guests/visitors associated with destinations."""

    destination = models.ForeignKey(
        'destination.Destination',
        on_delete=models.CASCADE,
        related_name='guests'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guest_entries'
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True, help_text="Guest's home location")
    visit_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-visit_date', '-created_at']

    def __str__(self):
        return f"{self.name} - {self.destination.name}"