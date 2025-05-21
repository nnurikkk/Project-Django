"""
Views for the properties app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.forms import modelformset_factory
from django.http import JsonResponse
from .models import Property, PropertyType, PropertyImage, PropertyDocument
from .forms import PropertyForm, PropertyImageForm, PropertyDocumentForm
from tenants.models import Lease
from payments.models import Payment

class PropertyListView(LoginRequiredMixin, ListView):
    """
    Display a list of properties with filtering options.
    """
    model = Property
    template_name = 'properties/property_list.html'
    context_object_name = 'properties'
    paginate_by = 9
    
    def get_queryset(self):
        """Filter properties based on query parameters."""
        queryset = Property.objects.filter(owner=self.request.user)
        
        # Apply filters if provided
        status = self.request.GET.get('status')
        property_type = self.request.GET.get('property_type')
        city = self.request.GET.get('city')
        bedrooms = self.request.GET.get('bedrooms')
        
        if status:
            queryset = queryset.filter(status=status)
        
        if property_type:
            queryset = queryset.filter(property_type_id=property_type)
        
        if city:
            queryset = queryset.filter(city=city)
        
        if bedrooms:
            if bedrooms == '4':
                queryset = queryset.filter(bedrooms__gte=4)
            else:
                queryset = queryset.filter(bedrooms=bedrooms)
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        
        # Get all properties for aggregate calculations
        properties = Property.objects.filter(owner=self.request.user)
        
        # Add property types for filter dropdown
        context['property_types'] = PropertyType.objects.all()
        
        # Add cities for filter dropdown
        context['cities'] = properties.values_list('city', flat=True).distinct().order_by('city')
        
        # Add count statistics
        context['rented_count'] = properties.filter(status='rented').count()
        context['available_count'] = properties.filter(status='available').count()
        
        # Monthly income from all properties
        monthly_income = 0
        for property in properties.filter(status='rented'):
            monthly_income += property.monthly_rent
        
        context['monthly_income'] = monthly_income
        
        return context

class PropertyDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed information about a property.
    """
    model = Property
    template_name = 'properties/property_detail.html'
    context_object_name = 'property'
    
    def get_queryset(self):
        """Ensure user can only view their own properties."""
        return Property.objects.filter(owner=self.request.user)
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        property = self.get_object()
        
        # Get current and past leases
        context['current_lease'] = Lease.objects.filter(
            property=property,
            status='active'
        ).first()
        
        context['past_leases'] = Lease.objects.filter(
            property=property
        ).exclude(status='active').order_by('-end_date')
        
        # Get income and expenses for this property
        payments = Payment.objects.filter(property=property)
        context['total_income'] = payments.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
        context['pending_payments'] = payments.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
        
        # Get income by year
        yearly_income = {}
        for payment in payments.filter(status='paid'):
            year = payment.payment_date.year
            if year not in yearly_income:
                yearly_income[year] = 0
            yearly_income[year] += payment.amount
        
        context['yearly_income'] = yearly_income
        
        # Get property images
        context['property_images'] = property.images.all()
        
        # Get property documents
        context['property_documents'] = property.documents.all()
        
        return context

class PropertyCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new property.
    """
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    
    def get_context_data(self, **kwargs):
        """Add property types to context."""
        context = super().get_context_data(**kwargs)
        context['property_types'] = PropertyType.objects.all()
        context['title'] = 'Add New Property'
        return context
    
    def form_valid(self, form):
        """Set the owner to current user and handle form submission."""
        form.instance.owner = self.request.user
        messages.success(self.request, 'Property created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to property detail page after creation."""
        return reverse_lazy('property_detail', kwargs={'pk': self.object.pk})

class PropertyUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing property.
    """
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    
    def get_queryset(self):
        """Ensure user can only update their own properties."""
        return Property.objects.filter(owner=self.request.user)
    
    def get_context_data(self, **kwargs):
        """Add property types to context."""
        context = super().get_context_data(**kwargs)
        context['property_types'] = PropertyType.objects.all()
        context['title'] = 'Update Property'
        return context
    
    def form_valid(self, form):
        """Handle form submission."""
        messages.success(self.request, 'Property updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to property detail page after update."""
        return reverse_lazy('property_detail', kwargs={'pk': self.object.pk})

class PropertyDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete a property.
    """
    model = Property
    template_name = 'properties/property_confirm_delete.html'
    success_url = reverse_lazy('property_list')
    
    def get_queryset(self):
        """Ensure user can only delete their own properties."""
        return Property.objects.filter(owner=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """Handle property deletion."""
        messages.success(request, 'Property deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def add_property_image(request, pk):
    """
    Add an image to a property.
    """
    property = get_object_or_404(Property, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = PropertyImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.property = property
            
            # If this is the first image or set as primary, update other images
            if form.cleaned_data['is_primary']:
                PropertyImage.objects.filter(property=property, is_primary=True).update(is_primary=False)
            elif PropertyImage.objects.filter(property=property).count() == 0:
                image.is_primary = True
                
            image.save()
            messages.success(request, 'Image added successfully!')
            return redirect('property_detail', pk=property.pk)
    else:
        form = PropertyImageForm()
    
    return render(request, 'properties/property_image_form.html', {
        'form': form,
        'property': property,
        'title': 'Add Property Image'
    })

@login_required
def add_property_document(request, pk):
    """
    Add a document to a property.
    """
    property = get_object_or_404(Property, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = PropertyDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.property = property
            document.save()
            messages.success(request, 'Document added successfully!')
            return redirect('property_detail', pk=property.pk)
    else:
        form = PropertyDocumentForm()
    
    return render(request, 'properties/property_document_form.html', {
        'form': form,
        'property': property,
        'title': 'Add Property Document'
    })

@login_required
def delete_property_image(request, pk):
    """
    Delete a property image.
    """
    image = get_object_or_404(PropertyImage, pk=pk, property__owner=request.user)
    property_id = image.property.id
    
    # Check if this is the primary image
    is_primary = image.is_primary
    
    image.delete()
    messages.success(request, 'Image deleted successfully!')
    
    # If deleted image was primary, set another image as primary
    if is_primary:
        next_image = PropertyImage.objects.filter(property_id=property_id).first()
        if next_image:
            next_image.is_primary = True
            next_image.save()
    
    return redirect('property_detail', pk=property_id)

@login_required
def delete_property_document(request, pk):
    """
    Delete a property document.
    """
    document = get_object_or_404(PropertyDocument, pk=pk, property__owner=request.user)
    property_id = document.property.id
    
    document.delete()
    messages.success(request, 'Document deleted successfully!')
    
    return redirect('property_detail', pk=property_id)
