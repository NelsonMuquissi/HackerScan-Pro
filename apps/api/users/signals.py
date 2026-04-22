"""
Django signals for the users app.
Creates UserProfile automatically after each User is saved for the first time.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance: User, created: bool, **kwargs):
    """Ensure every user has a profile from day one."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
