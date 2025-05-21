"""
Tests for the tenants app.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from properties.models import Property, PropertyType
from .models import Tenant, Lease
from decimal import Decimal

class TenantModelTests(TestCase):
    """Tests for the Tenant model."""
    
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a tenant
        self.tenant = Tenant.objects.create(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='555-123-4567',
            created_by=self.user
        )
    
    def test_tenant_creation(self):
        """Test that a tenant can be created."""
        self.assertEqual(self.tenant.first_name, 'John')
        self.assertEqual(self.tenant.last_name, 'Doe')
        self.assertEqual(self.tenant.email, 'john.doe@example.com')
    
    def test_tenant_full_name(self):
        """Test the full_name property."""
        self.assertEqual(self.tenant.full_name, 'John Doe')
    
    def test_tenant_string_representation(self):
        """Test the string representation of a tenant."""
        self.assertEqual(str(self.tenant), 'John Doe')

class LeaseModelTests(TestCase):
    """Tests for the Lease model."""
    
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
        
        # Create a tenant
        self.tenant = Tenant.objects.create(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='555-123-4567',
            created_by=self.user
        )
        
        # Create a lease
        self.today = timezone.now().date()
        self.lease = Lease.objects.create(
            property=self.property,
            tenant=self.tenant,
            lease_type='fixed',
            start_date=self.today,
            end_date=self.today + timedelta(days=365),
            rent_amount=Decimal('1000.00'),
            security_deposit=Decimal('1000.00'),
            status='active',
            payment_day=1,
            created_by=self.user
        )
    
    def test_lease_creation(self):
        """Test that a lease can be created."""
        self.assertEqual(self.lease.property, self.property)
        self.assertEqual(self.lease.tenant, self.tenant)
        self.assertEqual(self.lease.rent_amount, Decimal('1000.00'))
        self.assertEqual(self.lease.status, 'active')
    
    def test_lease_is_active(self):
        """Test the is_active property."""
        self.assertTrue(self.lease.is_active)
        
        # Test with an inactive lease
        inactive_lease = Lease.objects.create(
            property=self.property,
            tenant=self.tenant,
            lease_type='fixed',
            start_date=self.today - timedelta(days=730),  # 2 years ago
            end_date=self.today - timedelta(days=365),    # 1 year ago
            rent_amount=Decimal('900.00'),
            security_deposit=Decimal('900.00'),
            status='completed',
            payment_day=1,
            created_by=self.user
        )
        self.assertFalse(inactive_lease.is_active)
    
    def test_lease_term_months(self):
        """Test the lease_term_months property."""
        self.assertEqual(self.lease.lease_term_months, 12)
        
        # Test with a shorter lease
        short_lease = Lease.objects.create(
            property=self.property,
            tenant=self.tenant,
            lease_type='fixed',
            start_date=self.today,
            end_date=self.today + timedelta(days=180),  # 6 months
            rent_amount=Decimal('900.00'),
            security_deposit=Decimal('900.00'),
            status='active',
            payment_day=1,
            created_by=self.user
        )
        self.assertEqual(short_lease.lease_term_months, 6)
    
    def test_days_until_expiration(self):
        """Test the days_until_expiration property."""
        self.assertEqual(self.lease.days_until_expiration, 365)
        
        # Test with an expired lease
        expired_lease = Lease.objects.create(
            property=self.property,
            tenant=self.tenant,
            lease_type='fixed',
            start_date=self.today - timedelta(days=730),  # 2 years ago
            end_date=self.today - timedelta(days=365),    # 1 year ago
            rent_amount=Decimal('900.00'),
            security_deposit=Decimal('900.00'),
            status='completed',
            payment_day=1,
            created_by=self.user
        )
        self.assertEqual(expired_lease.days_until_expiration, 0)

class TenantViewTests(TestCase):
    """Tests for the Tenant views."""
    
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
        
        # Create a tenant
        self.tenant = Tenant.objects.create(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='555-123-4567',
            created_by=self.user
        )
        
        # Create a lease to associate tenant with property
        self.today = timezone.now().date()
        self.lease = Lease.objects.create(
            property=self.property,
            tenant=self.tenant,
            lease_type='fixed',
            start_date=self.today,
            end_date=self.today + timedelta(days=365),
            rent_amount=Decimal('1000.00'),
            security_deposit=Decimal('1000.00'),
            status='active',
            payment_day=1,
            created_by=self.user
        )
    
    def test_tenant_list_view(self):
        """Test that the tenant list view displays tenants."""
        url = reverse('tenant_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertTemplateUsed(response, 'tenants/tenant_list.html')
    
    def test_tenant_detail_view(self):
        """Test that the tenant detail view displays the tenant."""
        url = reverse('tenant_detail', args=[self.tenant.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'john.doe@example.com')
        self.assertTemplateUsed(response, 'tenants/tenant_detail.html')
    
    def test_tenant_create_view(self):
        """Test that a tenant can be created."""
        url = reverse('tenant_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tenants/tenant_form.html')
        
        # Test POST request
        data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com',
            'phone': '555-987-6543',
        }
        
        response = self.client.post(url, data)
        
        # Check that we have one more tenant
        self.assertEqual(Tenant.objects.count(), 2)
        
        # Get the newest tenant
        new_tenant = Tenant.objects.get(email='jane.smith@example.com')
        
        # Check that it has the correct values
        self.assertEqual(new_tenant.first_name, 'Jane')
        self.assertEqual(new_tenant.last_name, 'Smith')
        self.assertEqual(new_tenant.phone, '555-987-6543')
    
    def test_tenant_update_view(self):
        """Test that a tenant can be updated."""
        url = reverse('tenant_update', args=[self.tenant.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tenants/tenant_form.html')
        
        # Test POST request
        data = {
            'first_name': 'Johnny',  # Changed from John
            'last_name': 'Doe',
            'email': 'johnny.doe@example.com',  # Changed
            'phone': '555-123-4567',
        }
        
        response = self.client.post(url, data)
        
        # Refresh from database
        self.tenant.refresh_from_db()
        
        # Check that it has the updated values
        self.assertEqual(self.tenant.first_name, 'Johnny')
        self.assertEqual(self.tenant.email, 'johnny.doe@example.com')

class LeaseViewTests(TestCase):
    """Tests for the Lease views."""
    
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
        
        # Create a tenant
        self.tenant = Tenant.objects.create(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='555-123-4567',
            created_by=self.user
        )
        
        # Create a lease
        self.today = timezone.now().date()
        self.lease = Lease.objects.create(
            property=self.property,
            tenant=self.tenant,
            lease_type='fixed',
            start_date=self.today,
            end_date=self.today + timedelta(days=365),
            rent_amount=Decimal('1000.00'),
            security_deposit=Decimal('1000.00'),
            status='active',
            payment_day=1,
            created_by=self.user
        )
    
    def test_lease_list_view(self):
        """Test that the lease list view displays leases."""
        url = reverse('lease_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Property')
        self.assertContains(response, 'John Doe')
        self.assertTemplateUsed(response, 'tenants/lease_list.html')
    
    def test_lease_detail_view(self):
        """Test that the lease detail view displays the lease."""
        url = reverse('lease_detail', args=[self.lease.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Property')
        self.assertContains(response, 'John Doe')
        self.assertContains(response, '$1,000.00')  # Rent amount
        self.assertTemplateUsed(response, 'tenants/lease_detail.html')
    
    def test_lease_create_view(self):
        """Test that a lease can be created."""
        url = reverse('lease_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tenants/lease_form.html')
        
        # Create another property for testing
        property2 = Property.objects.create(
            owner=self.user,
            property_type=self.property_type,
            name='Test Property 2',
            address='456 Test St',
            city='Test City',
            state='TS',
            zip_code='12345',
            monthly_rent=Decimal('1200.00'),
            security_deposit=Decimal('1200.00')
        )
        
        # Test POST request
        data = {
            'property': property2.id,
            'tenant': self.tenant.id,
            'lease_type': 'fixed',
            'start_date': (self.today + timedelta(days=30)).strftime('%Y-%m-%d'),
            'end_date': (self.today + timedelta(days=395)).strftime('%Y-%m-%d'),
            'rent_amount': '1200.00',
            'security_deposit': '1200.00',
            'status': 'pending',
            'payment_day': 1,
            'late_fee': '50.00',
            'grace_period': 5,
        }
        
        response = self.client.post(url, data)
        
        # Check that we have one more lease
        self.assertEqual(Lease.objects.count(), 2)
        
        # Get the newest lease
        new_lease = Lease.objects.latest('date_created')
        
        # Check that it has the correct values
        self.assertEqual(new_lease.property, property2)
        self.assertEqual(new_lease.tenant, self.tenant)
        self.assertEqual(new_lease.rent_amount, Decimal('1200.00'))
        self.assertEqual(new_lease.status, 'pending')
    
    def test_lease_update_view(self):
        """Test that a lease can be updated."""
        url = reverse('lease_update', args=[self.lease.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tenants/lease_form.html')
        
        # Test POST request
        data = {
            'property': self.property.id,
            'tenant': self.tenant.id,
            'lease_type': 'fixed',
            'start_date': self.today.strftime('%Y-%m-%d'),
            'end_date': (self.today + timedelta(days=365)).strftime('%Y-%m-%d'),
            'rent_amount': '1100.00',  # Changed from 1000.00
            'security_deposit': '1000.00',
            'status': 'active',
            'payment_day': 1,
            'late_fee': '50.00',
            'grace_period': 7,  # Changed from 5
        }
        
        response = self.client.post(url, data)
        
        # Refresh from database
        self.lease.refresh_from_db()
        
        # Check that it has the updated values
        self.assertEqual(self.lease.rent_amount, Decimal('1100.00'))
        self.assertEqual(self.lease.grace_period, 7)
