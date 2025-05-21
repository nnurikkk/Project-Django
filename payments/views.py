"""
Views for the payments app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.http import HttpResponse
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
import csv
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from .models import Payment, PaymentCategory, LateFee
from .forms import PaymentForm, PaymentCategoryForm, LateFeeForm, WaiveLateFeeForm, PaymentFilterForm
from properties.models import Property
from tenants.models import Tenant, Lease
from core.models import Notification

class PaymentListView(LoginRequiredMixin, ListView):
    """
    Display a list of payments with filtering options.
    """
    model = Payment
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 15
    
    def get_queryset(self):
        """Filter payments based on query parameters."""
        queryset = Payment.objects.filter(rental_property__owner=self.request.user)
        
        # Get filter form
        self.form = PaymentFilterForm(self.request.GET or None, user=self.request.user)
        
        # Apply filters if the form is valid
        if self.form.is_valid():
            data = self.form.cleaned_data
            
            if data.get('start_date'):
                queryset = queryset.filter(due_date__gte=data['start_date'])
            
            if data.get('end_date'):
                queryset = queryset.filter(due_date__lte=data['end_date'])
            
            if data.get('property'):
                queryset = queryset.filter(rental_property=data['property'])
            
            if data.get('tenant'):
                queryset = queryset.filter(tenant=data['tenant'])
            
            if data.get('category'):
                queryset = queryset.filter(category=data['category'])
            
            if data.get('min_amount'):
                queryset = queryset.filter(amount__gte=data['min_amount'])
            
            if data.get('max_amount'):
                queryset = queryset.filter(amount__lte=data['max_amount'])
            
            if data.get('status'):
                queryset = queryset.filter(status=data['status'])
            
            # Sort results - make sure we only sort by valid fields
            sort_by = data.get('sort_by') or '-due_date'
            queryset = queryset.order_by(sort_by)
        else:
            # Default sorting
            queryset = queryset.order_by('-due_date')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        
        # Add filter form to context
        context['form'] = self.form
        
        # Get user payments for statistics
        all_user_payments = Payment.objects.filter(rental_property__owner=self.request.user)
        
        # Total collected
        context['total_collected'] = all_user_payments.filter(status='paid').aggregate(total=models.Sum('amount'))['total'] or 0
        
        # Pending amount
        context['pending_amount'] = all_user_payments.filter(status='pending').aggregate(total=models.Sum('amount'))['total'] or 0
        
        # Overdue payments
        today = timezone.now().date()
        overdue_payments = all_user_payments.filter(
            status='pending',
            due_date__lt=today
        )
        context['overdue_payments'] = overdue_payments.count()
        context['overdue_amount'] = overdue_payments.aggregate(total=models.Sum('amount'))['total'] or 0
        
        # This month's income
        start_of_month = today.replace(day=1)
        end_of_month = (start_of_month + relativedelta(months=1)) - timedelta(days=1)
        
        context['month_income'] = all_user_payments.filter(
            status='paid',
            payment_date__range=[start_of_month, end_of_month]
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        # Add today's date for comparing due dates
        context['today'] = today
        
        return context

class PaymentDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed information about a payment.
    """
    model = Payment
    template_name = 'payments/payment_detail.html'
    context_object_name = 'payment'
    
    def get_queryset(self):
        """Ensure user can only view their own payments."""
        return Payment.objects.filter(rental_property__owner=self.request.user)
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        payment = self.get_object()
        
        # Add late fees
        context['late_fees'] = payment.late_fees.all()
        
        # Add related payments (same tenant/property)
        context['related_payments'] = Payment.objects.filter(
            rental_property=payment.rental_property,
            tenant=payment.tenant
        ).exclude(id=payment.id).order_by('-due_date')[:5]
        
        # Add late fee form
        context['late_fee_form'] = LateFeeForm()
        
        return context

class PaymentCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new payment.
    """
    model = Payment
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'
    
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
    
    def get_initial(self):
        """Set initial values if creating from property or tenant."""
        initial = super().get_initial()
        
        property_id = self.kwargs.get('property_id')
        tenant_id = self.kwargs.get('tenant_id')
        
        if property_id:
            initial['rental_property'] = property_id
        
        if tenant_id:
            initial['tenant'] = tenant_id
            
            # If tenant has an active lease, pre-select it
            try:
                tenant = get_object_or_404(Tenant, id=tenant_id)
                # Get the current active lease instead of relying on a property
                active_lease = tenant.leases.filter(
                    status='active',
                    property__owner=self.request.user
                ).first()
                
                if active_lease:
                    initial['lease'] = active_lease.id
                    initial['rental_property'] = active_lease.property.id
                    initial['amount'] = active_lease.rent_amount
            except Exception as e:
                # Log any exceptions that might occur
                print(f"Error pre-selecting lease: {e}")
        
        return initial
    
    def get_context_data(self, **kwargs):
        """Add context data."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Payment'
        
        # If creating from property or tenant, add their details
        property_id = self.kwargs.get('property_id')
        tenant_id = self.kwargs.get('tenant_id')
        
        if property_id:
            context['selected_property'] = get_object_or_404(Property, id=property_id, owner=self.request.user)
        
        if tenant_id:
            context['selected_tenant'] = get_object_or_404(Tenant, id=tenant_id)
        
        return context
    
    def form_valid(self, form):
        """Set the created_by field and handle form submission."""
        form.instance.created_by = self.request.user
        
        # Create notification for tenant if status is pending
        if form.instance.status == 'pending':
            tenant = form.instance.tenant
            property_obj = form.instance.rental_property
            
            # Create notification for user (property owner)
            Notification.objects.create(
                user=self.request.user,
                notification_type='payment_due',
                title=f'Payment Due from {tenant.full_name}',
                message=f'A payment of ${form.instance.amount} is due on {form.instance.due_date} for {property_obj.name}.',
                related_link=f'/payments/{form.instance.id}/'
            )
        
        messages.success(self.request, 'Payment created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to payment detail page after creation."""
        return reverse_lazy('payment_detail', kwargs={'pk': self.object.pk})

class PaymentUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing payment.
    """
    model = Payment
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'
    
    def get_queryset(self):
        """Ensure user can only update their own payments."""
        return Payment.objects.filter(rental_property__owner=self.request.user)
    
    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add context data."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Payment'
        return context
    
    def form_valid(self, form):
        """Handle status changes and notifications."""
        old_status = self.get_object().status
        new_status = form.instance.status
        
        # If payment status changes to paid, record the payment date
        if old_status != 'paid' and new_status == 'paid' and not form.instance.payment_date:
            form.instance.payment_date = timezone.now().date()
        
        # Create notification if status changes to paid
        if old_status != 'paid' and new_status == 'paid':
            Notification.objects.create(
                user=self.request.user,
                notification_type='payment_received',
                title=f'Payment Received from {form.instance.tenant.full_name}',
                message=f'A payment of ${form.instance.amount} has been received for {form.instance.rental_property.name}.',
                related_link=f'/payments/{form.instance.id}/'
            )
        
        messages.success(self.request, 'Payment updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to payment detail page after update."""
        return reverse_lazy('payment_detail', kwargs={'pk': self.object.pk})

class PaymentDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete a payment.
    """
    model = Payment
    template_name = 'payments/payment_confirm_delete.html'
    success_url = reverse_lazy('payment_list')
    
    def get_queryset(self):
        """Ensure user can only delete their own payments."""
        return Payment.objects.filter(rental_property__owner=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """Handle payment deletion."""
        messages.success(request, 'Payment deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def mark_payment_as_paid(request, pk):
    """
    Mark a pending payment as paid.
    """
    payment = get_object_or_404(Payment, pk=pk, rental_property__owner=request.user)
    
    if payment.status != 'paid':
        payment.status = 'paid'
        payment.payment_date = timezone.now().date()
        payment.save()
        
        # Create notification
        Notification.objects.create(
            user=request.user,
            notification_type='payment_received',
            title=f'Payment Received from {payment.tenant.full_name}',
            message=f'A payment of ${payment.amount} has been received for {payment.rental_property.name}.',
            related_link=f'/payments/{payment.id}/'
        )
        
        messages.success(request, 'Payment marked as paid successfully!')
    else:
        messages.warning(request, 'Payment is already marked as paid.')
    
    return redirect('payment_detail', pk=payment.pk)

@login_required
def add_late_fee(request, pk):
    """
    Add a late fee to a payment.
    """
    payment = get_object_or_404(Payment, pk=pk, rental_property__owner=request.user)
    
    if request.method == 'POST':
        form = LateFeeForm(request.POST)
        if form.is_valid():
            late_fee = form.save(commit=False)
            late_fee.payment = payment
            late_fee.created_by = request.user
            late_fee.save()
            
            messages.success(request, 'Late fee added successfully!')
        else:
            messages.error(request, 'Error adding late fee. Please check the form.')
    
    return redirect('payment_detail', pk=payment.pk)

@login_required
def waive_late_fee(request, pk):
    """
    Waive a late fee.
    """
    late_fee = get_object_or_404(LateFee, pk=pk, payment__rental_property__owner=request.user)
    
    if request.method == 'POST':
        form = WaiveLateFeeForm(request.POST, instance=late_fee)
        if form.is_valid():
            late_fee = form.save(commit=False)
            late_fee.waived = True
            late_fee.waived_by = request.user
            late_fee.waived_date = timezone.now().date()
            late_fee.save()
            
            messages.success(request, 'Late fee waived successfully!')
        else:
            messages.error(request, 'Error waiving late fee. Please check the form.')
    
    return redirect('payment_detail', pk=late_fee.payment.pk)

class PaymentCategoryListView(LoginRequiredMixin, ListView):
    """
    Display a list of payment categories.
    """
    model = PaymentCategory
    template_name = 'payments/payment_category_list.html'
    context_object_name = 'categories'

class PaymentCategoryCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new payment category.
    """
    model = PaymentCategory
    form_class = PaymentCategoryForm
    template_name = 'payments/payment_category_form.html'
    success_url = reverse_lazy('payment_category_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Payment Category'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Payment category created successfully!')
        return super().form_valid(form)

class PaymentCategoryUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing payment category.
    """
    model = PaymentCategory
    form_class = PaymentCategoryForm
    template_name = 'payments/payment_category_form.html'
    success_url = reverse_lazy('payment_category_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Payment Category'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Payment category updated successfully!')
        return super().form_valid(form)

class PaymentCategoryDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete a payment category.
    """
    model = PaymentCategory
    template_name = 'payments/payment_category_confirm_delete.html'
    success_url = reverse_lazy('payment_category_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Payment category deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def create_recurring_payments(request):
    """
    Create recurring payments for active leases.
    """
    if request.method == 'POST':
        properties = request.POST.getlist('properties')
        due_date = request.POST.get('due_date')
        
        if not properties or not due_date:
            messages.error(request, 'Please select at least one property and a due date.')
            return redirect('payment_list')
        
        # Convert due_date to a date object
        try:
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('payment_list')
        
        # Get active leases for selected properties
        active_leases = Lease.objects.filter(
            rental_property_id__in=properties,
            rental_property__owner=request.user,
            status='active',
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        )
        
        # Get rent payment category
        rent_category, created = PaymentCategory.objects.get_or_create(
            name='Rent',
            defaults={'description': 'Monthly rent payment'}
        )
        
        # Create payments
        payments_created = 0
        for lease in active_leases:
            # Check if a payment already exists for this month and lease
            existing_payment = Payment.objects.filter(
                lease=lease,
                rental_property=lease.rental_property,
                tenant=lease.tenant,
                due_date__year=due_date.year,
                due_date__month=due_date.month
            ).exists()
            
            if not existing_payment:
                Payment.objects.create(
                    rental_property=lease.rental_property,
                    tenant=lease.tenant,
                    lease=lease,
                    category=rent_category,
                    amount=lease.rent_amount,
                    due_date=due_date,
                    status='pending',
                    created_by=request.user
                )
                payments_created += 1
        
        if payments_created > 0:
            messages.success(request, f'{payments_created} recurring payments created successfully!')
        else:
            messages.warning(request, 'No new payments were created. Payments may already exist for the selected properties and month.')
        
        return redirect('payment_list')
    
    # GET request - show form
    context = {
        'properties': Property.objects.filter(owner=request.user, status='rented')
    }
    
    return render(request, 'payments/create_recurring_payments.html', context)

@login_required
def export_payments(request):
    """
    Export payments to CSV.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payments.csv"'
    
    # Get filtered queryset
    form = PaymentFilterForm(request.GET or None, user=request.user)
    if form.is_valid():
        queryset = PaymentListView.get_queryset(request)
    else:
        queryset = Payment.objects.filter(rental_property__owner=request.user)
    
    # Create CSV writer
    writer = csv.writer(response)
    writer.writerow([
        'Property', 'Tenant', 'Category', 'Amount', 'Due Date', 
        'Payment Date', 'Status', 'Payment Method', 'Reference Number'
    ])
    
    # Add payment data
    for payment in queryset:
        writer.writerow([
            payment.rental_property.name,
            payment.tenant.full_name,
            payment.category.name if payment.category else '',
            payment.amount,
            payment.due_date,
            payment.payment_date if payment.payment_date else '',
            payment.get_status_display(),
            payment.get_payment_method_display() if payment.payment_method else '',
            payment.reference_number if payment.reference_number else ''
        ])
    
    return response

@login_required
def payment_debug(request):
    """
    Debug view for payment issues.
    Displays detailed information about payments, forms, and model relationships.
    """
    queryset = Payment.objects.filter(rental_property__owner=request.user)
    
    # Get filter form
    form = PaymentFilterForm(request.GET or None, user=request.user)
    
    # Get all tenants with their leases for debugging
    all_tenants = Tenant.objects.filter(
        leases__property__owner=request.user
    ).distinct().prefetch_related('leases', 'leases__property')
    
    # Get all properties owned by the user
    all_properties = Property.objects.filter(owner=request.user)
    
    # Check specific relationships
    lease_check = []
    for tenant in all_tenants:
        tenant_leases = tenant.leases.all()
        for lease in tenant_leases:
            lease_check.append({
                'tenant_id': tenant.id,
                'tenant_name': tenant.full_name,
                'lease_id': lease.id,
                'property_id': lease.property.id if lease.property else None,
                'property_name': lease.property.name if lease.property else None,
                'status': lease.status
            })
    
    # Inspect current request
    request_data = {
        'GET': dict(request.GET.items()),
        'user': request.user.username,
        'user_id': request.user.id
    }
    
    context = {
        'form': form,
        'queryset': queryset,
        'payments': queryset,
        'all_tenants': all_tenants,
        'all_properties': all_properties,
        'lease_check': lease_check,
        'request_data': request_data
    }
    
    return render(request, 'payments/payment_debug.html', context)

@login_required
def payment_emergency_debug(request):
    """
    Emergency debug view that doesn't use any forms or complex queries.
    Use this if other views are causing errors.
    """
    output = []
    output.append("<h1>Emergency Debug Page</h1>")
    output.append(f"<p>User: {request.user.username} (ID: {request.user.id})</p>")
    
    # Basic model counts - no filtering that could cause errors
    output.append("<h2>Model Counts</h2>")
    output.append(f"<p>Properties: {Property.objects.count()}</p>")
    output.append(f"<p>Tenants: {Tenant.objects.count()}</p>")
    output.append(f"<p>Leases: {Lease.objects.count()}</p>")
    output.append(f"<p>Payments: {Payment.objects.count()}</p>")
    
    # Try to identify user's properties without complex filtering
    output.append("<h2>Your Properties</h2>")
    try:
        properties = Property.objects.filter(owner=request.user)
        if properties:
            output.append("<ul>")
            for prop in properties:
                output.append(f"<li>ID: {prop.id} - Name: {prop.name}</li>")
            output.append("</ul>")
        else:
            output.append("<p>No properties found for this user.</p>")
    except Exception as e:
        output.append(f"<p>Error loading properties: {e}</p>")
    
    # Try to identify tenants using a simpler approach
    output.append("<h2>Tenants</h2>")
    try:
        tenants = Tenant.objects.all()[:10]  # Limit to 10 to avoid performance issues
        if tenants:
            output.append("<ul>")
            for tenant in tenants:
                output.append(f"<li>ID: {tenant.id} - Name: {tenant.full_name}</li>")
            output.append("</ul>")
        else:
            output.append("<p>No tenants found.</p>")
    except Exception as e:
        output.append(f"<p>Error loading tenants: {e}</p>")
    
    # Try to identify leases using a simpler approach
    output.append("<h2>Leases</h2>")
    try:
        leases = Lease.objects.all()[:10]  # Limit to 10 to avoid performance issues
        if leases:
            output.append("<ul>")
            for lease in leases:
                try:
                    property_name = lease.property.name if lease.property else "Unknown"
                    tenant_name = lease.tenant.full_name if lease.tenant else "Unknown"
                    output.append(f"<li>ID: {lease.id} - Property: {property_name} - Tenant: {tenant_name}</li>")
                except Exception as inner_e:
                    output.append(f"<li>Error with lease {lease.id}: {inner_e}</li>")
            output.append("</ul>")
        else:
            output.append("<p>No leases found.</p>")
    except Exception as e:
        output.append(f"<p>Error loading leases: {e}</p>")
    
    # Add this path to your urls.py
    # path('emergency-debug/', views.payment_emergency_debug, name='payment_emergency_debug'),
    
    return HttpResponse("<br>".join(output))