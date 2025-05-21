"""
Views for the reports app.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from datetime import datetime, timedelta
import csv
import io
from xhtml2pdf import pisa
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from openpyxl import Workbook
from dateutil.relativedelta import relativedelta
from properties.models import Property
from tenants.models import Tenant, Lease
from payments.models import Payment
from expenses.models import Expense

@login_required
def income_report(request):
    """
    Generate income report for selected properties and date range.
    """
    properties = Property.objects.filter(owner=request.user)
    
    # Default to current month
    today = timezone.now().date()
    start_date = today.replace(day=1)
    end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
    
    # Get date range from request if provided
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        selected_properties = request.POST.getlist('properties')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if selected_properties:
            properties = properties.filter(id__in=selected_properties)
    
    # Get all payments for selected date range and properties
    payments = Payment.objects.filter(
        rental_property__in=properties,
        payment_date__range=[start_date, end_date],
        status='paid'
    ).select_related('rental_property', 'tenant', 'category')
    
    # Calculate total income
    total_income = payments.aggregate(total=Sum('amount'))['total'] or 0
    
    # Group by property
    rental_property_income = {}
    for rental_property in properties:
        property_payments = payments.filter(rental_property=rental_property)
        property_total = property_payments.aggregate(total=Sum('amount'))['total'] or 0
        property_income[property] = {
            'payments': property_payments,
            'total': property_total
        }
    
    # Generate income by category
    income_by_category = payments.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # Generate report by month if date range spans multiple months
    months_data = []
    if (end_date.year - start_date.year) * 12 + end_date.month - start_date.month > 0:
        current = start_date.replace(day=1)
        while current <= end_date:
            month_end = min(end_date, (current + relativedelta(months=1)) - timedelta(days=1))
            month_payments = payments.filter(payment_date__range=[current, month_end])
            month_total = month_payments.aggregate(total=Sum('amount'))['total'] or 0
            
            months_data.append({
                'month': current.strftime('%B %Y'),
                'total': month_total,
                'payments': month_payments
            })
            
            current = current + relativedelta(months=1)
    
    # Handle export to different formats
    export_format = request.POST.get('export')
    if export_format:
        if export_format == 'pdf':
            return export_income_pdf(payments, total_income, start_date, end_date)
        elif export_format == 'csv':
            return export_income_csv(payments, start_date, end_date)
        elif export_format == 'excel':
            return export_income_excel(payments, start_date, end_date)
    
    context = {
        'properties': Property.objects.filter(owner=request.user),
        'selected_properties': properties,
        'start_date': start_date,
        'end_date': end_date,
        'payments': payments,
        'total_income': total_income,
        'property_income': rental_property_income,
        'income_by_category': income_by_category,
        'months_data': months_data,
    }
    
    return render(request, 'reports/income_report.html', context)

@login_required
def expense_report(request):
    """
    Generate expense report for selected properties and date range.
    """
    properties = Property.objects.filter(owner=request.user)
    
    # Default to current month
    today = timezone.now().date()
    start_date = today.replace(day=1)
    end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
    
    # Get date range from request if provided
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        selected_properties = request.POST.getlist('properties')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if selected_properties:
            properties = properties.filter(id__in=selected_properties)
    
    # Get all expenses for selected date range and properties
    expenses = Expense.objects.filter(
        rental_property__in=properties,
        date__range=[start_date, end_date],
        status='paid'
    ).select_related('rental_property', 'category', 'vendor')
    
    # Calculate total expenses
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    # Group by property
    property_expenses = {}
    for rental_property in properties:
        property_exp = expenses.filter(rental_property=rental_property)
        property_total = property_exp.aggregate(total=Sum('amount'))['total'] or 0
        property_expenses[property] = {
            'expenses': property_exp,
            'total': property_total
        }
    
    # Generate expenses by category
    expenses_by_category = expenses.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # Handle export to different formats
    export_format = request.POST.get('export')
    if export_format:
        if export_format == 'pdf':
            return export_expense_pdf(expenses, total_expenses, start_date, end_date)
        elif export_format == 'csv':
            return export_expense_csv(expenses, start_date, end_date)
        elif export_format == 'excel':
            return export_expense_excel(expenses, start_date, end_date)
    
    context = {
        'properties': Property.objects.filter(owner=request.user),
        'selected_properties': properties,
        'start_date': start_date,
        'end_date': end_date,
        'expenses': expenses,
        'total_expenses': total_expenses,
        'property_expenses': property_expenses,
        'expenses_by_category': expenses_by_category,
    }
    
    return render(request, 'reports/expense_report.html', context)

@login_required
def profit_loss_report(request):
    """
    Generate profit and loss report for selected properties and date range.
    """
    properties = Property.objects.filter(owner=request.user)
    
    # Default to current year
    today = timezone.now().date()
    start_date = today.replace(month=1, day=1)
    end_date = today.replace(month=12, day=31)
    
    # Get date range from request if provided
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        selected_properties = request.POST.getlist('properties')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if selected_properties:
            properties = properties.filter(id__in=selected_properties)
    
    # Get all payments for selected date range and properties
    payments = Payment.objects.filter(
        rental_property__in=properties,
        payment_date__range=[start_date, end_date],
        status='paid'
    ).select_related('rental_property', 'tenant', 'category')
    
    # Get all expenses for selected date range and properties
    expenses = Expense.objects.filter(
        rental_property__in=properties,
        date__range=[start_date, end_date],
        status='paid'
    ).select_related('rental_property', 'category', 'vendor')
    
    # Calculate totals
    total_income = payments.aggregate(total=Sum('amount'))['total'] or 0
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    net_profit = total_income - total_expenses
    
    # Calculate property-specific data
    rental_property_data = {}
    all_property_income = []
    for rental_property in properties:
        property_income = payments.filter(rental_property=rental_property).aggregate(total=Sum('amount'))['total'] or 0
        property_expense = expenses.filter(rental_property=rental_property).aggregate(total=Sum('amount'))['total'] or 0
        property_profit = property_income - property_expense
        property_payments = payments.filter(rental_property=rental_property)
        property_total = property_payments.aggregate(total=Sum('amount'))['total'] or 0
    
    percentage = 0
    if total_income > 0:
        percentage = (property_total / total_income) * 100

        property_income[property] = {
        'payments': property_payments,
        'total': property_total,
        'percentage': percentage  # Add this
    }
    # Store individual property data
        rental_property_data[rental_property] = {
            'income': property_income,
            'expenses': property_expense,
            'profit': property_profit,
            'roi': (property_profit / property.acquisition_price * 100) if property.acquisition_price else 0
        }
        
    
    # Add to our collection of property income data
        all_property_income.append({
            'property': rental_property.name,
            'income': property_income
        })
    
    # Generate monthly breakdown
    monthly_data = []
    current = start_date.replace(day=1)
    while current <= end_date:
        month_end = min(end_date, (current + relativedelta(months=1)) - timedelta(days=1))
        
        month_income = payments.filter(payment_date__range=[current, month_end]).aggregate(total=Sum('amount'))['total'] or 0
        month_expenses = expenses.filter(date__range=[current, month_end]).aggregate(total=Sum('amount'))['total'] or 0
        month_profit = month_income - month_expenses
        
        monthly_data.append({
            'month': current.strftime('%B %Y'),
            'income': month_income,
            'expenses': month_expenses,
            'profit': month_profit
        })
        
        current = current + relativedelta(months=1)
    
    # Handle export to different formats
    export_format = request.POST.get('export')
    if export_format:
        if export_format == 'pdf':
            return export_profit_loss_pdf(properties, rental_property_data, monthly_data, total_income, total_expenses, net_profit, start_date, end_date)
        elif export_format == 'csv':
            return export_profit_loss_csv(properties, rental_property_data, monthly_data, start_date, end_date)
        elif export_format == 'excel':
            return export_profit_loss_excel(properties, rental_property_data, monthly_data, start_date, end_date)
    
    context = {
        'properties': Property.objects.filter(owner=request.user),
        'selected_properties': properties,
        'start_date': start_date,
        'end_date': end_date,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'profit_margin': (net_profit / total_income * 100) if total_income > 0 else 0,
        'rental_property_data': rental_property_data,
        'monthly_data': monthly_data,
    }
    
    return render(request, 'reports/profit_loss_report.html', context)

@login_required
def tenant_report(request):
    """
    Generate tenant report including payment history, occupancy, etc.
    """
    # Default to all tenants
    tenants = Tenant.objects.filter(leases__rental_property__owner=request.user).distinct()
    
    if request.method == 'POST':
        selected_tenants = request.POST.getlist('tenants')
        if selected_tenants:
            tenants = tenants.filter(id__in=selected_tenants)
    
    tenant_data = {}
    for tenant in tenants:
        # Get tenant's leases
        leases = Lease.objects.filter(tenant=tenant, rental_property__owner=request.user)
        
        # Get tenant's payments
        payments = Payment.objects.filter(tenant=tenant, rental_property__owner=request.user)
        
        # Calculate payment stats
        total_paid = payments.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
        late_payments = payments.filter(status='paid', payment_date__gt=F('due_date')).count()
        on_time_payments = payments.filter(status='paid', payment_date__lte=F('due_date')).count()
        pending_payments = payments.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
        
        # Get current lease status
        current_lease = tenant.current_lease
        
        tenant_data[tenant] = {
            'leases': leases,
            'payments': payments,
            'total_paid': total_paid,
            'late_payments': late_payments,
            'on_time_payments': on_time_payments,
            'pending_payments': pending_payments,
            'current_lease': current_lease,
            'payment_reliability': (on_time_payments / (on_time_payments + late_payments) * 100) if (on_time_payments + late_payments) > 0 else 0
        }
    
    # Handle export
    export_format = request.POST.get('export')
    if export_format:
        if export_format == 'pdf':
            return export_tenant_pdf(tenants, tenant_data)
        elif export_format == 'csv':
            return export_tenant_csv(tenants, tenant_data)
        elif export_format == 'excel':
            return export_tenant_excel(tenants, tenant_data)
    
    context = {
        'tenants': Tenant.objects.filter(leases__rental_property__owner=request.user).distinct(),
        'selected_tenants': tenants,
        'tenant_data': tenant_data,
    }
    
    return render(request, 'reports/tenant_report.html', context)

# Export utility functions
def export_income_pdf(payments, total_income, start_date, end_date):
    """Generate PDF for income report."""
    buffer = io.BytesIO()
    
    # Create the PDF object, using the buffer as its "file."
    p = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Add title
    title = Paragraph(f"Income Report ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})", styles['Heading1'])
    elements.append(title)
    
    # Add total
    total = Paragraph(f"Total Income: ${total_income:.2f}", styles['Heading2'])
    elements.append(total)
    
    # Add payments table
    data = [['Date', 'Property', 'Tenant', 'Category', 'Amount']]
    
    for payment in payments:
        data.append([
            payment.payment_date.strftime('%Y-%m-%d'),
            payment.property.name,
            payment.tenant.full_name,
            payment.category.name if payment.category else 'N/A',
            f"${payment.amount:.2f}"
        ])
    
    # Create the table
    table = Table(data)
    
    # Style the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    
    table.setStyle(style)
    elements.append(table)
    
    # Write the PDF
    p.build(elements)
    
    # File response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="income_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf"'
    
    return response

def export_income_csv(payments, start_date, end_date):
    """Generate CSV for income report."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="income_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Property', 'Tenant', 'Category', 'Amount'])
    
    for payment in payments:
        writer.writerow([
            payment.payment_date.strftime('%Y-%m-%d'),
            payment.property.name,
            payment.tenant.full_name,
            payment.category.name if payment.category else 'N/A',
            payment.amount
        ])
    
    return response

def export_income_excel(payments, start_date, end_date):
    """Generate Excel for income report."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Income Report"
    
    # Add headers
    ws.append(['Date', 'Property', 'Tenant', 'Category', 'Amount'])
    
    # Add data
    for payment in payments:
        ws.append([
            payment.payment_date.strftime('%Y-%m-%d'),
            payment.property.name,
            payment.tenant.full_name,
            payment.category.name if payment.category else 'N/A',
            payment.amount
        ])
    
    # Create response
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="income_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.xlsx"'
    
    return response

# Similar export functions for expense_report, profit_loss_report, and tenant_report
# would be implemented here following the same pattern
