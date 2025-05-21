"""
Admin configuration for the payments app.
"""
from django.contrib import admin
from .models import PaymentCategory, Payment, LateFee

class LateFeeInline(admin.TabularInline):
    """Inline admin for LateFee."""
    model = LateFee
    extra = 0

@admin.register(PaymentCategory)
class PaymentCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for the PaymentCategory model."""
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin configuration for the Payment model."""
    list_display = ('rental_property', 'tenant', 'amount', 'due_date', 'payment_date', 'status')
    list_filter = ('status', 'payment_method', 'due_date', 'payment_date')
    search_fields = ('property__name', 'tenant__first_name', 'tenant__last_name', 'notes')
    date_hierarchy = 'due_date'
    inlines = [LateFeeInline]
    fieldsets = (
        ('Payment Details', {
            'fields': ('rental_property', 'tenant', 'lease', 'category', 'amount')
        }),
        ('Dates & Status', {
            'fields': ('due_date', 'payment_date', 'status'),
        }),
        ('Payment Method', {
            'fields': ('payment_method', 'reference_number'),
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by'),
        }),
    )

@admin.register(LateFee)
class LateFeeAdmin(admin.ModelAdmin):
    """Admin configuration for the LateFee model."""
    list_display = ('payment', 'amount', 'date_applied', 'waived')
    list_filter = ('waived', 'date_applied', 'waived_date')
    search_fields = ('payment__tenant__first_name', 'payment__tenant__last_name', 'reason', 'waived_reason')
    fieldsets = (
        ('Late Fee Details', {
            'fields': ('payment', 'amount', 'date_applied', 'reason')
        }),
        ('Waiver Information', {
            'fields': ('waived', 'waived_by', 'waived_date', 'waived_reason'),
            'classes': ('collapse',),
        }),
    )
