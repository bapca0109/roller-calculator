"""
Comprehensive Backend Tests for Belt Conveyor Roller Price Calculator App

Tests: Login, Calculator, Products/Search, Cart, Quotes, Customers, Admin, Profile features
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://belt-price-engine.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "test@test.com"
ADMIN_PASSWORD = "test123"
CUSTOMER_EMAIL = "customer@test.com"
CUSTOMER_PASSWORD = "test123"


@pytest.fixture(scope="module")
def admin_session():
    """Create authenticated admin session"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    session.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    return session


@pytest.fixture(scope="module")
def customer_session():
    """Create authenticated customer session"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": CUSTOMER_EMAIL,
        "password": CUSTOMER_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Customer login failed - customer account may not exist")
    data = response.json()
    session.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    return session


class TestAuthentication:
    """Test LOGIN and authentication flows"""
    
    def test_admin_login_success(self):
        """Test admin login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["role"] == "admin"
        print(f"Admin login successful - role: {data['user']['role']}")
    
    def test_customer_login_success(self):
        """Test customer login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CUSTOMER_EMAIL,
            "password": CUSTOMER_PASSWORD
        })
        # Customer might not exist, so skip if 401
        if response.status_code == 401:
            pytest.skip("Customer account doesn't exist")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "customer"
        print(f"Customer login successful - role: {data['user']['role']}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@email.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 404]
        print("Invalid credentials correctly rejected")


class TestCalculator:
    """Test CALCULATOR TAB functionality"""
    
    def test_get_roller_standards(self, admin_session):
        """Test fetching roller standards (pipe/shaft diameters, bearings)"""
        response = admin_session.get(f"{BASE_URL}/api/roller-standards")
        assert response.status_code == 200
        data = response.json()
        
        # Check for required fields
        assert "pipe_diameters" in data
        assert "shaft_diameters" in data
        assert "bearing_options" in data
        
        print(f"Roller standards: {len(data['pipe_diameters'])} pipe diameters, {len(data['shaft_diameters'])} shaft diameters")
    
    def test_calculate_carrying_roller_price(self, admin_session):
        """Test price calculation for carrying roller"""
        response = admin_session.post(f"{BASE_URL}/api/calculate-detailed-cost", json={
            "roller_type": "carrying",
            "pipe_diameter": 88.9,
            "pipe_length": 1000,
            "pipe_type": "B",
            "shaft_diameter": 25,
            "bearing_number": "6205",
            "bearing_make": "china",
            "quantity": 1,
            "packing_type": "standard"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "configuration" in data
        assert "cost_breakdown" in data
        assert "pricing" in data
        assert data["configuration"]["roller_type"] == "carrying"
        
        print(f"Carrying roller price: Rs. {data['pricing']['unit_price']}")
    
    def test_calculate_impact_roller_price(self, admin_session):
        """Test price calculation for impact roller"""
        response = admin_session.post(f"{BASE_URL}/api/calculate-detailed-cost", json={
            "roller_type": "impact",
            "pipe_diameter": 88.9,
            "pipe_length": 1000,
            "pipe_type": "B",
            "shaft_diameter": 25,
            "bearing_number": "6205",
            "bearing_make": "china",
            "rubber_diameter": 127,
            "quantity": 1,
            "packing_type": "standard"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["configuration"]["roller_type"] == "impact"
        print(f"Impact roller price: Rs. {data['pricing']['unit_price']}")
    
    def test_calculate_return_roller_price(self, admin_session):
        """Test price calculation for return roller"""
        response = admin_session.post(f"{BASE_URL}/api/calculate-detailed-cost", json={
            "roller_type": "return",
            "pipe_diameter": 88.9,
            "pipe_length": 1000,
            "pipe_type": "B",
            "shaft_diameter": 25,
            "bearing_number": "6205",
            "bearing_make": "china",
            "quantity": 1,
            "packing_type": "standard"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["configuration"]["roller_type"] == "return"
        print(f"Return roller price: Rs. {data['pricing']['unit_price']}")
    
    def test_get_compatible_shafts(self, admin_session):
        """Test getting compatible shaft diameters for a pipe diameter"""
        response = admin_session.get(f"{BASE_URL}/api/compatible-shafts/88.9")
        assert response.status_code == 200
        data = response.json()
        assert "compatible_shafts" in data
        print(f"Compatible shafts for 88.9mm pipe: {data['compatible_shafts']}")
    
    def test_get_compatible_bearings(self, admin_session):
        """Test getting compatible bearings for pipe/shaft combination"""
        response = admin_session.get(f"{BASE_URL}/api/compatible-bearings-for-pipe/88.9/25")
        assert response.status_code == 200
        data = response.json()
        assert "compatible_bearings" in data
        print(f"Compatible bearings: {len(data['compatible_bearings'])} options")


class TestProductSearch:
    """Test PRODUCTS/SEARCH TAB functionality"""
    
    def test_search_products_by_code(self, admin_session):
        """Test searching products by product code"""
        response = admin_session.get(f"{BASE_URL}/api/search/product-catalog", params={"query": "CR"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        print(f"Found {len(data['results'])} products for 'CR'")
    
    def test_search_products_by_diameter(self, admin_session):
        """Test searching products by diameter"""
        response = admin_session.get(f"{BASE_URL}/api/search/product-catalog", params={"query": "89"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        print(f"Found {len(data['results'])} products for '89'")
    
    def test_search_products_by_bearing(self, admin_session):
        """Test searching products by bearing number"""
        response = admin_session.get(f"{BASE_URL}/api/search/product-catalog", params={"query": "6205"})
        assert response.status_code == 200
        data = response.json()
        print(f"Found {len(data.get('results', []))} products for '6205'")
    
    def test_search_empty_query_fails(self, admin_session):
        """Test that empty search query returns error"""
        response = admin_session.get(f"{BASE_URL}/api/search/product-catalog", params={"query": ""})
        # Empty query should return 422 or 400
        assert response.status_code in [400, 422]
        print("Empty query correctly rejected")


class TestCart:
    """Test CART TAB functionality - via Quote creation"""
    
    def test_calculate_freight(self, admin_session):
        """Test freight calculation for cart items"""
        response = admin_session.post(f"{BASE_URL}/api/calculate-freight", json={
            "pincode": "382433",
            "total_weight_kg": 100
        })
        assert response.status_code == 200
        data = response.json()
        assert "freight_charges" in data
        print(f"Freight charges: Rs. {data['freight_charges']}")


class TestQuotes:
    """Test QUOTES TAB functionality"""
    
    def test_get_quotes_list(self, admin_session):
        """Test fetching quotes list"""
        response = admin_session.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} quotes")
    
    def test_quotes_have_required_fields(self, admin_session):
        """Test that quotes have required fields for display"""
        response = admin_session.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        quotes = response.json()
        
        if len(quotes) > 0:
            quote = quotes[0]
            # Check for required display fields
            assert "quote_number" in quote or "id" in quote
            assert "status" in quote
            assert "products" in quote
            assert "total_price" in quote
            print(f"Quote fields present: quote_number, status, products, total_price")
    
    def test_create_quote_with_products(self, admin_session):
        """Test creating a new quote with products"""
        # First get a customer
        customers_response = admin_session.get(f"{BASE_URL}/api/customers")
        assert customers_response.status_code == 200
        customers = customers_response.json().get("customers", [])
        
        customer_id = None
        if customers:
            customer_id = customers[0].get("id")
        
        response = admin_session.post(f"{BASE_URL}/api/quotes", json={
            "products": [{
                "product_id": "TEST-CR25-88-1000B",
                "product_name": "Test Carrying Roller",
                "quantity": 10,
                "unit_price": 500.0,
                "specifications": {
                    "pipe_diameter": 88.9,
                    "pipe_length": 1000,
                    "shaft_diameter": 25
                }
            }],
            "customer_id": customer_id,
            "delivery_location": "382433",
            "packing_type": "standard",
            "notes": "Test quote from pytest"
        })
        assert response.status_code == 200
        data = response.json()
        assert "quote_number" in data
        print(f"Created quote: {data['quote_number']}")
        return data["id"]


class TestCustomers:
    """Test CUSTOMERS TAB functionality"""
    
    def test_get_customers_list(self, admin_session):
        """Test fetching customers list"""
        response = admin_session.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200
        data = response.json()
        assert "customers" in data
        print(f"Found {len(data['customers'])} customers")
    
    def test_search_customers(self, admin_session):
        """Test searching customers"""
        response = admin_session.get(f"{BASE_URL}/api/customers", params={"search": "test"})
        assert response.status_code == 200
        data = response.json()
        print(f"Found {len(data.get('customers', []))} customers matching 'test'")


class TestAdmin:
    """Test ADMIN TAB functionality"""
    
    def test_get_prices_basic(self, admin_session):
        """Test fetching basic prices"""
        response = admin_session.get(f"{BASE_URL}/api/admin/prices")
        assert response.status_code == 200
        data = response.json()
        
        # Check for expected price categories
        assert "basic_rates" in data
        assert "bearing_costs" in data
        assert "housing_costs" in data
        assert "seal_costs" in data
        assert "circlip_costs" in data
        assert "rubber_ring_costs" in data
        assert "locking_ring_costs" in data
        
        print(f"Pipe cost: Rs. {data['basic_rates']['pipe_cost_per_kg']}/kg")
        print(f"Shaft cost: Rs. {data['basic_rates']['shaft_cost_per_kg']}/kg")
    
    def test_get_standards_summary(self, admin_session):
        """Test fetching standards summary"""
        response = admin_session.get(f"{BASE_URL}/api/admin/standards-summary")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        print(f"Standards collections: {len(data['summary'])}")
    
    def test_update_price(self, admin_session):
        """Test updating a price (and then reset)"""
        # Get current price
        response = admin_session.get(f"{BASE_URL}/api/admin/prices")
        original_pipe_cost = response.json()["basic_rates"]["pipe_cost_per_kg"]
        
        # Update price (temporarily)
        new_price = original_pipe_cost + 1
        update_response = admin_session.post(f"{BASE_URL}/api/admin/prices/update", json={
            "category": "pipe_cost",
            "key": "pipe_cost_per_kg",
            "sub_key": None,
            "value": new_price
        })
        assert update_response.status_code == 200
        print(f"Updated pipe cost from {original_pipe_cost} to {new_price}")
        
        # Reset to original
        reset_response = admin_session.post(f"{BASE_URL}/api/admin/prices/update", json={
            "category": "pipe_cost",
            "key": "pipe_cost_per_kg",
            "sub_key": None,
            "value": original_pipe_cost
        })
        assert reset_response.status_code == 200
        print(f"Reset pipe cost back to {original_pipe_cost}")


class TestProfile:
    """Test PROFILE TAB functionality"""
    
    def test_get_current_user(self, admin_session):
        """Test getting current user info for profile display"""
        # The user info is returned during login, verify the token works
        response = admin_session.get(f"{BASE_URL}/api/quotes")  # Any authenticated endpoint
        assert response.status_code == 200
        print("Token is valid - user profile accessible")
    
    def test_logout_clears_session(self):
        """Test that without token, requests are rejected"""
        response = requests.get(f"{BASE_URL}/api/quotes")
        assert response.status_code in [401, 403]
        print("Unauthenticated requests correctly rejected")


class TestQuoteWorkflow:
    """Test complete RFQ/Quote workflow"""
    
    def test_get_pending_rfqs(self, admin_session):
        """Test getting pending RFQs for admin review"""
        response = admin_session.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        quotes = response.json()
        
        pending = [q for q in quotes if q.get("status") == "pending"]
        rfqs = [q for q in pending if q.get("quote_number", "").startswith("RFQ")]
        
        print(f"Total quotes: {len(quotes)}, Pending: {len(pending)}, RFQs: {len(rfqs)}")
    
    def test_quote_detail_view(self, admin_session):
        """Test getting quote details for modal view"""
        response = admin_session.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        quotes = response.json()
        
        if len(quotes) > 0:
            quote_id = quotes[0].get("id")
            # Get quote revision history
            history_response = admin_session.get(f"{BASE_URL}/api/quotes/{quote_id}/history")
            # This might return 404 if no history, which is OK
            print(f"Quote history status: {history_response.status_code}")
    
    def test_get_approved_quotes(self, admin_session):
        """Test filtering approved quotes"""
        response = admin_session.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        quotes = response.json()
        
        approved = [q for q in quotes if q.get("status") == "approved"]
        print(f"Approved quotes: {len(approved)}")
    
    def test_get_rejected_quotes(self, admin_session):
        """Test filtering rejected quotes"""
        response = admin_session.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        quotes = response.json()
        
        rejected = [q for q in quotes if q.get("status") == "rejected"]
        print(f"Rejected quotes: {len(rejected)}")


class TestExportFeatures:
    """Test PDF and Excel export features"""
    
    def test_quote_export_endpoint_exists(self, admin_session):
        """Test that quote export endpoint exists"""
        response = admin_session.get(f"{BASE_URL}/api/quotes/export/excel")
        # Should return 200 with file or 404 if no quotes
        assert response.status_code in [200, 404, 400]
        print(f"Export endpoint status: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
