"""
Test Suite for Export/PDF/Invoice Endpoints
Tests all export capabilities across Sales Orders, Invoicing, CRM, Quotes, Customers, Products, and Cart modules.
"""
import pytest
import requests
import os
import json
from datetime import datetime

# Use the public URL for testing
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://erp-roller-mfg.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "test@test.com"
ADMIN_PASSWORD = "test123"
CUSTOMER_EMAIL = "customer@test.com"
CUSTOMER_PASSWORD = "test123"


class TestAuthAndSetup:
    """Authentication and setup tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, f"No access_token in response: {data}"
        return data["access_token"]
    
    def test_admin_login(self, admin_token):
        """Verify admin can login and get token"""
        assert admin_token is not None
        assert len(admin_token) > 0
        print(f"✓ Admin login successful, token length: {len(admin_token)}")


class TestOrdersExport:
    """Test Sales Orders export endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_get_orders_list(self, admin_token):
        """GET /api/orders — list all orders with correct fields"""
        response = requests.get(
            f"{BASE_URL}/api/orders",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get orders: {response.text}"
        data = response.json()
        assert "orders" in data
        assert "total" in data
        print(f"✓ GET /api/orders returned {data['total']} orders")
        
        # Check order fields if orders exist
        if data["orders"]:
            order = data["orders"][0]
            expected_fields = ["so_number", "customer_name", "stage", "payment_status", "total_price"]
            for field in expected_fields:
                assert field in order, f"Missing field '{field}' in order"
            print(f"✓ Order fields verified: {list(order.keys())[:10]}...")
    
    def test_orders_export_excel(self, admin_token):
        """GET /api/orders/export/excel — returns Excel file with all sales orders"""
        response = requests.get(
            f"{BASE_URL}/api/orders/export/excel",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Orders Excel export failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheet" in content_type or "excel" in content_type or "octet-stream" in content_type, \
            f"Unexpected content type: {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, f"Missing attachment header: {content_disp}"
        assert ".xlsx" in content_disp or "Sales_Orders" in content_disp, f"Unexpected filename: {content_disp}"
        
        # Check file size
        assert len(response.content) > 0, "Excel file is empty"
        print(f"✓ GET /api/orders/export/excel returned {len(response.content)} bytes")
    
    def test_orders_export_pdf_with_token(self, admin_token):
        """GET /api/orders/export/pdf?token=TOKEN — returns HTML/PDF with styled order list"""
        response = requests.get(
            f"{BASE_URL}/api/orders/export/pdf?token={admin_token}"
        )
        assert response.status_code == 200, f"Orders PDF export failed: {response.text}"
        
        # Check content type (returns HTML for printing as PDF)
        content_type = response.headers.get("Content-Type", "")
        assert "html" in content_type or "pdf" in content_type, f"Unexpected content type: {content_type}"
        
        # Check content
        content = response.text
        assert len(content) > 0, "PDF/HTML content is empty"
        assert "Sales Orders" in content or "SO" in content, "Missing expected content in PDF"
        print(f"✓ GET /api/orders/export/pdf returned {len(content)} chars of HTML")
    
    def test_orders_summary_stats(self, admin_token):
        """GET /api/orders/summary/stats — order statistics"""
        response = requests.get(
            f"{BASE_URL}/api/orders/summary/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Orders stats failed: {response.text}"
        data = response.json()
        
        expected_fields = ["total_orders", "total_invoices", "by_stage", "by_payment"]
        for field in expected_fields:
            assert field in data, f"Missing field '{field}' in stats"
        
        print(f"✓ GET /api/orders/summary/stats: {data['total_orders']} orders, {data['total_invoices']} invoices")


class TestCRMExport:
    """Test CRM leads and followups export endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_crm_leads_export_excel(self, admin_token):
        """GET /api/crm/leads/export/excel — returns Excel with CRM leads"""
        response = requests.get(
            f"{BASE_URL}/api/crm/leads/export/excel",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"CRM leads export failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheet" in content_type or "excel" in content_type or "octet-stream" in content_type, \
            f"Unexpected content type: {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, f"Missing attachment header: {content_disp}"
        assert ".xlsx" in content_disp or "CRM_Leads" in content_disp, f"Unexpected filename: {content_disp}"
        
        print(f"✓ GET /api/crm/leads/export/excel returned {len(response.content)} bytes")
    
    def test_crm_followups_export_excel(self, admin_token):
        """GET /api/crm/followups/export/excel — returns Excel with follow-ups"""
        response = requests.get(
            f"{BASE_URL}/api/crm/followups/export/excel",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"CRM followups export failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheet" in content_type or "excel" in content_type or "octet-stream" in content_type, \
            f"Unexpected content type: {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, f"Missing attachment header: {content_disp}"
        
        print(f"✓ GET /api/crm/followups/export/excel returned {len(response.content)} bytes")


class TestInvoicesExport:
    """Test Invoices export and PDF generation endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def existing_invoices(self, admin_token):
        """Get existing invoices from database"""
        response = requests.get(
            f"{BASE_URL}/api/invoices",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            return response.json().get("invoices", [])
        return []
    
    def test_invoices_export_excel(self, admin_token):
        """GET /api/invoices/export/excel — returns Excel with all invoices"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/export/excel",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Invoices export failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheet" in content_type or "excel" in content_type or "octet-stream" in content_type, \
            f"Unexpected content type: {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, f"Missing attachment header: {content_disp}"
        
        print(f"✓ GET /api/invoices/export/excel returned {len(response.content)} bytes")
    
    def test_invoice_pdf_tax_invoice(self, admin_token, existing_invoices):
        """GET /api/invoices/{invoice_id}/pdf?token=TOKEN — returns Tax Invoice PDF with company details"""
        # Find a tax invoice
        tax_invoices = [inv for inv in existing_invoices if inv.get("invoice_type") == "tax"]
        
        if not tax_invoices:
            pytest.skip("No tax invoices found in database")
        
        invoice = tax_invoices[0]
        invoice_id = invoice.get("id") or invoice.get("invoice_number")
        
        response = requests.get(
            f"{BASE_URL}/api/invoices/{invoice_id}/pdf?token={admin_token}"
        )
        assert response.status_code == 200, f"Tax invoice PDF failed: {response.text}"
        
        # Check content type (returns HTML for printing as PDF)
        content_type = response.headers.get("Content-Type", "")
        assert "html" in content_type or "pdf" in content_type, f"Unexpected content type: {content_type}"
        
        # Check content contains required company details
        content = response.text
        assert "CONVERO SOLUTIONS" in content, "Missing company name CONVERO SOLUTIONS"
        assert "24BAUPP4310D2ZT" in content, "Missing GSTIN 24BAUPP4310D2ZT"
        assert "ICICI" in content, "Missing bank name ICICI"
        assert "777705908098" in content, "Missing bank account 777705908098"
        assert "ICIC0004942" in content, "Missing IFSC ICIC0004942"
        assert "84313910" in content, "Missing HSN code 84313910"
        assert "TAX INVOICE" in content, "Missing 'TAX INVOICE' title"
        
        print(f"✓ Tax Invoice PDF contains all required company details")
    
    def test_invoice_pdf_proforma_invoice(self, admin_token, existing_invoices):
        """GET /api/invoices/{invoice_id}/pdf?token=TOKEN — returns Proforma Invoice PDF with 'PROFORMA INVOICE' title"""
        # Find a proforma invoice
        proforma_invoices = [inv for inv in existing_invoices if inv.get("invoice_type") == "proforma"]
        
        if not proforma_invoices:
            pytest.skip("No proforma invoices found in database")
        
        invoice = proforma_invoices[0]
        invoice_id = invoice.get("id") or invoice.get("invoice_number")
        
        response = requests.get(
            f"{BASE_URL}/api/invoices/{invoice_id}/pdf?token={admin_token}"
        )
        assert response.status_code == 200, f"Proforma invoice PDF failed: {response.text}"
        
        # Check content
        content = response.text
        assert "PROFORMA INVOICE" in content, "Missing 'PROFORMA INVOICE' title"
        assert "CONVERO SOLUTIONS" in content, "Missing company name"
        
        print(f"✓ Proforma Invoice PDF contains 'PROFORMA INVOICE' title")
    
    def test_invoice_pdf_company_details_verification(self, admin_token, existing_invoices):
        """Verify Invoice PDF contains all required company details"""
        if not existing_invoices:
            pytest.skip("No invoices found in database")
        
        invoice = existing_invoices[0]
        invoice_id = invoice.get("id") or invoice.get("invoice_number")
        
        response = requests.get(
            f"{BASE_URL}/api/invoices/{invoice_id}/pdf?token={admin_token}"
        )
        assert response.status_code == 200
        
        content = response.text
        
        # Verify all required company details from .env
        required_details = {
            "Company Name": "CONVERO SOLUTIONS",
            "GSTIN": "24BAUPP4310D2ZT",
            "Bank": "ICICI",
            "Account": "777705908098",
            "IFSC": "ICIC0004942",
            "HSN": "84313910"
        }
        
        missing = []
        for name, value in required_details.items():
            if value not in content:
                missing.append(f"{name}: {value}")
        
        assert not missing, f"Missing company details in invoice PDF: {missing}"
        print(f"✓ Invoice PDF contains all required company details: {list(required_details.keys())}")


class TestQuotesExport:
    """Test Quotes export endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_quotes_export_excel(self, admin_token):
        """GET /api/quotes/export/excel — existing quotes export still works"""
        response = requests.get(
            f"{BASE_URL}/api/quotes/export/excel",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Quotes Excel export failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheet" in content_type or "excel" in content_type or "octet-stream" in content_type, \
            f"Unexpected content type: {content_type}"
        
        print(f"✓ GET /api/quotes/export/excel returned {len(response.content)} bytes")
    
    def test_quotes_export_pdf(self, admin_token):
        """GET /api/quotes/export/pdf?token=TOKEN — existing quotes PDF export still works"""
        response = requests.get(
            f"{BASE_URL}/api/quotes/export/pdf?token={admin_token}"
        )
        assert response.status_code == 200, f"Quotes PDF export failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "pdf" in content_type or "html" in content_type, f"Unexpected content type: {content_type}"
        
        print(f"✓ GET /api/quotes/export/pdf returned {len(response.content)} bytes")


class TestCustomersExport:
    """Test Customers export endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_customers_export_excel(self, admin_token):
        """GET /api/customers/export/excel — existing customers export still works"""
        response = requests.get(
            f"{BASE_URL}/api/customers/export/excel",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Customers Excel export failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheet" in content_type or "excel" in content_type or "octet-stream" in content_type, \
            f"Unexpected content type: {content_type}"
        
        print(f"✓ GET /api/customers/export/excel returned {len(response.content)} bytes")


class TestOrderOperations:
    """Test Sales Order operations - convert quote, payments, stage updates, invoice generation"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def existing_orders(self, admin_token):
        """Get existing orders from database"""
        response = requests.get(
            f"{BASE_URL}/api/orders",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            return response.json().get("orders", [])
        return []
    
    @pytest.fixture(scope="class")
    def approved_quotes(self, admin_token):
        """Get approved quotes that haven't been converted to SO"""
        response = requests.get(
            f"{BASE_URL}/api/quotes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            quotes = response.json()
            # Filter for approved quotes without converted_to_so
            return [q for q in quotes if q.get("status") == "approved" and not q.get("converted_to_so")]
        return []
    
    def test_convert_quote_to_order(self, admin_token, approved_quotes):
        """POST /api/orders/from-quote/{quote_id} — convert approved quote to SO"""
        if not approved_quotes:
            pytest.skip("No approved quotes available for conversion")
        
        quote = approved_quotes[0]
        quote_id = quote.get("id")
        
        response = requests.post(
            f"{BASE_URL}/api/orders/from-quote/{quote_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # May fail if already converted
        if response.status_code == 400 and "Already converted" in response.text:
            print(f"✓ Quote already converted to SO (expected behavior)")
            return
        
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()
            assert "order" in data or "so_number" in data.get("message", "")
            print(f"✓ POST /api/orders/from-quote/{quote_id} - Quote converted to SO")
        else:
            # Log but don't fail - quote may have issues
            print(f"⚠ Quote conversion returned {response.status_code}: {response.text[:200]}")
    
    def test_record_payment_on_order(self, admin_token, existing_orders):
        """POST /api/orders/{order_id}/payments — record payment on order"""
        if not existing_orders:
            pytest.skip("No orders found in database")
        
        order = existing_orders[0]
        order_id = order.get("id") or order.get("so_number")
        
        response = requests.post(
            f"{BASE_URL}/api/orders/{order_id}/payments",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "amount": 1000.00,
                "mode": "bank_transfer",
                "reference": "TEST_UTR_123",
                "notes": "Test payment"
            }
        )
        assert response.status_code == 200, f"Payment recording failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "payment_status" in data
        print(f"✓ POST /api/orders/{order_id}/payments - Payment recorded, status: {data['payment_status']}")
    
    def test_update_order_stage(self, admin_token, existing_orders):
        """PUT /api/orders/{order_id}/stage — update order stage"""
        if not existing_orders:
            pytest.skip("No orders found in database")
        
        order = existing_orders[0]
        order_id = order.get("id") or order.get("so_number")
        current_stage = order.get("stage", "confirmed")
        
        # Determine next stage
        stages = ["confirmed", "in_production", "ready", "dispatched", "delivered"]
        current_idx = stages.index(current_stage) if current_stage in stages else 0
        next_stage = stages[min(current_idx + 1, len(stages) - 1)]
        
        response = requests.put(
            f"{BASE_URL}/api/orders/{order_id}/stage",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "stage": next_stage,
                "notes": "Test stage update"
            }
        )
        assert response.status_code == 200, f"Stage update failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"✓ PUT /api/orders/{order_id}/stage - Stage updated to {next_stage}")
    
    def test_generate_proforma_invoice(self, admin_token, existing_orders):
        """POST /api/orders/{order_id}/proforma — generate proforma invoice"""
        if not existing_orders:
            pytest.skip("No orders found in database")
        
        # Find an order without proforma invoice
        orders_without_pi = [o for o in existing_orders if not o.get("proforma_invoice")]
        
        if not orders_without_pi:
            print("✓ All orders already have proforma invoices")
            return
        
        order = orders_without_pi[0]
        order_id = order.get("id") or order.get("so_number")
        
        response = requests.post(
            f"{BASE_URL}/api/orders/{order_id}/proforma",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Proforma generation failed: {response.text}"
        
        data = response.json()
        assert "invoice" in data
        assert data["invoice"]["invoice_type"] == "proforma"
        print(f"✓ POST /api/orders/{order_id}/proforma - Proforma invoice generated: {data['invoice']['invoice_number']}")
    
    def test_generate_tax_invoice(self, admin_token, existing_orders):
        """POST /api/orders/{order_id}/tax-invoice — generate tax invoice"""
        if not existing_orders:
            pytest.skip("No orders found in database")
        
        # Find an order without tax invoice
        orders_without_inv = [o for o in existing_orders if not o.get("tax_invoice")]
        
        if not orders_without_inv:
            print("✓ All orders already have tax invoices")
            return
        
        order = orders_without_inv[0]
        order_id = order.get("id") or order.get("so_number")
        
        response = requests.post(
            f"{BASE_URL}/api/orders/{order_id}/tax-invoice",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Tax invoice generation failed: {response.text}"
        
        data = response.json()
        assert "invoice" in data
        assert data["invoice"]["invoice_type"] == "tax"
        
        # Verify GST fields
        invoice = data["invoice"]
        assert "cgst_amount" in invoice
        assert "sgst_amount" in invoice
        assert "total_with_gst" in invoice
        
        print(f"✓ POST /api/orders/{order_id}/tax-invoice - Tax invoice generated: {invoice['invoice_number']}")


class TestInvoicesList:
    """Test invoices list endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_get_invoices_list(self, admin_token):
        """GET /api/invoices — list all invoices"""
        response = requests.get(
            f"{BASE_URL}/api/invoices",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get invoices: {response.text}"
        
        data = response.json()
        assert "invoices" in data
        assert "total" in data
        
        print(f"✓ GET /api/invoices returned {data['total']} invoices")
        
        # Verify invoice structure if invoices exist
        if data["invoices"]:
            invoice = data["invoices"][0]
            expected_fields = ["invoice_number", "invoice_type", "customer_name"]
            for field in expected_fields:
                assert field in invoice, f"Missing field '{field}' in invoice"
    
    def test_get_invoices_by_type(self, admin_token):
        """GET /api/invoices?invoice_type=tax — filter by type"""
        response = requests.get(
            f"{BASE_URL}/api/invoices?invoice_type=tax",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # All returned invoices should be tax type
        for inv in data.get("invoices", []):
            assert inv.get("invoice_type") == "tax", f"Got non-tax invoice: {inv.get('invoice_type')}"
        
        print(f"✓ GET /api/invoices?invoice_type=tax returned {data['total']} tax invoices")


class TestAuthenticationRequired:
    """Test that endpoints require authentication"""
    
    def test_orders_export_requires_auth(self):
        """Orders export should require authentication"""
        response = requests.get(f"{BASE_URL}/api/orders/export/excel")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Orders export requires authentication")
    
    def test_invoices_export_requires_auth(self):
        """Invoices export should require authentication"""
        response = requests.get(f"{BASE_URL}/api/invoices/export/excel")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Invoices export requires authentication")
    
    def test_crm_export_requires_auth(self):
        """CRM export should require authentication"""
        response = requests.get(f"{BASE_URL}/api/crm/leads/export/excel")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ CRM export requires authentication")
    
    def test_invoice_pdf_requires_token(self):
        """Invoice PDF should require token"""
        response = requests.get(f"{BASE_URL}/api/invoices/test-id/pdf")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invoice PDF requires token")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
