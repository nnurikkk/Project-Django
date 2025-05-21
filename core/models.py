"""
Core models for the rental income manager application.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Profile(models.Model):
    """
    Extension of the User model with additional information.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_pics', default='default_profile.jpg')
    date_created = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class Notification(models.Model):
    """
    System notifications for users.
    """
    NOTIFICATION_TYPES = (
        ('payment_due', 'Payment Due'),
        ('payment_received', 'Payment Received'),
        ('lease_expiring', 'Lease Expiring'),
        ('maintenance', 'Maintenance Required'),
        ('system', 'System Notification'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    related_link = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
