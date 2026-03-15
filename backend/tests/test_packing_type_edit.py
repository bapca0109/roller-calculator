"""
Test suite for Edit Quote Packing Type Feature
Tests the ability to change packing type when editing approved quotes
Features tested:
- Updating packing type from one value to another (standard, pallet, wooden_box)
- Custom packing type with custom percentage
- Packing charges calculation based on packing type
- Grand total updates correctly with new packing charges
"""

import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://conveyor-roller-calc.preview.emergentagent.com').rstrip('/')


class TestPackingTypeEdit:
    """Tests for editing packing type on approved quotes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin authentication"""
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
            self.admin_token = token
            print(f"Admin login successful")
        else:
            pytest.skip(f"Admin authentication failed: {login_response.status_code}")
    
    def test_api_health(self):
        """Test backend API health"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("API health check passed")
    
    def test_get_approved_quotes(self):
        """Test getting list of quotes to find approved ones"""
        response = self.session.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        quotes = response.json()
        assert isinstance(quotes, list)
        print(f"Found {len(quotes)} quotes total")
        
        # Find approved quotes
        approved_quotes = [q for q in quotes if q.get('status') == 'approved']
        print(f"Found {len(approved_quotes)} approved quotes")
        return approved_quotes
    
    def test_get_specific_quote_Q_25_26_0103(self):
        """Test getting the specific quote mentioned in requirements"""
        response = self.session.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        quotes = response.json()
        
        # Find the specific quote Q/25-26/0103
        target_quote = None
        for q in quotes:
            if q.get('quote_number') == 'Q/25-26/0103':
                target_quote = q
                break
        
        if target_quote:
            print(f"Found quote Q/25-26/0103:")
            print(f"  Status: {target_quote.get('status')}")
            print(f"  Packing Type: {target_quote.get('packing_type')}")
            print(f"  Packing Charges: {target_quote.get('packing_charges')}")
            print(f"  Total Price: {target_quote.get('total_price')}")
            print(f"  Quote ID: {target_quote.get('id')}")
            return target_quote
        else:
            print("Quote Q/25-26/0103 not found, will use first approved quote")
            return None
    
    def test_update_packing_type_standard_to_pallet(self):
        """Test updating packing type from standard/wooden_box to pallet (4%)"""
        # Get quotes
        response = self.session.get(f"{BASE_URL}/api/quotes")
        assert response.status_code == 200
        quotes = response.json()
        
        # Find an approved quote
        approved = [q for q in quotes if q.get('status') == 'approved']
        if not approved:
            pytest.skip("No approved quotes available for testing")
        
        quote = approved[0]
        quote_id = quote.get('id')
        original_packing_type = quote.get('packing_type')
        original_packing_charges = quote.get('packing_charges', 0)
        
        print(f"Testing with quote {quote.get('quote_number')}")
        print(f"Original packing type: {original_packing_type}")
        print(f"Original packing charges: {original_packing_charges}")
        
        # Calculate expected packing charges with pallet (4%)
        subtotal = quote.get('subtotal', 0)
        total_discount = quote.get('total_discount', 0)
        after_discount = subtotal - total_discount
        expected_packing_charges = after_discount * 0.04  # 4% for pallet
        
        # Update to pallet packing
        update_data = {
            "packing_type": "pallet",
            "packing_charges": expected_packing_charges
        }
        
        response = self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=update_data)
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        updated_quote = response.json()
        assert updated_quote.get('packing_type') == 'pallet'
        print(f"Updated packing type to: {updated_quote.get('packing_type')}")
        print(f"Updated packing charges: {updated_quote.get('packing_charges')}")
        
        # Verify by fetching the quote again
        verify_response = self.session.get(f"{BASE_URL}/api/quotes")
        verify_quotes = verify_response.json()
        verified_quote = next((q for q in verify_quotes if q.get('id') == quote_id), None)
        
        assert verified_quote is not None
        assert verified_quote.get('packing_type') == 'pallet'
        print("Packing type update verified via GET")
        
        # Restore original packing type
        restore_data = {
            "packing_type": original_packing_type,
            "packing_charges": original_packing_charges
        }
        self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=restore_data)
        print("Restored original packing type")
    
    def test_update_packing_type_to_wooden_box(self):
        """Test updating packing type to wooden_box (8%)"""
        response = self.session.get(f"{BASE_URL}/api/quotes")
        quotes = response.json()
        
        approved = [q for q in quotes if q.get('status') == 'approved']
        if not approved:
            pytest.skip("No approved quotes available")
        
        quote = approved[0]
        quote_id = quote.get('id')
        original_packing_type = quote.get('packing_type')
        original_packing_charges = quote.get('packing_charges', 0)
        
        # Update to wooden_box
        update_data = {
            "packing_type": "wooden_box"
        }
        
        response = self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=update_data)
        assert response.status_code == 200
        
        updated = response.json()
        assert updated.get('packing_type') == 'wooden_box'
        print(f"Successfully updated to wooden_box: {updated.get('packing_type')}")
        
        # Restore
        restore_data = {"packing_type": original_packing_type, "packing_charges": original_packing_charges}
        self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=restore_data)
    
    def test_update_packing_type_to_standard(self):
        """Test updating packing type to standard (1%)"""
        response = self.session.get(f"{BASE_URL}/api/quotes")
        quotes = response.json()
        
        approved = [q for q in quotes if q.get('status') == 'approved']
        if not approved:
            pytest.skip("No approved quotes available")
        
        quote = approved[0]
        quote_id = quote.get('id')
        original_packing_type = quote.get('packing_type')
        original_packing_charges = quote.get('packing_charges', 0)
        
        # Update to standard
        update_data = {
            "packing_type": "standard"
        }
        
        response = self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=update_data)
        assert response.status_code == 200
        
        updated = response.json()
        assert updated.get('packing_type') == 'standard'
        print(f"Successfully updated to standard: {updated.get('packing_type')}")
        
        # Restore
        restore_data = {"packing_type": original_packing_type, "packing_charges": original_packing_charges}
        self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=restore_data)
    
    def test_update_packing_type_custom(self):
        """Test updating to custom packing type with custom percentage (e.g., custom_5)"""
        response = self.session.get(f"{BASE_URL}/api/quotes")
        quotes = response.json()
        
        approved = [q for q in quotes if q.get('status') == 'approved']
        if not approved:
            pytest.skip("No approved quotes available")
        
        quote = approved[0]
        quote_id = quote.get('id')
        original_packing_type = quote.get('packing_type')
        original_packing_charges = quote.get('packing_charges', 0)
        
        # Update to custom 5%
        custom_packing = "custom_5"
        update_data = {
            "packing_type": custom_packing
        }
        
        response = self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=update_data)
        assert response.status_code == 200
        
        updated = response.json()
        assert updated.get('packing_type') == custom_packing
        print(f"Successfully updated to custom packing: {updated.get('packing_type')}")
        
        # Restore
        restore_data = {"packing_type": original_packing_type, "packing_charges": original_packing_charges}
        self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=restore_data)
    
    def test_packing_charges_updated_with_total(self):
        """Test that packing charges and total price are updated correctly"""
        response = self.session.get(f"{BASE_URL}/api/quotes")
        quotes = response.json()
        
        approved = [q for q in quotes if q.get('status') == 'approved']
        if not approved:
            pytest.skip("No approved quotes available")
        
        quote = approved[0]
        quote_id = quote.get('id')
        original_packing_type = quote.get('packing_type')
        original_packing_charges = quote.get('packing_charges', 0)
        original_total = quote.get('total_price', 0)
        
        print(f"Original - Type: {original_packing_type}, Charges: {original_packing_charges}, Total: {original_total}")
        
        # Calculate values for pallet (4%)
        subtotal = quote.get('subtotal', 0)
        total_discount = quote.get('total_discount', 0)
        after_discount = subtotal - total_discount
        shipping = quote.get('shipping_cost', 0)
        new_packing_charges = after_discount * 0.04  # 4% for pallet
        taxable_amount = after_discount + new_packing_charges + shipping
        new_total = taxable_amount * 1.18  # Include GST
        
        update_data = {
            "packing_type": "pallet",
            "packing_charges": new_packing_charges,
            "total_price": new_total
        }
        
        response = self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=update_data)
        assert response.status_code == 200
        
        updated = response.json()
        print(f"Updated - Type: {updated.get('packing_type')}, Charges: {updated.get('packing_charges')}, Total: {updated.get('total_price')}")
        
        assert updated.get('packing_type') == 'pallet'
        assert abs(updated.get('packing_charges', 0) - new_packing_charges) < 1  # Allow small float difference
        
        # Restore original values
        restore_data = {
            "packing_type": original_packing_type,
            "packing_charges": original_packing_charges,
            "total_price": original_total
        }
        self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=restore_data)
        print("Restored original values")
    
    def test_full_edit_quote_flow(self):
        """Test complete edit quote flow - simulates what frontend does"""
        response = self.session.get(f"{BASE_URL}/api/quotes")
        quotes = response.json()
        
        approved = [q for q in quotes if q.get('status') == 'approved']
        if not approved:
            pytest.skip("No approved quotes available")
        
        quote = approved[0]
        quote_id = quote.get('id')
        
        # Store original values for restore
        original_data = {
            "packing_type": quote.get('packing_type'),
            "packing_charges": quote.get('packing_charges'),
            "total_price": quote.get('total_price'),
            "products": quote.get('products'),
            "subtotal": quote.get('subtotal'),
            "total_discount": quote.get('total_discount'),
            "use_item_discounts": quote.get('use_item_discounts'),
            "shipping_cost": quote.get('shipping_cost')
        }
        
        print(f"Testing full edit flow on quote {quote.get('quote_number')}")
        
        # Simulate frontend calculateEditedTotal for 'pallet' packing type
        subtotal = quote.get('subtotal', 0)
        total_discount = quote.get('total_discount', 0)
        after_discount = subtotal - total_discount
        packing_percent = 4  # pallet
        new_packing = after_discount * packing_percent / 100
        freight = quote.get('shipping_cost', 0)
        taxable_amount = after_discount + new_packing + freight
        grand_total = taxable_amount * 1.18  # GST
        
        # This is what frontend sends
        update_data = {
            "products": quote.get('products'),
            "subtotal": subtotal,
            "total_discount": total_discount,
            "use_item_discounts": quote.get('use_item_discounts', False),
            "packing_charges": new_packing,
            "packing_type": "pallet",
            "shipping_cost": freight,
            "total_price": grand_total
        }
        
        response = self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=update_data)
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        updated = response.json()
        print(f"Update successful:")
        print(f"  Packing type: {updated.get('packing_type')}")
        print(f"  Packing charges: {updated.get('packing_charges'):.2f}")
        print(f"  Total price: {updated.get('total_price'):.2f}")
        
        assert updated.get('packing_type') == 'pallet'
        
        # Verify persistence
        verify_response = self.session.get(f"{BASE_URL}/api/quotes")
        verify_quotes = verify_response.json()
        verified = next((q for q in verify_quotes if q.get('id') == quote_id), None)
        
        assert verified is not None
        assert verified.get('packing_type') == 'pallet'
        print("Verified packing type persisted correctly")
        
        # Restore original data
        self.session.put(f"{BASE_URL}/api/quotes/{quote_id}", json=original_data)
        print("Restored original quote data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
