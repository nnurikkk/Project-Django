"""
Models for the expenses app.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from simple_history.models import HistoricalRecords
from properties.models import Property

class ExpenseCategory(models.Model):
    """
    Categories for expenses (repairs, taxes, insurance, etc.)
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Expense Categories"
    
    def __str__(self):
        return self.name

class Vendor(models.Model):
    """
    Vendors or service providers who perform work on properties.
    """
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_vendors')
    date_created = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name

class Expense(models.Model):
    """
    Expenses related to properties.
    """
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('other', 'Other'),
    )
    
    EXPENSE_STATUS = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('cancelled', 'Cancelled'),
    )
    
    rental_property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, related_name='expenses')
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True, blank=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=EXPENSE_STATUS, default='pending')
    is_recurring = models.BooleanField(default=False)
    recurring_frequency = models.CharField(max_length=50, blank=True, null=True)
    tax_deductible = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_expenses')
    date_created = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"${self.amount} - {self.description} - {self.property.name}"
    
    @property
    def is_overdue(self):
        if self.status == 'paid' or not self.due_date:
            return False
        return self.due_date < timezone.now().date()

class ExpenseDocument(models.Model):
    """
    Documents associated with expenses (receipts, invoices, etc.)
    """
    DOCUMENT_TYPES = (
        ('receipt', 'Receipt'),
        ('invoice', 'Invoice'),
        ('quote', 'Quote'),
        ('contract', 'Contract'),
        ('other', 'Other'),
    )
    
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='expense_documents/')
    notes = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_expense_documents')
    upload_date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.expense}"
