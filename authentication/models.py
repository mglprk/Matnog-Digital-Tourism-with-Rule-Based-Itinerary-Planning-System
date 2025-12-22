from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    first_time_login = models.BooleanField(default=True)
    can_view_destinations = models.BooleanField(default=False)
    can_manage_destinations = models.BooleanField(default=False)
    can_view_accommodations = models.BooleanField(default=False)
    can_manage_accommodations = models.BooleanField(default=False)
    can_view_transportations = models.BooleanField(default=False)
    can_manage_transportations = models.BooleanField(default=False)
    can_view_announcements = models.BooleanField(default=False)
    can_manage_announcements = models.BooleanField(default=False)
    can_view_users = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
