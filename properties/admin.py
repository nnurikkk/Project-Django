"""
Admin configuration for the properties app.
"""
from django.contrib import admin
from .models import Property, PropertyType, PropertyImage, PropertyDocument

class PropertyImageInline(admin.TabularInline):
    """Inline admin for PropertyImage."""
    model = PropertyImage
    extra = 1

class PropertyDocumentInline(admin.TabularInline):
    """Inline admin for PropertyDocument."""
    model = PropertyDocument
    extra = 1

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    """Admin configuration for the Property model."""
    list_display = ('name', 'owner', 'property_type', 'address', 'city', 'status', 'monthly_rent')
    list_filter = ('status', 'property_type', 'city', 'state')
    search_fields = ('name', 'address', 'city', 'owner__username')
    inlines = [PropertyImageInline, PropertyDocumentInline]
    list_per_page = 20
    date_hierarchy = 'date_created'
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'name', 'property_type', 'status')
        }),
        ('Property Details', {
            'fields': ('bedrooms', 'bathrooms', 'square_feet', 'year_built'),
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'zip_code', 'country'),
        }),
        ('Financial', {
            'fields': ('monthly_rent', 'security_deposit', 'acquisition_date', 'acquisition_price', 'current_value'),
        }),
        ('Additional Information', {
            'fields': ('description', 'amenities', 'notes'),
            'classes': ('collapse',),
        }),
    )

@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    """Admin configuration for the PropertyType model."""
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    """Admin configuration for the PropertyImage model."""
    list_display = ('rental_property', 'caption', 'is_primary', 'upload_date')
    list_filter = ('is_primary', 'upload_date')
    search_fields = ('property__name', 'caption')
    date_hierarchy = 'upload_date'

@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for the PropertyDocument model."""
    list_display = ('rental_property', 'document_type', 'title', 'upload_date')
    list_filter = ('document_type', 'upload_date')
    search_fields = ('property__name', 'title', 'notes')
    date_hierarchy = 'upload_date'
