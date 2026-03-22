"""
Test Freight Calculation Feature
- Tests the /api/calculate-freight endpoint
- Tests freight calculation based on pincode zones and weight
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rfq-hub-4.preview.emergentagent.com').rstrip('/')

class TestFreightCalculation:
    """Tests for freight calculation endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@test.com",
            "password": "test123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed - skipping authenticated tests")
    
    @pytest.fixture(scope="class")
    def customer_token(self):
        """Get customer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "customer@test.com",
            "password": "test123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Customer authentication failed - skipping authenticated tests")
    
    def test_freight_calculation_gujarat_local(self, admin_token):
        """Test freight calculation for Gujarat local pincode (38* prefix) - 150km, Rs.2/kg"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Gujarat pincode 387630 (from the test case mentioned)
        response = requests.post(f"{BASE_URL}/api/calculate-freight", 
            json={
                "pincode": "387630",
                "total_weight_kg": 100.0
            },
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "freight_charges" in data
        assert "distance_km" in data
        assert "freight_rate_per_kg" in data
        
        # Gujarat local should be ~150km distance and Rs.2/kg rate
        assert data["distance_km"] == 150.0, f"Expected 150km for Gujarat local, got {data['distance_km']}"
        assert data["freight_rate_per_kg"] == 2.0, f"Expected Rs.2/kg for 0-300km, got {data['freight_rate_per_kg']}"
        assert data["freight_charges"] == 200.0, f"Expected 100kg * Rs.2/kg = Rs.200, got {data['freight_charges']}"
        
        print(f"Gujarat local freight: {data}")
    
    def test_freight_calculation_maharashtra(self, admin_token):
        """Test freight calculation for Maharashtra pincode (40* prefix) - ~500km, Rs.4/kg"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Maharashtra pincode (Mumbai area)
        response = requests.post(f"{BASE_URL}/api/calculate-freight", 
            json={
                "pincode": "400001",
                "total_weight_kg": 50.0
            },
            headers=headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["distance_km"] == 500.0, f"Expected ~500km for Maharashtra, got {data['distance_km']}"
        assert data["freight_rate_per_kg"] == 4.0, f"Expected Rs.4/kg for 300-600km, got {data['freight_rate_per_kg']}"
        assert data["freight_charges"] == 200.0, f"Expected 50kg * Rs.4/kg = Rs.200, got {data['freight_charges']}"
        
        print(f"Maharashtra freight: {data}")
    
    def test_freight_calculation_delhi(self, admin_token):
        """Test freight calculation for Delhi pincode (11* prefix) - ~900km, Rs.5/kg"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(f"{BASE_URL}/api/calculate-freight", 
            json={
                "pincode": "110001",
                "total_weight_kg": 100.0
            },
            headers=headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        # Delhi is ~900km from Gujarat (between 600-1000km range, Rs.5/kg)
        assert data["distance_km"] == 900.0, f"Expected ~900km for Delhi, got {data['distance_km']}"
        assert data["freight_rate_per_kg"] == 5.0, f"Expected Rs.5/kg for 600-1000km, got {data['freight_rate_per_kg']}"
        assert data["freight_charges"] == 500.0, f"Expected 100kg * Rs.5/kg = Rs.500, got {data['freight_charges']}"
        
        print(f"Delhi freight: {data}")
    
    def test_freight_calculation_tamil_nadu(self, admin_token):
        """Test freight calculation for Tamil Nadu pincode (60* prefix) - ~1600km, Rs.9/kg"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(f"{BASE_URL}/api/calculate-freight", 
            json={
                "pincode": "600001",
                "total_weight_kg": 100.0
            },
            headers=headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        # Tamil Nadu is ~1600km from Gujarat (1500+ range, Rs.9/kg)
        assert data["distance_km"] == 1600.0, f"Expected ~1600km for Tamil Nadu, got {data['distance_km']}"
        assert data["freight_rate_per_kg"] == 9.0, f"Expected Rs.9/kg for 1500+km, got {data['freight_rate_per_kg']}"
        assert data["freight_charges"] == 900.0, f"Expected 100kg * Rs.9/kg = Rs.900, got {data['freight_charges']}"
        
        print(f"Tamil Nadu freight: {data}")
    
    def test_freight_calculation_invalid_pincode_format(self, admin_token):
        """Test error handling for invalid pincode format"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Invalid pincode (5 digits)
        response = requests.post(f"{BASE_URL}/api/calculate-freight", 
            json={
                "pincode": "12345",
                "total_weight_kg": 100.0
            },
            headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid pincode, got {response.status_code}"
        assert "Invalid pincode format" in response.json().get("detail", "")
        
        print("Invalid pincode format test passed")
    
    def test_freight_calculation_invalid_weight(self, admin_token):
        """Test error handling for invalid weight (zero or negative)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Zero weight
        response = requests.post(f"{BASE_URL}/api/calculate-freight", 
            json={
                "pincode": "387630",
                "total_weight_kg": 0
            },
            headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400 for zero weight, got {response.status_code}"
        assert "Weight must be greater than 0" in response.json().get("detail", "")
        
        # Negative weight
        response = requests.post(f"{BASE_URL}/api/calculate-freight", 
            json={
                "pincode": "387630",
                "total_weight_kg": -50
            },
            headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400 for negative weight, got {response.status_code}"
        
        print("Invalid weight test passed")
    
    def test_freight_calculation_requires_auth(self):
        """Test that freight calculation requires authentication"""
        response = requests.post(f"{BASE_URL}/api/calculate-freight", 
            json={
                "pincode": "387630",
                "total_weight_kg": 100.0
            }
        )
        
        # Should require auth
        assert response.status_code in [401, 403], f"Expected 401/403 for unauthenticated request, got {response.status_code}"
        
        print("Authentication required test passed")
    
    def test_freight_response_structure(self, admin_token):
        """Test that the response has all required fields"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(f"{BASE_URL}/api/calculate-freight", 
            json={
                "pincode": "387630",
                "total_weight_kg": 100.0
            },
            headers=headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Check all required fields are present
        required_fields = [
            "destination_pincode",
            "dispatch_pincode", 
            "distance_km",
            "total_weight_kg",
            "freight_rate_per_kg",
            "freight_charges"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify dispatch pincode is the Gujarat factory location
        assert data["dispatch_pincode"] == "382433", f"Expected dispatch from 382433, got {data['dispatch_pincode']}"
        
        print(f"Response structure verified: {list(data.keys())}")


class TestRFQWithFreight:
    """Tests for RFQ with freight calculation integration"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@test.com",
            "password": "test123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed - skipping authenticated tests")
    
    def test_get_pending_rfq_with_delivery_pincode(self, admin_token):
        """Test getting a pending RFQ that has a delivery pincode - RFQ/25-26/0070"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all quotes
        response = requests.get(f"{BASE_URL}/api/quotes", headers=headers)
        assert response.status_code == 200
        
        quotes = response.json()
        
        # Find RFQ with delivery_location = 387630
        rfq_with_pincode = None
        for quote in quotes:
            if quote.get("quote_number", "").startswith("RFQ/") and quote.get("delivery_location") == "387630":
                rfq_with_pincode = quote
                break
        
        if rfq_with_pincode:
            print(f"Found RFQ with pincode 387630: {rfq_with_pincode.get('quote_number')}")
            assert rfq_with_pincode["delivery_location"] == "387630"
            print(f"RFQ details - products: {len(rfq_with_pincode.get('products', []))}, delivery: {rfq_with_pincode.get('delivery_location')}")
        else:
            # If no RFQ exists with that pincode, search for any RFQ with a delivery location
            rfq_with_any_pincode = None
            for quote in quotes:
                if quote.get("quote_number", "").startswith("RFQ/") and quote.get("delivery_location"):
                    rfq_with_any_pincode = quote
                    break
            
            if rfq_with_any_pincode:
                print(f"Found RFQ with delivery pincode: {rfq_with_any_pincode.get('quote_number')} - {rfq_with_any_pincode.get('delivery_location')}")
            else:
                print("No RFQs found with delivery_location set")
                # Not a failure, just documenting state
    
    def test_update_rfq_with_freight(self, admin_token):
        """Test updating an RFQ with freight details"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get pending RFQs
        response = requests.get(f"{BASE_URL}/api/quotes", headers=headers)
        assert response.status_code == 200
        
        quotes = response.json()
        
        # Find a pending RFQ
        pending_rfq = None
        for quote in quotes:
            if quote.get("quote_number", "").startswith("RFQ/") and quote.get("status") == "pending":
                pending_rfq = quote
                break
        
        if not pending_rfq:
            pytest.skip("No pending RFQ found to test update")
        
        # Calculate freight for pincode 387630
        freight_response = requests.post(f"{BASE_URL}/api/calculate-freight",
            json={
                "pincode": "387630",
                "total_weight_kg": 100.0
            },
            headers=headers
        )
        
        assert freight_response.status_code == 200
        freight_data = freight_response.json()
        
        # Update the RFQ with freight details
        update_response = requests.put(f"{BASE_URL}/api/quotes/{pending_rfq['id']}",
            json={
                "delivery_location": "387630",
                "shipping_cost": freight_data["freight_charges"],
                "freight_details": {
                    "freight_percent": 0,
                    "freight_amount": freight_data["freight_charges"],
                    "use_custom_amount": True
                }
            },
            headers=headers
        )
        
        assert update_response.status_code == 200, f"Failed to update RFQ: {update_response.text}"
        
        updated_rfq = update_response.json()
        assert updated_rfq.get("delivery_location") == "387630"
        assert updated_rfq.get("shipping_cost") == freight_data["freight_charges"]
        
        print(f"Updated RFQ {pending_rfq['quote_number']} with freight: Rs.{freight_data['freight_charges']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
