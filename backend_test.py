#!/usr/bin/env python3
"""
Belt Conveyor Roller Price Calculator - Freight Calculation System Tests
Testing the newly implemented freight calculation feature in /api/calculate-detailed-cost endpoint
"""

import requests
import json
from typing import Dict, Any

# Backend URL configuration
BASE_URL = "https://conveyor-pricer.preview.emergentagent.com/api"

class FreightCalculationTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.test_results = []
        
    def authenticate(self):
        """Authenticate with admin credentials"""
        print("🔐 Authenticating with admin credentials...")
        
        login_data = {
            "email": "admin@test.com",
            "password": "admin123"
        }
        
        try:
            response = requests.post(f"{self.base_url}/login", json=login_data)
            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data["access_token"]
                print(f"✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def get_headers(self):
        """Get headers with authorization token"""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_scenario(self, name: str, data: Dict[str, Any], expected_checks: Dict[str, Any]) -> bool:
        """Test a specific scenario and validate results"""
        print(f"\n🧪 Testing: {name}")
        print(f"📤 Request data: {json.dumps(data, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.base_url}/calculate-detailed-cost",
                json=data,
                headers=self.get_headers()
            )
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code} - {response.text}")
                return False
            
            result = response.json()
            print(f"📥 Response: {json.dumps(result, indent=2)}")
            
            # Validate expected checks
            all_checks_passed = True
            for check_name, expected_value in expected_checks.items():
                if check_name == "freight_null":
                    actual = result.get("freight")
                    if expected_value and actual is not None:
                        print(f"❌ Check '{check_name}': Expected freight to be null, got {actual}")
                        all_checks_passed = False
                    elif not expected_value and actual is None:
                        print(f"❌ Check '{check_name}': Expected freight data, got null")
                        all_checks_passed = False
                    else:
                        print(f"✅ Check '{check_name}': Passed")
                        
                elif check_name == "has_freight_fields":
                    freight = result.get("freight")
                    if freight:
                        required_fields = ["destination_pincode", "dispatch_pincode", "distance_km", 
                                         "single_roller_weight_kg", "total_weight_kg", 
                                         "freight_rate_per_kg", "freight_charges"]
                        missing_fields = [f for f in required_fields if f not in freight]
                        if missing_fields:
                            print(f"❌ Check '{check_name}': Missing fields {missing_fields}")
                            all_checks_passed = False
                        else:
                            print(f"✅ Check '{check_name}': All freight fields present")
                    else:
                        print(f"❌ Check '{check_name}': No freight data found")
                        all_checks_passed = False
                        
                elif check_name == "dispatch_pincode":
                    freight = result.get("freight")
                    if freight and freight.get("dispatch_pincode") == expected_value:
                        print(f"✅ Check '{check_name}': {freight.get('dispatch_pincode')}")
                    else:
                        actual = freight.get("dispatch_pincode") if freight else None
                        print(f"❌ Check '{check_name}': Expected {expected_value}, got {actual}")
                        all_checks_passed = False
                        
                elif check_name == "destination_pincode":
                    freight = result.get("freight")
                    if freight and freight.get("destination_pincode") == expected_value:
                        print(f"✅ Check '{check_name}': {freight.get('destination_pincode')}")
                    else:
                        actual = freight.get("destination_pincode") if freight else None
                        print(f"❌ Check '{check_name}': Expected {expected_value}, got {actual}")
                        all_checks_passed = False
                        
                elif check_name == "distance_range":
                    freight = result.get("freight")
                    if freight:
                        distance = freight.get("distance_km", 0)
                        min_dist, max_dist = expected_value
                        if min_dist <= distance <= max_dist:
                            print(f"✅ Check '{check_name}': Distance {distance}km within range {min_dist}-{max_dist}km")
                        else:
                            print(f"❌ Check '{check_name}': Distance {distance}km outside range {min_dist}-{max_dist}km")
                            all_checks_passed = False
                    else:
                        print(f"❌ Check '{check_name}': No freight data")
                        all_checks_passed = False
                        
                elif check_name == "freight_rate":
                    freight = result.get("freight")
                    if freight and freight.get("freight_rate_per_kg") == expected_value:
                        print(f"✅ Check '{check_name}': Rate ₹{freight.get('freight_rate_per_kg')}/kg")
                    else:
                        actual = freight.get("freight_rate_per_kg") if freight else None
                        print(f"❌ Check '{check_name}': Expected ₹{expected_value}/kg, got ₹{actual}/kg")
                        all_checks_passed = False
                        
                elif check_name == "total_weight_calculation":
                    freight = result.get("freight")
                    quantity = data.get("quantity", 1)
                    if freight:
                        single_weight = freight.get("single_roller_weight_kg", 0)
                        total_weight = freight.get("total_weight_kg", 0)
                        expected_total = single_weight * quantity
                        if abs(total_weight - expected_total) < 0.01:  # Allow small rounding differences
                            print(f"✅ Check '{check_name}': Total weight {total_weight}kg = {single_weight}kg × {quantity}")
                        else:
                            print(f"❌ Check '{check_name}': Expected {expected_total}kg, got {total_weight}kg")
                            all_checks_passed = False
                    else:
                        print(f"❌ Check '{check_name}': No freight data")
                        all_checks_passed = False
                        
                elif check_name == "grand_total_with_freight":
                    quantity = data.get("quantity", 1)
                    pricing = result.get("pricing", {})
                    freight = result.get("freight")
                    grand_total = result.get("grand_total", 0)
                    
                    product_total = pricing.get("final_price", 0) * quantity
                    freight_charges = freight.get("freight_charges", 0) if freight else 0
                    expected_grand_total = product_total + freight_charges
                    
                    if abs(grand_total - expected_grand_total) < 0.01:
                        print(f"✅ Check '{check_name}': Grand total ₹{grand_total} = ₹{product_total} + ₹{freight_charges}")
                    else:
                        print(f"❌ Check '{check_name}': Expected ₹{expected_grand_total}, got ₹{grand_total}")
                        all_checks_passed = False
                        
                elif check_name == "grand_total_without_freight":
                    quantity = data.get("quantity", 1)
                    pricing = result.get("pricing", {})
                    grand_total = result.get("grand_total", 0)
                    
                    expected_grand_total = pricing.get("final_price", 0) * quantity
                    
                    if abs(grand_total - expected_grand_total) < 0.01:
                        print(f"✅ Check '{check_name}': Grand total ₹{grand_total} = ₹{expected_grand_total}")
                    else:
                        print(f"❌ Check '{check_name}': Expected ₹{expected_grand_total}, got ₹{grand_total}")
                        all_checks_passed = False
                        
            self.test_results.append({
                "name": name,
                "passed": all_checks_passed,
                "response": result
            })
            
            if all_checks_passed:
                print(f"✅ {name}: ALL CHECKS PASSED")
            else:
                print(f"❌ {name}: SOME CHECKS FAILED")
                
            return all_checks_passed
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            self.test_results.append({
                "name": name,
                "passed": False,
                "error": str(e)
            })
            return False
    
    def run_freight_calculation_tests(self):
        """Run comprehensive freight calculation tests"""
        print("🚀 Starting Belt Conveyor Roller Freight Calculation Tests\n")
        
        if not self.authenticate():
            return False
        
        # Test 1: WITHOUT freight (baseline)
        baseline_data = {
            "pipe_diameter": 88.9,
            "pipe_length": 1000,
            "shaft_diameter": 25,
            "bearing_number": "6205",
            "bearing_make": "china",
            "pipe_type": "B",
            "quantity": 1
        }
        
        self.test_scenario(
            "Test 1: WITHOUT freight calculation (baseline)",
            baseline_data,
            {
                "freight_null": True,  # freight should be null
                "grand_total_without_freight": True
            }
        )
        
        # Test 2: WITH freight_pincode (Delhi - 110001)
        delhi_data = {
            "pipe_diameter": 88.9,
            "pipe_length": 1000,
            "shaft_diameter": 25,
            "bearing_number": "6205",
            "bearing_make": "china",
            "pipe_type": "B",
            "quantity": 1,
            "freight_pincode": "110001"
        }
        
        self.test_scenario(
            "Test 2: WITH freight_pincode (Delhi - 110001)",
            delhi_data,
            {
                "freight_null": False,  # freight should NOT be null
                "has_freight_fields": True,
                "dispatch_pincode": "382433",
                "destination_pincode": "110001",
                "distance_range": (800, 1000),  # ~900km for Delhi
                "freight_rate": 5.0,  # ₹5/kg for 600-1000km range
                "grand_total_with_freight": True
            }
        )
        
        # Test 3: Multiple quantity (5 rollers) with freight
        multiple_data = {
            "pipe_diameter": 88.9,
            "pipe_length": 1000,
            "shaft_diameter": 25,
            "bearing_number": "6205",
            "bearing_make": "china",
            "pipe_type": "B",
            "quantity": 5,
            "freight_pincode": "110001"
        }
        
        self.test_scenario(
            "Test 3: Multiple quantity (5 rollers) with freight",
            multiple_data,
            {
                "has_freight_fields": True,
                "total_weight_calculation": True,  # total_weight = single_weight × 5
                "grand_total_with_freight": True
            }
        )
        
        # Test 4a: Different distance tier - Gujarat (local, 382001)
        gujarat_data = {
            "pipe_diameter": 88.9,
            "pipe_length": 1000,
            "shaft_diameter": 25,
            "bearing_number": "6205",
            "bearing_make": "china",
            "pipe_type": "B",
            "quantity": 1,
            "freight_pincode": "382001"
        }
        
        self.test_scenario(
            "Test 4a: Gujarat local (382001) - Low distance tier",
            gujarat_data,
            {
                "has_freight_fields": True,
                "distance_range": (100, 200),  # ~150km distance
                "freight_rate": 2.0,  # ₹2/kg for 0-300km tier
                "grand_total_with_freight": True
            }
        )
        
        # Test 4b: Different distance tier - Tamil Nadu (600001)
        tamil_nadu_data = {
            "pipe_diameter": 88.9,
            "pipe_length": 1000,
            "shaft_diameter": 25,
            "bearing_number": "6205",
            "bearing_make": "china",
            "pipe_type": "B",
            "quantity": 1,
            "freight_pincode": "600001"
        }
        
        self.test_scenario(
            "Test 4b: Tamil Nadu (600001) - High distance tier",
            tamil_nadu_data,
            {
                "has_freight_fields": True,
                "distance_range": (1500, 1700),  # ~1600km distance
                "freight_rate": 9.0,  # ₹9/kg for 1500+ km tier
                "grand_total_with_freight": True
            }
        )
        
        # Test 5: Impact Roller with Rubber (heavier)
        impact_roller_data = {
            "pipe_diameter": 88.9,
            "pipe_length": 1000,
            "shaft_diameter": 25,
            "bearing_number": "6205",
            "bearing_make": "china",
            "pipe_type": "B",
            "rubber_diameter": 140,
            "quantity": 2,
            "freight_pincode": "110001"
        }
        
        self.test_scenario(
            "Test 5: Impact Roller with Rubber (heavier weight)",
            impact_roller_data,
            {
                "has_freight_fields": True,
                "total_weight_calculation": True,
                "grand_total_with_freight": True
            }
        )
        
        return True
    
    def print_final_summary(self):
        """Print final test summary"""
        print("\n" + "="*70)
        print("🎯 FREIGHT CALCULATION TEST SUMMARY")
        print("="*70)
        
        passed_count = sum(1 for result in self.test_results if result.get("passed", False))
        total_count = len(self.test_results)
        
        print(f"Total Tests: {total_count}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {total_count - passed_count}")
        
        if passed_count == total_count:
            print("🎉 ALL FREIGHT CALCULATION TESTS PASSED!")
        else:
            print("❌ Some tests failed. Check details above.")
            
        print("\nTest Details:")
        for i, result in enumerate(self.test_results, 1):
            status = "✅ PASS" if result.get("passed", False) else "❌ FAIL"
            print(f"{i}. {result['name']}: {status}")
            
        print("="*70)

def main():
    """Main test execution"""
    tester = FreightCalculationTester()
    
    print("Belt Conveyor Roller - FREIGHT CALCULATION SYSTEM TESTING")
    print("Testing newly implemented freight features in /api/calculate-detailed-cost")
    print("Backend URL:", BASE_URL)
    print("="*70)
    
    if tester.run_freight_calculation_tests():
        tester.print_final_summary()
    else:
        print("❌ Could not complete tests due to authentication failure")

if __name__ == "__main__":
    main()