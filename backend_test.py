#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Engineering Product App
Testing all auth, product, quote, and stats endpoints with role-based access control
"""

import requests
import json
import sys
from datetime import datetime

# Base URL for API testing
BASE_URL = "https://cost-calculator-77.preview.emergentagent.com/api"

# Test data storage
test_data = {
    "customer_token": None,
    "admin_token": None,
    "customer_user": None,
    "admin_user": None,
    "products": [],
    "quotes": []
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_test(test_name, result, details=None):
    """Log test results with color coding"""
    color = Colors.GREEN if result else Colors.RED
    status = "PASS" if result else "FAIL"
    print(f"{color}[{status}]{Colors.ENDC} {test_name}")
    if details:
        print(f"    {details}")
    return result

def make_request(method, endpoint, data=None, headers=None, params=None):
    """Make HTTP request with error handling"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=30)
        elif method.upper() == 'PUT':
            response = requests.put(url, json=data, headers=headers, timeout=30)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        return response
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}Request failed: {e}{Colors.ENDC}")
        return None

def get_auth_headers(token):
    """Get authorization headers"""
    return {"Authorization": f"Bearer {token}"} if token else {}

# Test 1: User Registration
def test_user_registration():
    """Test user registration for both customer and admin"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing User Registration ==={Colors.ENDC}")
    
    # Register customer user
    customer_data = {
        "email": "customer@test.com",
        "password": "test123",
        "name": "John Doe",
        "company": "Acme Corp",
        "role": "customer"
    }
    
    response = make_request('POST', '/auth/register', customer_data)
    if response and response.status_code == 200:
        data = response.json()
        test_data["customer_token"] = data["access_token"]
        test_data["customer_user"] = data["user"]
        log_test("Customer registration", True, f"Token: {data['access_token'][:20]}...")
    else:
        log_test("Customer registration", False, f"Status: {response.status_code if response else 'No response'}")
        return False
    
    # Register admin user  
    admin_data = {
        "email": "admin@test.com",
        "password": "admin123", 
        "name": "Admin User",
        "role": "admin"
    }
    
    response = make_request('POST', '/auth/register', admin_data)
    if response and response.status_code == 200:
        data = response.json()
        test_data["admin_token"] = data["access_token"]
        test_data["admin_user"] = data["user"]
        log_test("Admin registration", True, f"Token: {data['access_token'][:20]}...")
        return True
    else:
        log_test("Admin registration", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 2: User Login
def test_user_login():
    """Test user login functionality"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing User Login ==={Colors.ENDC}")
    
    # Login customer
    customer_login = {
        "email": "customer@test.com",
        "password": "test123"
    }
    
    response = make_request('POST', '/auth/login', customer_login)
    if response and response.status_code == 200:
        data = response.json()
        test_data["customer_token"] = data["access_token"]  # Update token
        log_test("Customer login", True, f"User: {data['user']['name']}")
    else:
        log_test("Customer login", False, f"Status: {response.status_code if response else 'No response'}")
        return False
    
    # Login admin
    admin_login = {
        "email": "admin@test.com", 
        "password": "admin123"
    }
    
    response = make_request('POST', '/auth/login', admin_login)
    if response and response.status_code == 200:
        data = response.json()
        test_data["admin_token"] = data["access_token"]  # Update token
        log_test("Admin login", True, f"User: {data['user']['name']}")
        return True
    else:
        log_test("Admin login", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 3: Get Current User
def test_get_current_user():
    """Test getting current user info"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Get Current User ==={Colors.ENDC}")
    
    headers = get_auth_headers(test_data["customer_token"])
    response = make_request('GET', '/auth/me', headers=headers)
    
    if response and response.status_code == 200:
        data = response.json()
        log_test("Get current user", True, f"User: {data['name']} ({data['role']})")
        return True
    else:
        log_test("Get current user", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 4: Create Products (Admin Only)
def test_create_products():
    """Test creating products with admin role"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Product Creation (Admin Only) ==={Colors.ENDC}")
    
    headers = get_auth_headers(test_data["admin_token"])
    
    # Product 1: Industrial Bearing
    product1 = {
        "name": "Industrial Bearing",
        "sku": "BRG-001",
        "description": "High-precision industrial bearing for heavy-duty applications",
        "category": "Bearings",
        "base_price": 125.50,
        "specifications": {
            "dimensions": "50x90x20 mm",
            "weight": "0.8 kg",
            "material": "Steel with ceramic coating",
            "technical_specs": {
                "load_capacity": "15000 N",
                "operating_temp": "-20 to 120°C",
                "speed_limit": "8000 RPM"
            }
        }
    }
    
    response = make_request('POST', '/products', product1, headers)
    if response and response.status_code == 200:
        data = response.json()
        test_data["products"].append(data)
        log_test("Create Product 1 (Industrial Bearing)", True, f"ID: {data['id']}")
    else:
        log_test("Create Product 1 (Industrial Bearing)", False, f"Status: {response.status_code if response else 'No response'}")
        return False
    
    # Product 2: Hydraulic Cylinder
    product2 = {
        "name": "Hydraulic Cylinder",
        "sku": "CYL-002", 
        "description": "Heavy-duty hydraulic cylinder for industrial machinery",
        "category": "Cylinders",
        "base_price": 450.00,
        "specifications": {
            "dimensions": "200x50x300 mm",
            "weight": "12.5 kg",
            "material": "Chrome-plated steel",
            "technical_specs": {
                "bore_size": "50 mm",
                "stroke_length": "200 mm",
                "working_pressure": "250 bar"
            }
        }
    }
    
    response = make_request('POST', '/products', product2, headers)
    if response and response.status_code == 200:
        data = response.json()
        test_data["products"].append(data)
        log_test("Create Product 2 (Hydraulic Cylinder)", True, f"ID: {data['id']}")
    else:
        log_test("Create Product 2 (Hydraulic Cylinder)", False, f"Status: {response.status_code if response else 'No response'}")
        return False
    
    # Product 3: Steel Shaft
    product3 = {
        "name": "Steel Shaft",
        "sku": "SHF-003",
        "description": "Precision-machined steel shaft for mechanical applications",
        "category": "Shafts", 
        "base_price": 89.99,
        "specifications": {
            "dimensions": "1000x25 mm diameter",
            "weight": "3.8 kg",
            "material": "Stainless steel 316",
            "technical_specs": {
                "surface_finish": "Ra 0.8",
                "tolerance": "h6",
                "hardness": "HRC 40-45"
            }
        }
    }
    
    response = make_request('POST', '/products', product3, headers)
    if response and response.status_code == 200:
        data = response.json()
        test_data["products"].append(data)
        log_test("Create Product 3 (Steel Shaft)", True, f"ID: {data['id']}")
        return True
    else:
        log_test("Create Product 3 (Steel Shaft)", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 5: Get Products with Search and Filter
def test_get_products():
    """Test getting products with various filters"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Get Products ==={Colors.ENDC}")
    
    headers = get_auth_headers(test_data["customer_token"])
    
    # Get all products
    response = make_request('GET', '/products', headers=headers)
    if response and response.status_code == 200:
        products = response.json()
        log_test("Get all products", True, f"Found {len(products)} products")
    else:
        log_test("Get all products", False, f"Status: {response.status_code if response else 'No response'}")
        return False
    
    # Test search functionality
    response = make_request('GET', '/products', headers=headers, params={"search": "bearing"})
    if response and response.status_code == 200:
        products = response.json()
        log_test("Search products (bearing)", True, f"Found {len(products)} products")
    else:
        log_test("Search products (bearing)", False, f"Status: {response.status_code if response else 'No response'}")
        return False
    
    # Test category filter
    response = make_request('GET', '/products', headers=headers, params={"category": "Bearings"})
    if response and response.status_code == 200:
        products = response.json()
        log_test("Filter by category (Bearings)", True, f"Found {len(products)} products")
        return True
    else:
        log_test("Filter by category (Bearings)", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 6: Get Single Product
def test_get_single_product():
    """Test getting single product details"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Get Single Product ==={Colors.ENDC}")
    
    if not test_data["products"]:
        log_test("Get single product", False, "No products available for testing")
        return False
    
    headers = get_auth_headers(test_data["customer_token"])
    product_id = test_data["products"][0]["id"]
    
    response = make_request('GET', f'/products/{product_id}', headers=headers)
    if response and response.status_code == 200:
        product = response.json()
        log_test("Get single product", True, f"Product: {product['name']}")
        return True
    else:
        log_test("Get single product", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 7: Update Product (Admin Only)
def test_update_product():
    """Test updating product with admin role"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Update Product (Admin Only) ==={Colors.ENDC}")
    
    if not test_data["products"]:
        log_test("Update product", False, "No products available for testing")
        return False
    
    headers = get_auth_headers(test_data["admin_token"])
    product_id = test_data["products"][0]["id"]
    
    # Update the first product's price
    updated_product = {
        "name": "Industrial Bearing",
        "sku": "BRG-001",
        "description": "High-precision industrial bearing for heavy-duty applications",
        "category": "Bearings",
        "base_price": 135.00,  # Updated price
        "specifications": {
            "dimensions": "50x90x20 mm",
            "weight": "0.8 kg", 
            "material": "Steel with ceramic coating",
            "technical_specs": {
                "load_capacity": "15000 N",
                "operating_temp": "-20 to 120°C",
                "speed_limit": "8000 RPM"
            }
        }
    }
    
    response = make_request('PUT', f'/products/{product_id}', updated_product, headers)
    if response and response.status_code == 200:
        product = response.json()
        log_test("Update product price", True, f"New price: ${product['base_price']}")
        return True
    else:
        log_test("Update product price", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 8: Create Quote (Customer)
def test_create_quote():
    """Test creating quote as customer"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Create Quote (Customer) ==={Colors.ENDC}")
    
    if len(test_data["products"]) < 2:
        log_test("Create quote", False, "Need at least 2 products for testing")
        return False
    
    headers = get_auth_headers(test_data["customer_token"])
    
    # Create quote with 2 products
    quote_data = {
        "products": [
            {
                "product_id": test_data["products"][0]["id"],
                "product_name": test_data["products"][0]["name"], 
                "quantity": 2,
                "unit_price": test_data["products"][0]["base_price"],
                "specifications": test_data["products"][0]["specifications"]
            },
            {
                "product_id": test_data["products"][1]["id"],
                "product_name": test_data["products"][1]["name"],
                "quantity": 1,
                "unit_price": test_data["products"][1]["base_price"],
                "specifications": test_data["products"][1]["specifications"]
            }
        ],
        "notes": "Need urgent delivery"
    }
    
    response = make_request('POST', '/quotes', quote_data, headers)
    if response and response.status_code == 200:
        quote = response.json()
        test_data["quotes"].append(quote)
        log_test("Create quote", True, f"Quote ID: {quote['id']}, Total: ${quote['total_price']}")
        return True
    else:
        log_test("Create quote", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 9: Get Quotes (Role-based)
def test_get_quotes():
    """Test getting quotes with role-based access"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Get Quotes (Role-based) ==={Colors.ENDC}")
    
    # Customer should only see their own quotes
    headers = get_auth_headers(test_data["customer_token"])
    response = make_request('GET', '/quotes', headers=headers)
    if response and response.status_code == 200:
        quotes = response.json()
        log_test("Customer get quotes", True, f"Found {len(quotes)} quotes")
    else:
        log_test("Customer get quotes", False, f"Status: {response.status_code if response else 'No response'}")
        return False
    
    # Admin should see all quotes
    headers = get_auth_headers(test_data["admin_token"])
    response = make_request('GET', '/quotes', headers=headers)
    if response and response.status_code == 200:
        quotes = response.json()
        log_test("Admin get all quotes", True, f"Found {len(quotes)} quotes")
        return True
    else:
        log_test("Admin get all quotes", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 10: Get Single Quote
def test_get_single_quote():
    """Test getting single quote details"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Get Single Quote ==={Colors.ENDC}")
    
    if not test_data["quotes"]:
        log_test("Get single quote", False, "No quotes available for testing")
        return False
    
    headers = get_auth_headers(test_data["customer_token"])
    quote_id = test_data["quotes"][0]["id"]
    
    response = make_request('GET', f'/quotes/{quote_id}', headers=headers)
    if response and response.status_code == 200:
        quote = response.json()
        log_test("Get single quote", True, f"Quote status: {quote['status']}")
        return True
    else:
        log_test("Get single quote", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 11: Update Quote Status (Admin/Sales Only) 
def test_update_quote_status():
    """Test updating quote status with admin role"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Update Quote Status (Admin/Sales Only) ==={Colors.ENDC}")
    
    if not test_data["quotes"]:
        log_test("Update quote status", False, "No quotes available for testing")
        return False
    
    headers = get_auth_headers(test_data["admin_token"])
    quote_id = test_data["quotes"][0]["id"]
    
    update_data = {
        "status": "approved",
        "notes": "Approved for processing"
    }
    
    response = make_request('PUT', f'/quotes/{quote_id}', update_data, headers)
    if response and response.status_code == 200:
        quote = response.json()
        log_test("Update quote status", True, f"New status: {quote['status']}")
        return True
    else:
        log_test("Update quote status", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 12: Get Stats (Admin/Sales Only)
def test_get_stats():
    """Test getting statistics with admin role"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Get Stats (Admin/Sales Only) ==={Colors.ENDC}")
    
    headers = get_auth_headers(test_data["admin_token"])
    response = make_request('GET', '/stats', headers=headers)
    
    if response and response.status_code == 200:
        stats = response.json()
        log_test("Get statistics", True, f"Products: {stats['total_products']}, Quotes: {stats['total_quotes']}")
        return True
    else:
        log_test("Get statistics", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 13: Delete Product (Admin Only)
def test_delete_product():
    """Test deleting product with admin role"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Delete Product (Admin Only) ==={Colors.ENDC}")
    
    if len(test_data["products"]) < 3:
        log_test("Delete product", False, "Need at least 3 products for testing")
        return False
    
    headers = get_auth_headers(test_data["admin_token"])
    product_id = test_data["products"][2]["id"]  # Delete third product (Steel Shaft)
    
    response = make_request('DELETE', f'/products/{product_id}', headers=headers)
    if response and response.status_code == 200:
        log_test("Delete product (Steel Shaft)", True, "Product deleted successfully")
        return True
    else:
        log_test("Delete product (Steel Shaft)", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 14: Get Categories
def test_get_categories():
    """Test getting product categories"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Get Categories ==={Colors.ENDC}")
    
    headers = get_auth_headers(test_data["customer_token"])
    response = make_request('GET', '/categories', headers=headers)
    
    if response and response.status_code == 200:
        data = response.json()
        categories = data.get("categories", [])
        log_test("Get categories", True, f"Categories: {', '.join(categories)}")
        return True
    else:
        log_test("Get categories", False, f"Status: {response.status_code if response else 'No response'}")
        return False

# Test 15: Role-based Access Control
def test_role_based_access():
    """Test that role-based access control is enforced"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== Testing Role-based Access Control ==={Colors.ENDC}")
    
    # Customer should NOT be able to create products (403 expected)
    headers = get_auth_headers(test_data["customer_token"])
    product_data = {
        "name": "Unauthorized Product",
        "sku": "UNAUTH-001",
        "description": "Should fail",
        "category": "Test",
        "base_price": 100.0,
        "specifications": {"test": "test"}
    }
    
    response = make_request('POST', '/products', product_data, headers)
    if response and response.status_code == 403:
        log_test("Customer cannot create product (403)", True, "Access correctly denied")
        return True
    else:
        log_test("Customer cannot create product (403)", False, f"Expected 403, got {response.status_code if response else 'No response'}")
        return False

def main():
    """Run all tests"""
    print(f"{Colors.BOLD}{Colors.BLUE}Starting comprehensive backend API testing...{Colors.ENDC}")
    print(f"Backend URL: {BASE_URL}")
    
    tests = [
        test_user_registration,
        test_user_login,
        test_get_current_user,
        test_create_products,
        test_get_products,
        test_get_single_product,
        test_update_product,
        test_create_quote,
        test_get_quotes,
        test_get_single_quote,
        test_update_quote_status,
        test_get_stats,
        test_delete_product,
        test_get_categories,
        test_role_based_access
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"{Colors.RED}Test {test.__name__} failed with exception: {e}{Colors.ENDC}")
            failed += 1
    
    print(f"\n{Colors.BOLD}=== Test Summary ==={Colors.ENDC}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.ENDC}")
    print(f"{Colors.RED}Failed: {failed}{Colors.ENDC}")
    print(f"{Colors.BLUE}Total: {passed + failed}{Colors.ENDC}")
    
    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All tests passed! Backend is working correctly.{Colors.ENDC}")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ {failed} test(s) failed. Please review the issues above.{Colors.ENDC}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)