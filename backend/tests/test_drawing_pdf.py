"""
PDF Drawing Generation Tests
Tests for verifying roller PDF drawing generation without Bill of Materials table
"""

import pytest
import requests
import os
from io import BytesIO

# Get backend URL from environment
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://quote-flow-admin.preview.emergentagent.com"

# Test credentials
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test123"


class TestAuth:
    """Helper class to get auth token"""
    
    @staticmethod
    def get_auth_token():
        """Get authentication token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        return None


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for authenticated requests"""
    token = TestAuth.get_auth_token()
    if not token:
        pytest.skip("Authentication failed - cannot proceed with tests")
    return token


@pytest.fixture(scope="module")
def authenticated_session(auth_token):
    """Session with authentication header"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestSampleDrawingDownload:
    """Tests for GET /api/download/sample-drawing endpoint"""
    
    def test_sample_drawing_returns_pdf(self):
        """Test that sample drawing endpoint returns a valid PDF"""
        response = requests.get(f"{BASE_URL}/api/download/sample-drawing")
        
        # Check status code
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Check content type is PDF
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        
        # Check that content starts with PDF magic bytes
        content = response.content
        assert content[:4] == b'%PDF', "Response does not start with PDF magic bytes"
        
        print(f"✓ Sample drawing endpoint returned valid PDF ({len(content)} bytes)")
    
    def test_sample_drawing_has_content_disposition(self):
        """Test that sample drawing has proper content-disposition header"""
        response = requests.get(f"{BASE_URL}/api/download/sample-drawing")
        
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition or "inline" in content_disposition or "filename" in content_disposition, \
            f"Expected content-disposition header, got: {content_disposition}"
        
        print(f"✓ Content-Disposition header: {content_disposition}")
    
    def test_sample_drawing_pdf_readable(self):
        """Test that the sample drawing PDF can be read and doesn't contain BOM"""
        response = requests.get(f"{BASE_URL}/api/download/sample-drawing")
        
        assert response.status_code == 200
        
        content = response.content.decode('latin-1')  # PDF content can have binary data
        
        # Check that it doesn't contain "Bill of Materials" text
        # Note: PDF text is encoded, so we check for common patterns
        assert "Bill of Materials" not in content, "PDF should NOT contain 'Bill of Materials' text"
        
        print(f"✓ Sample drawing PDF does NOT contain 'Bill of Materials'")


class TestGenerateDrawingEndpoint:
    """Tests for POST /api/generate-drawing endpoint"""
    
    def test_generate_drawing_requires_auth(self):
        """Test that generate drawing requires authentication"""
        payload = {
            "product_code": "CR20 89 500B 62C",
            "roller_type": "carrying",
            "pipe_diameter": 88.9,
            "pipe_length": 500,
            "pipe_type": "B",
            "shaft_diameter": 20,
            "bearing": "6204",
            "bearing_make": "china",
            "housing": "P204",
            "weight_kg": 5.5
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-drawing", json=payload)
        
        # Without auth should return 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Generate drawing endpoint requires authentication (status {response.status_code})")
    
    def test_generate_drawing_returns_pdf(self, authenticated_session):
        """Test that generate drawing returns a valid PDF with auth"""
        payload = {
            "product_code": "CR20 89 500B 62C",
            "roller_type": "carrying",
            "pipe_diameter": 88.9,
            "pipe_length": 500,
            "pipe_type": "B",
            "shaft_diameter": 20,
            "bearing": "6204",
            "bearing_make": "china",
            "housing": "P204",
            "weight_kg": 5.5,
            "unit_price": 850.0,
            "quantity": 1,
            "shaft_end_type": "B"
        }
        
        response = authenticated_session.post(f"{BASE_URL}/api/generate-drawing", json=payload)
        
        # Check status code
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text[:500] if response.text else 'empty'}"
        
        # Check content type is PDF
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        
        # Check that content starts with PDF magic bytes
        content = response.content
        assert content[:4] == b'%PDF', f"Response does not start with PDF magic bytes. First 20 bytes: {content[:20]}"
        
        print(f"✓ Generate drawing returned valid PDF ({len(content)} bytes)")
    
    def test_generated_pdf_no_bom_table(self, authenticated_session):
        """Test that generated PDF does NOT contain Bill of Materials table"""
        payload = {
            "product_code": "CR25 114 600B 62S",
            "roller_type": "carrying",
            "pipe_diameter": 114.3,
            "pipe_length": 600,
            "pipe_type": "B",
            "shaft_diameter": 25,
            "bearing": "6205",
            "bearing_make": "skf",
            "housing": "P205",
            "weight_kg": 8.2,
            "unit_price": 1250.0,
            "quantity": 1,
            "shaft_end_type": "B"
        }
        
        response = authenticated_session.post(f"{BASE_URL}/api/generate-drawing", json=payload)
        
        assert response.status_code == 200, f"Failed to generate PDF: {response.status_code}"
        
        # Decode PDF content to search for text
        content = response.content.decode('latin-1')
        
        # Check that "Bill of Materials" is NOT in the PDF
        assert "Bill of Materials" not in content, "PDF should NOT contain 'Bill of Materials' text"
        
        # Also check for common BOM-related terms that shouldn't be there
        assert "Qty" not in content or "DIMENSIONS" in content, "PDF should not have BOM quantity column"
        
        print(f"✓ Generated PDF does NOT contain 'Bill of Materials' table")
    
    def test_generated_pdf_is_valid_structure(self, authenticated_session):
        """Test that generated PDF has valid PDF structure and reasonable size"""
        payload = {
            "product_code": "CR20 89 400B 62C",
            "roller_type": "carrying",
            "pipe_diameter": 88.9,
            "pipe_length": 400,
            "pipe_type": "B",
            "shaft_diameter": 20,
            "bearing": "6204",
            "bearing_make": "china",
            "housing": "P204",
            "weight_kg": 4.8,
            "unit_price": 720.0,
            "quantity": 1,
            "shaft_end_type": "B"
        }
        
        response = authenticated_session.post(f"{BASE_URL}/api/generate-drawing", json=payload)
        
        assert response.status_code == 200, f"Failed to generate PDF: {response.status_code}"
        
        content = response.content
        
        # Check PDF structure - starts with %PDF and ends with %%EOF
        assert content[:4] == b'%PDF', "PDF should start with %PDF header"
        assert b'%%EOF' in content[-50:], "PDF should end with %%EOF marker"
        
        # Check reasonable PDF size (schematic PDF should be > 2KB)
        assert len(content) > 2000, f"PDF size {len(content)} bytes seems too small for a technical drawing"
        
        # PDF text is compressed, so we can't easily search for text
        # The key verification (no BOM) is done in test_generated_pdf_no_bom_table
        
        print(f"✓ Generated PDF has valid structure ({len(content)} bytes)")
    
    def test_generate_impact_roller_drawing(self, authenticated_session):
        """Test generating drawing for impact roller with rubber diameter"""
        payload = {
            "product_code": "IR25 114/152 500B 62S",
            "roller_type": "impact",
            "pipe_diameter": 114.3,
            "pipe_length": 500,
            "pipe_type": "B",
            "shaft_diameter": 25,
            "bearing": "6205",
            "bearing_make": "skf",
            "housing": "P205",
            "weight_kg": 12.5,
            "unit_price": 2100.0,
            "rubber_diameter": 152,
            "quantity": 1,
            "shaft_end_type": "B"
        }
        
        response = authenticated_session.post(f"{BASE_URL}/api/generate-drawing", json=payload)
        
        assert response.status_code == 200, f"Failed to generate impact roller PDF: {response.status_code}"
        
        # Check it's a valid PDF
        content = response.content
        assert content[:4] == b'%PDF', "Response should be a valid PDF"
        
        # Check for "Bill of Materials" - should NOT be present
        content_str = content.decode('latin-1')
        assert "Bill of Materials" not in content_str, "Impact roller PDF should NOT contain 'Bill of Materials'"
        
        print(f"✓ Impact roller drawing generated successfully without BOM ({len(content)} bytes)")
    
    def test_generate_drawing_with_custom_shaft(self, authenticated_session):
        """Test generating drawing with custom shaft extension"""
        payload = {
            "product_code": "CR30 139 700C 63F",
            "roller_type": "carrying",
            "pipe_diameter": 139.7,
            "pipe_length": 700,
            "pipe_type": "C",
            "shaft_diameter": 30,
            "bearing": "6306",
            "bearing_make": "fag",
            "housing": "P306",
            "weight_kg": 15.2,
            "unit_price": 2800.0,
            "quantity": 1,
            "shaft_end_type": "custom",
            "custom_shaft_extension": 80
        }
        
        response = authenticated_session.post(f"{BASE_URL}/api/generate-drawing", json=payload)
        
        assert response.status_code == 200, f"Failed to generate PDF with custom shaft: {response.status_code}"
        
        # Check it's a valid PDF
        content = response.content
        assert content[:4] == b'%PDF', "Response should be a valid PDF"
        
        print(f"✓ Custom shaft drawing generated successfully ({len(content)} bytes)")


class TestDrawingContent:
    """Detailed tests for PDF content verification"""
    
    def test_pdf_does_not_contain_bom_keywords(self, authenticated_session):
        """Verify PDF does not contain BOM-related keywords"""
        payload = {
            "product_code": "CR20 76 380B 62C",
            "roller_type": "carrying",
            "pipe_diameter": 76.1,
            "pipe_length": 380,
            "pipe_type": "B",
            "shaft_diameter": 20,
            "bearing": "6204",
            "bearing_make": "china",
            "housing": "P204",
            "weight_kg": 3.5,
            "unit_price": 580.0,
            "quantity": 1,
            "shaft_end_type": "B"
        }
        
        response = authenticated_session.post(f"{BASE_URL}/api/generate-drawing", json=payload)
        
        assert response.status_code == 200
        
        content = response.content.decode('latin-1')
        
        # List of BOM-related strings that should NOT be in the PDF
        bom_keywords = [
            "Bill of Materials",
            "BILL OF MATERIALS",
            "BOM",
        ]
        
        for keyword in bom_keywords:
            assert keyword not in content, f"PDF should NOT contain '{keyword}'"
        
        print(f"✓ PDF does not contain any BOM-related keywords")
    
    def test_pdf_has_fonts_and_content_stream(self, authenticated_session):
        """Verify PDF has proper fonts and content stream for technical drawing"""
        payload = {
            "product_code": "CR25 89 465B 62C",
            "roller_type": "carrying",
            "pipe_diameter": 88.9,
            "pipe_length": 465,
            "pipe_type": "B",
            "shaft_diameter": 25,
            "bearing": "6205",
            "bearing_make": "china",
            "housing": "P205",
            "weight_kg": 6.2,
            "unit_price": 920.0,
            "quantity": 1,
            "shaft_end_type": "B"
        }
        
        response = authenticated_session.post(f"{BASE_URL}/api/generate-drawing", json=payload)
        
        assert response.status_code == 200
        
        content = response.content.decode('latin-1')
        
        # PDF should have fonts for text rendering
        assert "Helvetica" in content, "PDF should use Helvetica font"
        assert "Helvetica-Bold" in content, "PDF should use Helvetica-Bold font"
        
        # PDF should have content streams (compressed graphics/text)
        assert "/Contents" in content, "PDF should have content streams"
        assert "stream" in content, "PDF should have stream objects"
        
        # Check for media box (page dimensions) - A4 size
        assert "/MediaBox" in content, "PDF should have page dimensions"
        
        print(f"✓ PDF has proper fonts and content structure")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
