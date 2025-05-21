"""
Views for the tenants app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import HttpResponse
import csv
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from .models import Tenant, Lease, LeaseDocument
from .forms import (
    TenantForm, LeaseForm, LeaseDocumentForm,
    TenantFilterForm, LeaseFilterForm
)
from properties.models import Property
from payments.models import Payment
from core.models import Notification

class TenantListView(LoginRequiredMixin, ListView):
    """
    Display a list of tenants with filtering options.
    """
    model = Tenant
    template_name = 'tenants/tenant_list.html'
    context_object_name = 'tenants'
    paginate_by = 12
    
    def get_queryset(self):
        """Filter tenants based on query parameters."""
        # Start with tenants who have leases on properties owned by the current user
        queryset = Tenant.objects.filter(leases__rental_property__owner=self.request.user).distinct()
        
        # Get filter form
        self.form = TenantFilterForm(self.request.GET or None, user=self.request.user)
        
        # Apply filters if the form is valid
        if self.form.is_valid():
            data = self.form.cleaned_data
            
            if data.get('search'):
                search_term = data['search']
                queryset = queryset.filter(
                    Q(first_name__icontains=search_term) |
                    Q(last_name__icontains=search_term) |
                    Q(email__icontains=search_term) |
                    Q(phone__icontains=search_term)
                )
            
            if data.get('property'):
                queryset = queryset.filter(leases__rental_property=data['property']).distinct()
            
            if data.get('has_active_lease') == 'yes':
                today = timezone.now().date()
                queryset = queryset.filter(
                    leases__status='active',
                    leases__start_date__lte=today,
                    leases__end_date__gte=today
                ).distinct()
            elif data.get('has_active_lease') == 'no':
                today = timezone.now().date()
                active_tenant_ids = Tenant.objects.filter(
                    leases__status='active',
                    leases__start_date__lte=today,
                    leases__end_date__gte=today
                ).values_list('id', flat=True)
                queryset = queryset.exclude(id__in=active_tenant_ids)
            
            # Sort results
            sort_by = data.get('sort_by') or 'last_name'
            queryset = queryset.order_by(sort_by)
        else:
            # Default sorting
            queryset = queryset.order_by('last_name')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        
        # Add filter form to context
        context['form'] = self.form
        
        # Add tenant stats
        tenants = Tenant.objects.filter(leases__rental_property__owner=self.request.user).distinct()
        
        # Count of all tenants
        context['total_tenants'] = tenants.count()
        
        # Count of active tenants
        today = timezone.now().date()
        context['active_tenants'] = tenants.filter(
            leases__status='active',
            leases__start_date__lte=today,
            leases__end_date__gte=today
        ).distinct().count()
        
        # Calculate tenants with leases expiring in the next 30 days
        thirty_days_from_now = today + timedelta(days=30)
        context['expiring_leases'] = Lease.objects.filter(
            rental_property__owner=self.request.user,
            status='active',
            end_date__range=[today, thirty_days_from_now]
        ).count()
        
        return context

class TenantDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed information about a tenant.
    """
    model = Tenant
    template_name = 'tenants/tenant_detail.html'
    context_object_name = 'tenant'
    
    def get_queryset(self):
        """Ensure user can only view tenants with leases on their properties."""
        return Tenant.objects.filter(leases__rental_property__owner=self.request.user).distinct()
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        tenant = self.get_object()
        
        # Get tenant leases
        context['leases'] = Lease.objects.filter(
            tenant=tenant,
            rental_property__owner=self.request.user
        ).order_by('-start_date')
        
        # Get active lease
        context['active_lease'] = tenant.current_lease
        
        # Get payment history
        context['payments'] = Payment.objects.filter(
            tenant=tenant,
            rental_property__owner=self.request.user
        ).order_by('-due_date')
        
        # Calculate payment statistics
        total_paid = context['payments'].filter(status='paid').aggregate(
            total=Sum('amount'))['total'] or 0
        context['total_paid'] = total_paid
        
        paid_on_time = context['payments'].filter(
            status='paid', 
            payment_date__lte=F('due_date')
        ).count()
        
        paid_late = context['payments'].filter(
            status='paid', 
            payment_date__gt=F('due_date')
        ).count()
        
        total_payments = paid_on_time + paid_late
        if total_payments > 0:
            context['on_time_percentage'] = (paid_on_time / total_payments) * 100
        else:
            context['on_time_percentage'] = 0
        
        # Pending payments
        context['pending_payments'] = context['payments'].filter(
            status='pending', 
            due_date__gte=timezone.now().date()
        )
        
        # Overdue payments
        context['overdue_payments'] = context['payments'].filter(
            status='pending', 
            due_date__lt=timezone.now().date()
        )
        
        return context

class TenantCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new tenant.
    """
    model = Tenant
    form_class = TenantForm
    template_name = 'tenants/tenant_form.html'
    
    def get_context_data(self, **kwargs):
        """Add context data."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Tenant'
        return context
    
    def form_valid(self, form):
        """Set the created_by field and handle form submission."""
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Tenant created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to tenant detail page after creation."""
        return reverse_lazy('tenant_detail', kwargs={'pk': self.object.pk})

class TenantUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing tenant.
    """
    model = Tenant
    form_class = TenantForm
    template_name = 'tenants/tenant_form.html'
    
    def get_queryset(self):
        """Ensure user can only update tenants with leases on their properties."""
        return Tenant.objects.filter(leases__rental_property__owner=self.request.user).distinct()
    
    def get_context_data(self, **kwargs):
        """Add context data."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Tenant'
        return context
    
    def form_valid(self, form):
        """Handle form submission."""
        messages.success(self.request, 'Tenant updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to tenant detail page after update."""
        return reverse_lazy('tenant_detail', kwargs={'pk': self.object.pk})

class TenantDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete a tenant.
    """
    model = Tenant
    template_name = 'tenants/tenant_confirm_delete.html'
    success_url = reverse_lazy('tenant_list')
    
    def get_queryset(self):
        """Ensure user can only delete tenants with leases on their properties."""
        return Tenant.objects.filter(leases__rental_property__owner=self.request.user).distinct()
    
    def delete(self, request, *args, **kwargs):
        """Handle tenant deletion."""
        messages.success(request, 'Tenant deleted successfully!')
        return super().delete(request, *args, **kwargs)

class LeaseListView(LoginRequiredMixin, ListView):
    """
    Display a list of leases with filtering options.
    """
    model = Lease
    template_name = 'tenants/lease_list.html'
    context_object_name = 'leases'
    paginate_by = 10
    
    def get_queryset(self):
        """Filter leases based on query parameters."""
        queryset = Lease.objects.filter(rental_property__owner=self.request.user)
        
        # Get filter form
        self.form = LeaseFilterForm(self.request.GET or None, user=self.request.user)
        
        # Apply filters if the form is valid
        if self.form.is_valid():
            data = self.form.cleaned_data
            
            if data.get('property'):
                queryset = queryset.filter(rental_property=data['property'])
            
            if data.get('tenant'):
                queryset = queryset.filter(tenant=data['tenant'])
            
            if data.get('status'):
                queryset = queryset.filter(status=data['status'])
            
            if data.get('lease_type'):
                queryset = queryset.filter(lease_type=data['lease_type'])
            
            if data.get('start_date_after'):
                queryset = queryset.filter(start_date__gte=data['start_date_after'])
            
            if data.get('start_date_before'):
                queryset = queryset.filter(start_date__lte=data['start_date_before'])
            
            if data.get('end_date_after'):
                queryset = queryset.filter(end_date__gte=data['end_date_after'])
            
            if data.get('end_date_before'):
                queryset = queryset.filter(end_date__lte=data['end_date_before'])
            
            if data.get('min_rent'):
                queryset = queryset.filter(rent_amount__gte=data['min_rent'])
            
            if data.get('max_rent'):
                queryset = queryset.filter(rent_amount__lte=data['max_rent'])
            
            # Sort results
            sort_by = data.get('sort_by') or '-start_date'
            queryset = queryset.order_by(sort_by)
        else:
            # Default sorting
            queryset = queryset.order_by('-start_date')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        
        # Add filter form to context
        context['form'] = self.form
        
        # Add lease stats
        today = timezone.now().date()
        
        # Active leases
        context['active_leases'] = Lease.objects.filter(
            rental_property__owner=self.request.user,
            status='active',
            start_date__lte=today,
            end_date__gte=today
        ).count()
        
        # Expiring soon (next 30 days)
        thirty_days_from_now = today + timedelta(days=30)
        context['expiring_soon'] = Lease.objects.filter(
            rental_property__owner=self.request.user,
            status='active',
            end_date__range=[today, thirty_days_from_now]
        ).count()
        
        # Recently started (last 30 days)
        thirty_days_ago = today - timedelta(days=30)
        context['recently_started'] = Lease.objects.filter(
            rental_property__owner=self.request.user,
            start_date__range=[thirty_days_ago, today]
        ).count()
        
        # Monthly rent from active leases
        context['monthly_rent'] = Lease.objects.filter(
            rental_property__owner=self.request.user,
            status='active',
            start_date__lte=today,
            end_date__gte=today
        ).aggregate(total=Sum('rent_amount'))['total'] or 0
        
        return context

class LeaseDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed information about a lease.
    """
    model = Lease
    template_name = 'tenants/lease_detail.html'
    context_object_name = 'lease'
    
    def get_queryset(self):
        """Ensure user can only view their own leases."""
        return Lease.objects.filter(rental_property__owner=self.request.user)
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        lease = self.get_object()
        
        # Add lease documents
        context['documents'] = lease.documents.all()
        
        # Get payments for this lease
        context['payments'] = Payment.objects.filter(lease=lease).order_by('-due_date')
        
        # Calculate lease statistics
        context['total_payments'] = context['payments'].filter(status='paid').aggregate(
            total=Sum('amount'))['total'] or 0
        
        context['pending_payments'] = context['payments'].filter(
            status='pending'
        ).order_by('due_date')
        
        context['pending_amount'] = context['pending_payments'].aggregate(
            total=Sum('amount'))['total'] or 0
        
        # Calculate days remaining on lease
        today = timezone.now().date()
        if lease.status == 'active' and lease.end_date >= today:
            context['days_remaining'] = (lease.end_date - today).days
        else:
            context['days_remaining'] = 0
        
        return context

class LeaseCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new lease.
    """
    model = Lease
    form_class = LeaseForm
    template_name = 'tenants/lease_form.html'
    
    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # If creating from a specific property or tenant
        property_id = self.kwargs.get('property_id')
        tenant_id = self.kwargs.get('tenant_id')
        
        if property_id:
            kwargs['property_id'] = property_id
        
        if tenant_id:
            kwargs['tenant_id'] = tenant_id
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add context data."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Lease'
        
        # If creating from property or tenant, add their details
        property_id = self.kwargs.get('property_id')
        tenant_id = self.kwargs.get('tenant_id')
        
        if property_id:
            context['selected_property'] = get_object_or_404(
                Property, id=property_id, owner=self.request.user
            )
        
        if tenant_id:
            context['selected_tenant'] = get_object_or_404(Tenant, id=tenant_id)
        
        return context
    
    def form_valid(self, form):
        """Set the created_by field and handle form submission."""
        form.instance.created_by = self.request.user
        
        # If lease is active, update property status to rented
        if form.instance.status == 'active':
            property_obj = form.instance.property
            property_obj.status = 'rented'
            property_obj.save()
        
        # Create notification for lease
        tenant = form.instance.tenant
        property_obj = form.instance.property
        
        Notification.objects.create(
            user=self.request.user,
            notification_type='lease',
            title=f'New Lease Created for {property_obj.name}',
            message=f'A lease with {tenant.full_name} has been created for {property_obj.name} from {form.instance.start_date} to {form.instance.end_date}.',
            related_link=f'/tenants/leases/{form.instance.id}/'
        )
        
        messages.success(self.request, 'Lease created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to lease detail page after creation."""
        return reverse_lazy('lease_detail', kwargs={'pk': self.object.pk})

class LeaseUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing lease.
    """
    model = Lease
    form_class = LeaseForm
    template_name = 'tenants/lease_form.html'
    
    def get_queryset(self):
        """Ensure user can only update their own leases."""
        return Lease.objects.filter(rental_property__owner=self.request.user)
    
    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add context data."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Lease'
        return context
    
    def form_valid(self, form):
        """Handle lease status changes."""
        old_status = self.get_object().status
        new_status = form.instance.status
        
        # If lease status changes to or from active, update property status
        if old_status != 'active' and new_status == 'active':
            # Lease became active
            property_obj = form.instance.rental_property
            property_obj.status = 'rented'
            property_obj.save()
        elif old_status == 'active' and new_status != 'active':
            # Lease is no longer active
            property_obj = form.instance.rental_property
            # Check if there are other active leases for this property
            other_active_leases = Lease.objects.filter(
                rental_property=property_obj,
                status='active'
            ).exclude(pk=self.get_object().pk).exists()
            
            if not other_active_leases:
                property_obj.status = 'available'
                property_obj.save()
        
        messages.success(self.request, 'Lease updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to lease detail page after update."""
        return reverse_lazy('lease_detail', kwargs={'pk': self.object.pk})

class LeaseDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete a lease.
    """
    model = Lease
    template_name = 'tenants/lease_confirm_delete.html'
    success_url = reverse_lazy('lease_list')
    
    def get_queryset(self):
        """Ensure user can only delete their own leases."""
        return Lease.objects.filter(rental_property__owner=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """Handle lease deletion and property status update."""
        lease = self.get_object()
        
        # If this is an active lease, check if we need to update property status
        if lease.status == 'active':
            property_obj = lease.rental_property
            # Check if there are other active leases for this property
            other_active_leases = Lease.objects.filter(
                rental_property=property_obj,
                status='active'
            ).exclude(pk=lease.pk).exists()
            
            if not other_active_leases:
                property_obj.status = 'available'
                property_obj.save()
        
        messages.success(request, 'Lease deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def renew_lease(request, pk):
    """
    Renew a lease with updated terms.
    """
    old_lease = get_object_or_404(Lease, pk=pk, rental_property__owner=request.user)
    
    if request.method == 'POST':
        form = LeaseForm(request.POST, user=request.user)
        if form.is_valid():
            # Create new lease
            new_lease = form.save(commit=False)
            new_lease.created_by = request.user
            new_lease.save()
            
            # Update old lease status
            old_lease.status = 'renewed'
            old_lease.save()
            
            # Update property status if needed
            if new_lease.status == 'active':
                property_obj = new_lease.rental_property
                property_obj.status = 'rented'
                property_obj.save()
            
            # Create notification
            Notification.objects.create(
                user=request.user,
                notification_type='lease',
                title=f'Lease Renewed for {new_lease.rental_property.name}',
                message=f'The lease with {new_lease.tenant.full_name} for {new_lease.rental_property.name} has been renewed from {new_lease.start_date} to {new_lease.end_date}.',
                related_link=f'/tenants/leases/{new_lease.id}/'
            )
            
            messages.success(request, 'Lease renewed successfully!')
            return redirect('lease_detail', pk=new_lease.pk)
    else:
        # Pre-fill form with data from old lease
        initial_data = {
            'property': old_lease.property.id,
            'tenant': old_lease.tenant.id,
            'lease_type': old_lease.lease_type,
            'start_date': old_lease.end_date + timedelta(days=1),  # Start the day after old lease ends
            'end_date': old_lease.end_date + relativedelta(years=1),  # Default to 1 year
            'rent_amount': old_lease.rent_amount,
            'security_deposit': old_lease.security_deposit,
            'status': 'active',
            'payment_day': old_lease.payment_day,
            'late_fee': old_lease.late_fee,
            'grace_period': old_lease.grace_period,
            'is_security_deposit_paid': True,  # Assuming deposit carries over
            'notes': f"Renewal of lease {old_lease.id}. " + (old_lease.notes or ""),
        }
        form = LeaseForm(initial=initial_data, user=request.user)
    
    context = {
        'form': form,
        'old_lease': old_lease,
        'title': 'Renew Lease',
        'is_renewal': True
    }
    
    return render(request, 'tenants/lease_form.html', context)

@login_required
def terminate_lease(request, pk):
    """
    Terminate a lease early.
    """
    lease = get_object_or_404(Lease, pk=pk, rental_property__owner=request.user)
    
    if request.method == 'POST':
        termination_date = request.POST.get('termination_date')
        reason = request.POST.get('reason')
        
        if not termination_date:
            messages.error(request, 'Termination date is required.')
            return redirect('lease_detail', pk=lease.pk)
        
        try:
            termination_date = datetime.strptime(termination_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('lease_detail', pk=lease.pk)
        
        # Update lease
        lease.status = 'terminated'
        lease.end_date = termination_date
        lease.notes = f"{lease.notes}\n\nLease terminated on {termination_date}. Reason: {reason}"
        lease.save()
        
        # Update property status if no other active leases
        property_obj = lease.rental_property
        other_active_leases = Lease.objects.filter(
            rental_property=property_obj,
            status='active'
        ).exclude(pk=lease.pk).exists()
        
        if not other_active_leases:
            property_obj.status = 'available'
            property_obj.save()
        
        # Create notification
        Notification.objects.create(
            user=request.user,
            notification_type='lease',
            title=f'Lease Terminated for {property_obj.name}',
            message=f'The lease with {lease.tenant.full_name} for {property_obj.name} has been terminated as of {termination_date}. Reason: {reason}',
            related_link=f'/tenants/leases/{lease.id}/'
        )
        
        messages.success(request, 'Lease terminated successfully!')
        return redirect('lease_detail', pk=lease.pk)
    
    # GET request - show form
    context = {
        'lease': lease,
        'today': timezone.now().date(),
    }
    
    return render(request, 'tenants/lease_terminate.html', context)

@login_required
def add_lease_document(request, pk):
    """
    Add a document to a lease.
    """
    lease = get_object_or_404(Lease, pk=pk, rental_property__owner=request.user)
    
    if request.method == 'POST':
        form = LeaseDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.lease = lease
            document.uploaded_by = request.user
            document.save()
            messages.success(request, 'Document added successfully!')
            return redirect('lease_detail', pk=lease.pk)
    else:
        form = LeaseDocumentForm()
    
    return render(request, 'tenants/lease_document_form.html', {
        'form': form,
        'lease': lease,
        'title': 'Add Lease Document'
    })

@login_required
def delete_lease_document(request, pk):
    """
    Delete a lease document.
    """
    document = get_object_or_404(LeaseDocument, pk=pk, lease__rental_property__owner=request.user)
    lease_id = document.lease.id
    
    document.delete()
    messages.success(request, 'Document deleted successfully!')
    
    return redirect('lease_detail', pk=lease_id)

@login_required
def export_tenants(request):
    """
    Export tenants to CSV.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tenants.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    writer.writerow([
        'First Name', 'Last Name', 'Email', 'Phone', 'Date of Birth',
        'Emergency Contact', 'Emergency Phone', 'Current Lease', 'Current Property'
    ])
    
    # Add tenant data
    tenants = Tenant.objects.filter(leases__rental_property__owner=request.user).distinct()
    for tenant in tenants:
        current_lease = tenant.current_lease
        current_property = tenant.current_property
        
        writer.writerow([
            tenant.first_name,
            tenant.last_name,
            tenant.email or '',
            tenant.phone or '',
            tenant.date_of_birth.strftime('%Y-%m-%d') if tenant.date_of_birth else '',
            tenant.emergency_contact_name or '',
            tenant.emergency_contact_phone or '',
            f"{current_lease.start_date} to {current_lease.end_date}" if current_lease else 'None',
            current_property.name if current_property else 'None'
        ])
    
    return response

@login_required
def export_leases(request):
    """
    Export leases to CSV.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leases.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    writer.writerow([
        'Property', 'Tenant', 'Type', 'Start Date', 'End Date',
        'Status', 'Rent Amount', 'Security Deposit', 'Payment Day'
    ])
    
    # Add lease data
    leases = Lease.objects.filter(property__owner=request.user)
    for lease in leases:
        writer.writerow([
            lease.rental_property.name,
            lease.tenant.full_name,
            lease.get_lease_type_display(),
            lease.start_date,
            lease.end_date,
            lease.get_status_display(),
            lease.rent_amount,
            lease.security_deposit,
            lease.payment_day
        ])
    
    return response
