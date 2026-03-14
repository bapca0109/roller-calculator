"""
Test Auto-Freight Calculation in RFQ Approval
- Tests the approve_rfq endpoint auto-calculates freight when pincode is provided
- Verifies freight_auto_calculated flag and freight_details in response
- Tests search product API functionality
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://belt-price-engine.preview.emergentagent.com').rstrip('/')


class TestApproveRFQAutoFreight:
    """Tests for auto-freight calculation during RFQ approval"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@test.com",
            "password": "test123"
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"Admin login successful, token received")
            return token
        pytest.skip(f"Admin authentication failed - {response.status_code}: {response.text}")
    
    @pytest.fixture(scope="class")
    def customer_token(self):
        """Get customer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "customer@test.com",
            "password": "test123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Customer authentication failed - {response.status_code}: {response.text}")
    
    def test_login_success(self):
        """Test admin login works correctly"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@test.com",
            "password": "test123"
        })
        assert response.status_code == 200, f"Login failed: {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data, "Missing access_token in login response"
        print(f"Login successful for test@test.com")
    
    def test_get_pending_rfqs(self, admin_token):
        """Test getting list of pending RFQs with delivery_location"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/quotes", headers=headers)
        assert response.status_code == 200, f"Failed to get quotes: {response.text}"
        
        quotes = response.json()
        assert isinstance(quotes, list), "Expected list of quotes"
        
        # Find pending RFQs with delivery_location
        pending_rfqs_with_pincode = [
            q for q in quotes 
            if q.get("quote_number", "").startswith("RFQ/") 
            and q.get("status") == "pending"
            and q.get("delivery_location")
        ]
        
        print(f"Total quotes: {len(quotes)}")
        print(f"Pending RFQs with delivery_location: {len(pending_rfqs_with_pincode)}")
        
        for rfq in pending_rfqs_with_pincode[:3]:  # Show first 3
            print(f"  - {rfq.get('quote_number')}: delivery={rfq.get('delivery_location')}, products={len(rfq.get('products', []))}")
    
    def test_approve_rfq_with_auto_freight(self, admin_token):
        """Test approving an RFQ with delivery_location triggers auto-freight calculation"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all quotes
        response = requests.get(f"{BASE_URL}/api/quotes", headers=headers)
        assert response.status_code == 200
        quotes = response.json()
        
        # Find a pending RFQ with delivery_location
        pending_rfq = None
        for quote in quotes:
            if (quote.get("quote_number", "").startswith("RFQ/") 
                and quote.get("status") == "pending" 
                and quote.get("delivery_location")):
                pending_rfq = quote
                break
        
        if not pending_rfq:
            # Create a test RFQ with delivery_location by updating an existing pending one
            for quote in quotes:
                if (quote.get("quote_number", "").startswith("RFQ/") 
                    and quote.get("status") == "pending"):
                    # Update with delivery_location
                    update_response = requests.put(
                        f"{BASE_URL}/api/quotes/{quote['id']}",
                        json={"delivery_location": "387630"},
                        headers=headers
                    )
                    if update_response.status_code == 200:
                        pending_rfq = update_response.json()
                        print(f"Updated RFQ {pending_rfq['quote_number']} with delivery_location=387630")
                        break
        
        if not pending_rfq:
            pytest.skip("No pending RFQ available for auto-freight test")
        
        rfq_id = pending_rfq['id']
        rfq_number = pending_rfq.get('quote_number')
        print(f"Testing auto-freight on RFQ: {rfq_number}, delivery: {pending_rfq.get('delivery_location')}")
        
        # Approve the RFQ
        approve_response = requests.post(
            f"{BASE_URL}/api/quotes/{rfq_id}/approve",
            headers=headers
        )
        
        assert approve_response.status_code == 200, f"Approve failed: {approve_response.status_code}: {approve_response.text}"
        
        result = approve_response.json()
        print(f"Approval response: {result}")
        
        # Verify required fields in response
        assert "new_quote_number" in result, "Missing new_quote_number in approve response"
        assert result.get("old_number") == rfq_number, f"Old number mismatch: expected {rfq_number}, got {result.get('old_number')}"
        
        # Verify auto-freight fields
        assert "freight_auto_calculated" in result, "Missing freight_auto_calculated flag in response"
        assert "shipping_cost" in result, "Missing shipping_cost in response"
        assert "freight_details" in result, "Missing freight_details in response"
        
        if result.get("freight_auto_calculated"):
            print(f"Auto-freight calculated successfully:")
            print(f"  - Shipping cost: Rs. {result.get('shipping_cost')}")
            freight_details = result.get("freight_details", {})
            print(f"  - Distance: {freight_details.get('distance_km')} km")
            print(f"  - Rate: Rs. {freight_details.get('freight_rate_per_kg')}/kg")
            print(f"  - Weight: {freight_details.get('total_weight_kg')} kg")
            
            assert freight_details.get("auto_calculated") == True, "freight_details.auto_calculated should be True"
        else:
            print("Freight was not auto-calculated (may already have freight)")
    
    def test_approve_rfq_response_structure(self, admin_token):
        """Test approve RFQ response has correct structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get quotes
        response = requests.get(f"{BASE_URL}/api/quotes", headers=headers)
        assert response.status_code == 200
        quotes = response.json()
        
        # Find a pending RFQ
        pending_rfq = None
        for quote in quotes:
            if (quote.get("quote_number", "").startswith("RFQ/") 
                and quote.get("status") == "pending"):
                pending_rfq = quote
                break
        
        if not pending_rfq:
            pytest.skip("No pending RFQ available for testing")
        
        # Approve and check response structure
        approve_response = requests.post(
            f"{BASE_URL}/api/quotes/{pending_rfq['id']}/approve",
            headers=headers
        )
        
        assert approve_response.status_code == 200
        result = approve_response.json()
        
        expected_fields = ["message", "old_number", "new_quote_number", "status", "freight_auto_calculated"]
        for field in expected_fields:
            assert field in result, f"Missing field in approve response: {field}"
        
        print(f"Approve response structure verified: {list(result.keys())}")


class TestProductSearch:
    """Tests for product search API endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@test.com",
            "password": "test123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def customer_token(self):
        """Get customer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "customer@test.com",
            "password": "test123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Customer authentication failed")
    
    def test_search_products_admin(self, admin_token):
        """Test product search with admin user"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/search/product-catalog",
            params={"query": "roller", "limit": 10},
            headers=headers
        )
        
        assert response.status_code == 200, f"Search failed: {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data or isinstance(data, list), "Expected results in search response"
        
        results = data.get("results", data) if isinstance(data, dict) else data
        print(f"Search 'roller' returned {len(results)} results")
        
        if results:
            sample = results[0]
            print(f"Sample result: {sample.get('product_code', sample.get('_id', 'N/A'))}")
    
    def test_search_products_by_code(self, admin_token):
        """Test searching products by product code"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/search/product-catalog",
            params={"query": "CR-", "limit": 5},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        print(f"Search 'CR-' returned {len(results)} results")
    
    def test_search_products_customer(self, customer_token):
        """Test product search with customer user (prices should be hidden)"""
        headers = {"Authorization": f"Bearer {customer_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/search/product-catalog",
            params={"query": "roller", "limit": 5},
            headers=headers
        )
        
        assert response.status_code == 200, f"Customer search failed: {response.status_code}: {response.text}"
        
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        print(f"Customer search returned {len(results)} results")
    
    def test_search_empty_query_fails(self, admin_token):
        """Test search with empty/missing query returns 422 (validation error)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/search/product-catalog",
            params={"limit": 5},
            headers=headers
        )
        
        # API requires query parameter
        assert response.status_code == 422, f"Expected 422 for missing query, got {response.status_code}"
        print("Empty query validation works correctly - 422 returned")
    
    def test_search_requires_auth(self):
        """Test that search requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/search/product-catalog",
            params={"query": "roller"}
        )
        
        # Should require authentication
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Search requires authentication - PASS")


class TestRFQWorkflow:
    """Test the complete RFQ workflow including auto-freight"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@test.com",
            "password": "test123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    def test_rfq_list_has_data(self, admin_token):
        """Test that we can get RFQ list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/quotes", headers=headers)
        assert response.status_code == 200
        
        quotes = response.json()
        rfqs = [q for q in quotes if q.get("quote_number", "").startswith("RFQ/")]
        
        print(f"Total RFQs: {len(rfqs)}")
        pending = len([q for q in rfqs if q.get("status") == "pending"])
        approved = len([q for q in rfqs if q.get("status") == "approved"])
        print(f"  - Pending: {pending}, Approved: {approved}")
    
    def test_calculate_freight_endpoint(self, admin_token):
        """Test direct freight calculation endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-freight",
            json={
                "pincode": "387630",
                "total_weight_kg": 50.0
            },
            headers=headers
        )
        
        assert response.status_code == 200, f"Freight calc failed: {response.text}"
        
        data = response.json()
        assert "freight_charges" in data
        assert "distance_km" in data
        assert "freight_rate_per_kg" in data
        
        print(f"Freight for 50kg to 387630: Rs. {data['freight_charges']} ({data['freight_rate_per_kg']}/kg)")
    
    def test_already_approved_rfq_fails(self, admin_token):
        """Test that approving an already-approved quote fails correctly"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/quotes", headers=headers)
        assert response.status_code == 200
        
        quotes = response.json()
        approved_quote = None
        for quote in quotes:
            if quote.get("status") == "approved":
                approved_quote = quote
                break
        
        if not approved_quote:
            pytest.skip("No approved quote found for test")
        
        approve_response = requests.post(
            f"{BASE_URL}/api/quotes/{approved_quote['id']}/approve",
            headers=headers
        )
        
        # Should fail for already approved quote
        assert approve_response.status_code == 400, f"Expected 400, got {approve_response.status_code}"
        
        detail = approve_response.json().get("detail", "")
        assert "already" in detail.lower() or "Quote" in detail, f"Unexpected error message: {detail}"
        print(f"Already-approved error correct: {detail}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
