"""
URL Configuration for the reports app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('income/', views.income_report, name='income_report'),
    path('expenses/', views.expense_report, name='expense_report'),
    path('profit-loss/', views.profit_loss_report, name='profit_loss_report'),
    path('tenants/', views.tenant_report, name='tenant_report'),
]
