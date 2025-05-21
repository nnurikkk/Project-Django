"""
URL Configuration for the properties app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Property CRUD
    path('', views.PropertyListView.as_view(), name='property_list'),
    path('<int:pk>/', views.PropertyDetailView.as_view(), name='property_detail'),
    path('create/', views.PropertyCreateView.as_view(), name='property_create'),
    path('<int:pk>/update/', views.PropertyUpdateView.as_view(), name='property_update'),
    path('<int:pk>/delete/', views.PropertyDeleteView.as_view(), name='property_delete'),
    
    # Property images
    path('<int:pk>/add-image/', views.add_property_image, name='add_property_image'),
    path('image/<int:pk>/delete/', views.delete_property_image, name='delete_property_image'),
    
    # Property documents
    path('<int:pk>/add-document/', views.add_property_document, name='add_property_document'),
    path('document/<int:pk>/delete/', views.delete_property_document, name='delete_property_document'),
]
