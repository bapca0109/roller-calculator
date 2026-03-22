"""
Backend API Tests for Customer CRUD and Roller Quote with Customer Details
Tests customer creation, retrieval, and quote creation with customer_details field
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rfq-hub-4.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200, f"Auth failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    return data["access_token"]


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


# ============= AUTH TESTS =============

class TestAuth:
    """Authentication endpoint tests"""
    
    def test_login_success(self):
        """Test successful login returns token and user data"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpass"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401


# ============= CUSTOMER CRUD TESTS =============

class TestCustomerCRUD:
    """Customer CRUD endpoint tests"""
    
    def test_create_customer_basic(self, api_client):
        """Test creating a customer with minimal fields"""
        unique_id = str(uuid.uuid4())[:8]
        customer_data = {
            "name": f"TEST_Customer_{unique_id}"
        }
        
        response = api_client.post(f"{BASE_URL}/api/customers", json=customer_data)
        assert response.status_code == 200, f"Failed to create customer: {response.text}"
        
        data = response.json()
        assert "customer" in data
        assert data["customer"]["name"] == customer_data["name"]
        assert "id" in data["customer"]
        
        # Store for cleanup
        self.__class__.created_customer_id = data["customer"]["id"]
    
    def test_create_customer_with_all_fields(self, api_client):
        """Test creating a customer with all fields populated"""
        unique_id = str(uuid.uuid4())[:8]
        customer_data = {
            "name": f"TEST_FullCustomer_{unique_id}",
            "company": "Test Company Ltd",
            "email": f"customer_{unique_id}@testcompany.com",
            "phone": "+91 9876543210",
            "address": "123 Industrial Area",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "gst_number": "27AABCU9603R1ZM",
            "notes": "VIP customer - priority support"
        }
        
        response = api_client.post(f"{BASE_URL}/api/customers", json=customer_data)
        assert response.status_code == 200, f"Failed to create customer: {response.text}"
        
        data = response.json()
        assert "customer" in data
        customer = data["customer"]
        
        # Validate all fields were stored
        assert customer["name"] == customer_data["name"]
        assert customer["company"] == customer_data["company"]
        assert customer["email"] == customer_data["email"]
        assert customer["phone"] == customer_data["phone"]
        assert customer["address"] == customer_data["address"]
        assert customer["city"] == customer_data["city"]
        assert customer["state"] == customer_data["state"]
        assert customer["pincode"] == customer_data["pincode"]
        assert customer["gst_number"] == customer_data["gst_number"]
        assert customer["notes"] == customer_data["notes"]
        assert "id" in customer
        
        # Store for later tests
        self.__class__.full_customer_id = customer["id"]
        self.__class__.full_customer_data = customer_data
    
    def test_get_all_customers(self, api_client):
        """Test fetching all customers"""
        response = api_client.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200
        
        data = response.json()
        assert "customers" in data
        assert isinstance(data["customers"], list)
        assert len(data["customers"]) >= 1  # At least one customer should exist
    
    def test_get_customer_by_id(self, api_client):
        """Test fetching a specific customer by ID"""
        # Use the customer created in previous test
        customer_id = getattr(self.__class__, 'full_customer_id', None)
        if not customer_id:
            pytest.skip("No customer created in previous test")
        
        response = api_client.get(f"{BASE_URL}/api/customers/{customer_id}")
        assert response.status_code == 200, f"Failed to get customer: {response.text}"
        
        customer = response.json()
        assert customer["id"] == customer_id
        assert customer["name"] == self.__class__.full_customer_data["name"]
    
    def test_update_customer(self, api_client):
        """Test updating a customer"""
        customer_id = getattr(self.__class__, 'full_customer_id', None)
        if not customer_id:
            pytest.skip("No customer created in previous test")
        
        updated_data = {
            "name": f"TEST_UpdatedCustomer_{str(uuid.uuid4())[:8]}",
            "company": "Updated Company Ltd",
            "email": "updated@testcompany.com",
            "phone": "+91 9999999999",
            "address": "456 Updated Address",
            "city": "Delhi",
            "state": "Delhi",
            "pincode": "110001",
            "gst_number": "07AABCU9603R1ZM",
            "notes": "Updated notes"
        }
        
        response = api_client.put(f"{BASE_URL}/api/customers/{customer_id}", json=updated_data)
        assert response.status_code == 200, f"Failed to update customer: {response.text}"
        
        # Verify update by fetching the customer
        get_response = api_client.get(f"{BASE_URL}/api/customers/{customer_id}")
        assert get_response.status_code == 200
        
        customer = get_response.json()
        assert customer["name"] == updated_data["name"]
        assert customer["company"] == updated_data["company"]
        assert customer["city"] == updated_data["city"]
    
    def test_get_customer_not_found(self, api_client):
        """Test fetching a non-existent customer returns 404"""
        fake_id = "000000000000000000000000"  # Valid ObjectId format but non-existent
        response = api_client.get(f"{BASE_URL}/api/customers/{fake_id}")
        assert response.status_code == 404
    
    def test_delete_customer(self, api_client):
        """Test deleting a customer"""
        # Create a new customer to delete
        unique_id = str(uuid.uuid4())[:8]
        create_response = api_client.post(
            f"{BASE_URL}/api/customers",
            json={"name": f"TEST_ToDelete_{unique_id}"}
        )
        assert create_response.status_code == 200
        customer_id = create_response.json()["customer"]["id"]
        
        # Delete the customer
        delete_response = api_client.delete(f"{BASE_URL}/api/customers/{customer_id}")
        assert delete_response.status_code == 200, f"Failed to delete customer: {delete_response.text}"
        
        # Verify deletion
        get_response = api_client.get(f"{BASE_URL}/api/customers/{customer_id}")
        assert get_response.status_code == 404


# ============= ROLLER QUOTE WITH CUSTOMER DETAILS TESTS =============

class TestRollerQuoteWithCustomer:
    """Tests for creating roller quotes with customer_details"""
    
    def test_create_roller_quote_with_customer_details(self, api_client):
        """Test creating a roller quote with full customer_details"""
        unique_id = str(uuid.uuid4())[:8]
        
        # First, create a customer
        customer_data = {
            "name": f"TEST_QuoteCustomer_{unique_id}",
            "company": "Quote Test Company",
            "email": f"quote_{unique_id}@test.com",
            "phone": "+91 8888888888",
            "address": "789 Quote Street",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "pincode": "600001",
            "gst_number": "33AABCU9603R1ZM",
            "notes": "Quote test customer"
        }
        
        customer_response = api_client.post(f"{BASE_URL}/api/customers", json=customer_data)
        assert customer_response.status_code == 200, f"Failed to create customer: {customer_response.text}"
        customer = customer_response.json()["customer"]
        customer_id = customer["id"]
        
        # Create roller quote with customer_details
        quote_data = {
            "customer_name": customer_data["name"],
            "customer_id": customer_id,
            "customer_details": {
                "name": customer_data["name"],
                "company": customer_data["company"],
                "email": customer_data["email"],
                "phone": customer_data["phone"],
                "address": customer_data["address"],
                "city": customer_data["city"],
                "state": customer_data["state"],
                "pincode": customer_data["pincode"],
                "gst_number": customer_data["gst_number"]
            },
            "configuration": {
                "product_code": f"CR20 89 1000B 62C",
                "roller_type": "carrying",
                "pipe_diameter_mm": 88.9,
                "pipe_length_mm": 1000,
                "pipe_type": "B",
                "shaft_diameter_mm": 20,
                "bearing": "6204",
                "bearing_make": "china",
                "housing": "M-1",
                "quantity": 10
            },
            "cost_breakdown": {
                "pipe_cost": 500.0,
                "shaft_cost": 200.0,
                "bearing_cost": 150.0,
                "total_raw_material": 850.0
            },
            "pricing": {
                "unit_price": 1200.0,
                "order_value": 12000.0,
                "discount_amount": 600.0,
                "packing_charges": 100.0,
                "final_price": 11500.0
            },
            "freight": {
                "destination_pincode": "600001",
                "freight_charges": 500.0
            },
            "grand_total": 12000.0,
            "notes": "Test roller quote with customer details"
        }
        
        response = api_client.post(f"{BASE_URL}/api/quotes/roller", json=quote_data)
        assert response.status_code == 200, f"Failed to create roller quote: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert "quote_number" in data
        assert "total_price" in data
        
        # Store quote_id for verification
        self.__class__.created_quote_id = data["id"]
        self.__class__.customer_id = customer_id
        self.__class__.customer_details = quote_data["customer_details"]
    
    def test_verify_customer_details_in_quote(self, api_client):
        """Test that customer_details are properly stored and retrieved from quote"""
        quote_id = getattr(self.__class__, 'created_quote_id', None)
        expected_customer_details = getattr(self.__class__, 'customer_details', None)
        
        if not quote_id:
            pytest.skip("No quote created in previous test")
        
        response = api_client.get(f"{BASE_URL}/api/quotes/{quote_id}")
        assert response.status_code == 200, f"Failed to get quote: {response.text}"
        
        quote = response.json()
        
        # Verify quote has customer_details
        assert "customer_details" in quote, "Quote is missing customer_details field"
        assert quote["customer_details"] is not None, "customer_details is None"
        
        # Verify customer_details fields match what was sent
        stored_details = quote["customer_details"]
        assert stored_details["name"] == expected_customer_details["name"]
        assert stored_details["company"] == expected_customer_details["company"]
        assert stored_details["email"] == expected_customer_details["email"]
        assert stored_details["phone"] == expected_customer_details["phone"]
        assert stored_details["address"] == expected_customer_details["address"]
        assert stored_details["city"] == expected_customer_details["city"]
        assert stored_details["state"] == expected_customer_details["state"]
        assert stored_details["pincode"] == expected_customer_details["pincode"]
        assert stored_details["gst_number"] == expected_customer_details["gst_number"]
        
        # Also verify customer_id is stored
        assert quote["customer_id"] == self.__class__.customer_id
    
    def test_create_roller_quote_without_customer_details(self, api_client):
        """Test creating roller quote without customer_details (should still work)"""
        unique_id = str(uuid.uuid4())[:8]
        
        quote_data = {
            "customer_name": f"TEST_NoCustDetails_{unique_id}",
            "customer_id": None,
            "customer_details": None,  # No customer details
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
                "quantity": 5
            },
            "cost_breakdown": {
                "pipe_cost": 600.0,
                "shaft_cost": 250.0,
                "bearing_cost": 180.0,
                "total_raw_material": 1030.0
            },
            "pricing": {
                "unit_price": 1500.0,
                "order_value": 7500.0,
                "discount_amount": 0.0,
                "packing_charges": 50.0,
                "final_price": 7550.0
            },
            "grand_total": 7550.0,
            "notes": "Quote without customer details"
        }
        
        response = api_client.post(f"{BASE_URL}/api/quotes/roller", json=quote_data)
        assert response.status_code == 200, f"Failed to create quote: {response.text}"
        
        data = response.json()
        assert "id" in data
        
        # Verify the quote was created without customer_details
        quote_response = api_client.get(f"{BASE_URL}/api/quotes/{data['id']}")
        assert quote_response.status_code == 200
        quote = quote_response.json()
        
        # customer_details should be None
        assert quote.get("customer_details") is None
    
    def test_create_roller_quote_with_partial_customer_details(self, api_client):
        """Test creating roller quote with partial customer_details"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Only provide name and company in customer_details
        partial_customer_details = {
            "name": f"TEST_PartialCust_{unique_id}",
            "company": "Partial Test Company"
        }
        
        quote_data = {
            "customer_name": partial_customer_details["name"],
            "customer_id": None,
            "customer_details": partial_customer_details,
            "configuration": {
                "product_code": "IR30 139 1200B 62C",
                "roller_type": "impact",
                "pipe_diameter_mm": 139.7,
                "pipe_length_mm": 1200,
                "pipe_type": "B",
                "shaft_diameter_mm": 30,
                "bearing": "6206",
                "bearing_make": "china",
                "housing": "M-3",
                "rubber_diameter_mm": 200,
                "quantity": 3
            },
            "cost_breakdown": {
                "pipe_cost": 700.0,
                "shaft_cost": 300.0,
                "bearing_cost": 200.0,
                "rubber_cost": 150.0,
                "total_raw_material": 1350.0
            },
            "pricing": {
                "unit_price": 2000.0,
                "order_value": 6000.0,
                "discount_amount": 0.0,
                "packing_charges": 60.0,
                "final_price": 6060.0
            },
            "grand_total": 6060.0,
            "notes": "Impact roller with partial customer details"
        }
        
        response = api_client.post(f"{BASE_URL}/api/quotes/roller", json=quote_data)
        assert response.status_code == 200, f"Failed to create quote: {response.text}"
        
        data = response.json()
        assert "id" in data
        
        # Verify partial customer_details were stored
        quote_response = api_client.get(f"{BASE_URL}/api/quotes/{data['id']}")
        assert quote_response.status_code == 200
        quote = quote_response.json()
        
        assert quote["customer_details"] is not None
        assert quote["customer_details"]["name"] == partial_customer_details["name"]
        assert quote["customer_details"]["company"] == partial_customer_details["company"]


# ============= QUOTES LIST TESTS =============

class TestQuotesList:
    """Tests for fetching quotes list"""
    
    def test_get_all_quotes(self, api_client):
        """Test fetching all quotes for current user"""
        response = api_client.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        
        quotes = response.json()
        assert isinstance(quotes, list)
        assert len(quotes) >= 1  # At least one quote should exist from previous tests
    
    def test_quotes_contain_customer_details(self, api_client):
        """Test that quotes list contains customer_details when present"""
        response = api_client.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        
        quotes = response.json()
        
        # Find quotes with customer_details
        quotes_with_details = [q for q in quotes if q.get("customer_details") is not None]
        
        # Should have at least one quote with customer_details from our tests
        assert len(quotes_with_details) >= 1, "No quotes found with customer_details"
        
        # Verify structure of customer_details in a quote
        for quote in quotes_with_details:
            details = quote["customer_details"]
            # Check that it's a dict with expected fields
            assert isinstance(details, dict)
            if "name" in details:
                assert isinstance(details["name"], str)


# ============= CLEANUP =============

class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_customers(self, api_client):
        """Clean up all TEST_ prefixed customers"""
        response = api_client.get(f"{BASE_URL}/api/customers")
        if response.status_code == 200:
            customers = response.json().get("customers", [])
            deleted_count = 0
            for customer in customers:
                if customer.get("name", "").startswith("TEST_"):
                    delete_response = api_client.delete(f"{BASE_URL}/api/customers/{customer['id']}")
                    if delete_response.status_code == 200:
                        deleted_count += 1
            print(f"Cleaned up {deleted_count} test customers")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
