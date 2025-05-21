"""
Forms for the tenants app.
"""
from django import forms
from django.utils import timezone
from .models import Tenant, Lease, LeaseDocument
from properties.models import Property

class TenantForm(forms.ModelForm):
    """
    Form for creating and updating tenants.
    """
    class Meta:
        model = Tenant
        exclude = ['created_by', 'date_created', 'history']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'ssn_last_four': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'employment_status': forms.TextInput(attrs={'class': 'form-control'}),
            'employer': forms.TextInput(attrs={'class': 'form-control'}),
            'income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_ssn_last_four(self):
        """Validate the last 4 digits of SSN."""
        ssn_last_four = self.cleaned_data.get('ssn_last_four')
        if ssn_last_four and not ssn_last_four.isdigit():
            raise forms.ValidationError("SSN must contain only digits.")
        if ssn_last_four and len(ssn_last_four) != 4:
            raise forms.ValidationError("Please enter exactly the last 4 digits of the SSN.")
        return ssn_last_four
    
    def clean_phone(self):
        """Clean phone number."""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove non-digit characters
            phone = ''.join(c for c in phone if c.isdigit())
            # Ensure it's a valid length
            if len(phone) < 10:
                raise forms.ValidationError("Please enter a valid phone number with at least 10 digits.")
        return phone

class LeaseForm(forms.ModelForm):
    """
    Form for creating and updating leases.
    """
    class Meta:
        model = Lease
        exclude = ['created_by', 'date_created', 'history']
        widgets = {
            'property': forms.Select(attrs={'class': 'form-select'}),
            'tenant': forms.Select(attrs={'class': 'form-select'}),
            'lease_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'rent_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'security_deposit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'payment_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '31'}),
            'late_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'grace_period': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_security_deposit_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        property_id = kwargs.pop('property_id', None)
        tenant_id = kwargs.pop('tenant_id', None)
        super(LeaseForm, self).__init__(*args, **kwargs)
        
        if user:
            # Filter properties to only show those owned by this user
            self.fields['property'].queryset = Property.objects.filter(owner=user)
        
        if property_id:
            # If a property is pre-selected, set it as initial value
            self.initial['property'] = property_id
            # Also set initial rent amount and security deposit based on property
            try:
                property_obj = Property.objects.get(id=property_id, owner=user)
                self.initial['rent_amount'] = property_obj.monthly_rent
                self.initial['security_deposit'] = property_obj.security_deposit
            except Property.DoesNotExist:
                pass
        
        if tenant_id:
            # If a tenant is pre-selected, set it as initial value
            self.initial['tenant'] = tenant_id
    
    def clean(self):
        """Validate the lease form."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        property_obj = cleaned_data.get('property')
        tenant = cleaned_data.get('tenant')
        status = cleaned_data.get('status')
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', "End date cannot be before start date.")
        
        # If lease is active, check if property is already rented by another active lease
        if status == 'active' and property_obj:
            existing_leases = Lease.objects.filter(
                property=property_obj,
                status='active',
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            
            # Exclude the current lease if updating
            if self.instance.pk:
                existing_leases = existing_leases.exclude(pk=self.instance.pk)
            
            if existing_leases.exists():
                self.add_error('status', "This property already has an active lease for this date range.")
        
        # Validate property status if lease is active
        if status == 'active' and property_obj and property_obj.status != 'rented':
            self.add_error('property', "The property status should be 'Rented' for an active lease.")
        
        # Check if tenant already has an active lease
        if status == 'active' and tenant:
            existing_tenant_leases = Lease.objects.filter(
                tenant=tenant,
                status='active',
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            
            # Exclude the current lease if updating
            if self.instance.pk:
                existing_tenant_leases = existing_tenant_leases.exclude(pk=self.instance.pk)
            
            if existing_tenant_leases.exists():
                self.add_error('tenant', "This tenant already has an active lease for this date range.")
        
        return cleaned_data

class LeaseDocumentForm(forms.ModelForm):
    """
    Form for adding documents to a lease.
    """
    class Meta:
        model = LeaseDocument
        fields = ['document_type', 'title', 'file', 'notes']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class LeaseFilterForm(forms.Form):
    """
    Form for filtering leases.
    """
    SORT_CHOICES = (
        ('start_date', 'Start Date (oldest first)'),
        ('-start_date', 'Start Date (newest first)'),
        ('end_date', 'End Date (oldest first)'),
        ('-end_date', 'End Date (newest first)'),
        ('rent_amount', 'Rent Amount (lowest first)'),
        ('-rent_amount', 'Rent Amount (highest first)'),
    )

    property = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Properties",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tenant = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Tenants",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Lease.LEASE_STATUS),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    lease_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Lease.LEASE_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    start_date_after = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    start_date_before = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    end_date_after = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    end_date_before = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    min_rent = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    max_rent = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-start_date',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(LeaseFilterForm, self).__init__(*args, **kwargs)
        
        if user:
            # Only show properties owned by this user
            self.fields['property'].queryset = Property.objects.filter(owner=user)
            
            # Only show tenants with leases on properties owned by this user
            self.fields['tenant'].queryset = Tenant.objects.filter(leases__property__owner=user).distinct()

class TenantFilterForm(forms.Form):
    """
    Form for filtering tenants.
    """
    SORT_CHOICES = (
        ('last_name', 'Last Name (A-Z)'),
        ('-last_name', 'Last Name (Z-A)'),
        ('date_created', 'Date Added (oldest first)'),
        ('-date_created', 'Date Added (newest first)'),
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email, or phone'
        })
    )
    
    property = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Properties",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    has_active_lease = forms.ChoiceField(
        choices=[
            ('', 'All Tenants'),
            ('yes', 'With Active Lease'),
            ('no', 'Without Active Lease')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='last_name',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TenantFilterForm, self).__init__(*args, **kwargs)
        
        if user:
            # Only show properties owned by this user
            self.fields['property'].queryset = Property.objects.filter(owner=user)
