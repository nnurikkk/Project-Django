"""
URL Configuration for the expenses app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Expense CRUD
    path('', views.ExpenseListView.as_view(), name='expense_list'),
    path('<int:pk>/', views.ExpenseDetailView.as_view(), name='expense_detail'),
    path('create/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('<int:pk>/update/', views.ExpenseUpdateView.as_view(), name='expense_update'),
    path('<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense_delete'),
    
    # Expense documents
    path('<int:pk>/add-document/', views.add_expense_document, name='add_expense_document'),
    path('document/<int:pk>/delete/', views.delete_expense_document, name='delete_expense_document'),
    
    # Categories and vendors
    path('categories/', views.ExpenseCategoryListView.as_view(), name='expense_category_list'),
    path('categories/create/', views.ExpenseCategoryCreateView.as_view(), name='expense_category_create'),
    path('categories/<int:pk>/update/', views.ExpenseCategoryUpdateView.as_view(), name='expense_category_update'),
    path('categories/<int:pk>/delete/', views.ExpenseCategoryDeleteView.as_view(), name='expense_category_delete'),
    
    path('vendors/', views.VendorListView.as_view(), name='vendor_list'),
    path('vendors/create/', views.VendorCreateView.as_view(), name='vendor_create'),
    path('vendors/<int:pk>/', views.VendorDetailView.as_view(), name='vendor_detail'),
    path('vendors/<int:pk>/update/', views.VendorUpdateView.as_view(), name='vendor_update'),
    path('vendors/<int:pk>/delete/', views.VendorDeleteView.as_view(), name='vendor_delete'),
]
