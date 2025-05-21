"""
Admin configuration for the core app.
"""
from django.contrib import admin
from .models import Profile, Notification

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Admin configuration for the Profile model."""
    list_display = ('user', 'phone_number', 'company_name', 'date_created')
    search_fields = ('user__username', 'user__email', 'phone_number', 'company_name')
    list_filter = ('date_created',)
    date_hierarchy = 'date_created'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin configuration for the Notification model."""
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    date_hierarchy = 'created_at'
