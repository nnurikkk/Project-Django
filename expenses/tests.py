"""
Test cases for the expenses app.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from properties.models import Property, PropertyType
from .models import Expense, ExpenseCategory, Vendor
from decimal import Decimal
from datetime import date

class ExpenseModelTests(TestCase):
    """Tests for the Expense model."""
    
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a property type
        self.property_type = PropertyType.objects.create(
            name='Apartment',
            description='Residential apartment'
        )
        
        # Create a property
        self.property = Property.objects.create(
            owner=self.user,
            property_type=self.property_type,
            name='Test Property',
            address='123 Test St',
            city='Test City',
            state='TS',
            zip_code='12345',
            monthly_rent=Decimal('1000.00'),
            security_deposit=Decimal('1000.00')
        )
        
        # Create an expense category
        self.category = ExpenseCategory.objects.create(
            name='Maintenance',
            description='Property maintenance expenses'
        )
        
        # Create a vendor
        self.vendor = Vendor.objects.create(
            name='Test Vendor',
            contact_person='John Doe',
            email='vendor@example.com',
            phone='123-456-7890',
            created_by=self.user
        )
        
        # Create an expense
        self.expense = Expense.objects.create(
            property=self.property,
            category=self.category,
            vendor=self.vendor,
            amount=Decimal('250.00'),
            date=date.today(),
            description='Test expense',
            status='paid',
            tax_deductible=True,
            created_by=self.user
        )
    
    def test_expense_creation(self):
        """Test that an expense can be created."""
        self.assertEqual(self.expense.property, self.property)
        self.assertEqual(self.expense.category, self.category)
        self.assertEqual(self.expense.vendor, self.vendor)
        self.assertEqual(self.expense.amount, Decimal('250.00'))
        self.assertEqual(self.expense.status, 'paid')
        self.assertTrue(self.expense.tax_deductible)
    
    def test_expense_str(self):
        """Test the string representation of an expense."""
        expected_str = f"${self.expense.amount} - {self.expense.description} - {self.property.name}"
        self.assertEqual(str(self.expense), expected_str)

class ExpenseViewTests(TestCase):
    """Tests for the Expense views."""
    
    def setUp(self):
        # Create a user and login
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpassword')
        
        # Create a property type
        self.property_type = PropertyType.objects.create(
            name='Apartment',
            description='Residential apartment'
        )
        
        # Create a property
        self.property = Property.objects.create(
            owner=self.user,
            property_type=self.property_type,
            name='Test Property',
            address='123 Test St',
            city='Test City',
            state='TS',
            zip_code='12345',
            monthly_rent=Decimal('1000.00'),
            security_deposit=Decimal('1000.00')
        )
        
        # Create an expense category
        self.category = ExpenseCategory.objects.create(
            name='Maintenance',
            description='Property maintenance expenses'
        )
        
        # Create a vendor
        self.vendor = Vendor.objects.create(
            name='Test Vendor',
            contact_person='John Doe',
            email='vendor@example.com',
            phone='123-456-7890',
            created_by=self.user
        )
        
        # Create an expense
        self.expense = Expense.objects.create(
            property=self.property,
            category=self.category,
            vendor=self.vendor,
            amount=Decimal('250.00'),
            date=date.today(),
            description='Test expense',
            status='paid',
            tax_deductible=True,
            created_by=self.user
        )
    
    def test_expense_list_view(self):
        """Test that the expense list view displays expenses."""
        url = reverse('expense_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test expense')
        self.assertContains(response, '250.00')
        self.assertTemplateUsed(response, 'expenses/expense_list.html')
    
    def test_expense_detail_view(self):
        """Test that the expense detail view displays the expense."""
        url = reverse('expense_detail', args=[self.expense.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test expense')
        self.assertContains(response, '250.00')
        self.assertContains(response, 'Test Vendor')
        self.assertTemplateUsed(response, 'expenses/expense_detail.html')
    
    def test_expense_create_view(self):
        """Test that an expense can be created."""
        url = reverse('expense_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'expenses/expense_form.html')
        
        # Test POST request
        data = {
            'property': self.property.id,
            'category': self.category.id,
            'vendor': self.vendor.id,
            'amount': '150.00',
            'date': date.today().strftime('%Y-%m-%d'),
            'description': 'New test expense',
            'status': 'pending',
            'tax_deductible': True
        }
        
        response = self.client.post(url, data)
        
        # Check that we have one more expense
        self.assertEqual(Expense.objects.count(), 2)
        
        # Get the newest expense
        new_expense = Expense.objects.latest('date_created')
        
        # Check that it has the correct values
        self.assertEqual(new_expense.property, self.property)
        self.assertEqual(new_expense.amount, Decimal('150.00'))
        self.assertEqual(new_expense.description, 'New test expense')
    
    def test_expense_update_view(self):
        """Test that an expense can be updated."""
        url = reverse('expense_update', args=[self.expense.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'expenses/expense_form.html')
        
        # Test POST request
        data = {
            'property': self.property.id,
            'category': self.category.id,
            'vendor': self.vendor.id,
            'amount': '300.00',  # Changed value
            'date': date.today().strftime('%Y-%m-%d'),
            'description': 'Updated test expense',  # Changed value
            'status': 'paid',
            'tax_deductible': True
        }
        
        response = self.client.post(url, data)
        
        # Refresh from database
        self.expense.refresh_from_db()
        
        # Check that it has the updated values
        self.assertEqual(self.expense.amount, Decimal('300.00'))
        self.assertEqual(self.expense.description, 'Updated test expense')
    
    def test_expense_delete_view(self):
        """Test that an expense can be deleted."""
        url = reverse('expense_delete', args=[self.expense.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'expenses/expense_confirm_delete.html')
        
        # Test POST request
        response = self.client.post(url)
        
        # Check that the expense is deleted
        self.assertEqual(Expense.objects.count(), 0)
