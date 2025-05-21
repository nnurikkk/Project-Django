"""
Models for the payments app.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from simple_history.models import HistoricalRecords
from properties.models import Property
from tenants.models import Tenant, Lease

class PaymentCategory(models.Model):
    """
    Categories for incoming payments (rent, fees, deposits, etc.)
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Payment Categories"
    
    def __str__(self):
        return self.name

class Payment(models.Model):
    """
    Payments received from tenants.
    """
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('late', 'Late'),
        ('declined', 'Declined'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('venmo', 'Venmo'),
        ('zelle', 'Zelle'),
        ('other', 'Other'),
    )
    
    rental_property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='payments')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='payments')
    lease = models.ForeignKey(Lease, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    category = models.ForeignKey(PaymentCategory, on_delete=models.SET_NULL, null=True, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True, blank=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_payments')
    date_created = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()
    
    class Meta:
        ordering = ['-due_date', '-payment_date']
    
    def __str__(self):
        return f"Payment of ${self.amount} - {self.tenant.full_name} - {self.rental_property.name}"
    
    @property
    def is_overdue(self):
        if self.status == 'paid' or not self.due_date:
            return False
        return self.due_date < timezone.now().date()
    
    @property
    def days_overdue(self):
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.due_date).days

class LateFee(models.Model):
    """
    Late fees applied to payments.
    """
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='late_fees')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_applied = models.DateField(default=timezone.now)
    reason = models.TextField(blank=True, null=True)
    waived = models.BooleanField(default=False)
    waived_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='waived_fees')
    waived_date = models.DateField(null=True, blank=True)
    waived_reason = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_late_fees')
    
    def __str__(self):
        status = "Waived" if self.waived else "Active"
        return f"Late Fee ${self.amount} for {self.payment} - {status}"
