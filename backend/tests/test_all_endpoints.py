"""
Comprehensive Backend API Tests for Belt Conveyor Engineering ERP
Tests all critical endpoints: Auth, Products, Sales, CRM, Cart, Customers, Admin, Exports
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://erp-conveyor.preview.emergentagent.com')
if not BASE_URL.endswith('/api'):
    BASE_URL = BASE_URL.rstrip('/') + '/api'

# Test credentials
ADMIN_EMAIL = "test@test.com"
ADMIN_PASSWORD = "test123"
CUSTOMER_EMAIL = "customer@test.com"
CUSTOMER_PASSWORD = "test123"


class TestAuth:
    """Authentication endpoint tests"""
    
    def test_admin_login(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data or "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        print(f"✓ Admin login successful - user: {data.get('user', {}).get('email')}")
    
    def test_customer_login(self):
        """Test customer login with valid credentials"""
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "email": CUSTOMER_EMAIL,
            "password": CUSTOMER_PASSWORD
        })
        assert response.status_code == 200, f"Customer login failed: {response.text}"
        data = response.json()
        assert "access_token" in data or "token" in data, "No token in response"
        print(f"✓ Customer login successful - user: {data.get('user', {}).get('email')}")
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 400], f"Expected 401/400, got {response.status_code}"
        print("✓ Invalid login correctly rejected")


@pytest.fixture
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture
def customer_token():
    """Get customer authentication token"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": CUSTOMER_EMAIL,
        "password": CUSTOMER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip("Customer authentication failed")


@pytest.fixture
def admin_headers(admin_token):
    """Get headers with admin auth"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture
def customer_headers(customer_token):
    """Get headers with customer auth"""
    return {"Authorization": f"Bearer {customer_token}", "Content-Type": "application/json"}


class TestProducts:
    """Products/Calculator endpoint tests"""
    
    def test_roller_standards(self, admin_headers):
        """Test roller standards endpoint"""
        response = requests.get(f"{BASE_URL}/roller-standards", headers=admin_headers)
        assert response.status_code == 200, f"Roller standards failed: {response.text}"
        data = response.json()
        assert "pipe_diameters" in data, "Missing pipe_diameters"
        assert "shaft_diameters" in data, "Missing shaft_diameters"
        print(f"✓ Roller standards loaded - {len(data.get('pipe_diameters', []))} pipe diameters")
    
    def test_pulley_standards(self, admin_headers):
        """Test pulley standards endpoint"""
        response = requests.get(f"{BASE_URL}/pulley-standards", headers=admin_headers)
        assert response.status_code == 200, f"Pulley standards failed: {response.text}"
        data = response.json()
        assert "pipe_diameters" in data, "Missing pipe_diameters"
        assert "pulley_types" in data, "Missing pulley_types"
        print(f"✓ Pulley standards loaded - {len(data.get('pulley_types', []))} pulley types")
    
    def test_roller_price_calculation(self, admin_headers):
        """Test roller price calculation"""
        payload = {
            "roller_type": "carrying",
            "pipe_diameter": 88.9,
            "pipe_length": 500,
            "shaft_diameter": 25,
            "bearing_number": "6205",
            "bearing_make": "skf",
            "pipe_type": "B",
            "quantity": 10,
            "packing_type": "standard"
        }
        response = requests.post(f"{BASE_URL}/calculate-detailed-cost", json=payload, headers=admin_headers)
        assert response.status_code == 200, f"Roller calculation failed: {response.text}"
        data = response.json()
        assert "pricing" in data, "Missing pricing"
        assert "configuration" in data, "Missing configuration"
        assert data["pricing"]["unit_price"] > 0, "Unit price should be > 0"
        print(f"✓ Roller calculation - Unit price: Rs.{data['pricing']['unit_price']:.2f}")
    
    def test_pulley_price_calculation(self, admin_headers):
        """Test pulley price calculation"""
        payload = {
            "pulley_type": "Drive",
            "pipe_diameter": 219,
            "pipe_thickness": 8,
            "face_length": 500,
            "shaft_diameter_centre": 80,
            "shaft_material": "MS",
            "shaft_length": 700,
            "end_plate_thickness": 12,
            "end_plate_qty": 2,
            "hub_type": "no_hub",
            "quantity": 1,
            "packing_type": "none"
        }
        response = requests.post(f"{BASE_URL}/calculate-pulley-cost", json=payload, headers=admin_headers)
        assert response.status_code == 200, f"Pulley calculation failed: {response.text}"
        data = response.json()
        assert "pricing" in data, "Missing pricing"
        assert "configuration" in data, "Missing configuration"
        assert data["pricing"]["unit_price"] > 0, "Unit price should be > 0"
        print(f"✓ Pulley calculation - Unit price: Rs.{data['pricing']['unit_price']:.2f}")
    
    def test_product_search(self, admin_headers):
        """Test product catalog search"""
        response = requests.get(f"{BASE_URL}/search/product-catalog", params={"query": "89"}, headers=admin_headers)
        assert response.status_code == 200, f"Product search failed: {response.text}"
        data = response.json()
        assert "results" in data, "Missing results"
        print(f"✓ Product search - Found {len(data.get('results', []))} results for '89'")


class TestQuotes:
    """Quotes/Sales endpoint tests"""
    
    def test_get_quotes(self, admin_headers):
        """Test get all quotes"""
        response = requests.get(f"{BASE_URL}/quotes", headers=admin_headers)
        assert response.status_code == 200, f"Get quotes failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of quotes"
        print(f"✓ Get quotes - Found {len(data)} quotes")
    
    def test_quotes_export_excel(self, admin_headers):
        """Test quotes Excel export"""
        response = requests.get(f"{BASE_URL}/quotes/export/excel", headers=admin_headers)
        assert response.status_code == 200, f"Quotes Excel export failed: {response.text}"
        assert "spreadsheet" in response.headers.get("Content-Type", "") or "octet-stream" in response.headers.get("Content-Type", ""), "Expected Excel file"
        print(f"✓ Quotes Excel export - Size: {len(response.content)} bytes")
    
    def test_quotes_export_pdf(self, admin_headers):
        """Test quotes PDF export"""
        response = requests.get(f"{BASE_URL}/quotes/export/pdf", headers=admin_headers)
        assert response.status_code == 200, f"Quotes PDF export failed: {response.text}"
        print(f"✓ Quotes PDF export - Size: {len(response.content)} bytes")


class TestOrders:
    """Orders endpoint tests"""
    
    def test_get_orders(self, admin_headers):
        """Test get all orders"""
        response = requests.get(f"{BASE_URL}/orders", headers=admin_headers)
        assert response.status_code == 200, f"Get orders failed: {response.text}"
        data = response.json()
        assert "orders" in data, "Missing orders key"
        print(f"✓ Get orders - Found {len(data.get('orders', []))} orders")
    
    def test_orders_export_excel(self, admin_headers):
        """Test orders Excel export"""
        response = requests.get(f"{BASE_URL}/orders/export/excel", headers=admin_headers)
        assert response.status_code == 200, f"Orders Excel export failed: {response.text}"
        print(f"✓ Orders Excel export - Size: {len(response.content)} bytes")
    
    def test_orders_summary_stats(self, admin_headers):
        """Test orders summary statistics"""
        response = requests.get(f"{BASE_URL}/orders/summary/stats", headers=admin_headers)
        assert response.status_code == 200, f"Orders summary failed: {response.text}"
        data = response.json()
        assert "total_orders" in data, "Missing total_orders"
        print(f"✓ Orders summary - Total orders: {data.get('total_orders', 0)}")


class TestCRM:
    """CRM endpoint tests"""
    
    def test_crm_summary(self, admin_headers):
        """Test CRM summary"""
        response = requests.get(f"{BASE_URL}/crm/summary", headers=admin_headers)
        assert response.status_code == 200, f"CRM summary failed: {response.text}"
        data = response.json()
        assert "total_leads" in data, "Missing total_leads"
        print(f"✓ CRM summary - Total leads: {data.get('total_leads', 0)}")
    
    def test_crm_leads(self, admin_headers):
        """Test get CRM leads"""
        response = requests.get(f"{BASE_URL}/crm/leads", headers=admin_headers)
        assert response.status_code == 200, f"CRM leads failed: {response.text}"
        data = response.json()
        assert "leads" in data, "Missing leads key"
        print(f"✓ CRM leads - Found {len(data.get('leads', []))} leads")
    
    def test_crm_followups(self, admin_headers):
        """Test get CRM follow-ups"""
        response = requests.get(f"{BASE_URL}/crm/followups", headers=admin_headers)
        assert response.status_code == 200, f"CRM followups failed: {response.text}"
        data = response.json()
        assert "followups" in data, "Missing followups key"
        print(f"✓ CRM followups - Found {len(data.get('followups', []))} follow-ups")
    
    def test_crm_activities(self, admin_headers):
        """Test get CRM activities"""
        response = requests.get(f"{BASE_URL}/crm/activities", headers=admin_headers)
        assert response.status_code == 200, f"CRM activities failed: {response.text}"
        data = response.json()
        assert "activities" in data, "Missing activities key"
        print(f"✓ CRM activities - Found {len(data.get('activities', []))} activities")
    
    def test_crm_leads_export_excel(self, admin_headers):
        """Test CRM leads Excel export"""
        response = requests.get(f"{BASE_URL}/crm/leads/export/excel", headers=admin_headers)
        assert response.status_code == 200, f"CRM leads export failed: {response.text}"
        print(f"✓ CRM leads Excel export - Size: {len(response.content)} bytes")
    
    def test_crm_followups_export_excel(self, admin_headers):
        """Test CRM follow-ups Excel export"""
        response = requests.get(f"{BASE_URL}/crm/followups/export/excel", headers=admin_headers)
        assert response.status_code == 200, f"CRM followups export failed: {response.text}"
        print(f"✓ CRM followups Excel export - Size: {len(response.content)} bytes")
    
    def test_create_lead(self, admin_headers):
        """Test create new lead"""
        payload = {
            "name": f"TEST_Lead_{int(time.time())}",
            "company": "Test Company",
            "email": "testlead@example.com",
            "phone": "9876543210",
            "source": "phone",
            "product_interest": "roller",
            "estimated_value": 50000,
            "notes": "Test lead created by automated test"
        }
        response = requests.post(f"{BASE_URL}/crm/leads", json=payload, headers=admin_headers)
        assert response.status_code in [200, 201], f"Create lead failed: {response.text}"
        data = response.json()
        # Response can have id at root or nested in lead object
        lead_id = data.get("id") or data.get("lead", {}).get("id")
        assert lead_id, "Missing lead id"
        print(f"✓ Create lead - ID: {lead_id}")
        return data.get("id")


class TestCustomers:
    """Customers endpoint tests"""
    
    def test_get_customers(self, admin_headers):
        """Test get all customers"""
        response = requests.get(f"{BASE_URL}/customers", headers=admin_headers)
        assert response.status_code == 200, f"Get customers failed: {response.text}"
        data = response.json()
        assert "customers" in data, "Missing customers key"
        print(f"✓ Get customers - Found {len(data.get('customers', []))} customers")
    
    def test_customers_export_excel(self, admin_headers):
        """Test customers Excel export"""
        response = requests.get(f"{BASE_URL}/customers/export/excel", headers=admin_headers)
        assert response.status_code == 200, f"Customers export failed: {response.text}"
        print(f"✓ Customers Excel export - Size: {len(response.content)} bytes")


class TestInvoices:
    """Invoices endpoint tests"""
    
    def test_get_invoices(self, admin_headers):
        """Test get all invoices"""
        response = requests.get(f"{BASE_URL}/invoices", headers=admin_headers)
        assert response.status_code == 200, f"Get invoices failed: {response.text}"
        data = response.json()
        assert "invoices" in data, "Missing invoices key"
        print(f"✓ Get invoices - Found {len(data.get('invoices', []))} invoices")
    
    def test_invoices_export_excel(self, admin_headers):
        """Test invoices Excel export"""
        response = requests.get(f"{BASE_URL}/invoices/export/excel", headers=admin_headers)
        assert response.status_code == 200, f"Invoices export failed: {response.text}"
        print(f"✓ Invoices Excel export - Size: {len(response.content)} bytes")


class TestCommercialTerms:
    """Commercial terms endpoint tests"""
    
    def test_commercial_terms_options(self, admin_headers):
        """Test get commercial terms options"""
        response = requests.get(f"{BASE_URL}/commercial-terms-options", headers=admin_headers)
        assert response.status_code == 200, f"Commercial terms failed: {response.text}"
        data = response.json()
        print(f"✓ Commercial terms options loaded")


class TestCustomerFlow:
    """Customer-specific flow tests"""
    
    def test_customer_can_view_quotes(self, customer_headers):
        """Test customer can view their quotes"""
        response = requests.get(f"{BASE_URL}/quotes", headers=customer_headers)
        assert response.status_code == 200, f"Customer quotes failed: {response.text}"
        print("✓ Customer can view quotes")
    
    def test_customer_roller_calculation(self, customer_headers):
        """Test customer can calculate roller price"""
        payload = {
            "roller_type": "carrying",
            "pipe_diameter": 88.9,
            "pipe_length": 500,
            "shaft_diameter": 25,
            "bearing_number": "6205",
            "bearing_make": "skf",
            "pipe_type": "B",
            "quantity": 5,
            "packing_type": "standard"
        }
        response = requests.post(f"{BASE_URL}/calculate-detailed-cost", json=payload, headers=customer_headers)
        assert response.status_code == 200, f"Customer roller calc failed: {response.text}"
        print("✓ Customer can calculate roller price")


class TestAuthRequired:
    """Test endpoints require authentication"""
    
    def test_quotes_require_auth(self):
        """Test quotes endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/quotes")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Quotes endpoint requires authentication")
    
    def test_orders_require_auth(self):
        """Test orders endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/orders")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Orders endpoint requires authentication")
    
    def test_crm_requires_auth(self):
        """Test CRM endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/crm/leads")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ CRM endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
