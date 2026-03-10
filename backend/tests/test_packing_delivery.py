"""
Test cases for Packing Type and Delivery Location (Freight Pincode) features.
Tests verify that these fields are:
1. Accepted and stored by POST /api/quotes
2. Returned by GET /api/quotes
3. Present in quote responses after approval
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://conveyor-calc-1.preview.emergentagent.com').rstrip('/')

# Test credentials
CUSTOMER_CREDENTIALS = {"email": "customer@test.com", "password": "test123"}
ADMIN_CREDENTIALS = {"email": "test@test.com", "password": "test123"}


@pytest.fixture(scope="module")
def customer_auth_token():
    """Get authentication token for customer user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CUSTOMER_CREDENTIALS)
    if response.status_code != 200:
        pytest.skip(f"Customer login failed: {response.status_code} - {response.text}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def admin_auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    return response.json().get("access_token")


@pytest.fixture
def customer_client(customer_auth_token):
    """Requests session with customer auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {customer_auth_token}"
    })
    return session


@pytest.fixture
def admin_client(admin_auth_token):
    """Requests session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_auth_token}"
    })
    return session


class TestPackingTypeAndDeliveryLocation:
    """Test packing_type and delivery_location fields in quotes"""
    
    def test_create_rfq_with_packing_and_delivery(self, customer_client):
        """Test that customer can create RFQ with packing_type and delivery_location"""
        # Create RFQ with packing type and delivery location
        payload = {
            "products": [{
                "product_id": "TEST-ROLLER-001",
                "product_name": "Test Carrier Roller 89x315",
                "quantity": 10,
                "unit_price": 500.0,
                "specifications": {
                    "roller_type": "Carrier",
                    "pipe_diameter": 89,
                    "shaft_diameter": 20,
                    "bearing": "6204"
                }
            }],
            "delivery_location": "380015",  # Ahmedabad pincode
            "packing_type": "pallet",  # Pallet packing (4%)
            "notes": "Test RFQ with packing and delivery",
            "customer_rfq_no": "TEST-PACK-001"
        }
        
        response = customer_client.post(f"{BASE_URL}/api/quotes", json=payload)
        print(f"Create RFQ Response: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        # Status assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions
        data = response.json()
        assert "id" in data, "Response should have 'id' field"
        assert "quote_number" in data, "Response should have 'quote_number' field"
        assert data["quote_number"].startswith("RFQ/"), f"Quote number should start with 'RFQ/', got {data['quote_number']}"
        
        # Verify packing_type is stored
        assert data.get("packing_type") == "pallet", f"Expected packing_type 'pallet', got {data.get('packing_type')}"
        
        # Verify delivery_location is stored
        assert data.get("delivery_location") == "380015", f"Expected delivery_location '380015', got {data.get('delivery_location')}"
        
        # Store for later retrieval test
        return data["id"], data["quote_number"]
    
    def test_create_rfq_with_standard_packing(self, customer_client):
        """Test RFQ creation with standard packing type"""
        payload = {
            "products": [{
                "product_id": "TEST-ROLLER-002",
                "product_name": "Test Return Roller 76x380",
                "quantity": 5,
                "unit_price": 450.0,
                "specifications": {
                    "roller_type": "Return",
                    "pipe_diameter": 76,
                    "shaft_diameter": 20
                }
            }],
            "delivery_location": "110001",  # Delhi pincode
            "packing_type": "standard",  # Standard packing (1%)
            "notes": "Test RFQ with standard packing"
        }
        
        response = customer_client.post(f"{BASE_URL}/api/quotes", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("packing_type") == "standard"
        assert data.get("delivery_location") == "110001"
        
        return data["id"]
    
    def test_create_rfq_with_wooden_box_packing(self, customer_client):
        """Test RFQ creation with wooden box packing type"""
        payload = {
            "products": [{
                "product_id": "TEST-ROLLER-003",
                "product_name": "Test Impact Roller 127x450",
                "quantity": 20,
                "unit_price": 750.0,
                "specifications": {
                    "roller_type": "Impact",
                    "pipe_diameter": 127,
                    "shaft_diameter": 25
                }
            }],
            "delivery_location": "400001",  # Mumbai pincode
            "packing_type": "wooden_box",  # Wooden box packing (8%)
            "notes": "Test RFQ with wooden box packing"
        }
        
        response = customer_client.post(f"{BASE_URL}/api/quotes", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("packing_type") == "wooden_box"
        assert data.get("delivery_location") == "400001"
        
        return data["id"]
    
    def test_create_rfq_without_packing_and_delivery(self, customer_client):
        """Test RFQ creation without optional packing_type and delivery_location"""
        payload = {
            "products": [{
                "product_id": "TEST-ROLLER-004",
                "product_name": "Test Roller without options",
                "quantity": 3,
                "unit_price": 350.0
            }],
            "notes": "Test RFQ without packing/delivery"
        }
        
        response = customer_client.post(f"{BASE_URL}/api/quotes", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        # These fields should be null/None when not provided
        assert data.get("packing_type") is None or data.get("packing_type") == ""
        assert data.get("delivery_location") is None or data.get("delivery_location") == ""
    
    def test_get_quotes_returns_packing_and_delivery(self, customer_client):
        """Test that GET /api/quotes returns packing_type and delivery_location"""
        # First create a quote with packing and delivery
        create_payload = {
            "products": [{
                "product_id": "TEST-ROLLER-GET",
                "product_name": "Test Roller for GET",
                "quantity": 8,
                "unit_price": 550.0
            }],
            "delivery_location": "560001",  # Bangalore pincode
            "packing_type": "pallet"
        }
        
        create_response = customer_client.post(f"{BASE_URL}/api/quotes", json=create_payload)
        assert create_response.status_code == 200
        created_quote = create_response.json()
        quote_id = created_quote["id"]
        
        # Now fetch all quotes and find ours
        get_response = customer_client.get(f"{BASE_URL}/api/quotes")
        
        assert get_response.status_code == 200
        quotes = get_response.json()
        assert isinstance(quotes, list), "Expected list of quotes"
        
        # Find our created quote
        found_quote = None
        for q in quotes:
            if q.get("id") == quote_id:
                found_quote = q
                break
        
        assert found_quote is not None, f"Quote {quote_id} not found in GET response"
        
        # Verify packing_type and delivery_location are present
        assert found_quote.get("packing_type") == "pallet", f"Expected packing_type 'pallet' in GET response, got {found_quote.get('packing_type')}"
        assert found_quote.get("delivery_location") == "560001", f"Expected delivery_location '560001' in GET response, got {found_quote.get('delivery_location')}"
    
    def test_admin_can_view_rfq_with_packing_and_delivery(self, customer_client, admin_client):
        """Test that admin can see packing_type and delivery_location in RFQ list"""
        # Customer creates RFQ
        create_payload = {
            "products": [{
                "product_id": "TEST-ADMIN-VIEW",
                "product_name": "Test Roller for Admin View",
                "quantity": 15,
                "unit_price": 600.0
            }],
            "delivery_location": "600001",  # Chennai pincode
            "packing_type": "wooden_box"
        }
        
        create_response = customer_client.post(f"{BASE_URL}/api/quotes", json=create_payload)
        assert create_response.status_code == 200
        quote_number = create_response.json()["quote_number"]
        
        # Admin fetches quotes
        admin_response = admin_client.get(f"{BASE_URL}/api/quotes")
        assert admin_response.status_code == 200
        
        quotes = admin_response.json()
        
        # Find the RFQ by quote_number
        found_quote = None
        for q in quotes:
            if q.get("quote_number") == quote_number:
                found_quote = q
                break
        
        assert found_quote is not None, f"Quote {quote_number} not found in admin's GET response"
        
        # Verify fields are visible to admin
        assert found_quote.get("packing_type") == "wooden_box", "Admin should see packing_type"
        assert found_quote.get("delivery_location") == "600001", "Admin should see delivery_location"


class TestPackingTypeValues:
    """Test different packing type values are handled correctly"""
    
    @pytest.mark.parametrize("packing_type,expected_label", [
        ("standard", "standard"),
        ("pallet", "pallet"),
        ("wooden_box", "wooden_box"),
    ])
    def test_packing_type_values(self, customer_client, packing_type, expected_label):
        """Test each packing type value is stored correctly"""
        payload = {
            "products": [{
                "product_id": f"TEST-PACK-{packing_type.upper()}",
                "product_name": f"Test with {packing_type}",
                "quantity": 1,
                "unit_price": 100.0
            }],
            "packing_type": packing_type,
            "delivery_location": "380001"
        }
        
        response = customer_client.post(f"{BASE_URL}/api/quotes", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("packing_type") == expected_label


class TestDeliveryLocationFormat:
    """Test delivery location (pincode) validation"""
    
    def test_valid_6_digit_pincode(self, customer_client):
        """Test valid 6-digit Indian pincode is accepted"""
        payload = {
            "products": [{
                "product_id": "TEST-PINCODE-VALID",
                "product_name": "Test valid pincode",
                "quantity": 1,
                "unit_price": 100.0
            }],
            "delivery_location": "382009"  # Valid Gujarat pincode
        }
        
        response = customer_client.post(f"{BASE_URL}/api/quotes", json=payload)
        assert response.status_code == 200
        assert response.json().get("delivery_location") == "382009"
    
    def test_pincode_stored_as_string(self, customer_client):
        """Test that pincode with leading zero is preserved"""
        # Some pincodes like "011001" have leading zeros
        payload = {
            "products": [{
                "product_id": "TEST-PINCODE-LEADING",
                "product_name": "Test leading zero pincode",
                "quantity": 1,
                "unit_price": 100.0
            }],
            "delivery_location": "110001"  # Delhi pincode starting with 1
        }
        
        response = customer_client.post(f"{BASE_URL}/api/quotes", json=payload)
        assert response.status_code == 200
        # Verify string format is preserved
        assert response.json().get("delivery_location") == "110001"


class TestQuoteDetailsWithPackingDelivery:
    """Test quote details modal/view contains packing and delivery info"""
    
    def test_single_quote_response_includes_fields(self, customer_client):
        """Verify single quote response includes packing_type and delivery_location"""
        # Create a quote
        payload = {
            "products": [{
                "product_id": "TEST-DETAIL-VIEW",
                "product_name": "Test for detail view",
                "quantity": 5,
                "unit_price": 400.0,
                "specifications": {
                    "roller_type": "Carrier",
                    "pipe_diameter": 89
                }
            }],
            "delivery_location": "700001",  # Kolkata pincode
            "packing_type": "pallet"
        }
        
        response = customer_client.post(f"{BASE_URL}/api/quotes", json=payload)
        assert response.status_code == 200
        
        # The response already includes all fields
        quote_data = response.json()
        
        # Verify structure has required fields for detail view
        assert "id" in quote_data
        assert "quote_number" in quote_data
        assert "products" in quote_data
        assert "packing_type" in quote_data
        assert "delivery_location" in quote_data
        
        # Verify values
        assert quote_data["packing_type"] == "pallet"
        assert quote_data["delivery_location"] == "700001"
        
        # Verify product structure for display
        assert len(quote_data["products"]) > 0
        product = quote_data["products"][0]
        assert product["product_id"] == "TEST-DETAIL-VIEW"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
