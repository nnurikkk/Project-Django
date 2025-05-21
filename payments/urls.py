"""
URL Configuration for the payments app.
"""
from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

@login_required
def payment_debug(request):
    queryset = Payment.objects.filter(rental_property__owner=request.user)
    form = PaymentFilterForm(request.GET or None, user=request.user)
    all_tenants = Tenant.objects.filter(leases__property__owner=request.user).distinct()
    
    context = {
        'form': form,
        'queryset': queryset,
        'payments': queryset,
        'all_tenants': all_tenants,
    }
    
    return render(request, 'payments/payment_debug.html', context)

urlpatterns = [
    # Payment CRUD
    path('', views.PaymentListView.as_view(), name='payment_list'),
    path('<int:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    path('create/', views.PaymentCreateView.as_view(), name='payment_create'),
    path('create/property/<int:property_id>/', views.PaymentCreateView.as_view(), name='payment_create_for_property'),
    path('create/tenant/<int:tenant_id>/', views.PaymentCreateView.as_view(), name='payment_create_for_tenant'),
    path('<int:pk>/update/', views.PaymentUpdateView.as_view(), name='payment_update'),
    path('<int:pk>/delete/', views.PaymentDeleteView.as_view(), name='payment_delete'),
    
    # Payment status updates
    path('<int:pk>/mark-as-paid/', views.mark_payment_as_paid, name='mark_payment_as_paid'),
    path('<int:pk>/add-late-fee/', views.add_late_fee, name='add_late_fee'),
    path('late-fee/<int:pk>/waive/', views.waive_late_fee, name='waive_late_fee'),
    
    # Payment categories
    path('categories/', views.PaymentCategoryListView.as_view(), name='payment_category_list'),
    path('categories/create/', views.PaymentCategoryCreateView.as_view(), name='payment_category_create'),
    path('categories/<int:pk>/update/', views.PaymentCategoryUpdateView.as_view(), name='payment_category_update'),
    path('categories/<int:pk>/delete/', views.PaymentCategoryDeleteView.as_view(), name='payment_category_delete'),
    
    # Batch operations
    path('create-recurring/', views.create_recurring_payments, name='create_recurring_payments'),
    path('export/', views.export_payments, name='export_payments'),
    path('debug/', views.payment_debug, name='payment_debug'),
    path('emergency-debug/', views.payment_emergency_debug, name='payment_emergency_debug'),
]
