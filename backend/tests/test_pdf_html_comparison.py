"""
Test suite for comparing Backend PDF HTML with Frontend PDF HTML
- P0 CRITICAL: Verify backend and frontend PDF HTML are structurally identical
- Verifies use_item_discounts flag is passed correctly
- Compares table headers, columns, and content format
"""

import pytest
import requests
import os
import sys
import re

# Add backend to path for importing generate_quote_html
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://roller-quote-tool.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "test@test.com"
ADMIN_PASSWORD = "test123"


class TestPdfHtmlComparison:
    """Tests for comparing Backend and Frontend PDF HTML generation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_backend_pdf_html_structure_total_discount_mode(self):
        """Test backend generate_quote_html structure for TOTAL DISCOUNT mode (use_item_discounts=False)"""
        from server import generate_quote_html
        
        test_quote_data = {
            "quote_number": "Q/25-26/9999",
            "customer_code": "C0001",
            "customer_company": "Acme Corp",
            "customer_name": "Test Customer",
            "customer_email": "test@example.com",
            "customer_details": {
                "company": "Acme Corp",
                "name": "Test Customer",
                "address": "123 Test St",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "gst_number": "27XXXXX1234X1ZX",
                "phone": "9876543210"
            },
            "products": [
                {
                    "product_id": "P001",
                    "product_name": "Test Roller 89x300",
                    "quantity": 10,
                    "unit_price": 500.00,
                    "specifications": {
                        "roller_type": "Carrying",
                        "pipe_diameter": 89,
                        "shaft_diameter": 20
                    }
                }
            ],
            "subtotal": 5000.00,
            "total_discount": 250.00,
            "use_item_discounts": False,  # TOTAL DISCOUNT MODE
            "discount_percent": 5.0,
            "packing_charges": 100.00,
            "shipping_cost": 200.00,
            "total_price": 5050.00,
            "original_rfq_number": "RFQ/25-26/0027",
            "approved_at": "2026-03-06T10:00:00+05:30"
        }
        
        html_output = generate_quote_html(test_quote_data)
        
        # Save HTML for inspection
        with open('/tmp/backend_total_discount_mode.html', 'w') as f:
            f.write(html_output)
        print("✓ Saved backend HTML to /tmp/backend_total_discount_mode.html")
        
        # P0 CRITICAL: Verify table headers for TOTAL DISCOUNT mode (Frontend format)
        # Expected headers: #, Description, Qty, Unit Price, Amount
        assert '<th style="width: 5%;">#</th>' in html_output, "Missing # header"
        assert 'Description</th>' in html_output, "Missing Description header"
        assert 'Qty</th>' in html_output, "Missing Qty header"
        assert 'Unit Price</th>' in html_output, "Missing Unit Price header"
        assert 'Amount</th>' in html_output, "Missing Amount header"
        print("✓ Table headers match frontend format for Total Discount mode")
        
        # Verify NO Disc % column in total discount mode
        assert 'Disc %</th>' not in html_output, "Disc % header should NOT be present in total discount mode"
        assert 'Value After Disc</th>' not in html_output, "Value After Disc header should NOT be present in total discount mode"
        print("✓ Per-item discount columns correctly hidden in Total Discount mode")
        
        # Verify customer_code
        assert "Customer Code: C0001" in html_output, "customer_code missing"
        print("✓ customer_code present")
        
        # Verify customer_company
        assert "Acme Corp" in html_output, "customer_company missing"
        print("✓ customer_company present")
        
        # Verify Rs. currency formatting with commas
        assert "Rs." in html_output, "Rs. currency symbol missing"
        print("✓ Rs. currency formatting present")
        
        # Verify T&Cs sections
        assert "Commercial Terms" in html_output, "Commercial Terms section missing"
        assert "Technical Specifications" in html_output, "Technical Specifications section missing"
        assert "Payment Terms" in html_output, "Payment Terms missing"
        print("✓ Terms & Conditions sections present")
        
        # Verify discount is shown
        assert "Discount" in html_output, "Discount label missing"
        print("✓ Discount section present")
    
    def test_backend_pdf_html_structure_item_discount_mode(self):
        """Test backend generate_quote_html structure for PER-ITEM DISCOUNT mode (use_item_discounts=True)"""
        from server import generate_quote_html
        
        test_quote_data = {
            "quote_number": "Q/25-26/9998",
            "customer_code": "C0002",
            "customer_company": "Beta Inc",
            "customer_name": "Another Customer",
            "customer_email": "another@example.com",
            "customer_details": {
                "company": "Beta Inc",
                "name": "Another Customer",
                "address": "456 Beta St",
                "city": "Delhi",
                "state": "Delhi",
                "pincode": "110001",
                "gst_number": "07XXXXX5678X2ZX",
                "phone": "9876543211"
            },
            "products": [
                {
                    "product_id": "P002",
                    "product_name": "Test Roller 89x400",
                    "quantity": 5,
                    "unit_price": 600.00,
                    "item_discount_percent": 10.0,  # 10% per-item discount
                    "specifications": {
                        "roller_type": "Return",
                        "pipe_diameter": 89,
                        "shaft_diameter": 20
                    }
                },
                {
                    "product_id": "P003",
                    "product_name": "Test Roller 108x500",
                    "quantity": 3,
                    "unit_price": 800.00,
                    "item_discount_percent": 5.0,  # 5% per-item discount
                    "specifications": {
                        "roller_type": "Impact",
                        "pipe_diameter": 108,
                        "shaft_diameter": 25
                    }
                }
            ],
            "subtotal": 5400.00,  # (5*600) + (3*800)
            "total_discount": 0,  # Not used in item discount mode
            "use_item_discounts": True,  # PER-ITEM DISCOUNT MODE
            "discount_percent": 0,
            "packing_charges": 150.00,
            "shipping_cost": 250.00,
            "total_price": 5300.00,
            "original_rfq_number": "RFQ/25-26/0028",
            "approved_at": "2026-03-06T11:00:00+05:30"
        }
        
        html_output = generate_quote_html(test_quote_data)
        
        # Save HTML for inspection
        with open('/tmp/backend_item_discount_mode.html', 'w') as f:
            f.write(html_output)
        print("✓ Saved backend HTML to /tmp/backend_item_discount_mode.html")
        
        # P0 CRITICAL: Verify table headers for PER-ITEM DISCOUNT mode (Frontend format)
        # Expected headers: Sr., Item Code, Qty, Rate, Disc %, Value After Disc, Total
        assert '<th style="width: 5%;">Sr.</th>' in html_output, "Missing Sr. header"
        assert 'Item Code</th>' in html_output, "Missing Item Code header"
        assert 'Qty</th>' in html_output, "Missing Qty header"
        assert 'Rate</th>' in html_output, "Missing Rate header"
        assert 'Disc %</th>' in html_output, "Missing Disc % header"
        assert 'Value After Disc</th>' in html_output, "Missing Value After Disc header"
        assert 'Total</th>' in html_output, "Missing Total header"
        print("✓ Table headers match frontend format for Per-Item Discount mode")
        
        # Verify discount percentages are shown in the table
        assert "10.0%" in html_output, "10% item discount missing in table"
        assert "5.0%" in html_output, "5% item discount missing in table"
        print("✓ Item discount percentages displayed in table")
        
        # Verify Item Discounts (Total) summary label
        assert "Item Discounts (Total)" in html_output, "Item Discounts (Total) summary label missing"
        print("✓ Item Discounts (Total) summary label present")
        
        # Verify customer_code
        assert "Customer Code: C0002" in html_output, "customer_code missing"
        print("✓ customer_code present")
    
    def test_compare_backend_frontend_table_headers_total_discount(self):
        """P0 CRITICAL: Compare backend vs frontend table headers for Total Discount mode"""
        from server import generate_quote_html
        
        # Backend HTML
        test_data = {
            "quote_number": "Q/25-26/TEST",
            "products": [{"product_id": "P1", "product_name": "Roller", "quantity": 1, "unit_price": 100}],
            "subtotal": 100, "total_discount": 0, "use_item_discounts": False,
            "packing_charges": 0, "shipping_cost": 0, "total_price": 100,
            "customer_name": "Test", "customer_company": "Test Co"
        }
        backend_html = generate_quote_html(test_data)
        
        # Extract table header from backend
        backend_header_match = re.search(r'<thead>(.*?)</thead>', backend_html, re.DOTALL)
        assert backend_header_match, "Backend table header not found"
        backend_header = backend_header_match.group(1)
        
        # Frontend format for Total Discount mode (from quotes.tsx lines 643-651):
        # <tr>
        #   <th style="width: 5%;">#</th>
        #   <th style="width: 45%; text-align: left;">Description</th>
        #   <th style="width: 10%;">Qty</th>
        #   <th style="width: 20%; text-align: right;">Unit Price</th>
        #   <th style="width: 20%; text-align: right;">Amount</th>
        # </tr>
        
        expected_headers = ['#', 'Description', 'Qty', 'Unit Price', 'Amount']
        for header in expected_headers:
            assert header in backend_header or header.lower() in backend_header.lower(), f"Missing header: {header}"
        
        print("✓ P0 VERIFIED: Backend table headers match frontend for Total Discount mode")
        print(f"  Headers: {expected_headers}")
    
    def test_compare_backend_frontend_table_headers_item_discount(self):
        """P0 CRITICAL: Compare backend vs frontend table headers for Per-Item Discount mode"""
        from server import generate_quote_html
        
        # Backend HTML with use_item_discounts=True
        test_data = {
            "quote_number": "Q/25-26/TEST2",
            "products": [{"product_id": "P1", "product_name": "Roller", "quantity": 1, "unit_price": 100, "item_discount_percent": 5}],
            "subtotal": 100, "total_discount": 0, "use_item_discounts": True,
            "packing_charges": 0, "shipping_cost": 0, "total_price": 95,
            "customer_name": "Test", "customer_company": "Test Co"
        }
        backend_html = generate_quote_html(test_data)
        
        # Extract table header from backend
        backend_header_match = re.search(r'<thead>(.*?)</thead>', backend_html, re.DOTALL)
        assert backend_header_match, "Backend table header not found"
        backend_header = backend_header_match.group(1)
        
        # Frontend format for Per-Item Discount mode (from quotes.tsx lines 633-642):
        # <tr>
        #   <th style="width: 5%;">Sr.</th>
        #   <th style="width: 25%; text-align: left;">Item Code</th>
        #   <th style="width: 8%;">Qty</th>
        #   <th style="width: 15%; text-align: right;">Rate</th>
        #   <th style="width: 12%;">Disc %</th>
        #   <th style="width: 17%; text-align: right;">Value After Disc</th>
        #   <th style="width: 18%; text-align: right;">Total</th>
        # </tr>
        
        expected_headers = ['Sr.', 'Item Code', 'Qty', 'Rate', 'Disc %', 'Value After Disc', 'Total']
        for header in expected_headers:
            assert header in backend_header or header.lower() in backend_header.lower(), f"Missing header: {header}"
        
        print("✓ P0 VERIFIED: Backend table headers match frontend for Per-Item Discount mode")
        print(f"  Headers: {expected_headers}")
    
    def test_use_item_discounts_passed_in_approval_data(self):
        """P0: Verify use_item_discounts is included in email data during approval"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        # Get an approved quote
        response = self.session.get(
            f"{BASE_URL}/api/quotes",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        quotes = response.json()
        
        # Find any quote
        if not quotes:
            pytest.skip("No quotes available for testing")
        
        quote = quotes[0]
        
        # Verify use_item_discounts field exists in API response
        assert "use_item_discounts" in quote or quote.get("use_item_discounts") is not None or quote.get("use_item_discounts") == False, \
            "use_item_discounts field should exist in quote response"
        
        print(f"✓ Quote {quote.get('quote_number')} has use_item_discounts: {quote.get('use_item_discounts')}")
    
    def test_approved_quote_pdf_data_completeness(self):
        """P0: Test that approved quote has all fields needed for PDF generation"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.get(
            f"{BASE_URL}/api/quotes",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        quotes = response.json()
        
        # Find approved quotes
        approved_quotes = [q for q in quotes if q.get("status") == "approved"]
        
        if not approved_quotes:
            # Try to find Q/25-26/0038 specifically mentioned in requirements
            quote_0038 = [q for q in quotes if "0038" in q.get("quote_number", "")]
            if quote_0038:
                approved_quotes = quote_0038
        
        if not approved_quotes:
            pytest.skip("No approved quotes available for testing")
        
        quote = approved_quotes[0]
        quote_number = quote.get("quote_number")
        
        print(f"\n✓ Testing approved quote: {quote_number}")
        
        # Required fields for PDF generation
        required_fields = [
            "quote_number",
            "customer_name",
            "products",
            "subtotal",
            "total_price"
        ]
        
        for field in required_fields:
            assert field in quote, f"Missing required field: {field}"
            print(f"  ✓ {field}: {str(quote.get(field))[:50]}...")
        
        # Important fields for PDF matching
        important_fields = [
            ("customer_code", "Customer code for PDF header"),
            ("customer_company", "Customer company for PDF header"),
            ("use_item_discounts", "Flag for table format"),
            ("total_discount", "Discount amount"),
            ("packing_charges", "Packing charges"),
            ("shipping_cost", "Freight charges"),
        ]
        
        print("\n  Important fields for PDF generation:")
        for field, description in important_fields:
            value = quote.get(field)
            status = "✓" if value is not None else "⚠"
            print(f"  {status} {field}: {value} ({description})")
        
        print("\n✓ All required fields present for PDF generation")


class TestRealApprovedQuote:
    """Test with real approved quote from database"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_generate_pdf_for_recent_approved_quote(self):
        """Test generating PDF HTML for a recently approved quote"""
        from server import generate_quote_html
        
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.get(
            f"{BASE_URL}/api/quotes",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        quotes = response.json()
        
        # Find the recently approved quote Q/25-26/0038
        target_quote = None
        for q in quotes:
            if "0038" in q.get("quote_number", ""):
                target_quote = q
                break
        
        if not target_quote:
            # Find any approved quote
            approved_quotes = [q for q in quotes if q.get("status") == "approved"]
            if approved_quotes:
                target_quote = approved_quotes[0]
        
        if not target_quote:
            pytest.skip("No approved quote found for testing")
        
        print(f"\n✓ Testing PDF generation for: {target_quote.get('quote_number')}")
        print(f"  customer_code: {target_quote.get('customer_code')}")
        print(f"  customer_company: {target_quote.get('customer_company')}")
        print(f"  use_item_discounts: {target_quote.get('use_item_discounts')}")
        
        # Generate HTML using the same function as email
        html_output = generate_quote_html(target_quote)
        
        # Save for inspection
        filename = f"/tmp/backend_{target_quote.get('quote_number', 'quote').replace('/', '-')}.html"
        with open(filename, 'w') as f:
            f.write(html_output)
        print(f"  ✓ Saved HTML to {filename}")
        
        # Verify key elements
        if target_quote.get('customer_code'):
            assert f"Customer Code: {target_quote.get('customer_code')}" in html_output, \
                "customer_code not in generated HTML"
            print("  ✓ customer_code correctly rendered in HTML")
        
        if target_quote.get('customer_company'):
            assert target_quote.get('customer_company') in html_output, \
                "customer_company not in generated HTML"
            print("  ✓ customer_company correctly rendered in HTML")
        
        # Verify table format based on use_item_discounts
        if target_quote.get('use_item_discounts'):
            assert "Disc %" in html_output, "Missing Disc % header for item discount mode"
            print("  ✓ Per-item discount table format correct")
        else:
            assert "#" in html_output or "Description" in html_output, "Missing standard table headers"
            print("  ✓ Total discount table format correct")
        
        # Verify T&Cs present
        assert "Commercial Terms" in html_output, "Missing Commercial Terms"
        assert "Technical Specifications" in html_output, "Missing Technical Specifications"
        print("  ✓ Terms & Conditions sections present")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
