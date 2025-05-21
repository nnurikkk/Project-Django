"""
Core views for the rental income manager application.
"""
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from properties.models import Property
from tenants.models import Tenant
from payments.models import Payment
from expenses.models import Expense

def home(request):
    """Display the homepage for non-authenticated users."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    """
    Display the main dashboard with summary information.
    """
    # Get user's properties
    properties = Property.objects.filter(owner=request.user)
    property_count = properties.count()
    
    # Get tenant information
    tenant_count = Tenant.objects.filter(leases__rental_property__owner=request.user).distinct().count()
    
    # Date ranges
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    end_of_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    start_of_year = today.replace(month=1, day=1)
    
    # Payment statistics
    payments_this_month = Payment.objects.filter(
        rental_property__owner=request.user,
        payment_date__range=[start_of_month, end_of_month]
    )
    income_this_month = payments_this_month.aggregate(total=Sum('amount'))['total'] or 0
    
    payments_this_year = Payment.objects.filter(
        rental_property__owner=request.user,
        payment_date__range=[start_of_year, today]
    )
    income_this_year = payments_this_year.aggregate(total=Sum('amount'))['total'] or 0
    
    # Expense statistics
    expenses_this_month = Expense.objects.filter(
        rental_property__owner=request.user,
        date__range=[start_of_month, end_of_month]
    )
    expense_this_month = expenses_this_month.aggregate(total=Sum('amount'))['total'] or 0
    
    expenses_this_year = Expense.objects.filter(
        rental_property__owner=request.user,
        date__range=[start_of_year, today]
    )
    expense_this_year = expenses_this_year.aggregate(total=Sum('amount'))['total'] or 0
    
    # Net income
    net_income_month = income_this_month - expense_this_month
    net_income_year = income_this_year - expense_this_year
    
    # Upcoming payments
    upcoming_payments = Payment.objects.filter(
        rental_property__owner=request.user,
        status='pending',
        due_date__gte=today
    ).order_by('due_date')[:5]
    
    # Overdue payments
    overdue_payments = Payment.objects.filter(
        rental_property__owner=request.user,
        status='pending',
        due_date__lt=today
    ).order_by('due_date')
    
    overdue_amount = overdue_payments.aggregate(total=Sum('amount'))['total'] or 0
    overdue_count = overdue_payments.count()
    
    # Monthly income data for chart
    monthly_income = []
    monthly_expenses = []
    monthly_net = []
    
    for month in range(1, 13):
        month_start = today.replace(month=month, day=1)
        if month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month + 1, day=1) - timedelta(days=1)
        
        month_income = Payment.objects.filter(
            rental_property__owner=request.user,
            payment_date__range=[month_start, month_end]
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        month_expense = Expense.objects.filter(
            rental_property__owner=request.user,
            date__range=[month_start, month_end]
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_income.append(month_income)
        monthly_expenses.append(month_expense)
        monthly_net.append(month_income - month_expense)
    
    context = {
        'property_count': property_count,
        'tenant_count': tenant_count,
        'income_this_month': income_this_month,
        'income_this_year': income_this_year,
        'expense_this_month': expense_this_month,
        'expense_this_year': expense_this_year,
        'net_income_month': net_income_month,
        'net_income_year': net_income_year,
        'upcoming_payments': upcoming_payments,
        'overdue_amount': overdue_amount,
        'overdue_count': overdue_count,
        'monthly_income': json.dumps([1000, 1200, 1100, 1300, 1400, 1200, 1100, 1300, 1500, 1400, 1200, 1300]),
        'monthly_expenses': json.dumps([800, 850, 900, 950, 1000, 800, 750, 900, 950, 1000, 900, 950]),
        'monthly_net': json.dumps([200, 350, 200, 350, 400, 400, 350, 400, 550, 400, 300, 350]),
    }
    
    return render(request, 'core/dashboard.html', context)
