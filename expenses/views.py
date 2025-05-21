"""
Views for the expenses app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import Expense, ExpenseCategory, Vendor, ExpenseDocument
from .forms import ExpenseForm, ExpenseCategoryForm, VendorForm, ExpenseDocumentForm, ExpenseFilterForm

class ExpenseListView(LoginRequiredMixin, ListView):
    """
    Display a list of expenses with filtering options.
    """
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 15
    
    def get_queryset(self):
        """Filter expenses based on query parameters."""
        queryset = Expense.objects.filter(rental_property__owner=self.request.user)
        
        # Get filter form
        self.form = ExpenseFilterForm(self.request.GET or None, user=self.request.user)
        
        # Apply filters if the form is valid
        if self.form.is_valid():
            data = self.form.cleaned_data
            
            if data.get('start_date'):
                queryset = queryset.filter(date__gte=data['start_date'])
            
            if data.get('end_date'):
                queryset = queryset.filter(date__lte=data['end_date'])
            
            if data.get('rental_property'):
                queryset = queryset.filter(rental_property=data['rental_property'])
            
            if data.get('category'):
                queryset = queryset.filter(category=data['category'])
            
            if data.get('vendor'):
                queryset = queryset.filter(vendor=data['vendor'])
            
            if data.get('min_amount'):
                queryset = queryset.filter(amount__gte=data['min_amount'])
            
            if data.get('max_amount'):
                queryset = queryset.filter(amount__lte=data['max_amount'])
            
            if data.get('status'):
                queryset = queryset.filter(status=data['status'])
            
            if data.get('tax_deductible') is not None:
                queryset = queryset.filter(tax_deductible=data['tax_deductible'])
            
            # Sort results
            sort_by = data.get('sort_by') or '-date'
            queryset = queryset.order_by(sort_by)
        else:
            # Default sorting
            queryset = queryset.order_by('-date')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        
        # Add filter form to context
        context['form'] = self.form
        
        # Add total expenses
        total_expenses = Expense.objects.filter(
            rental_property__owner=self.request.user,
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        context['total_expenses'] = total_expenses
        
        # Add expenses by category
        expenses_by_category = Expense.objects.filter(
            rental_property__owner=self.request.user,
            status='paid'
        ).values('category__name').annotate(total=Sum('amount')).order_by('-total')
        context['expenses_by_category'] = expenses_by_category
        
        return context

class ExpenseDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed information about an expense.
    """
    model = Expense
    template_name = 'expenses/expense_detail.html'
    context_object_name = 'expense'
    
    def get_queryset(self):
        """Ensure user can only view their own expenses."""
        return Expense.objects.filter(rental_property__owner=self.request.user)
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        expense = self.get_object()
        
        # Add expense documents
        context['documents'] = expense.documents.all()
        
        # Add related expenses (same property/category)
        context['related_expenses'] = Expense.objects.filter(
            rental_property=expense.property,
            category=expense.category
        ).exclude(id=expense.id).order_by('-date')[:5]
        
        return context

class ExpenseCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new expense.
    """
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    
    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add context data."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Expense'
        return context
    
    def form_valid(self, form):
        """Set the created_by field and handle form submission."""
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Expense created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to expense detail page after creation."""
        return reverse_lazy('expense_detail', kwargs={'pk': self.object.pk})

class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing expense.
    """
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    
    def get_queryset(self):
        """Ensure user can only update their own expenses."""
        return Expense.objects.filter(rental_property__owner=self.request.user)
    
    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add context data."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Expense'
        return context
    
    def form_valid(self, form):
        """Handle form submission."""
        messages.success(self.request, 'Expense updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to expense detail page after update."""
        return reverse_lazy('expense_detail', kwargs={'pk': self.object.pk})

class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete an expense.
    """
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expense_list')
    
    def get_queryset(self):
        """Ensure user can only delete their own expenses."""
        return Expense.objects.filter(rental_property__owner=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """Handle expense deletion."""
        messages.success(request, 'Expense deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def add_expense_document(request, pk):
    """
    Add a document to an expense.
    """
    expense = get_object_or_404(Expense, pk=pk, rental_property__owner=request.user)
    
    if request.method == 'POST':
        form = ExpenseDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.expense = expense
            document.save()
            messages.success(request, 'Document added successfully!')
            return redirect('expense_detail', pk=expense.pk)
    else:
        form = ExpenseDocumentForm()
    
    return render(request, 'expenses/expense_document_form.html', {
        'form': form,
        'expense': expense,
        'title': 'Add Expense Document'
    })

@login_required
def delete_expense_document(request, pk):
    """
    Delete an expense document.
    """
    document = get_object_or_404(ExpenseDocument, pk=pk, expense__rental_property__owner=request.user)
    expense_id = document.expense.id
    
    document.delete()
    messages.success(request, 'Document deleted successfully!')
    
    return redirect('expense_detail', pk=expense_id)

class ExpenseCategoryListView(LoginRequiredMixin, ListView):
    """
    Display a list of expense categories.
    """
    model = ExpenseCategory
    template_name = 'expenses/expense_category_list.html'
    context_object_name = 'categories'

class ExpenseCategoryCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new expense category.
    """
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'expenses/expense_category_form.html'
    success_url = reverse_lazy('expense_category_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Expense Category'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Expense category created successfully!')
        return super().form_valid(form)

class ExpenseCategoryUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing expense category.
    """
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'expenses/expense_category_form.html'
    success_url = reverse_lazy('expense_category_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Expense Category'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Expense category updated successfully!')
        return super().form_valid(form)

class ExpenseCategoryDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete an expense category.
    """
    model = ExpenseCategory
    template_name = 'expenses/expense_category_confirm_delete.html'
    success_url = reverse_lazy('expense_category_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Expense category deleted successfully!')
        return super().delete(request, *args, **kwargs)

class VendorListView(LoginRequiredMixin, ListView):
    """
    Display a list of vendors.
    """
    model = Vendor
    template_name = 'expenses/vendor_list.html'
    context_object_name = 'vendors'
    
    def get_queryset(self):
        """Filter vendors to show only those created by the current user."""
        return Vendor.objects.filter(created_by=self.request.user)

class VendorDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed information about a vendor.
    """
    model = Vendor
    template_name = 'expenses/vendor_detail.html'
    context_object_name = 'vendor'
    
    def get_queryset(self):
        """Ensure user can only view their own vendors."""
        return Vendor.objects.filter(created_by=self.request.user)
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        vendor = self.get_object()
        
        # Get expenses for this vendor
        context['expenses'] = Expense.objects.filter(
            vendor=vendor,
            rental_property__owner=self.request.user
        ).order_by('-date')
        
        # Calculate total expense amount
        context['total_expenses'] = context['expenses'].aggregate(
            total=Sum('amount'))['total'] or 0
        
        return context

class VendorCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new vendor.
    """
    model = Vendor
    form_class = VendorForm
    template_name = 'expenses/vendor_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Vendor'
        return context
    
    def form_valid(self, form):
        """Set the created_by field and handle form submission."""
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Vendor created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to vendor detail page after creation."""
        return reverse_lazy('vendor_detail', kwargs={'pk': self.object.pk})

class VendorUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing vendor.
    """
    model = Vendor
    form_class = VendorForm
    template_name = 'expenses/vendor_form.html'
    
    def get_queryset(self):
        """Ensure user can only update their own vendors."""
        return Vendor.objects.filter(created_by=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Vendor'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Vendor updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to vendor detail page after update."""
        return reverse_lazy('vendor_detail', kwargs={'pk': self.object.pk})

class VendorDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete a vendor.
    """
    model = Vendor
    template_name = 'expenses/vendor_confirm_delete.html'
    success_url = reverse_lazy('vendor_list')
    
    def get_queryset(self):
        """Ensure user can only delete their own vendors."""
        return Vendor.objects.filter(created_by=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Vendor deleted successfully!')
        return super().delete(request, *args, **kwargs)