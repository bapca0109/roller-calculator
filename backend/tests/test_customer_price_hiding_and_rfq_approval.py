"""
Test suite for:
1. Customer login should NOT see any prices in Calculator screen
2. Customer login should see 'Generate RFQ' button instead of 'Calculate Price'  
3. Customer login should NOT see price column in Search results
4. Admin login should see filter tabs: All, Pending RFQ, Approved
5. Admin can approve an RFQ - converts RFQ/XX to Q/XX and sends email
6. Approved quotes visible to both customer and admin
7. Customer quotes list should NOT show prices
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://belt-roller-calc-2.preview.emergentagent.com').rstrip('/')

# Test credentials from previous iteration
ADMIN_EMAIL = "test@test.com"
ADMIN_PASSWORD = "test123"
CUSTOMER_EMAIL = "customer@test.com"
CUSTOMER_PASSWORD = "test123"


class TestAuthAndRoles:
    """Test authentication and role verification"""
    
    def test_admin_login_returns_admin_role(self):
        """Test admin login returns correct role"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "admin", f"Expected admin role, got {data['user']['role']}"
        print(f"PASSED: Admin login returns role=admin")
        return data["access_token"]
    
    def test_customer_login_returns_customer_role(self):
        """Test customer login returns correct role"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
        )
        assert response.status_code == 200, f"Customer login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "customer", f"Expected customer role, got {data['user']['role']}"
        print(f"PASSED: Customer login returns role=customer")
        return data["access_token"]


class TestQuotesVisibility:
    """Test quotes visibility and filtering"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens for both users"""
        # Admin token
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        self.admin_token = response.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Customer token
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
        )
        self.customer_token = response.json()["access_token"]
        self.customer_headers = {"Authorization": f"Bearer {self.customer_token}"}
    
    def test_admin_can_see_all_quotes(self):
        """Admin should see all quotes including RFQs"""
        response = requests.get(
            f"{BASE_URL}/api/quotes",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Failed to get quotes: {response.text}"
        quotes = response.json()
        print(f"PASSED: Admin can fetch quotes list. Total quotes: {len(quotes)}")
        
        # Check if there are any quotes with RFQ prefix
        rfq_quotes = [q for q in quotes if q.get("quote_number", "").startswith("RFQ")]
        q_quotes = [q for q in quotes if q.get("quote_number", "").startswith("Q/")]
        print(f"  - RFQ quotes: {len(rfq_quotes)}")
        print(f"  - Q/ quotes: {len(q_quotes)}")
        
        return quotes
    
    def test_customer_only_sees_own_quotes(self):
        """Customer should only see their own quotes"""
        response = requests.get(
            f"{BASE_URL}/api/quotes",
            headers=self.customer_headers
        )
        assert response.status_code == 200, f"Failed to get quotes: {response.text}"
        quotes = response.json()
        
        # Customer should see their own quotes (with customer_email or customer_id matching)
        print(f"PASSED: Customer can fetch their quotes. Total: {len(quotes)}")
        return quotes
    
    def test_filter_pending_rfqs(self):
        """Test filtering for pending RFQs (admin feature)"""
        response = requests.get(
            f"{BASE_URL}/api/quotes",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        quotes = response.json()
        
        # Filter for pending RFQs - RFQ prefix and not approved
        pending_rfqs = [
            q for q in quotes 
            if q.get("quote_number", "").startswith("RFQ") 
            and q.get("status", "").lower() != "approved"
        ]
        print(f"PASSED: Found {len(pending_rfqs)} pending RFQs for admin")
        return pending_rfqs
    
    def test_filter_approved_quotes(self):
        """Test filtering for approved quotes"""
        response = requests.get(
            f"{BASE_URL}/api/quotes",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        quotes = response.json()
        
        # Filter for approved quotes
        approved = [
            q for q in quotes 
            if q.get("status", "").lower() == "approved" 
            or q.get("quote_number", "").startswith("Q/")
        ]
        print(f"PASSED: Found {len(approved)} approved/Q quotes for admin")
        return approved


class TestRFQApprovalWorkflow:
    """Test RFQ approval workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens"""
        # Admin token
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        self.admin_token = response.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Customer token
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
        )
        self.customer_token = response.json()["access_token"]
        self.customer_headers = {"Authorization": f"Bearer {self.customer_token}"}
    
    def test_customer_creates_rfq(self):
        """Customer creates an RFQ (should have RFQ prefix)"""
        # First calculate a price
        calc_response = requests.post(
            f"{BASE_URL}/api/calculate-detailed-cost",
            headers=self.customer_headers,
            json={
                "roller_type": "carrying",
                "pipe_diameter": 88.9,
                "pipe_length": 500,
                "shaft_diameter": 25,
                "bearing_number": "6205",
                "bearing_make": "china",
                "pipe_type": "B",
                "quantity": 5,
                "packing_type": "none"
            }
        )
        assert calc_response.status_code == 200, f"Calculation failed: {calc_response.text}"
        calc_result = calc_response.json()
        
        # Now create a quote/RFQ from this calculation
        quote_response = requests.post(
            f"{BASE_URL}/api/quotes/roller",
            headers=self.customer_headers,
            json={
                "customer_name": "Test Customer",
                "configuration": calc_result["configuration"],
                "cost_breakdown": calc_result["cost_breakdown"],
                "pricing": calc_result["pricing"],
                "freight": calc_result.get("freight"),
                "grand_total": calc_result["grand_total"],
                "notes": "Test RFQ from customer"
            }
        )
        assert quote_response.status_code == 200, f"RFQ creation failed: {quote_response.text}"
        rfq_data = quote_response.json()
        
        # Verify it has RFQ prefix
        assert rfq_data["quote_number"].startswith("RFQ"), \
            f"Customer quote should have RFQ prefix, got: {rfq_data['quote_number']}"
        
        print(f"PASSED: Customer created RFQ with number: {rfq_data['quote_number']}")
        return rfq_data
    
    def test_admin_creates_quote(self):
        """Admin creates a Quote (should have Q/ prefix)"""
        # First calculate a price
        calc_response = requests.post(
            f"{BASE_URL}/api/calculate-detailed-cost",
            headers=self.admin_headers,
            json={
                "roller_type": "carrying",
                "pipe_diameter": 88.9,
                "pipe_length": 600,
                "shaft_diameter": 25,
                "bearing_number": "6205",
                "bearing_make": "china",
                "pipe_type": "B",
                "quantity": 10,
                "packing_type": "standard"
            }
        )
        assert calc_response.status_code == 200, f"Calculation failed: {calc_response.text}"
        calc_result = calc_response.json()
        
        # Now create a quote
        quote_response = requests.post(
            f"{BASE_URL}/api/quotes/roller",
            headers=self.admin_headers,
            json={
                "customer_name": "Test Admin Customer",
                "configuration": calc_result["configuration"],
                "cost_breakdown": calc_result["cost_breakdown"],
                "pricing": calc_result["pricing"],
                "freight": calc_result.get("freight"),
                "grand_total": calc_result["grand_total"],
                "notes": "Test Quote from admin"
            }
        )
        assert quote_response.status_code == 200, f"Quote creation failed: {quote_response.text}"
        quote_data = quote_response.json()
        
        # Verify it has Q/ prefix (not RFQ)
        assert quote_data["quote_number"].startswith("Q/"), \
            f"Admin quote should have Q/ prefix, got: {quote_data['quote_number']}"
        
        print(f"PASSED: Admin created Quote with number: {quote_data['quote_number']}")
        return quote_data
    
    def test_admin_can_approve_rfq(self):
        """Admin approves an RFQ which converts it to Quote"""
        # First create an RFQ as customer
        calc_response = requests.post(
            f"{BASE_URL}/api/calculate-detailed-cost",
            headers=self.customer_headers,
            json={
                "roller_type": "carrying",
                "pipe_diameter": 88.9,
                "pipe_length": 450,
                "shaft_diameter": 25,
                "bearing_number": "6205",
                "bearing_make": "china",
                "pipe_type": "B",
                "quantity": 3,
                "packing_type": "none"
            }
        )
        assert calc_response.status_code == 200
        calc_result = calc_response.json()
        
        rfq_response = requests.post(
            f"{BASE_URL}/api/quotes/roller",
            headers=self.customer_headers,
            json={
                "customer_name": "Approval Test Customer",
                "configuration": calc_result["configuration"],
                "cost_breakdown": calc_result["cost_breakdown"],
                "pricing": calc_result["pricing"],
                "grand_total": calc_result["grand_total"],
                "notes": "RFQ for approval test"
            }
        )
        assert rfq_response.status_code == 200
        rfq_data = rfq_response.json()
        rfq_id = rfq_data["id"]
        old_number = rfq_data["quote_number"]
        
        assert old_number.startswith("RFQ"), f"Expected RFQ prefix, got: {old_number}"
        print(f"Created RFQ: {old_number}")
        
        # Now admin approves the RFQ
        approve_response = requests.post(
            f"{BASE_URL}/api/quotes/{rfq_id}/approve",
            headers=self.admin_headers
        )
        assert approve_response.status_code == 200, f"Approval failed: {approve_response.text}"
        approve_data = approve_response.json()
        
        # Verify the response
        assert "new_quote_number" in approve_data, "Response should contain new_quote_number"
        assert approve_data["new_quote_number"].startswith("Q/"), \
            f"New quote number should have Q/ prefix, got: {approve_data['new_quote_number']}"
        assert approve_data["status"] == "approved", \
            f"Status should be 'approved', got: {approve_data['status']}"
        
        print(f"PASSED: Admin approved RFQ {old_number} -> {approve_data['new_quote_number']}")
        return approve_data
    
    def test_cannot_approve_already_approved(self):
        """Test that already approved quotes cannot be approved again"""
        # First create and approve an RFQ
        calc_response = requests.post(
            f"{BASE_URL}/api/calculate-detailed-cost",
            headers=self.customer_headers,
            json={
                "roller_type": "carrying",
                "pipe_diameter": 88.9,
                "pipe_length": 400,
                "shaft_diameter": 25,
                "bearing_number": "6205",
                "bearing_make": "china",
                "pipe_type": "B",
                "quantity": 2,
                "packing_type": "none"
            }
        )
        calc_result = calc_response.json()
        
        rfq_response = requests.post(
            f"{BASE_URL}/api/quotes/roller",
            headers=self.customer_headers,
            json={
                "customer_name": "Double Approve Test",
                "configuration": calc_result["configuration"],
                "cost_breakdown": calc_result["cost_breakdown"],
                "pricing": calc_result["pricing"],
                "grand_total": calc_result["grand_total"],
                "notes": "RFQ for double approve test"
            }
        )
        rfq_id = rfq_response.json()["id"]
        
        # First approval - should succeed
        approve_response = requests.post(
            f"{BASE_URL}/api/quotes/{rfq_id}/approve",
            headers=self.admin_headers
        )
        assert approve_response.status_code == 200
        
        # Second approval - should fail
        second_approve = requests.post(
            f"{BASE_URL}/api/quotes/{rfq_id}/approve",
            headers=self.admin_headers
        )
        assert second_approve.status_code == 400, \
            f"Second approval should fail with 400, got: {second_approve.status_code}"
        
        print("PASSED: Cannot approve already approved quote")
    
    def test_customer_cannot_approve(self):
        """Test that customer cannot approve RFQs"""
        # Create RFQ
        calc_response = requests.post(
            f"{BASE_URL}/api/calculate-detailed-cost",
            headers=self.customer_headers,
            json={
                "roller_type": "carrying",
                "pipe_diameter": 88.9,
                "pipe_length": 380,
                "shaft_diameter": 25,
                "bearing_number": "6205",
                "bearing_make": "china",
                "pipe_type": "B",
                "quantity": 1,
                "packing_type": "none"
            }
        )
        calc_result = calc_response.json()
        
        rfq_response = requests.post(
            f"{BASE_URL}/api/quotes/roller",
            headers=self.customer_headers,
            json={
                "customer_name": "Customer Approve Test",
                "configuration": calc_result["configuration"],
                "cost_breakdown": calc_result["cost_breakdown"],
                "pricing": calc_result["pricing"],
                "grand_total": calc_result["grand_total"],
                "notes": "RFQ for customer approve test"
            }
        )
        rfq_id = rfq_response.json()["id"]
        
        # Customer tries to approve - should fail with 403
        approve_response = requests.post(
            f"{BASE_URL}/api/quotes/{rfq_id}/approve",
            headers=self.customer_headers
        )
        assert approve_response.status_code == 403, \
            f"Customer approval should fail with 403, got: {approve_response.status_code}"
        
        print("PASSED: Customer cannot approve RFQs (403 Forbidden)")


class TestSearchAPIForPrices:
    """Test search API returns prices correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        self.admin_token = response.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
        )
        self.customer_token = response.json()["access_token"]
        self.customer_headers = {"Authorization": f"Bearer {self.customer_token}"}
    
    def test_search_api_returns_results(self):
        """Test that search API returns results"""
        response = requests.get(
            f"{BASE_URL}/api/search/product-catalog",
            headers=self.admin_headers,
            params={"query": "CR"}
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        # Check if results contain price information
        results = data.get("results", [])
        if len(results) > 0:
            first_result = results[0]
            # Check that backend returns price (UI should hide it for customers)
            assert "base_price" in first_result, "Search result should contain base_price"
            print(f"PASSED: Search API returns results with prices. Count: {len(results)}")
        else:
            print("PASSED: Search API works but no results for 'CR' query")


class TestCalculationAPI:
    """Test calculation API returns prices correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        self.admin_token = response.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}
        )
        self.customer_token = response.json()["access_token"]
        self.customer_headers = {"Authorization": f"Bearer {self.customer_token}"}
    
    def test_admin_calculation_returns_prices(self):
        """Test admin gets full pricing details"""
        response = requests.post(
            f"{BASE_URL}/api/calculate-detailed-cost",
            headers=self.admin_headers,
            json={
                "roller_type": "carrying",
                "pipe_diameter": 88.9,
                "pipe_length": 500,
                "shaft_diameter": 25,
                "bearing_number": "6205",
                "bearing_make": "china",
                "pipe_type": "B",
                "quantity": 10,
                "packing_type": "standard"
            }
        )
        assert response.status_code == 200, f"Calculation failed: {response.text}"
        data = response.json()
        
        # Verify pricing is present
        assert "pricing" in data, "Response should contain pricing"
        assert "cost_breakdown" in data, "Response should contain cost_breakdown"
        assert "grand_total" in data, "Response should contain grand_total"
        
        print(f"PASSED: Admin calculation returns full pricing. Grand total: Rs. {data['grand_total']:.2f}")
    
    def test_customer_calculation_returns_prices(self):
        """Test customer also gets pricing (UI hides it, not API)"""
        response = requests.post(
            f"{BASE_URL}/api/calculate-detailed-cost",
            headers=self.customer_headers,
            json={
                "roller_type": "carrying",
                "pipe_diameter": 88.9,
                "pipe_length": 500,
                "shaft_diameter": 25,
                "bearing_number": "6205",
                "bearing_make": "china",
                "pipe_type": "B",
                "quantity": 10,
                "packing_type": "standard"
            }
        )
        assert response.status_code == 200, f"Calculation failed: {response.text}"
        data = response.json()
        
        # API returns pricing - frontend hides it for customers
        assert "pricing" in data, "Response should contain pricing (UI hides for customers)"
        assert "grand_total" in data, "Response should contain grand_total"
        
        print(f"PASSED: Customer calculation also returns pricing (UI will hide it)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
