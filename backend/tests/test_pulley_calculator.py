"""
Pulley Calculator API Tests
Tests for the new Pulley Calculator feature including:
- GET /api/pulley-standards - Configuration options
- POST /api/calculate-pulley-cost - Cost calculation with various configurations
- GET /api/pulley-thicknesses/{pipe_dia} - Thickness lookup
- GET /api/pulley-kla-model/{shaft_dia_hub} - KLA model lookup
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://inventory-qc-hub-1.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "test123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestPulleyStandards:
    """Tests for GET /api/pulley-standards endpoint"""

    def test_get_pulley_standards_success(self, auth_headers):
        """Test that pulley standards returns all configuration options"""
        response = requests.get(f"{BASE_URL}/api/pulley-standards", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all required fields are present
        assert "pulley_types" in data, "Missing pulley_types"
        assert "pipe_diameters" in data, "Missing pipe_diameters"
        assert "pipe_thickness_map" in data, "Missing pipe_thickness_map"
        assert "shaft_diameters" in data, "Missing shaft_diameters"
        assert "shaft_materials" in data, "Missing shaft_materials"
        assert "end_plate_thicknesses" in data, "Missing end_plate_thicknesses"
        assert "hub_types" in data, "Missing hub_types"
        assert "hub_diameters" in data, "Missing hub_diameters"
        assert "kla_shaft_hub_options" in data, "Missing kla_shaft_hub_options"
        assert "rubber_lagging_types" in data, "Missing rubber_lagging_types"
        assert "rubber_plain_thicknesses" in data, "Missing rubber_plain_thicknesses"
        assert "rubber_ceramic_thicknesses" in data, "Missing rubber_ceramic_thicknesses"
        
        # Verify pulley types
        assert "Drive" in data["pulley_types"], "Drive pulley type missing"
        assert "Tail" in data["pulley_types"], "Tail pulley type missing"
        assert "Bend" in data["pulley_types"], "Bend pulley type missing"
        
        # Verify pipe diameters range (139-1000mm)
        assert 139 in data["pipe_diameters"], "Min pipe diameter 139 missing"
        assert 1000 in data["pipe_diameters"], "Max pipe diameter 1000 missing"
        
        # Verify shaft diameters range (50-300mm)
        assert 50 in data["shaft_diameters"], "Min shaft diameter 50 missing"
        assert 300 in data["shaft_diameters"], "Max shaft diameter 300 missing"
        
        # Verify shaft materials
        assert "MS" in data["shaft_materials"], "MS material missing"
        assert "EN-8" in data["shaft_materials"], "EN-8 material missing"
        assert "EN-9" in data["shaft_materials"], "EN-9 material missing"
        assert "EN-19" in data["shaft_materials"], "EN-19 material missing"
        
        # Verify hub types
        assert "no_hub" in data["hub_types"], "no_hub type missing"
        assert "with_hub" in data["hub_types"], "with_hub type missing"
        assert "kla" in data["hub_types"], "kla type missing"
        
        # Verify rubber types
        assert "none" in data["rubber_lagging_types"], "none rubber type missing"
        assert "plain" in data["rubber_lagging_types"], "plain rubber type missing"
        assert "diamond" in data["rubber_lagging_types"], "diamond rubber type missing"
        assert "ceramic" in data["rubber_lagging_types"], "ceramic rubber type missing"
        
        print(f"✓ Pulley standards returned {len(data['pulley_types'])} pulley types, {len(data['pipe_diameters'])} pipe diameters")

    def test_get_pulley_standards_unauthorized(self):
        """Test that pulley standards requires authentication"""
        response = requests.get(f"{BASE_URL}/api/pulley-standards")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestCalculatePulleyCost:
    """Tests for POST /api/calculate-pulley-cost endpoint"""

    def test_calculate_basic_pulley_cost(self, auth_headers):
        """Test basic pulley cost calculation with minimal config"""
        payload = {
            "pulley_type": "Drive",
            "pipe_diameter": 219,
            "pipe_thickness": 8,
            "face_length": 500,
            "shaft_diameter_centre": 80,
            "shaft_material": "MS",
            "shaft_length": 700,
            "end_plate_thickness": 12,
            "hub_type": "no_hub",
            "rubber_type": "none",
            "quantity": 1,
            "packing_type": "none"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "configuration" in data, "Missing configuration"
        assert "cost_breakdown" in data, "Missing cost_breakdown"
        assert "pricing" in data, "Missing pricing"
        assert "grand_total" in data, "Missing grand_total"
        
        # Verify configuration
        config = data["configuration"]
        assert config["pulley_type"] == "Drive"
        assert config["pipe_diameter_mm"] == 219
        assert config["pipe_thickness_mm"] == 8
        assert config["face_length_mm"] == 500
        assert config["shaft_diameter_centre_mm"] == 80
        assert config["shaft_material"] == "MS"
        assert config["product_code"] is not None
        
        # Verify cost breakdown has required fields
        breakdown = data["cost_breakdown"]
        assert "pipe_cost" in breakdown
        assert "shaft_cost" in breakdown
        assert "end_plate_cost" in breakdown
        assert "total_raw_material" in breakdown
        assert "single_pulley_weight_kg" in breakdown
        
        # Verify pricing
        pricing = data["pricing"]
        assert "unit_price" in pricing
        assert "order_value" in pricing
        assert "final_price" in pricing
        
        # Verify grand_total is positive
        assert data["grand_total"] > 0, "Grand total should be positive"
        
        print(f"✓ Basic pulley cost: Rs. {data['grand_total']:.2f}")

    def test_calculate_pulley_with_hub(self, auth_headers):
        """Test pulley cost with 'with_hub' configuration"""
        payload = {
            "pulley_type": "Tail",
            "pipe_diameter": 323,
            "pipe_thickness": 10,
            "face_length": 600,
            "shaft_diameter_centre": 100,
            "shaft_material": "EN-8",
            "shaft_length": 800,
            "end_plate_thickness": 16,
            "hub_type": "with_hub",
            "hub_diameter": 150,  # Must be >= shaft_dia + 40 = 140
            "hub_length": 80,
            "rubber_type": "none",
            "quantity": 2,
            "packing_type": "standard"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify hub cost is included
        assert data["cost_breakdown"]["hub_cost"] > 0, "Hub cost should be positive for with_hub"
        assert data["configuration"]["hub_type"] == "with_hub"
        assert data["configuration"]["hub_diameter_mm"] == 150
        assert data["configuration"]["hub_length_mm"] == 80
        
        print(f"✓ Pulley with hub cost: Rs. {data['grand_total']:.2f}, Hub cost: Rs. {data['cost_breakdown']['hub_cost']:.2f}")

    def test_calculate_pulley_with_hub_min_diameter_validation(self, auth_headers):
        """Test that hub_diameter must be >= shaft_dia + 40mm"""
        payload = {
            "pulley_type": "Drive",
            "pipe_diameter": 219,
            "pipe_thickness": 8,
            "face_length": 500,
            "shaft_diameter_centre": 100,
            "shaft_material": "MS",
            "shaft_length": 700,
            "end_plate_thickness": 12,
            "hub_type": "with_hub",
            "hub_diameter": 130,  # Invalid: should be >= 100 + 40 = 140
            "hub_length": 80,
            "quantity": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid hub diameter, got {response.status_code}"
        assert "Hub diameter must be" in response.json().get("detail", ""), "Should mention hub diameter constraint"
        
        print("✓ Hub diameter validation working (min = shaft_dia + 40mm)")

    def test_calculate_pulley_with_kla(self, auth_headers):
        """Test pulley cost with KLA hub type"""
        payload = {
            "pulley_type": "Drive",
            "pipe_diameter": 406,
            "pipe_thickness": 12,
            "face_length": 800,
            "shaft_diameter_centre": 120,
            "shaft_material": "EN-9",
            "shaft_length": 1000,
            "end_plate_thickness": 20,
            "hub_type": "kla",
            "shaft_dia_hub": 90,  # KLA-90 model
            "rubber_type": "none",
            "quantity": 1,
            "packing_type": "pallet"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify KLA configuration
        assert data["configuration"]["hub_type"] == "kla"
        assert data["configuration"]["shaft_dia_hub_mm"] == 90
        assert data["configuration"]["kla_model"] is not None, "KLA model should be set"
        assert data["cost_breakdown"]["hub_cost"] > 0, "KLA hub cost should be positive"
        
        print(f"✓ Pulley with KLA: Rs. {data['grand_total']:.2f}, KLA Model: {data['configuration']['kla_model']}")

    def test_calculate_pulley_kla_requires_shaft_dia_hub(self, auth_headers):
        """Test that KLA hub type requires shaft_dia_hub"""
        payload = {
            "pulley_type": "Drive",
            "pipe_diameter": 219,
            "pipe_thickness": 8,
            "face_length": 500,
            "shaft_diameter_centre": 80,
            "shaft_material": "MS",
            "shaft_length": 700,
            "end_plate_thickness": 12,
            "hub_type": "kla",
            # Missing shaft_dia_hub
            "quantity": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400 for missing shaft_dia_hub, got {response.status_code}"
        assert "Shaft Dia @ Hub is required" in response.json().get("detail", "")
        
        print("✓ KLA validation working (requires shaft_dia_hub)")

    def test_calculate_pulley_with_rubber_plain(self, auth_headers):
        """Test pulley cost with plain rubber lagging"""
        payload = {
            "pulley_type": "Drive",
            "pipe_diameter": 273,
            "pipe_thickness": 10,
            "face_length": 600,
            "shaft_diameter_centre": 90,
            "shaft_material": "MS",
            "shaft_length": 750,
            "end_plate_thickness": 14,
            "hub_type": "no_hub",
            "rubber_type": "plain",
            "rubber_thickness": 10,
            "quantity": 1,
            "packing_type": "none"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify rubber cost is included
        assert data["cost_breakdown"]["rubber_cost"] > 0, "Rubber cost should be positive"
        assert data["configuration"]["rubber_type"] == "plain"
        assert data["configuration"]["rubber_thickness_mm"] == 10
        
        print(f"✓ Pulley with plain rubber: Rs. {data['grand_total']:.2f}, Rubber cost: Rs. {data['cost_breakdown']['rubber_cost']:.2f}")

    def test_calculate_pulley_with_rubber_ceramic(self, auth_headers):
        """Test pulley cost with ceramic rubber lagging"""
        payload = {
            "pulley_type": "Drive",
            "pipe_diameter": 355,
            "pipe_thickness": 12,
            "face_length": 700,
            "shaft_diameter_centre": 100,
            "shaft_material": "EN-8",
            "shaft_length": 850,
            "end_plate_thickness": 16,
            "hub_type": "no_hub",
            "rubber_type": "ceramic",
            "rubber_thickness": 15,  # Ceramic thicknesses: 12, 15, 22
            "quantity": 1,
            "packing_type": "none"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify ceramic rubber cost
        assert data["cost_breakdown"]["rubber_cost"] > 0, "Ceramic rubber cost should be positive"
        assert data["configuration"]["rubber_type"] == "ceramic"
        assert data["configuration"]["rubber_thickness_mm"] == 15
        
        print(f"✓ Pulley with ceramic rubber: Rs. {data['grand_total']:.2f}, Rubber cost: Rs. {data['cost_breakdown']['rubber_cost']:.2f}")

    def test_calculate_pulley_ceramic_invalid_thickness(self, auth_headers):
        """Test that ceramic rubber validates thickness (only 12, 15, 22 allowed)"""
        payload = {
            "pulley_type": "Drive",
            "pipe_diameter": 219,
            "pipe_thickness": 8,
            "face_length": 500,
            "shaft_diameter_centre": 80,
            "shaft_material": "MS",
            "shaft_length": 700,
            "end_plate_thickness": 12,
            "hub_type": "no_hub",
            "rubber_type": "ceramic",
            "rubber_thickness": 10,  # Invalid for ceramic (only 12, 15, 22)
            "quantity": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid ceramic thickness, got {response.status_code}"
        assert "ceramic" in response.json().get("detail", "").lower()
        
        print("✓ Ceramic rubber thickness validation working")

    def test_calculate_pulley_invalid_pipe_diameter(self, auth_headers):
        """Test validation for invalid pipe diameter"""
        payload = {
            "pulley_type": "Drive",
            "pipe_diameter": 999,  # Invalid
            "pipe_thickness": 8,
            "face_length": 500,
            "shaft_diameter_centre": 80,
            "shaft_material": "MS",
            "shaft_length": 700,
            "end_plate_thickness": 12,
            "hub_type": "no_hub",
            "quantity": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid pipe diameter, got {response.status_code}"
        
        print("✓ Invalid pipe diameter validation working")

    def test_calculate_pulley_invalid_thickness_for_diameter(self, auth_headers):
        """Test validation for thickness not available for pipe diameter"""
        payload = {
            "pulley_type": "Drive",
            "pipe_diameter": 139,  # Only has 4.8, 5.4 thicknesses
            "pipe_thickness": 10,  # Invalid for 139mm pipe
            "face_length": 500,
            "shaft_diameter_centre": 80,
            "shaft_material": "MS",
            "shaft_length": 700,
            "end_plate_thickness": 12,
            "hub_type": "no_hub",
            "quantity": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid thickness, got {response.status_code}"
        assert "thickness" in response.json().get("detail", "").lower()
        
        print("✓ Pipe thickness validation for diameter working")

    def test_calculate_pulley_with_quantity_and_packing(self, auth_headers):
        """Test pulley cost with quantity and packing charges"""
        payload = {
            "pulley_type": "Snub",
            "pipe_diameter": 245,
            "pipe_thickness": 8,
            "face_length": 450,
            "shaft_diameter_centre": 70,
            "shaft_material": "MS",
            "shaft_length": 600,
            "end_plate_thickness": 10,
            "hub_type": "no_hub",
            "rubber_type": "none",
            "quantity": 10,
            "packing_type": "wooden_box"  # 8% packing
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify quantity and packing
        assert data["configuration"]["quantity"] == 10
        assert data["pricing"]["quantity"] == 10
        assert data["pricing"]["packing_type"] == "wooden_box"
        assert data["pricing"]["packing_percent"] == 8
        assert data["pricing"]["packing_charges"] > 0
        
        # Verify order value = unit_price * quantity (allow small floating point tolerance)
        expected_order_value = data["pricing"]["unit_price"] * 10
        assert abs(data["pricing"]["order_value"] - expected_order_value) < 0.1  # Allow 0.1 tolerance for floating point
        
        print(f"✓ Pulley with qty=10, wooden_box packing: Rs. {data['grand_total']:.2f}")


class TestPulleyThicknesses:
    """Tests for GET /api/pulley-thicknesses/{pipe_dia} endpoint"""

    def test_get_thicknesses_for_valid_diameter(self, auth_headers):
        """Test getting thicknesses for a valid pipe diameter"""
        response = requests.get(
            f"{BASE_URL}/api/pulley-thicknesses/219",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["pipe_diameter"] == 219
        assert "thicknesses" in data
        assert len(data["thicknesses"]) > 0
        
        # 219mm should have 6.3, 8, 10, 12
        expected = [6.3, 8, 10, 12]
        for t in expected:
            assert t in data["thicknesses"], f"Thickness {t} missing for 219mm pipe"
        
        print(f"✓ Thicknesses for 219mm: {data['thicknesses']}")

    def test_get_thicknesses_for_small_diameter(self, auth_headers):
        """Test getting thicknesses for small pipe diameter (139mm)"""
        response = requests.get(
            f"{BASE_URL}/api/pulley-thicknesses/139",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 139mm should only have 4.8, 5.4
        assert 4.8 in data["thicknesses"]
        assert 5.4 in data["thicknesses"]
        assert len(data["thicknesses"]) == 2
        
        print(f"✓ Thicknesses for 139mm: {data['thicknesses']}")

    def test_get_thicknesses_for_large_diameter(self, auth_headers):
        """Test getting thicknesses for large pipe diameter (1000mm)"""
        response = requests.get(
            f"{BASE_URL}/api/pulley-thicknesses/1000",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 1000mm should have 20, 22, 24, 26
        expected = [20, 22, 24, 26]
        for t in expected:
            assert t in data["thicknesses"], f"Thickness {t} missing for 1000mm pipe"
        
        print(f"✓ Thicknesses for 1000mm: {data['thicknesses']}")

    def test_get_thicknesses_for_invalid_diameter(self, auth_headers):
        """Test getting thicknesses for invalid pipe diameter"""
        response = requests.get(
            f"{BASE_URL}/api/pulley-thicknesses/999",
            headers=auth_headers
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid diameter, got {response.status_code}"
        
        print("✓ Invalid diameter returns 404")


class TestPulleyKlaModel:
    """Tests for GET /api/pulley-kla-model/{shaft_dia_hub} endpoint"""

    def test_get_kla_model_valid(self, auth_headers):
        """Test getting KLA model for valid shaft diameter"""
        response = requests.get(
            f"{BASE_URL}/api/pulley-kla-model/90",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "model" in data
        assert "price" in data
        assert "min_shaft" in data
        assert "max_shaft" in data
        
        # 90mm should be KLA-70 (range 71-90)
        assert data["model"] == "KLA-70"
        assert data["price"] > 0
        
        print(f"✓ KLA model for 90mm: {data['model']}, Price: Rs. {data['price']}")

    def test_get_kla_model_small_shaft(self, auth_headers):
        """Test getting KLA model for small shaft diameter"""
        response = requests.get(
            f"{BASE_URL}/api/pulley-kla-model/30",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 30mm should be KLA-25 (range 25-35)
        assert data["model"] == "KLA-25"
        
        print(f"✓ KLA model for 30mm: {data['model']}")

    def test_get_kla_model_large_shaft(self, auth_headers):
        """Test getting KLA model for large shaft diameter"""
        response = requests.get(
            f"{BASE_URL}/api/pulley-kla-model/280",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 280mm should be KLA-260 (range 261-290)
        assert data["model"] == "KLA-260"
        
        print(f"✓ KLA model for 280mm: {data['model']}")

    def test_get_kla_model_invalid_shaft(self, auth_headers):
        """Test getting KLA model for invalid shaft diameter (out of range)"""
        response = requests.get(
            f"{BASE_URL}/api/pulley-kla-model/10",  # Too small
            headers=auth_headers
        )
        
        assert response.status_code == 404, f"Expected 404 for out-of-range shaft, got {response.status_code}"
        
        print("✓ Invalid shaft diameter returns 404")

    def test_get_kla_model_boundary_values(self, auth_headers):
        """Test KLA model at boundary values"""
        # Test at exact boundary (35 is max for KLA-25)
        response = requests.get(
            f"{BASE_URL}/api/pulley-kla-model/35",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["model"] == "KLA-25"
        
        # Test at next boundary (36 is min for KLA-35)
        response = requests.get(
            f"{BASE_URL}/api/pulley-kla-model/36",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["model"] == "KLA-35"
        
        print("✓ KLA model boundary values working correctly")


class TestPulleyGSTCalculation:
    """Tests for GST calculation in pulley cost"""

    def test_gst_included_in_response(self, auth_headers):
        """Test that GST is calculated and included in response"""
        payload = {
            "pulley_type": "Drive",
            "pipe_diameter": 219,
            "pipe_thickness": 8,
            "face_length": 500,
            "shaft_diameter_centre": 80,
            "shaft_material": "MS",
            "shaft_length": 700,
            "end_plate_thickness": 12,
            "hub_type": "no_hub",
            "quantity": 1,
            "packing_type": "none"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate-pulley-cost",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify GST structure
        assert "gst" in data
        gst = data["gst"]
        assert "taxable_amount" in gst
        assert "cgst_rate" in gst
        assert "cgst_amount" in gst
        assert "sgst_rate" in gst
        assert "sgst_amount" in gst
        assert "total_gst" in gst
        
        # Verify GST calculation (18% = 9% CGST + 9% SGST)
        assert gst["cgst_rate"] == 9
        assert gst["sgst_rate"] == 9
        
        # Verify total GST = CGST + SGST
        expected_total_gst = gst["cgst_amount"] + gst["sgst_amount"]
        assert abs(gst["total_gst"] - expected_total_gst) < 0.01
        
        # Verify grand_total = final_price + total_gst
        expected_grand_total = data["pricing"]["final_price"] + gst["total_gst"]
        assert abs(data["grand_total"] - expected_grand_total) < 0.01
        
        print(f"✓ GST calculation: Taxable={gst['taxable_amount']:.2f}, GST={gst['total_gst']:.2f}, Grand Total={data['grand_total']:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
