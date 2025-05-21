"""
Models for the properties app.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from simple_history.models import HistoricalRecords

class PropertyType(models.Model):
    """
    Types of rental properties (apartment, house, commercial, etc.)
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Property Types"
    
    def __str__(self):
        return self.name

class Property(models.Model):
    """
    Rental property model containing all property details.
    """
    PROPERTY_STATUS = (
        ('available', 'Available'),
        ('rented', 'Rented'),
        ('maintenance', 'Under Maintenance'),
        ('not_available', 'Not Available'),
    )
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    property_type = models.ForeignKey(PropertyType, on_delete=models.SET_NULL, null=True, related_name='properties')
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='United States')
    description = models.TextField(blank=True, null=True)
    bedrooms = models.PositiveSmallIntegerField(default=1)
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)
    square_feet = models.PositiveIntegerField(blank=True, null=True)
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PROPERTY_STATUS, default='available')
    amenities = models.TextField(blank=True, null=True)
    year_built = models.PositiveIntegerField(blank=True, null=True)
    acquisition_date = models.DateField(blank=True, null=True)
    acquisition_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    current_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()
    
    class Meta:
        verbose_name_plural = "Properties"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def is_rented(self):
        return self.status == 'rented'
    
    @property
    def annual_income_potential(self):
        return self.monthly_rent * 12
    
    @property
    def current_tenant(self):
        """Return the current tenant if property is rented."""
        current_lease = self.leases.filter(
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date(),
            status='active'
        ).first()
        
        if current_lease:
            return current_lease.tenant
        return None

class PropertyImage(models.Model):
    """
    Images associated with a property.
    """
    rental_property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/')
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    upload_date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Image for {self.property.name}"

class PropertyDocument(models.Model):
    """
    Documents associated with a property (deeds, contracts, etc.)
    """
    DOCUMENT_TYPES = (
        ('deed', 'Property Deed'),
        ('insurance', 'Insurance Document'),
        ('tax', 'Tax Document'),
        ('inspection', 'Inspection Report'),
        ('permit', 'Permit'),
        ('other', 'Other'),
    )
    
    rental_property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='property_documents/')
    notes = models.TextField(blank=True, null=True)
    upload_date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.property.name}"
