"""
Admin configuration for the tenants app.
"""
from django.contrib import admin
from .models import Tenant, Lease, LeaseDocument

class LeaseDocumentInline(admin.TabularInline):
    """Inline admin for LeaseDocument."""
    model = LeaseDocument
    extra = 1

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Admin configuration for the Tenant model."""
    list_display = ('full_name', 'email', 'phone', 'created_by', 'date_created')
    list_filter = ('created_by', 'date_created')
    search_fields = ('first_name', 'last_name', 'email', 'phone')
    date_hierarchy = 'date_created'
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'date_of_birth', 'ssn_last_four')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone'),
        }),
        ('Employment Information', {
            'fields': ('employment_status', 'employer', 'income'),
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by'),
        }),
    )
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Name'

@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    """Admin configuration for the Lease model."""
    list_display = ('rental_property', 'tenant', 'lease_type', 'start_date', 'end_date', 'status', 'rent_amount')
    list_filter = ('status', 'lease_type', 'start_date', 'end_date')
    search_fields = ('property__name', 'tenant__first_name', 'tenant__last_name')
    date_hierarchy = 'start_date'
    inlines = [LeaseDocumentInline]
    fieldsets = (
        ('Lease Details', {
            'fields': ('rental_property', 'tenant', 'lease_type', 'start_date', 'end_date', 'status')
        }),
        ('Financial', {
            'fields': ('rent_amount', 'security_deposit', 'is_security_deposit_paid'),
        }),
        ('Payment Terms', {
            'fields': ('payment_day', 'late_fee', 'grace_period'),
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by'),
        }),
    )

@admin.register(LeaseDocument)
class LeaseDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for the LeaseDocument model."""
    list_display = ('lease', 'document_type', 'title', 'upload_date')
    list_filter = ('document_type', 'upload_date')
    search_fields = ('lease__property__name', 'lease__tenant__first_name', 'lease__tenant__last_name', 'title')
    date_hierarchy = 'upload_date'
