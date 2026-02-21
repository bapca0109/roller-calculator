import requests
import json
import uuid

# Backend URL from frontend .env
BASE_URL = "https://cost-calculator-77.preview.emergentagent.com/api"

class BeltConveyorRollerAPITest:
    def __init__(self):
        self.admin_token = None
        self.customer_token = None
        self.created_products = []
        self.created_quote_id = None
        
    def test_user_login(self):
        """Test 1: User Authentication"""
        print("\n=== Testing User Login ===")
        
        # Login as admin
        admin_login_data = {
            "email": "admin@test.com",
            "password": "admin123"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=admin_login_data)
        print(f"Admin Login - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            self.admin_token = data['access_token']
            print(f"✅ Admin login successful. Token obtained.")
        else:
            print(f"❌ Admin login failed: {response.text}")
            return False
            
        # Login as customer
        customer_login_data = {
            "email": "customer@test.com", 
            "password": "test123"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=customer_login_data)
        print(f"Customer Login - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            self.customer_token = data['access_token']
            print(f"✅ Customer login successful. Token obtained.")
        else:
            print(f"❌ Customer login failed: {response.text}")
            return False
            
        return True
    
    def test_create_conveyor_roller_products(self):
        """Test 2: Create Belt Conveyor Roller Products"""
        print("\n=== Testing Create Conveyor Roller Products ===")
        
        if not self.admin_token:
            print("❌ No admin token available")
            return False
        
        headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
        
        # Product 1: Carrying Roller - Standard Steel
        product1 = {
            "name": "Standard Carrying Roller",
            "sku": "CR-STD-001",
            "category": "Standard",
            "description": "Heavy-duty steel carrying roller for belt conveyors",
            "base_price": 85.50,
            "specifications": {
                "diameter": 89,
                "length": 500,
                "shaft_diameter": 20,
                "material": "Steel",
                "bearing_type": "6204 2RS",
                "load_capacity": 250,
                "surface_type": "Smooth",
                "application_type": "Carrying",
                "rpm": 400,
                "temperature_rating": 80
            }
        }
        
        # Product 2: Impact Roller - Rubber Lagged
        product2 = {
            "name": "Impact Roller - Rubber Lagged",
            "sku": "IR-RL-002", 
            "category": "Special",
            "description": "Impact roller with rubber lagging for loading zones",
            "base_price": 125.00,
            "specifications": {
                "diameter": 108,
                "length": 600,
                "shaft_diameter": 25,
                "material": "Steel",
                "bearing_type": "6205 2RS",
                "load_capacity": 350,
                "surface_type": "Rubber-lagged",
                "application_type": "Impact",
                "rpm": 350,
                "temperature_rating": 70
            }
        }
        
        # Product 3: Return Roller - HDPE
        product3 = {
            "name": "HDPE Return Roller",
            "sku": "RR-HDPE-003",
            "category": "Material Variant", 
            "description": "Lightweight HDPE return roller for belt underside",
            "base_price": 45.00,
            "specifications": {
                "diameter": 89,
                "length": 450,
                "shaft_diameter": 17,
                "material": "HDPE",
                "bearing_type": "6203 2RS",
                "load_capacity": 150,
                "surface_type": "Smooth",
                "application_type": "Return",
                "rpm": 450,
                "temperature_rating": 60
            }
        }
        
        products = [product1, product2, product3]
        
        for i, product in enumerate(products, 1):
            response = requests.post(f"{BASE_URL}/products", json=product, headers=headers)
            print(f"Product {i} Creation - Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.created_products.append(data)
                print(f"✅ {product['name']} created successfully. ID: {data['id']}")
                print(f"   SKU: {data['sku']}, Base Price: ${data['base_price']}")
                print(f"   Specifications: {data['specifications']['material']} - {data['specifications']['diameter']}mm")
            else:
                print(f"❌ Failed to create {product['name']}: {response.text}")
                return False
                
        return len(self.created_products) == 3
    
    def test_get_products(self):
        """Test 3: Get All Products"""
        print("\n=== Testing Get Products ===")
        
        if not self.admin_token:
            print("❌ No admin token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        response = requests.get(f"{BASE_URL}/products", headers=headers)
        print(f"Get Products - Status: {response.status_code}")
        
        if response.status_code == 200:
            products = response.json()
            print(f"✅ Retrieved {len(products)} products")
            
            for product in products:
                print(f"   • {product['name']} ({product['sku']}) - ${product['base_price']}")
                specs = product['specifications']
                print(f"     Specs: {specs['material']}, {specs['diameter']}mm x {specs['length']}mm, {specs['application_type']}")
                
            return len(products) >= 3
        else:
            print(f"❌ Failed to get products: {response.text}")
            return False
    
    def test_get_single_product(self):
        """Test 4: Get Single Product Details"""
        print("\n=== Testing Get Single Product ===")
        
        if not self.created_products:
            print("❌ No products created")
            return False
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        product_id = self.created_products[0]['id']
        
        response = requests.get(f"{BASE_URL}/products/{product_id}", headers=headers)
        print(f"Get Single Product - Status: {response.status_code}")
        
        if response.status_code == 200:
            product = response.json()
            print(f"✅ Retrieved product: {product['name']}")
            print(f"   Complete specifications:")
            for key, value in product['specifications'].items():
                print(f"     {key}: {value}")
            return True
        else:
            print(f"❌ Failed to get product: {response.text}")
            return False
    
    def test_price_calculation(self):
        """Test 5: Price Calculation with Quantity Discounts"""
        print("\n=== Testing Price Calculation ===")
        
        if not self.created_products:
            print("❌ No products created")
            return False
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test cases with different quantities for discount tiers
        test_cases = [
            (self.created_products[0]['id'], 10, "Carrying Roller", 5),    # 5% discount
            (self.created_products[1]['id'], 50, "Impact Roller", 10),    # 10% discount  
            (self.created_products[2]['id'], 100, "Return Roller", 15)    # 15% discount
        ]
        
        for product_id, quantity, name, expected_discount in test_cases:
            calc_data = {
                "product_id": product_id,
                "quantity": quantity,
                "delivery_location": "New York, NY"
            }
            
            response = requests.post(f"{BASE_URL}/calculate-price", json=calc_data, headers=headers)
            print(f"{name} Price Calculation (qty: {quantity}) - Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {name} calculation successful:")
                print(f"   Unit Price: ${data['unit_price']}")
                print(f"   Subtotal: ${data['subtotal']}")
                print(f"   Discount: ${data['quantity_discount']} ({data['discount_percent']}%)")
                print(f"   Total Price: ${data['total_price']}")
                
                # Verify discount percentage
                if data['discount_percent'] == expected_discount:
                    print(f"   ✅ Correct discount percentage: {expected_discount}%")
                else:
                    print(f"   ❌ Incorrect discount percentage. Expected: {expected_discount}%, Got: {data['discount_percent']}%")
                    return False
            else:
                print(f"❌ Failed to calculate price for {name}: {response.text}")
                return False
                
        return True
    
    def test_create_quote_with_roller_products(self):
        """Test 6: Create Quote with Roller Products"""
        print("\n=== Testing Create Quote with Roller Products ===")
        
        if not self.customer_token or not self.created_products:
            print("❌ No customer token or products available")
            return False
        
        headers = {"Authorization": f"Bearer {self.customer_token}"}
        
        quote_data = {
            "products": [
                {
                    "product_id": self.created_products[0]['id'],
                    "product_name": self.created_products[0]['name'],
                    "quantity": 20,
                    "unit_price": 85.50,
                    "specifications": self.created_products[0]['specifications']
                },
                {
                    "product_id": self.created_products[1]['id'],
                    "product_name": self.created_products[1]['name'], 
                    "quantity": 15,
                    "unit_price": 125.00,
                    "specifications": self.created_products[1]['specifications']
                }
            ],
            "delivery_location": "New York, NY",
            "notes": "Quote for belt conveyor roller installation project"
        }
        
        response = requests.post(f"{BASE_URL}/quotes", json=quote_data, headers=headers)
        print(f"Create Quote - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            self.created_quote_id = data['id']
            print(f"✅ Quote created successfully. ID: {data['id']}")
            print(f"   Subtotal: ${data['subtotal']}")
            print(f"   Total Discount: ${data['total_discount']}")
            print(f"   Total Price: ${data['total_price']}")
            print(f"   Products:")
            for product in data['products']:
                print(f"     • {product['product_name']}: {product['quantity']} units @ ${product['unit_price']} each")
                print(f"       Discount Applied: ${product['calculated_discount']}")
            return True
        else:
            print(f"❌ Failed to create quote: {response.text}")
            return False
    
    def test_update_quote_with_shipping(self):
        """Test 7: Update Quote with Shipping Cost"""
        print("\n=== Testing Update Quote with Shipping ===")
        
        if not self.admin_token or not self.created_quote_id:
            print("❌ No admin token or quote ID available")
            return False
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        update_data = {
            "status": "approved",
            "shipping_cost": 75.00,
            "notes": "Approved - Standard shipping to NY"
        }
        
        response = requests.put(f"{BASE_URL}/quotes/{self.created_quote_id}", json=update_data, headers=headers)
        print(f"Update Quote - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Quote updated successfully:")
            print(f"   Status: {data['status']}")
            print(f"   Shipping Cost: ${data['shipping_cost']}")
            print(f"   Total Price (with shipping): ${data['total_price']}")
            print(f"   Notes: {data['notes']}")
            return True
        else:
            print(f"❌ Failed to update quote: {response.text}")
            return False
    
    def test_get_quote(self):
        """Test 8: Get Quote Details"""
        print("\n=== Testing Get Quote ===")
        
        if not self.customer_token or not self.created_quote_id:
            print("❌ No customer token or quote ID available")
            return False
        
        headers = {"Authorization": f"Bearer {self.customer_token}"}
        
        response = requests.get(f"{BASE_URL}/quotes/{self.created_quote_id}", headers=headers)
        print(f"Get Quote - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Quote retrieved successfully:")
            print(f"   ID: {data['id']}")
            print(f"   Status: {data['status']}")
            print(f"   Subtotal: ${data['subtotal']}")
            print(f"   Total Discount: ${data['total_discount']}")
            print(f"   Shipping Cost: ${data['shipping_cost']}")
            print(f"   Total Price: ${data['total_price']}")
            print(f"   Delivery Location: {data['delivery_location']}")
            print(f"   Products with Discounts:")
            for product in data['products']:
                print(f"     • {product['product_name']}: {product['quantity']} @ ${product['unit_price']} = ${product['calculated_discount']} discount")
            return True
        else:
            print(f"❌ Failed to get quote: {response.text}")
            return False
    
    def run_all_tests(self):
        """Run all Belt Conveyor Roller API tests"""
        print("🚀 Starting Belt Conveyor Roller API Tests...")
        print(f"Backend URL: {BASE_URL}")
        
        tests = [
            ("User Login", self.test_user_login),
            ("Create Conveyor Roller Products", self.test_create_conveyor_roller_products),
            ("Get Products", self.test_get_products),
            ("Get Single Product", self.test_get_single_product),
            ("Price Calculation", self.test_price_calculation),
            ("Create Quote with Roller Products", self.test_create_quote_with_roller_products),
            ("Update Quote with Shipping", self.test_update_quote_with_shipping),
            ("Get Quote", self.test_get_quote)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed += 1
                    print(f"✅ {test_name} - PASSED")
                else:
                    failed += 1 
                    print(f"❌ {test_name} - FAILED")
            except Exception as e:
                failed += 1
                print(f"❌ {test_name} - ERROR: {str(e)}")
        
        print(f"\n📊 Test Results Summary:")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        return passed, failed

if __name__ == "__main__":
    tester = BeltConveyorRollerAPITest()
    tester.run_all_tests()