"""
Admin configuration for the expenses app.
"""
from django.contrib import admin
from .models import ExpenseCategory, Vendor, Expense, ExpenseDocument

class ExpenseDocumentInline(admin.TabularInline):
    """Inline admin for ExpenseDocument."""
    model = ExpenseDocument
    extra = 1

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for the ExpenseCategory model."""
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    """Admin configuration for the Vendor model."""
    list_display = ('name', 'contact_person', 'email', 'phone', 'created_by')
    list_filter = ('created_by', 'date_created')
    search_fields = ('name', 'contact_person', 'email', 'phone', 'notes')
    date_hierarchy = 'date_created'

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """Admin configuration for the Expense model."""
    list_display = ('rental_property', 'category', 'vendor', 'amount', 'date', 'status', 'tax_deductible')
    list_filter = ('status', 'tax_deductible', 'date', 'is_recurring')
    search_fields = ('property__name', 'description', 'notes')
    date_hierarchy = 'date'
    inlines = [ExpenseDocumentInline]
    fieldsets = (
        ('Expense Details', {
            'fields': ('rental_property', 'category', 'vendor', 'amount', 'date', 'description')
        }),
        ('Status & Payment', {
            'fields': ('status', 'due_date', 'payment_date', 'payment_method', 'reference_number'),
        }),
        ('Recurring Settings', {
            'fields': ('is_recurring', 'recurring_frequency'),
            'classes': ('collapse',),
        }),
        ('Tax & Additional Information', {
            'fields': ('tax_deductible', 'notes', 'created_by'),
        }),
    )

@admin.register(ExpenseDocument)
class ExpenseDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for the ExpenseDocument model."""
    list_display = ('expense', 'document_type', 'title', 'upload_date')
    list_filter = ('document_type', 'upload_date')
    search_fields = ('expense__property__name', 'title', 'notes')
    date_hierarchy = 'upload_date'
