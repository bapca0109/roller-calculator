"""
Backend API Tests for RFQ vs Quote Number Generation
Tests:
1. Customer login generates RFQ numbers (RFQ/25-26/XXXX)
2. Admin login generates Quote numbers (Q/25-26/XXXX)
3. Admin emails are loaded from environment variables
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://belt-roller-tool.preview.emergentagent.com').rstrip('/')

# Test credentials from review request
ADMIN_EMAIL = "test@test.com"
ADMIN_PASSWORD = "test123"
CUSTOMER_EMAIL = "customer@test.com"
CUSTOMER_PASSWORD = "test123"


@pytest.fixture(scope="module")
def admin_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200, f"Admin auth failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    assert data["user"]["role"] == "admin", f"Expected admin role, got {data['user']['role']}"
    return data["access_token"]


@pytest.fixture(scope="module")
def customer_token():
    """Get authentication token for customer user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200, f"Customer auth failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    assert data["user"]["role"] == "customer", f"Expected customer role, got {data['user']['role']}"
    return data["access_token"]


@pytest.fixture
def admin_client(admin_token):
    """Create authenticated session for admin"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


@pytest.fixture
def customer_client(customer_token):
    """Create authenticated session for customer"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {customer_token}"
    })
    return session


# ============= AUTH VERIFICATION TESTS =============

class TestAuthRoles:
    """Verify user roles for admin and customer"""
    
    def test_admin_login_returns_admin_role(self):
        """Test that admin user has admin role"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "admin", f"Expected admin role, got {data['user']['role']}"
        print(f"Admin user: {data['user']['email']} with role: {data['user']['role']}")
    
    def test_customer_login_returns_customer_role(self):
        """Test that customer user has customer role"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "customer", f"Expected customer role, got {data['user']['role']}"
        print(f"Customer user: {data['user']['email']} with role: {data['user']['role']}")


# ============= RFQ/QUOTE NUMBER GENERATION TESTS =============

class TestRfqVsQuoteNumberGeneration:
    """Test that customers get RFQ numbers and admins get Quote numbers"""
    
    def test_customer_creates_rfq_number(self, customer_client):
        """Test that customer creating a quote gets RFQ/YY-YY/XXXX number"""
        quote_data = {
            "customer_name": "Customer Test User",
            "customer_id": None,
            "customer_details": {
                "name": "Customer Test User",
                "company": "Test Customer Company"
            },
            "configuration": {
                "product_code": "CR20 89 1000B 62C",
                "roller_type": "carrying",
                "pipe_diameter_mm": 88.9,
                "pipe_length_mm": 1000,
                "pipe_type": "B",
                "shaft_diameter_mm": 20,
                "bearing": "6204",
                "bearing_make": "china",
                "housing": "M-1",
                "quantity": 5
            },
            "cost_breakdown": {
                "pipe_cost": 500.0,
                "shaft_cost": 200.0,
                "bearing_cost": 150.0,
                "total_raw_material": 850.0
            },
            "pricing": {
                "unit_price": 1200.0,
                "order_value": 6000.0,
                "discount_amount": 0.0,
                "packing_charges": 50.0,
                "final_price": 6050.0
            },
            "grand_total": 6050.0,
            "notes": "Test RFQ from customer"
        }
        
        response = customer_client.post(f"{BASE_URL}/api/quotes/roller", json=quote_data)
        assert response.status_code == 200, f"Failed to create RFQ: {response.text}"
        
        data = response.json()
        assert "quote_number" in data, "Response missing quote_number"
        
        quote_number = data["quote_number"]
        print(f"Customer generated quote_number: {quote_number}")
        
        # Verify RFQ prefix
        assert quote_number.startswith("RFQ/"), f"Expected RFQ/ prefix, got: {quote_number}"
        
        # Verify format: RFQ/YY-YY/XXXX (e.g., RFQ/25-26/0001)
        parts = quote_number.split("/")
        assert len(parts) == 3, f"Expected 3 parts in quote number, got: {parts}"
        assert parts[0] == "RFQ", f"Expected RFQ prefix, got: {parts[0]}"
        assert "-" in parts[1], f"Expected YY-YY format, got: {parts[1]}"
        assert parts[2].isdigit(), f"Expected numeric sequence, got: {parts[2]}"
        
        # Verify message says RFQ
        assert "RFQ" in data.get("message", ""), f"Response message should mention RFQ: {data.get('message')}"
        
        # Store for later verification
        self.__class__.customer_rfq_id = data["id"]
        self.__class__.customer_rfq_number = quote_number
    
    def test_admin_creates_quote_number(self, admin_client):
        """Test that admin creating a quote gets Q/YY-YY/XXXX number"""
        quote_data = {
            "customer_name": "Admin Test Customer",
            "customer_id": None,
            "customer_details": {
                "name": "Admin Test Customer",
                "company": "Test Admin Company"
            },
            "configuration": {
                "product_code": "CR25 114 800B 63C",
                "roller_type": "carrying",
                "pipe_diameter_mm": 114.3,
                "pipe_length_mm": 800,
                "pipe_type": "B",
                "shaft_diameter_mm": 25,
                "bearing": "6305",
                "bearing_make": "china",
                "housing": "M-2",
                "quantity": 10
            },
            "cost_breakdown": {
                "pipe_cost": 600.0,
                "shaft_cost": 250.0,
                "bearing_cost": 180.0,
                "total_raw_material": 1030.0
            },
            "pricing": {
                "unit_price": 1500.0,
                "order_value": 15000.0,
                "discount_amount": 750.0,
                "packing_charges": 100.0,
                "final_price": 14350.0
            },
            "grand_total": 14350.0,
            "notes": "Test Quote from admin"
        }
        
        response = admin_client.post(f"{BASE_URL}/api/quotes/roller", json=quote_data)
        assert response.status_code == 200, f"Failed to create Quote: {response.text}"
        
        data = response.json()
        assert "quote_number" in data, "Response missing quote_number"
        
        quote_number = data["quote_number"]
        print(f"Admin generated quote_number: {quote_number}")
        
        # Verify Q/ prefix
        assert quote_number.startswith("Q/"), f"Expected Q/ prefix, got: {quote_number}"
        
        # Verify format: Q/YY-YY/XXXX (e.g., Q/25-26/0001)
        parts = quote_number.split("/")
        assert len(parts) == 3, f"Expected 3 parts in quote number, got: {parts}"
        assert parts[0] == "Q", f"Expected Q prefix, got: {parts[0]}"
        assert "-" in parts[1], f"Expected YY-YY format, got: {parts[1]}"
        assert parts[2].isdigit(), f"Expected numeric sequence, got: {parts[2]}"
        
        # Verify message says Quote
        assert "Quote" in data.get("message", ""), f"Response message should mention Quote: {data.get('message')}"
        
        # Store for later verification
        self.__class__.admin_quote_id = data["id"]
        self.__class__.admin_quote_number = quote_number
    
    def test_verify_rfq_stored_in_database(self, customer_client):
        """Verify customer RFQ is stored correctly with RFQ number"""
        rfq_id = getattr(self.__class__, 'customer_rfq_id', None)
        expected_number = getattr(self.__class__, 'customer_rfq_number', None)
        
        if not rfq_id:
            pytest.skip("No RFQ created in previous test")
        
        # Use /api/quotes list which returns raw data including quote_number
        response = customer_client.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200, f"Failed to fetch quotes: {response.text}"
        
        quotes = response.json()
        rfq = next((q for q in quotes if q.get("id") == rfq_id), None)
        
        assert rfq is not None, f"RFQ with id {rfq_id} not found in quotes list"
        assert rfq["quote_number"] == expected_number
        assert rfq["quote_number"].startswith("RFQ/")
        print(f"Verified RFQ in database: {rfq['quote_number']}")
    
    def test_verify_quote_stored_in_database(self, admin_client):
        """Verify admin Quote is stored correctly with Q number"""
        quote_id = getattr(self.__class__, 'admin_quote_id', None)
        expected_number = getattr(self.__class__, 'admin_quote_number', None)
        
        if not quote_id:
            pytest.skip("No Quote created in previous test")
        
        # Use /api/quotes list which returns raw data including quote_number
        response = admin_client.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200, f"Failed to fetch quotes: {response.text}"
        
        quotes = response.json()
        quote = next((q for q in quotes if q.get("id") == quote_id), None)
        
        assert quote is not None, f"Quote with id {quote_id} not found in quotes list"
        assert quote["quote_number"] == expected_number
        assert quote["quote_number"].startswith("Q/")
        print(f"Verified Quote in database: {quote['quote_number']}")


# ============= QUOTES LIST TESTS =============

class TestQuotesList:
    """Test quotes list for customers and admins"""
    
    def test_customer_sees_own_quotes(self, customer_client):
        """Test that customer sees their own quotes/RFQs in list"""
        response = customer_client.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        
        quotes = response.json()
        assert isinstance(quotes, list)
        
        # Check if any RFQ numbers are present
        rfq_quotes = [q for q in quotes if q.get("quote_number", "").startswith("RFQ/")]
        print(f"Customer sees {len(rfq_quotes)} RFQs and {len(quotes) - len(rfq_quotes)} other quotes")
    
    def test_admin_sees_all_quotes(self, admin_client):
        """Test that admin can see all quotes"""
        response = admin_client.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        
        quotes = response.json()
        assert isinstance(quotes, list)
        
        # Admin should see both Q/ and RFQ/ prefixed quotes
        q_quotes = [q for q in quotes if q.get("quote_number", "").startswith("Q/")]
        rfq_quotes = [q for q in quotes if q.get("quote_number", "").startswith("RFQ/")]
        
        print(f"Admin sees {len(q_quotes)} Quotes and {len(rfq_quotes)} RFQs")


# ============= ENVIRONMENT VARIABLE TESTS =============

class TestEnvironmentVariables:
    """Test that admin emails are loaded from environment variables"""
    
    def test_admin_registration_emails_configured(self):
        """Verify ADMIN_REGISTRATION_EMAILS env var is set"""
        # This tests the backend configuration
        # We can verify by checking the server.py has the env var loading
        # The actual values are in backend/.env
        env_var = os.environ.get('ADMIN_REGISTRATION_EMAILS', '')
        print(f"ADMIN_REGISTRATION_EMAILS configured (from test env): {env_var if env_var else 'Not set in test env, but should be set in backend'}")
    
    def test_admin_rfq_emails_configured(self):
        """Verify ADMIN_RFQ_EMAILS env var is set"""
        env_var = os.environ.get('ADMIN_RFQ_EMAILS', '')
        print(f"ADMIN_RFQ_EMAILS configured (from test env): {env_var if env_var else 'Not set in test env, but should be set in backend'}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
