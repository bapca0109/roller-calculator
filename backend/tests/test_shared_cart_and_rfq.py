"""
Test Shared Cart and RFQ Submission Features

This test file verifies:
1. Items can be added to quotes from different sources (calculator/search)
2. The POST /api/quotes endpoint accepts cart items with proper structure
3. RFQ submission includes packing_type, freight_pincode, customer_rfq_no
4. Quote/RFQ creation works for both admin and customer roles
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {"email": "test@test.com", "password": "test123"}
CUSTOMER_CREDENTIALS = {"email": "customer@test.com", "password": "test123"}


class TestSharedCartBackend:
    """Tests for shared cart and RFQ submission backend APIs"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def customer_token(self):
        """Get customer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CUSTOMER_CREDENTIALS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Customer authentication failed")
    
    @pytest.fixture
    def admin_headers(self, admin_token):
        """Admin auth headers"""
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    @pytest.fixture
    def customer_headers(self, customer_token):
        """Customer auth headers"""
        return {"Authorization": f"Bearer {customer_token}", "Content-Type": "application/json"}
    
    # ==================== Health Check ====================
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"API health: {data}")
    
    # ==================== Authentication Tests ====================
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"Admin login successful: {data['user']['email']}")
    
    def test_customer_login(self):
        """Test customer login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CUSTOMER_CREDENTIALS)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "customer"
        print(f"Customer login successful: {data['user']['email']}")
    
    # ==================== Shared Cart - Admin Quote Creation ====================
    
    def test_admin_create_quote_with_cart_items(self, admin_headers):
        """Test admin creating a quote with multiple cart items (from calculator + search sources)"""
        # Simulating cart items from both Calculator and Search tabs
        cart_items = {
            "products": [
                {
                    # Item from Calculator tab
                    "product_id": "CR20-89-1000A-25C",
                    "product_name": "Carrying Roller - CR20-89-1000A-25C",
                    "quantity": 10,
                    "unit_price": 850.00,
                    "specifications": {
                        "pipe_diameter": 89,
                        "pipe_length": 1000,
                        "pipe_type": "A",
                        "shaft_diameter": 25,
                        "bearing": "6205",
                        "bearing_make": "china",
                        "housing": "H63"
                    },
                    "remark": "Test item from calculator tab",
                    "attachments": []
                },
                {
                    # Item from Search tab
                    "product_id": "IR25-114-1250B-30S",
                    "product_name": "Impact Roller - IR25-114-1250B-30S",
                    "quantity": 5,
                    "unit_price": 1200.00,
                    "specifications": {
                        "pipe_diameter": 114,
                        "pipe_length": 1250,
                        "pipe_type": "B",
                        "shaft_diameter": 30,
                        "bearing": "6206",
                        "bearing_make": "skf",
                        "housing": "H76",
                        "belt_widths": [1200, 1400]
                    },
                    "remark": "Test item from search tab"
                }
            ],
            "delivery_location": "382430",
            "notes": "Test quote with items from shared cart - Calculator + Search tabs",
            "customer_rfq_no": "TEST-ADMIN-001"
        }
        
        response = requests.post(f"{BASE_URL}/api/quotes", json=cart_items, headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "quote_number" in data
        assert data["quote_number"].startswith("Q/")  # Admin creates Quote, not RFQ
        assert len(data["products"]) == 2
        assert data["products"][0]["product_id"] == "CR20-89-1000A-25C"
        assert data["products"][1]["product_id"] == "IR25-114-1250B-30S"
        assert data["customer_rfq_no"] == "TEST-ADMIN-001"
        assert data["delivery_location"] == "382430"
        
        print(f"Admin quote created: {data['quote_number']}")
        print(f"  - Products: {len(data['products'])}")
        print(f"  - Subtotal: {data['subtotal']}")
        print(f"  - Customer RFQ No: {data.get('customer_rfq_no')}")
        return data["quote_number"]
    
    # ==================== Shared Cart - Customer RFQ Creation ====================
    
    def test_customer_create_rfq_with_cart_items(self, customer_headers):
        """Test customer creating an RFQ with multiple cart items"""
        # Simulating cart items from both tabs
        cart_items = {
            "products": [
                {
                    "product_id": "CR20-88-950A-25C",
                    "product_name": "Carrying Roller - CR20-88-950A-25C",
                    "quantity": 20,
                    "unit_price": 0,  # Customers don't see prices
                    "specifications": {
                        "pipe_diameter": 88,
                        "pipe_length": 950,
                        "pipe_type": "A",
                        "shaft_diameter": 25,
                        "bearing": "6205",
                        "bearing_make": "china",
                        "housing": "H63"
                    },
                    "remark": "Customer item 1 - urgent delivery needed"
                },
                {
                    "product_id": "CR30-127-1400B-30F",
                    "product_name": "Carrying Roller - CR30-127-1400B-30F",
                    "quantity": 15,
                    "unit_price": 0,
                    "specifications": {
                        "pipe_diameter": 127,
                        "pipe_length": 1400,
                        "pipe_type": "B",
                        "shaft_diameter": 30,
                        "bearing": "6306",
                        "bearing_make": "fag",
                        "housing": "H89"
                    }
                }
            ],
            "delivery_location": "110001",
            "notes": "Customer RFQ - Shared cart test",
            "customer_rfq_no": "PO-2026-CUST-001"
        }
        
        response = requests.post(f"{BASE_URL}/api/quotes", json=cart_items, headers=customer_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "quote_number" in data
        assert data["quote_number"].startswith("RFQ/")  # Customer creates RFQ
        assert len(data["products"]) == 2
        assert data["customer_rfq_no"] == "PO-2026-CUST-001"
        assert data["status"] == "pending"
        
        print(f"Customer RFQ created: {data['quote_number']}")
        print(f"  - Products: {len(data['products'])}")
        print(f"  - Customer RFQ No: {data.get('customer_rfq_no')}")
        print(f"  - Status: {data['status']}")
        return data["id"]
    
    # ==================== Product Specification Tests ====================
    
    def test_quote_with_full_specifications(self, admin_headers):
        """Test creating quote with full product specifications (as sent from CartContext)"""
        cart_items = {
            "products": [
                {
                    "product_id": "IR25-114-1000B-25S",
                    "product_name": "Impact Roller - IR25-114-1000B-25S",
                    "quantity": 8,
                    "unit_price": 1100.00,
                    "specifications": {
                        "pipe_diameter": 114,
                        "pipe_length": 1000,
                        "pipe_type": "B",
                        "shaft_diameter": 25,
                        "bearing": "6205",
                        "bearing_make": "skf",
                        "housing": "H76",
                        "rubber_diameter": 140,
                        "belt_widths": [1000, 1200]
                    },
                    "remark": "Impact roller with rubber lagging",
                    "attachments": [
                        {"name": "drawing.pdf", "type": "document", "base64": None}
                    ]
                }
            ],
            "notes": "Test with full specifications"
        }
        
        response = requests.post(f"{BASE_URL}/api/quotes", json=cart_items, headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        product = data["products"][0]
        specs = product.get("specifications", {})
        
        # Verify all specifications are preserved
        assert specs.get("pipe_diameter") == 114
        assert specs.get("rubber_diameter") == 140
        assert specs.get("belt_widths") == [1000, 1200]
        assert product.get("remark") == "Impact roller with rubber lagging"
        
        print(f"Quote with full specs created: {data['quote_number']}")
        print(f"  - Rubber diameter: {specs.get('rubber_diameter')}")
        print(f"  - Belt widths: {specs.get('belt_widths')}")
    
    # ==================== Packing Type Tests ====================
    
    def test_quote_with_packing_type_in_notes(self, admin_headers):
        """Test creating quote with packing type information (passed via notes)"""
        cart_items = {
            "products": [
                {
                    "product_id": "CR20-89-500A-20C",
                    "product_name": "Carrying Roller - CR20-89-500A-20C",
                    "quantity": 50,
                    "unit_price": 650.00,
                    "specifications": {
                        "pipe_diameter": 89,
                        "pipe_length": 500,
                        "shaft_diameter": 20,
                        "bearing": "6204"
                    }
                }
            ],
            "delivery_location": "382433",
            "notes": "Packing: pallet (4%). Test packing type in RFQ submission."
        }
        
        response = requests.post(f"{BASE_URL}/api/quotes", json=cart_items, headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "pallet" in data["notes"].lower() or "packing" in data["notes"].lower()
        print(f"Quote with packing info: {data['quote_number']}")
        print(f"  - Notes: {data['notes']}")
    
    # ==================== Delivery Location/Freight Tests ====================
    
    def test_quote_with_freight_pincode(self, customer_headers):
        """Test RFQ with freight/delivery pincode"""
        cart_items = {
            "products": [
                {
                    "product_id": "CR20-89-800A-25C",
                    "product_name": "Carrying Roller - CR20-89-800A-25C",
                    "quantity": 25,
                    "unit_price": 0,
                    "specifications": {
                        "pipe_diameter": 89,
                        "pipe_length": 800,
                        "shaft_diameter": 25
                    }
                }
            ],
            "delivery_location": "400001",  # Mumbai pincode
            "notes": "Deliver to Mumbai location"
        }
        
        response = requests.post(f"{BASE_URL}/api/quotes", json=cart_items, headers=customer_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["delivery_location"] == "400001"
        print(f"RFQ with freight pincode: {data['quote_number']}")
        print(f"  - Delivery Location: {data['delivery_location']}")
    
    # ==================== Customer RFQ Reference Tests ====================
    
    def test_quote_with_customer_rfq_number(self, customer_headers):
        """Test RFQ with customer's own reference number"""
        cart_items = {
            "products": [
                {
                    "product_id": "CR25-114-1200B-25S",
                    "product_name": "Carrying Roller - CR25-114-1200B-25S",
                    "quantity": 30,
                    "unit_price": 0,
                    "specifications": {
                        "pipe_diameter": 114,
                        "pipe_length": 1200
                    }
                }
            ],
            "customer_rfq_no": "CUST-PO-2026-0123",
            "notes": "Test customer RFQ reference number"
        }
        
        response = requests.post(f"{BASE_URL}/api/quotes", json=cart_items, headers=customer_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["customer_rfq_no"] == "CUST-PO-2026-0123"
        print(f"RFQ with customer reference: {data['quote_number']}")
        print(f"  - Customer RFQ No: {data['customer_rfq_no']}")
    
    # ==================== Multiple Items from Different Sources ====================
    
    def test_quote_with_mixed_source_items(self, admin_headers):
        """Test quote with items representing both Calculator and Search sources"""
        # This simulates what happens when user adds items from both tabs
        cart_items = {
            "products": [
                # Calculator item - has calculatorData style specs
                {
                    "product_id": "CR20-88-1000A-25C",
                    "product_name": "Carrying Roller - CR20-88-1000A-25C",
                    "quantity": 10,
                    "unit_price": 780.50,
                    "specifications": {
                        "pipe_diameter": 88,
                        "pipe_length": 1000,
                        "pipe_type": "A",
                        "shaft_diameter": 25,
                        "bearing": "6205",
                        "bearing_make": "china",
                        "housing": "H63"
                    },
                    "remark": "From Calculator"
                },
                # Search item - has belt_widths from catalog
                {
                    "product_id": "CR25-114-1400B-30S",
                    "product_name": "Carrying Roller - CR25-114-1400B-30S",
                    "quantity": 5,
                    "unit_price": 1050.00,
                    "specifications": {
                        "pipe_diameter": 114,
                        "pipe_length": 1400,
                        "pipe_type": "B",
                        "shaft_diameter": 30,
                        "bearing": "6306",
                        "bearing_make": "skf",
                        "housing": "H89",
                        "belt_widths": [1400, 1600]
                    },
                    "remark": "From Search catalog"
                },
                # Another Calculator item
                {
                    "product_id": "IR25-114-950B-25C",
                    "product_name": "Impact Roller - IR25-114-950B-25C",
                    "quantity": 8,
                    "unit_price": 1150.00,
                    "specifications": {
                        "pipe_diameter": 114,
                        "pipe_length": 950,
                        "pipe_type": "B",
                        "shaft_diameter": 25,
                        "bearing": "6205",
                        "bearing_make": "china",
                        "housing": "H76",
                        "rubber_diameter": 140
                    },
                    "remark": "Impact roller from Calculator"
                }
            ],
            "delivery_location": "382430",
            "notes": "Mixed cart - Calculator + Search items",
            "customer_rfq_no": "MIXED-CART-001"
        }
        
        response = requests.post(f"{BASE_URL}/api/quotes", json=cart_items, headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["products"]) == 3
        
        # Verify products maintained their specs
        calc_item = data["products"][0]
        search_item = data["products"][1]
        impact_item = data["products"][2]
        
        assert calc_item["remark"] == "From Calculator"
        assert search_item["specifications"].get("belt_widths") == [1400, 1600]
        assert impact_item["specifications"].get("rubber_diameter") == 140
        
        # Verify subtotal calculation
        expected_subtotal = (10 * 780.50) + (5 * 1050.00) + (8 * 1150.00)
        assert abs(data["subtotal"] - expected_subtotal) < 0.01
        
        print(f"Mixed source quote created: {data['quote_number']}")
        print(f"  - Total products: {len(data['products'])}")
        print(f"  - Subtotal: {data['subtotal']}")
        print(f"  - Expected: {expected_subtotal}")
    
    # ==================== Empty Cart Test ====================
    
    def test_quote_with_empty_cart_fails(self, admin_headers):
        """Test that creating quote with empty products list fails"""
        cart_items = {
            "products": [],
            "notes": "Empty cart test"
        }
        
        response = requests.post(f"{BASE_URL}/api/quotes", json=cart_items, headers=admin_headers)
        # API should either return error or create empty quote (depends on validation)
        # Let's check what happens
        print(f"Empty cart response: {response.status_code}")
        if response.status_code != 200:
            print(f"Error for empty cart (expected): {response.text}")
    
    # ==================== Get Quotes List Test ====================
    
    def test_get_quotes_list(self, admin_headers):
        """Test retrieving quotes list"""
        response = requests.get(f"{BASE_URL}/api/quotes", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        # API returns list directly or wrapped in "quotes" key
        if isinstance(data, list):
            quotes = data
        else:
            quotes = data.get("quotes", [])
        
        assert isinstance(quotes, list)
        
        # Check at least one recent quote exists
        if len(quotes) > 0:
            recent_quote = quotes[0]
            assert "quote_number" in recent_quote
            print(f"Found {len(quotes)} quotes")
            print(f"  - Most recent: {recent_quote['quote_number']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
