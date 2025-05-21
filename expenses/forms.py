"""
Forms for the expenses app.
"""
from django import forms
from .models import Expense, ExpenseCategory, Vendor, ExpenseDocument

class ExpenseForm(forms.ModelForm):
    """
    Form for creating and updating expenses.
    """
    class Meta:
        model = Expense
        exclude = ['created_by', 'date_created', 'history']
        widgets = {
            'property': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'vendor': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recurring_frequency': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_deductible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ExpenseCategoryForm(forms.ModelForm):
    """
    Form for creating and updating expense categories.
    """
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class VendorForm(forms.ModelForm):
    """
    Form for creating and updating vendors.
    """
    class Meta:
        model = Vendor
        exclude = ['created_by', 'date_created']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ExpenseDocumentForm(forms.ModelForm):
    """
    Form for adding documents to an expense.
    """
    class Meta:
        model = ExpenseDocument
        fields = ['document_type', 'title', 'file', 'notes']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ExpenseFilterForm(forms.Form):
    """
    Form for filtering expenses.
    """
    SORT_CHOICES = (
        ('date', 'Date (newest first)'),
        ('-date', 'Date (oldest first)'),
        ('amount', 'Amount (lowest first)'),
        ('-amount', 'Amount (highest first)'),
    )

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    property = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    vendor = forms.ModelChoiceField(
        queryset=Vendor.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    min_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    max_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All')] + list(Expense.EXPENSE_STATUS),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    tax_deductible = forms.NullBooleanField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}, choices=[
            ('', 'All'),
            ('true', 'Yes'),
            ('false', 'No')
        ])
    )
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='date',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ExpenseFilterForm, self).__init__(*args, **kwargs)
        
        if user:
            # Only show properties owned by this user
            from properties.models import Property
            self.fields['property'].queryset = Property.objects.filter(owner=user)
