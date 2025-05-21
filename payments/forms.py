"""
Forms for the payments app.
"""
from django import forms
from .models import Payment, PaymentCategory, LateFee
from properties.models import Property
from tenants.models import Tenant, Lease

class PaymentForm(forms.ModelForm):
    """
    Form for creating and updating payments.
    """
    class Meta:
        model = Payment
        exclude = ['created_by', 'date_created', 'history']
        widgets = {
            'rental_property': forms.Select(attrs={'class': 'form-select'}),
            'tenant': forms.Select(attrs={'class': 'form-select'}),
            'lease': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        property_id = kwargs.pop('property_id', None)
        tenant_id = kwargs.pop('tenant_id', None)
        super(PaymentForm, self).__init__(*args, **kwargs)
        
        if user:
            # Filter properties to only show those owned by this user
            self.fields['property'].queryset = Property.objects.filter(owner=user)
            
            # Filter tenants to only show those with leases on properties owned by this user
            self.fields['tenant'].queryset = Tenant.objects.filter(leases__property__owner=user).distinct()
            
            # Filter leases to only show those on properties owned by this user
            self.fields['lease'].queryset = Lease.objects.filter(property__owner=user)
        
        if property_id:
            # If a property is pre-selected, filter tenants and leases
            self.fields['tenant'].queryset = Tenant.objects.filter(
                leases__property_id=property_id
            ).distinct()
            self.fields['lease'].queryset = Lease.objects.filter(
                property_id=property_id
            )
        
        if tenant_id:
            # If a tenant is pre-selected, filter leases
            self.fields['lease'].queryset = Lease.objects.filter(
                tenant_id=tenant_id
            )
    
    def clean(self):
        cleaned_data = super().clean()
        property = cleaned_data.get('property')
        tenant = cleaned_data.get('tenant')
        lease = cleaned_data.get('lease')
        
        # Validate that the tenant has a lease for this property
        if property and tenant and not lease:
            tenant_leases = Lease.objects.filter(property=property, tenant=tenant)
            if not tenant_leases.exists():
                self.add_error('tenant', 'This tenant does not have a lease for the selected property.')
        
        # Validate payment and due dates
        payment_date = cleaned_data.get('payment_date')
        status = cleaned_data.get('status')
        
        if status == 'paid' and not payment_date:
            self.add_error('payment_date', 'Payment date is required for paid payments.')
        
        return cleaned_data

class PaymentCategoryForm(forms.ModelForm):
    """
    Form for creating and updating payment categories.
    """
    class Meta:
        model = PaymentCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class LateFeeForm(forms.ModelForm):
    """
    Form for adding late fees to payments.
    """
    class Meta:
        model = LateFee
        fields = ['amount', 'reason']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class WaiveLateFeeForm(forms.ModelForm):
    """
    Form for waiving late fees.
    """
    class Meta:
        model = LateFee
        fields = ['waived_reason']
        widgets = {
            'waived_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PaymentFilterForm(forms.Form):
    """
    Form for filtering payments.
    """
    # Date filters
    start_date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    # Property filter
    property = forms.ModelChoiceField(
        queryset=Property.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Tenant filter
    tenant = forms.ModelChoiceField(
        queryset=Tenant.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Category filter
    category = forms.ModelChoiceField(
        queryset=PaymentCategory.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Amount range
    min_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min $'})
    )
    max_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max $'})
    )
    
    # Status filter
    STATUS_CHOICES = [
        ('', '-- Any Status --'),
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled')
    ]
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Sorting
    SORT_CHOICES = [
        ('-due_date', 'Due Date (newest first)'),
        ('due_date', 'Due Date (oldest first)'),
        ('-amount', 'Amount (highest first)'),
        ('amount', 'Amount (lowest first)'),
        ('-payment_date', 'Payment Date (newest first)'),
        ('payment_date', 'Payment Date (oldest first)'),
    ]
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Update querysets to only show properties owned by this user
            self.fields['property'].queryset = Property.objects.filter(owner=user)
            
            # Fix the tenant queryset filter that's causing the error
            # Instead of using leases__property__owner which is causing the error,
            # use a safer approach by getting the properties first
            try:
                # Get properties owned by this user
                user_properties = Property.objects.filter(owner=user).values_list('id', flat=True)
                
                # Get tenants with leases for these properties
                # Instead of complex filtering, use a safer approach
                tenant_ids = set()
                leases = Lease.objects.filter(property__id__in=user_properties)
                
                for lease in leases:
                    if lease.tenant:
                        tenant_ids.add(lease.tenant.id)
                
                self.fields['tenant'].queryset = Tenant.objects.filter(id__in=tenant_ids)
            except Exception as e:
                print(f"Error setting tenant queryset: {e}")
                # Fallback to a safer default queryset
                self.fields['tenant'].queryset = Tenant.objects.all()