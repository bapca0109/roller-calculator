"""
Test Revision History Feature for Quotes
- GET /api/quotes/{quote_id}/history endpoint
- PUT /api/quotes/{quote_id} with revision tracking
- Tracks changes to packing_type, freight, discount, etc.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://conveyor-roller-calc-1.preview.emergentagent.com').rstrip('/')

class TestRevisionHistory:
    """Test revision history feature for quotes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@test.com",
            "password": "test123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.user = login_response.json().get("user", {})
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
    
    def test_01_get_quote_for_testing(self):
        """Get an approved quote to test revision history - Q/25-26/0103"""
        # First get all quotes to find the one mentioned
        response = self.session.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200, f"Failed to get quotes: {response.text}"
        
        quotes = response.json()
        assert len(quotes) > 0, "No quotes found"
        
        # Find the specific quote mentioned in the task
        target_quote = None
        for quote in quotes:
            if quote.get('quote_number') == 'Q/25-26/0103':
                target_quote = quote
                break
        
        if target_quote:
            print(f"Found target quote: {target_quote['quote_number']} with ID: {target_quote['id']}")
            self.__class__.test_quote_id = target_quote['id']
            self.__class__.test_quote = target_quote
        else:
            # Use any approved quote
            approved_quotes = [q for q in quotes if q.get('status', '').lower() == 'approved']
            if approved_quotes:
                target_quote = approved_quotes[0]
                print(f"Using approved quote: {target_quote['quote_number']} with ID: {target_quote['id']}")
                self.__class__.test_quote_id = target_quote['id']
                self.__class__.test_quote = target_quote
            else:
                pytest.skip("No approved quotes found for testing")
    
    def test_02_get_revision_history_endpoint(self):
        """Test GET /api/quotes/{quote_id}/history endpoint"""
        if not hasattr(self.__class__, 'test_quote_id'):
            pytest.skip("No test quote available")
        
        quote_id = self.__class__.test_quote_id
        response = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}/history")
        
        assert response.status_code == 200, f"Failed to get history: {response.text}"
        
        data = response.json()
        assert "quote_id" in data, "Response missing quote_id"
        assert "quote_number" in data, "Response missing quote_number"
        assert "revision_count" in data, "Response missing revision_count"
        assert "history" in data, "Response missing history array"
        
        print(f"Revision count: {data['revision_count']}")
        print(f"Quote number: {data['quote_number']}")
        
        if data['history']:
            print(f"Latest revision: {data['history'][0]}")
            # Check structure of revision entry
            entry = data['history'][0]
            assert "timestamp" in entry, "Entry missing timestamp"
            assert "changed_by" in entry, "Entry missing changed_by"
            assert "action" in entry, "Entry missing action"
            assert "changes" in entry, "Entry missing changes"
        
        self.__class__.initial_revision_count = data['revision_count']
    
    def test_03_get_history_invalid_quote_id(self):
        """Test GET history with invalid quote ID returns 400"""
        response = self.session.get(f"{BASE_URL}/api/quotes/invalid-id/history")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    def test_04_get_history_nonexistent_quote_id(self):
        """Test GET history with nonexistent quote ID returns 404"""
        # Use a valid ObjectId format but non-existent
        response = self.session.get(f"{BASE_URL}/api/quotes/000000000000000000000000/history")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_05_update_quote_packing_type_creates_revision(self):
        """Test updating packing type creates a revision history entry"""
        if not hasattr(self.__class__, 'test_quote_id'):
            pytest.skip("No test quote available")
        
        quote_id = self.__class__.test_quote_id
        
        # Get current quote state
        quote_response = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}")
        assert quote_response.status_code == 200
        current_quote = quote_response.json()
        
        # Choose a different packing type
        current_packing = current_quote.get('packing_type', 'standard')
        new_packing = 'pallet' if current_packing != 'pallet' else 'wooden_box'
        
        # Update packing type
        update_response = self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json={
            "packing_type": new_packing,
        })
        
        assert update_response.status_code == 200, f"Failed to update quote: {update_response.text}"
        
        # Wait for database write
        time.sleep(0.5)
        
        # Check revision history
        history_response = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}/history")
        assert history_response.status_code == 200
        
        history_data = history_response.json()
        
        # Should have at least one entry
        assert len(history_data['history']) > 0, "No revision history entries found after update"
        
        # Latest entry should be about packing type change
        latest = history_data['history'][0]
        print(f"Latest revision entry: {latest}")
        
        # Check the changes include packing type
        if 'Packing Type' in latest.get('changes', {}):
            packing_change = latest['changes']['Packing Type']
            print(f"Packing Type change: {packing_change}")
            assert 'old' in packing_change, "Change missing old value"
            assert 'new' in packing_change, "Change missing new value"
        
        # Verify action is 'updated'
        assert latest.get('action') == 'updated', f"Expected action 'updated', got {latest.get('action')}"
        
        # Verify changed_by is recorded
        assert latest.get('changed_by'), "Changed_by not recorded"
    
    def test_06_update_quote_freight_creates_revision(self):
        """Test updating freight creates a revision history entry"""
        if not hasattr(self.__class__, 'test_quote_id'):
            pytest.skip("No test quote available")
        
        quote_id = self.__class__.test_quote_id
        
        # Get current quote state
        quote_response = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}")
        assert quote_response.status_code == 200
        current_quote = quote_response.json()
        
        # Update shipping cost (freight)
        current_freight = current_quote.get('shipping_cost', 0)
        new_freight = current_freight + 100 if current_freight < 5000 else current_freight - 100
        
        update_response = self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json={
            "shipping_cost": new_freight,
        })
        
        assert update_response.status_code == 200, f"Failed to update quote: {update_response.text}"
        
        # Wait for database write
        time.sleep(0.5)
        
        # Check revision history
        history_response = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}/history")
        assert history_response.status_code == 200
        
        history_data = history_response.json()
        latest = history_data['history'][0]
        
        print(f"Latest revision after freight update: {latest}")
        
        # Check if freight change is logged
        if 'Freight' in latest.get('changes', {}):
            freight_change = latest['changes']['Freight']
            print(f"Freight change: {freight_change}")
            assert 'new' in freight_change, "Freight change missing new value"
    
    def test_07_update_quote_discount_creates_revision(self):
        """Test updating discount creates a revision history entry"""
        if not hasattr(self.__class__, 'test_quote_id'):
            pytest.skip("No test quote available")
        
        quote_id = self.__class__.test_quote_id
        
        # Get current quote state
        quote_response = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}")
        assert quote_response.status_code == 200
        current_quote = quote_response.json()
        
        # Update discount percent
        current_discount = current_quote.get('discount_percent', 0)
        new_discount = current_discount + 2 if current_discount < 20 else current_discount - 2
        
        update_response = self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json={
            "discount_percent": new_discount,
        })
        
        assert update_response.status_code == 200, f"Failed to update quote: {update_response.text}"
        
        # Wait for database write
        time.sleep(0.5)
        
        # Check revision history
        history_response = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}/history")
        assert history_response.status_code == 200
        
        history_data = history_response.json()
        latest = history_data['history'][0]
        
        print(f"Latest revision after discount update: {latest}")
        
        # Check if discount change is logged
        if 'Discount %' in latest.get('changes', {}):
            discount_change = latest['changes']['Discount %']
            print(f"Discount change: {discount_change}")
            assert 'new' in discount_change, "Discount change missing new value"
    
    def test_08_revision_history_has_before_after_values(self):
        """Verify revision history entries have before/after values for tracked fields"""
        if not hasattr(self.__class__, 'test_quote_id'):
            pytest.skip("No test quote available")
        
        quote_id = self.__class__.test_quote_id
        
        history_response = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}/history")
        assert history_response.status_code == 200
        
        history_data = history_response.json()
        
        # Check if we have entries with proper before/after format
        has_valid_changes = False
        for entry in history_data['history']:
            changes = entry.get('changes', {})
            for field, values in changes.items():
                if isinstance(values, dict) and 'old' in values and 'new' in values:
                    has_valid_changes = True
                    print(f"Field '{field}': old='{values['old']}', new='{values['new']}'")
        
        if history_data['history']:
            assert has_valid_changes, "No entries found with proper old/new value format"
    
    def test_09_revision_history_sorted_by_timestamp(self):
        """Verify revision history is sorted by timestamp (newest first)"""
        if not hasattr(self.__class__, 'test_quote_id'):
            pytest.skip("No test quote available")
        
        quote_id = self.__class__.test_quote_id
        
        history_response = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}/history")
        assert history_response.status_code == 200
        
        history_data = history_response.json()
        history = history_data['history']
        
        if len(history) >= 2:
            for i in range(len(history) - 1):
                current_ts = history[i].get('timestamp', '')
                next_ts = history[i + 1].get('timestamp', '')
                if current_ts and next_ts:
                    # Newer should come first (descending order)
                    assert current_ts >= next_ts, f"History not sorted correctly: {current_ts} should be >= {next_ts}"
            print(f"Verified {len(history)} entries are sorted by timestamp descending")
    
    def test_10_multiple_field_update_single_revision_entry(self):
        """Test updating multiple fields creates single revision entry with all changes"""
        if not hasattr(self.__class__, 'test_quote_id'):
            pytest.skip("No test quote available")
        
        quote_id = self.__class__.test_quote_id
        
        # Get current state
        quote_response = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}")
        assert quote_response.status_code == 200
        current_quote = quote_response.json()
        
        # Get current history count
        history_before = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}/history")
        count_before = history_before.json()['revision_count']
        
        # Update multiple fields at once
        current_packing = current_quote.get('packing_type', 'standard')
        new_packing = 'standard' if current_packing != 'standard' else 'pallet'
        
        current_freight = current_quote.get('shipping_cost', 0)
        new_freight = current_freight + 50
        
        update_response = self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json={
            "packing_type": new_packing,
            "shipping_cost": new_freight,
        })
        
        assert update_response.status_code == 200
        
        time.sleep(0.5)
        
        # Check history
        history_after = self.session.get(f"{BASE_URL}/api/quotes/{quote_id}/history")
        count_after = history_after.json()['revision_count']
        
        # Should have added exactly one entry
        assert count_after == count_before + 1, f"Expected one new entry, got {count_after - count_before}"
        
        # Latest entry should have both changes
        latest = history_after.json()['history'][0]
        changes = latest.get('changes', {})
        
        print(f"Multi-field update changes: {changes}")
        
        # Both changes should be in the same entry
        assert len(changes) >= 2, "Multi-field update should have multiple changes in one entry"


class TestRevisionHistoryUnauthenticated:
    """Test revision history access control"""
    
    def test_history_requires_auth(self):
        """Test that history endpoint requires authentication"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Try to access without auth
        response = session.get(f"{BASE_URL}/api/quotes/000000000000000000000000/history")
        
        # Should return 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
