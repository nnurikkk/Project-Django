"""
Models for the tenants app.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from simple_history.models import HistoricalRecords
from properties.models import Property

class Tenant(models.Model):
    """
    Tenant information model.
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20)
    date_of_birth = models.DateField(blank=True, null=True)
    ssn_last_four = models.CharField(max_length=4, blank=True, null=True, verbose_name="Last 4 digits of SSN")
    emergency_contact_name = models.CharField(max_length=200, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    employment_status = models.CharField(max_length=100, blank=True, null=True)
    employer = models.CharField(max_length=200, blank=True, null=True)
    income = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tenants')
    date_created = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def current_lease(self):
        """Return the current active lease for this tenant."""
        today = timezone.now().date()
        return self.leases.filter(
            start_date__lte=today,
            end_date__gte=today,
            status='active'
        ).first()
    
    @property
    def current_property(self):
        """Return the property where the tenant currently lives."""
        lease = self.current_lease
        if lease:
            return lease.property
        return None

class Lease(models.Model):
    """
    Lease agreement between property owner and tenant.
    """
    LEASE_STATUS = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
        ('renewed', 'Renewed'),
    )
    
    LEASE_TYPES = (
        ('fixed', 'Fixed Term'),
        ('month_to_month', 'Month to Month'),
        ('week_to_week', 'Week to Week'),
    )
    
    rental_property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='leases')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='leases')
    lease_type = models.CharField(max_length=20, choices=LEASE_TYPES, default='fixed')
    start_date = models.DateField()
    end_date = models.DateField()
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=LEASE_STATUS, default='pending')
    payment_day = models.PositiveSmallIntegerField(default=1, help_text="Day of the month rent is due")
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    grace_period = models.PositiveSmallIntegerField(default=5, help_text="Days after due date before late fee applies")
    is_security_deposit_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_leases')
    date_created = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()
    
    def __str__(self):
        return f"Lease for {self.property.name} - {self.tenant.full_name}"
    
    @property
    def is_active(self):
        today = timezone.now().date()
        return (
            self.status == 'active' and 
            self.start_date <= today and 
            self.end_date >= today
        )
    
    @property
    def lease_term_months(self):
        """Calculate the lease term in months."""
        months = (self.end_date.year - self.start_date.year) * 12
        months += (self.end_date.month - self.start_date.month)
        return months
    
    @property
    def days_until_expiration(self):
        """Return the number of days until lease expires."""
        if self.status != 'active':
            return 0
        
        today = timezone.now().date()
        if self.end_date < today:
            return 0
        
        return (self.end_date - today).days

class LeaseDocument(models.Model):
    """
    Documents associated with a lease (contract, addendums, etc.)
    """
    DOCUMENT_TYPES = (
        ('lease_agreement', 'Lease Agreement'),
        ('addendum', 'Addendum'),
        ('extension', 'Extension'),
        ('notice', 'Notice'),
        ('other', 'Other'),
    )
    
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='lease_documents/')
    notes = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_lease_documents')
    upload_date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.lease}"
