#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for IS-Standards Belt Conveyor Roller Configuration and Costing
Tests all new endpoints for IS-9295 and IS-8598 standards compliance
"""

import requests
import json
import sys
from typing import Dict, Any

# Backend URL - using the configured URL from frontend
BACKEND_URL = "https://cost-calculator-77.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"

# Global variables to store test data
auth_token = None
test_results = {
    "login": False,
    "roller_standards": False,
    "compatible_bearings_20": False,
    "compatible_bearings_25": False,
    "compatible_bearings_30": False,
    "compatible_housing_76_6204": False,
    "compatible_housing_889_6205": False,
    "compatible_housing_1143_6206": False,
    "detailed_cost_carrying": False,
    "detailed_cost_impact": False,
    "detailed_cost_return": False,
    "invalid_pipe_diameter": False,
    "invalid_shaft_diameter": False,
    "invalid_bearing_combination": False,
    "cost_calculation_accuracy": False
}

def print_test_result(test_name: str, passed: bool, message: str = ""):
    """Print formatted test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{test_name}: {status}")
    if message:
        print(f"   {message}")
    print()

def make_request(method: str, endpoint: str, data: dict = None, headers: dict = None) -> Dict[Any, Any]:
    """Make HTTP request with error handling"""
    url = f"{BACKEND_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        return {
            "success": True,
            "status_code": response.status_code,
            "data": response.json() if response.content else {},
            "response": response
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "status_code": None,
            "data": {}
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"JSON decode error: {str(e)}",
            "status_code": response.status_code if 'response' in locals() else None,
            "data": {}
        }

def test_login():
    """Test 1: Admin login functionality"""
    global auth_token
    
    print("🔐 Testing Admin Login...")
    
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    result = make_request("POST", "/auth/login", login_data)
    
    if not result["success"]:
        print_test_result("Login Test", False, f"Request failed: {result['error']}")
        return False
    
    if result["status_code"] == 200:
        data = result["data"]
        if "access_token" in data and "user" in data:
            auth_token = data["access_token"]
            user = data["user"]
            print_test_result("Login Test", True, 
                f"Successfully logged in as {user.get('name', 'N/A')} ({user.get('email', 'N/A')}) with role {user.get('role', 'N/A')}")
            test_results["login"] = True
            return True
        else:
            print_test_result("Login Test", False, "Login response missing required fields")
            return False
    else:
        print_test_result("Login Test", False, f"Login failed with status {result['status_code']}: {result.get('data', {})}")
        return False

def get_auth_headers():
    """Get authorization headers for authenticated requests"""
    return {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

def test_roller_standards():
    """Test 2: Get roller standards endpoint"""
    print("📏 Testing Roller Standards Endpoint...")
    
    result = make_request("GET", "/roller-standards", headers=get_auth_headers())
    
    if not result["success"]:
        print_test_result("Roller Standards Test", False, f"Request failed: {result['error']}")
        return False
    
    if result["status_code"] == 200:
        data = result["data"]
        required_fields = ["pipe_diameters", "shaft_diameters", "bearing_options", "roller_lengths_by_belt_width"]
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            print_test_result("Roller Standards Test", False, f"Missing fields: {missing_fields}")
            return False
        
        # Validate specific IS standard data
        pipe_diameters = data["pipe_diameters"]
        shaft_diameters = data["shaft_diameters"]
        bearing_options = data["bearing_options"]
        roller_lengths = data["roller_lengths_by_belt_width"]
        
        # Check IS-9295 pipe diameters
        expected_pipe_diameters = [63.5, 76.1, 88.9, 101.6, 108.0, 114.3, 127.0, 139.7, 152.4, 159.0, 165.0, 219.1]
        if set(pipe_diameters) != set(expected_pipe_diameters):
            print_test_result("Roller Standards Test", False, "IS-9295 pipe diameters don't match expected values")
            return False
        
        # Check shaft diameters
        expected_shaft_diameters = [20, 25, 30, 35, 40, 45, 50]
        if set(shaft_diameters) != set(expected_shaft_diameters):
            print_test_result("Roller Standards Test", False, "Shaft diameters don't match expected values")
            return False
        
        # Check bearing options mapping
        if "20" not in bearing_options or "25" not in bearing_options or "30" not in bearing_options:
            print_test_result("Roller Standards Test", False, "Missing bearing options for key shaft diameters")
            return False
        
        # Check IS-8598 roller lengths
        if "1000" not in roller_lengths or "1200" not in roller_lengths or "1600" not in roller_lengths:
            print_test_result("Roller Standards Test", False, "Missing IS-8598 roller lengths for standard belt widths")
            return False
        
        print_test_result("Roller Standards Test", True, 
            f"Retrieved IS standards: {len(pipe_diameters)} pipe diameters, {len(shaft_diameters)} shaft diameters, roller lengths for {len(roller_lengths)} belt widths")
        test_results["roller_standards"] = True
        return True
    
    else:
        print_test_result("Roller Standards Test", False, f"Failed with status {result['status_code']}")
        return False

def test_compatible_bearings():
    """Test 3: Get compatible bearings for shaft diameters"""
    print("🔩 Testing Compatible Bearings Endpoints...")
    
    test_cases = [
        (20, ["6204", "6304"], "compatible_bearings_20"),
        (25, ["6205", "6305"], "compatible_bearings_25"), 
        (30, ["6206", "6306"], "compatible_bearings_30")
    ]
    
    all_passed = True
    
    for shaft_dia, expected_bearings, test_key in test_cases:
        result = make_request("GET", f"/compatible-bearings/{shaft_dia}", headers=get_auth_headers())
        
        if not result["success"]:
            print_test_result(f"Bearings for {shaft_dia}mm shaft", False, f"Request failed: {result['error']}")
            all_passed = False
            continue
        
        if result["status_code"] == 200:
            data = result["data"]
            if "shaft_diameter" in data and "bearings" in data:
                actual_bearings = data["bearings"]
                if set(actual_bearings) == set(expected_bearings):
                    print_test_result(f"Bearings for {shaft_dia}mm shaft", True, 
                        f"Returned correct bearings: {actual_bearings}")
                    test_results[test_key] = True
                else:
                    print_test_result(f"Bearings for {shaft_dia}mm shaft", False, 
                        f"Expected {expected_bearings}, got {actual_bearings}")
                    all_passed = False
            else:
                print_test_result(f"Bearings for {shaft_dia}mm shaft", False, "Missing required fields in response")
                all_passed = False
        else:
            print_test_result(f"Bearings for {shaft_dia}mm shaft", False, f"Failed with status {result['status_code']}")
            all_passed = False
    
    return all_passed

def test_compatible_housing():
    """Test 4: Get compatible housing for pipe and bearing combinations"""
    print("🏠 Testing Compatible Housing Endpoints...")
    
    test_cases = [
        (76.1, "6204", "72/47", "compatible_housing_76_6204"),
        (88.9, "6205", "84/52", "compatible_housing_889_6205"),
        (114.3, "6206", "108/62", "compatible_housing_1143_6206")
    ]
    
    all_passed = True
    
    for pipe_dia, bearing, expected_housing, test_key in test_cases:
        result = make_request("GET", f"/compatible-housing/{pipe_dia}/{bearing}", headers=get_auth_headers())
        
        if not result["success"]:
            print_test_result(f"Housing for pipe {pipe_dia}mm + bearing {bearing}", False, f"Request failed: {result['error']}")
            all_passed = False
            continue
        
        if result["status_code"] == 200:
            data = result["data"]
            if "housing" in data:
                actual_housing = data["housing"]
                if actual_housing == expected_housing:
                    print_test_result(f"Housing for pipe {pipe_dia}mm + bearing {bearing}", True,
                        f"Returned correct housing: {actual_housing}")
                    test_results[test_key] = True
                else:
                    print_test_result(f"Housing for pipe {pipe_dia}mm + bearing {bearing}", False,
                        f"Expected {expected_housing}, got {actual_housing}")
                    all_passed = False
            else:
                print_test_result(f"Housing for pipe {pipe_dia}mm + bearing {bearing}", False, "Missing housing in response")
                all_passed = False
        else:
            print_test_result(f"Housing for pipe {pipe_dia}mm + bearing {bearing}", False, f"Failed with status {result['status_code']}")
            all_passed = False
    
    return all_passed

def test_detailed_cost_calculations():
    """Test 5: Calculate detailed cost for different roller configurations"""
    print("💰 Testing Detailed Cost Calculations...")
    
    test_configurations = [
        {
            "name": "Standard Carrying Roller",
            "data": {
                "pipe_diameter": 88.9,
                "pipe_length": 1190,  # IS-8598 for 1000mm belt width
                "shaft_diameter": 20,
                "bearing_number": "6204",
                "belt_width": 1000
            },
            "test_key": "detailed_cost_carrying"
        },
        {
            "name": "Heavy Duty Impact Roller", 
            "data": {
                "pipe_diameter": 114.3,
                "pipe_length": 1390,  # IS-8598 for 1200mm belt width
                "shaft_diameter": 25,
                "bearing_number": "6305", 
                "belt_width": 1200
            },
            "test_key": "detailed_cost_impact"
        },
        {
            "name": "Large Return Roller",
            "data": {
                "pipe_diameter": 127.0,
                "pipe_length": 1790,  # IS-8598 for 1600mm belt width
                "shaft_diameter": 30,
                "bearing_number": "6306",
                "belt_width": 1600
            },
            "test_key": "detailed_cost_return"
        }
    ]
    
    all_passed = True
    
    for config in test_configurations:
        print(f"  Testing {config['name']}...")
        
        result = make_request("POST", "/calculate-detailed-cost", config["data"], headers=get_auth_headers())
        
        if not result["success"]:
            print_test_result(f"Cost calculation - {config['name']}", False, f"Request failed: {result['error']}")
            all_passed = False
            continue
        
        if result["status_code"] == 200:
            data = result["data"]
            required_sections = ["configuration", "cost_breakdown", "pricing"]
            
            missing_sections = [section for section in required_sections if section not in data]
            if missing_sections:
                print_test_result(f"Cost calculation - {config['name']}", False, f"Missing sections: {missing_sections}")
                all_passed = False
                continue
            
            # Validate configuration section
            configuration = data["configuration"]
            config_data = config["data"]
            
            expected_shaft_length = config_data["pipe_length"] + 70
            if configuration.get("shaft_length_mm") != expected_shaft_length:
                print_test_result(f"Cost calculation - {config['name']}", False, 
                    f"Incorrect shaft length calculation: expected {expected_shaft_length}, got {configuration.get('shaft_length_mm')}")
                all_passed = False
                continue
            
            # Validate cost breakdown
            cost_breakdown = data["cost_breakdown"]
            required_costs = ["pipe_cost", "shaft_cost", "bearing_cost", "housing_cost", "seal_cost", "total_raw_material"]
            missing_costs = [cost for cost in required_costs if cost not in cost_breakdown]
            if missing_costs:
                print_test_result(f"Cost calculation - {config['name']}", False, f"Missing cost components: {missing_costs}")
                all_passed = False
                continue
            
            # Validate pricing section
            pricing = data["pricing"]
            required_pricing = ["raw_material_cost", "layout_cost", "profit", "final_price"]
            missing_pricing = [price for price in required_pricing if price not in pricing]
            if missing_pricing:
                print_test_result(f"Cost calculation - {config['name']}", False, f"Missing pricing components: {missing_pricing}")
                all_passed = False
                continue
            
            # Validate pricing formula: final_price = raw_material_cost × 2.112
            raw_material = pricing["raw_material_cost"]
            final_price = pricing["final_price"]
            expected_final = round(raw_material * 2.112, 2)
            
            if abs(final_price - expected_final) > 0.01:  # Allow small rounding differences
                print_test_result(f"Cost calculation - {config['name']}", False,
                    f"Pricing formula incorrect: expected {expected_final}, got {final_price}")
                all_passed = False
                continue
            
            print_test_result(f"Cost calculation - {config['name']}", True,
                f"Raw material: ₹{raw_material}, Final price: ₹{final_price} (verified 2.112x formula)")
            test_results[config["test_key"]] = True
            
        else:
            print_test_result(f"Cost calculation - {config['name']}", False, f"Failed with status {result['status_code']}")
            all_passed = False
    
    return all_passed

def test_invalid_configurations():
    """Test 6: Validate error handling for invalid configurations"""
    print("🚫 Testing Invalid Configuration Handling...")
    
    test_cases = [
        {
            "name": "Invalid pipe diameter (100.0 - not in IS-9295)",
            "data": {
                "pipe_diameter": 100.0,  # Not in IS-9295 standards
                "pipe_length": 1190,
                "shaft_diameter": 20,
                "bearing_number": "6204"
            },
            "test_key": "invalid_pipe_diameter"
        },
        {
            "name": "Invalid shaft diameter (22 - not standard)",
            "data": {
                "pipe_diameter": 88.9,
                "pipe_length": 1190,
                "shaft_diameter": 22,  # Not standard
                "bearing_number": "6204"
            },
            "test_key": "invalid_shaft_diameter"
        },
        {
            "name": "Incompatible bearing for shaft (6205 for 20mm shaft)",
            "data": {
                "pipe_diameter": 88.9,
                "pipe_length": 1190,
                "shaft_diameter": 20,
                "bearing_number": "6205"  # 6205 is for 25mm shaft, not 20mm
            },
            "test_key": "invalid_bearing_combination"
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        result = make_request("POST", "/calculate-detailed-cost", test_case["data"], headers=get_auth_headers())
        
        if not result["success"]:
            # Network errors are not expected - this should be a handled 400 error
            print_test_result(f"Invalid config - {test_case['name']}", False, f"Network error: {result['error']}")
            all_passed = False
            continue
        
        if result["status_code"] == 400:
            # Expected behavior - should return 400 with error message
            error_data = result["data"]
            if "detail" in error_data:
                print_test_result(f"Invalid config - {test_case['name']}", True, 
                    f"Correctly rejected with error: {error_data['detail']}")
                test_results[test_case["test_key"]] = True
            else:
                print_test_result(f"Invalid config - {test_case['name']}", False, "400 status but missing error detail")
                all_passed = False
        else:
            print_test_result(f"Invalid config - {test_case['name']}", False, 
                f"Expected 400 error, got {result['status_code']}")
            all_passed = False
    
    return all_passed

def test_cost_calculation_accuracy():
    """Test 7: Manual verification of cost calculation accuracy"""
    print("🔍 Testing Cost Calculation Accuracy (Manual Verification)...")
    
    # Use the Standard Carrying Roller configuration for detailed verification
    test_config = {
        "pipe_diameter": 88.9,
        "pipe_length": 1190,
        "shaft_diameter": 20,
        "bearing_number": "6204",
        "belt_width": 1000
    }
    
    result = make_request("POST", "/calculate-detailed-cost", test_config, headers=get_auth_headers())
    
    if not result["success"]:
        print_test_result("Cost Calculation Accuracy", False, f"Request failed: {result['error']}")
        return False
    
    if result["status_code"] != 200:
        print_test_result("Cost Calculation Accuracy", False, f"Failed with status {result['status_code']}")
        return False
    
    data = result["data"]
    configuration = data["configuration"]
    cost_breakdown = data["cost_breakdown"]
    pricing = data["pricing"]
    
    # Verify shaft length calculation
    expected_shaft_length = test_config["pipe_length"] + 70  # 1190 + 70 = 1260
    actual_shaft_length = configuration["shaft_length_mm"]
    if actual_shaft_length != expected_shaft_length:
        print_test_result("Cost Calculation Accuracy", False, 
            f"Shaft length incorrect: expected {expected_shaft_length}, got {actual_shaft_length}")
        return False
    
    # Verify housing selection
    expected_housing = "84/47"  # For pipe 88.9mm and bearing 6204 (OD 47mm)
    actual_housing = configuration["housing"]
    if actual_housing != expected_housing:
        print_test_result("Cost Calculation Accuracy", False,
            f"Housing incorrect: expected {expected_housing}, got {actual_housing}")
        return False
    
    # Verify cost components are present and positive
    cost_components = ["pipe_cost", "shaft_cost", "bearing_cost", "housing_cost", "seal_cost"]
    for component in cost_components:
        if cost_breakdown[component] <= 0:
            print_test_result("Cost Calculation Accuracy", False, f"{component} should be positive, got {cost_breakdown[component]}")
            return False
    
    # Verify total raw material is sum of components
    expected_total = sum(cost_breakdown[comp] for comp in cost_components)
    actual_total = cost_breakdown["total_raw_material"]
    if abs(expected_total - actual_total) > 0.01:
        print_test_result("Cost Calculation Accuracy", False,
            f"Total raw material calculation incorrect: expected {expected_total}, got {actual_total}")
        return False
    
    # Verify layout cost = raw material × 0.32
    raw_material = pricing["raw_material_cost"]
    expected_layout = raw_material * 0.32
    actual_layout = pricing["layout_cost"]
    if abs(expected_layout - actual_layout) > 0.01:
        print_test_result("Cost Calculation Accuracy", False,
            f"Layout cost calculation incorrect: expected {expected_layout}, got {actual_layout}")
        return False
    
    # Verify profit = (raw_material + layout) × 0.60
    expected_profit = (raw_material + actual_layout) * 0.60
    actual_profit = pricing["profit"]
    if abs(expected_profit - actual_profit) > 0.01:
        print_test_result("Cost Calculation Accuracy", False,
            f"Profit calculation incorrect: expected {expected_profit}, got {actual_profit}")
        return False
    
    # Verify final price = raw_material × 2.112
    expected_final = raw_material * 2.112
    actual_final = pricing["final_price"]
    if abs(expected_final - actual_final) > 0.01:
        print_test_result("Cost Calculation Accuracy", False,
            f"Final price calculation incorrect: expected {expected_final}, got {actual_final}")
        return False
    
    print_test_result("Cost Calculation Accuracy", True,
        f"All calculations verified: Raw Material ₹{raw_material} → Final Price ₹{actual_final} (2.112x multiplier)")
    test_results["cost_calculation_accuracy"] = True
    return True

def run_all_tests():
    """Run all test sequences"""
    print("🚀 Starting Comprehensive IS-Standards Belt Conveyor Roller API Testing")
    print("=" * 80)
    print()
    
    # Test sequence as per review request
    test_functions = [
        ("1. Admin Login", test_login),
        ("2. Roller Standards", test_roller_standards),
        ("3. Compatible Bearings", test_compatible_bearings),
        ("4. Compatible Housing", test_compatible_housing),
        ("5. Detailed Cost Calculations", test_detailed_cost_calculations),
        ("6. Invalid Configuration Handling", test_invalid_configurations),
        ("7. Cost Calculation Accuracy", test_cost_calculation_accuracy)
    ]
    
    passed_tests = 0
    total_tests = len(test_functions)
    
    for test_name, test_func in test_functions:
        print(f"Running {test_name}...")
        print("-" * 40)
        
        if test_func():
            passed_tests += 1
        
        print()
    
    # Print final summary
    print("=" * 80)
    print("🎯 TEST SUMMARY")
    print("=" * 80)
    
    for key, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{key.replace('_', ' ').title()}: {status}")
    
    print()
    print(f"Overall Result: {passed_tests}/{total_tests} test groups passed")
    
    # Detailed analysis
    failed_tests = [key for key, passed in test_results.items() if not passed]
    if failed_tests:
        print(f"❌ Failed Tests: {', '.join(failed_tests)}")
        return False
    else:
        print("🎉 All IS-Standards Belt Conveyor Roller APIs working correctly!")
        return True

if __name__ == "__main__":
    print("IS-Standards Belt Conveyor Roller Configuration and Costing API Test Suite")
    print(f"Backend URL: {BACKEND_URL}")
    print()
    
    success = run_all_tests()
    sys.exit(0 if success else 1)