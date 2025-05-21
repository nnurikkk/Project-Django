"""
URL Configuration for the tenants app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Tenant CRUD
    path('', views.TenantListView.as_view(), name='tenant_list'),
    path('<int:pk>/', views.TenantDetailView.as_view(), name='tenant_detail'),
    path('create/', views.TenantCreateView.as_view(), name='tenant_create'),
    path('<int:pk>/update/', views.TenantUpdateView.as_view(), name='tenant_update'),
    path('<int:pk>/delete/', views.TenantDeleteView.as_view(), name='tenant_delete'),
    
    # Lease CRUD
    path('leases/', views.LeaseListView.as_view(), name='lease_list'),
    path('leases/<int:pk>/', views.LeaseDetailView.as_view(), name='lease_detail'),
    path('leases/create/', views.LeaseCreateView.as_view(), name='lease_create'),
    path('leases/create/property/<int:property_id>/', views.LeaseCreateView.as_view(), name='lease_create_for_property'),
    path('leases/create/tenant/<int:tenant_id>/', views.LeaseCreateView.as_view(), name='lease_create_for_tenant'),
    path('leases/<int:pk>/update/', views.LeaseUpdateView.as_view(), name='lease_update'),
    path('leases/<int:pk>/delete/', views.LeaseDeleteView.as_view(), name='lease_delete'),
    path('leases/<int:pk>/renew/', views.renew_lease, name='lease_renew'),
    path('leases/<int:pk>/terminate/', views.terminate_lease, name='lease_terminate'),
    
    # Lease documents
    path('leases/<int:pk>/add-document/', views.add_lease_document, name='add_lease_document'),
    path('lease-document/<int:pk>/delete/', views.delete_lease_document, name='delete_lease_document'),
    
    # Export and import
    path('export/', views.export_tenants, name='export_tenants'),
    path('leases/export/', views.export_leases, name='export_leases'),
]
