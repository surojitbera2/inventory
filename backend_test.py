import requests
import sys
import json
from datetime import datetime

class DashboardAPITester:
    def __init__(self, base_url="https://8e0cb205-5783-4097-b543-f2846a0eefc0.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.admin_token = None
        self.user_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_ids = {
            "vendor": None,
            "customer": None,
            "product": None,
            "sale": None
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, admin_required=False):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        # Use the appropriate token
        if admin_required and self.admin_token:
            headers['Authorization'] = f'Bearer {self.admin_token}'
        elif token:
            headers['Authorization'] = f'Bearer {token}'
        elif self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            
            # Print response details
            print(f"Status: {response.status_code}")
            try:
                response_data = response.json()
                print(f"Response: {json.dumps(response_data, indent=2)}")
            except:
                print(f"Response: {response.text}")
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self, username, password, is_admin=False):
        """Test login and get token"""
        success, response = self.run_test(
            f"Login as {username}",
            "POST",
            "auth/login",
            200,
            data={"username": username, "password": password}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            if is_admin:
                self.admin_token = response['access_token']
            else:
                self.user_token = response['access_token']
            print(f"User role: {response['user']['role']}")
            return True
        return False

    def test_get_current_user(self):
        """Test getting current user info"""
        return self.run_test(
            "Get Current User Info",
            "GET",
            "auth/me",
            200
        )

    def test_create_vendor(self, name, address, phone):
        """Test creating a vendor"""
        success, response = self.run_test(
            "Create Vendor",
            "POST",
            "vendors",
            200,
            data={"name": name, "address": address, "phone": phone}
        )
        if success and 'id' in response:
            self.created_ids["vendor"] = response['id']
        return success, response

    def test_get_vendors(self):
        """Test getting all vendors"""
        return self.run_test(
            "Get All Vendors",
            "GET",
            "vendors",
            200
        )

    def test_update_vendor(self, vendor_id, name, address, phone):
        """Test updating a vendor"""
        return self.run_test(
            "Update Vendor",
            "PUT",
            f"vendors/{vendor_id}",
            200,
            data={"name": name, "address": address, "phone": phone}
        )

    def test_delete_vendor(self, vendor_id):
        """Test deleting a vendor (admin only)"""
        return self.run_test(
            "Delete Vendor (Admin Only)",
            "DELETE",
            f"vendors/{vendor_id}",
            200,
            admin_required=True
        )

    def test_create_customer(self, name, address, phone):
        """Test creating a customer"""
        success, response = self.run_test(
            "Create Customer",
            "POST",
            "customers",
            200,
            data={"name": name, "address": address, "phone": phone}
        )
        if success and 'id' in response:
            self.created_ids["customer"] = response['id']
        return success, response

    def test_get_customers(self):
        """Test getting all customers"""
        return self.run_test(
            "Get All Customers",
            "GET",
            "customers",
            200
        )

    def test_update_customer(self, customer_id, name, address, phone):
        """Test updating a customer"""
        return self.run_test(
            "Update Customer",
            "PUT",
            f"customers/{customer_id}",
            200,
            data={"name": name, "address": address, "phone": phone}
        )

    def test_delete_customer(self, customer_id):
        """Test deleting a customer (admin only)"""
        return self.run_test(
            "Delete Customer (Admin Only)",
            "DELETE",
            f"customers/{customer_id}",
            200,
            admin_required=True
        )

    def test_create_product(self, name, vendor_id, quantity, purchase_price, selling_price):
        """Test creating a product"""
        success, response = self.run_test(
            "Create Product",
            "POST",
            "products",
            200,
            data={
                "name": name,
                "vendor_id": vendor_id,
                "quantity": quantity,
                "purchase_price": purchase_price,
                "selling_price": selling_price
            }
        )
        if success and 'id' in response:
            self.created_ids["product"] = response['id']
        return success, response

    def test_get_products(self):
        """Test getting all products"""
        return self.run_test(
            "Get All Products",
            "GET",
            "products",
            200
        )

    def test_update_product(self, product_id, name, vendor_id, quantity, purchase_price, selling_price):
        """Test updating a product"""
        return self.run_test(
            "Update Product",
            "PUT",
            f"products/{product_id}",
            200,
            data={
                "name": name,
                "vendor_id": vendor_id,
                "quantity": quantity,
                "purchase_price": purchase_price,
                "selling_price": selling_price
            }
        )

    def test_delete_product(self, product_id):
        """Test deleting a product (admin only)"""
        return self.run_test(
            "Delete Product (Admin Only)",
            "DELETE",
            f"products/{product_id}",
            200,
            admin_required=True
        )

    def test_create_sale(self, customer_id, items):
        """Test creating a sale"""
        success, response = self.run_test(
            "Create Sale",
            "POST",
            "sales",
            200,
            data={
                "customer_id": customer_id,
                "items": items
            }
        )
        if success and 'id' in response:
            self.created_ids["sale"] = response['id']
        return success, response

    def test_get_sales(self):
        """Test getting all sales"""
        return self.run_test(
            "Get All Sales",
            "GET",
            "sales",
            200
        )

    def test_get_stock(self):
        """Test getting stock information"""
        return self.run_test(
            "Get Stock Information",
            "GET",
            "stock",
            200
        )

    def test_get_dashboard_stats(self):
        """Test getting dashboard statistics"""
        return self.run_test(
            "Get Dashboard Statistics",
            "GET",
            "dashboard/stats",
            200
        )

    def test_get_company_details(self):
        """Test getting company details"""
        return self.run_test(
            "Get Company Details",
            "GET",
            "company",
            200
        )

    def test_update_company_details(self, name, address, phone=None, email=None, tax_number=None):
        """Test updating company details (admin only)"""
        return self.run_test(
            "Update Company Details (Admin Only)",
            "PUT",
            "company",
            200,
            data={
                "name": name,
                "address": address,
                "phone": phone,
                "email": email,
                "tax_number": tax_number
            },
            admin_required=True
        )

    def test_role_based_access(self):
        """Test role-based access control"""
        print("\n🔍 Testing Role-Based Access Control...")
        
        # Test user trying to delete a vendor (should fail)
        success, _ = self.run_test(
            "User Trying to Delete Vendor (Should Fail)",
            "DELETE",
            f"vendors/{self.created_ids['vendor']}",
            403,
            token=self.user_token
        )
        
        # Test user trying to update company details (should fail)
        success, _ = self.run_test(
            "User Trying to Update Company Details (Should Fail)",
            "PUT",
            "company",
            403,
            data={
                "name": "Test Company",
                "address": "Test Address"
            },
            token=self.user_token
        )
        
        return True

def main():
    # Setup
    tester = DashboardAPITester()
    timestamp = datetime.now().strftime('%H%M%S')
    
    print("=" * 50)
    print("DASHBOARD API TESTING")
    print("=" * 50)
    
    # Test admin login
    if not tester.test_login("admin", "admin123", is_admin=True):
        print("❌ Admin login failed, stopping tests")
        return 1
    
    # Test getting current user info
    tester.test_get_current_user()
    
    # Test vendor operations
    success, vendor_response = tester.test_create_vendor(
        f"Test Vendor {timestamp}",
        "123 Test St",
        "1234567890"
    )
    if not success:
        print("❌ Vendor creation failed")
    
    tester.test_get_vendors()
    
    if tester.created_ids["vendor"]:
        tester.test_update_vendor(
            tester.created_ids["vendor"],
            f"Updated Vendor {timestamp}",
            "456 Test Ave",
            "0987654321"
        )
    
    # Test customer operations
    success, customer_response = tester.test_create_customer(
        f"Test Customer {timestamp}",
        "789 Test Blvd",
        "1122334455"
    )
    if not success:
        print("❌ Customer creation failed")
    
    tester.test_get_customers()
    
    if tester.created_ids["customer"]:
        tester.test_update_customer(
            tester.created_ids["customer"],
            f"Updated Customer {timestamp}",
            "321 Test Dr",
            "5544332211"
        )
    
    # Test product operations
    if tester.created_ids["vendor"]:
        success, product_response = tester.test_create_product(
            f"Test Product {timestamp}",
            tester.created_ids["vendor"],
            100,
            50.0,
            75.0
        )
        if not success:
            print("❌ Product creation failed")
    
    tester.test_get_products()
    
    if tester.created_ids["product"] and tester.created_ids["vendor"]:
        tester.test_update_product(
            tester.created_ids["product"],
            f"Updated Product {timestamp}",
            tester.created_ids["vendor"],
            90,
            55.0,
            80.0
        )
    
    # Test sale operations
    if tester.created_ids["product"] and tester.created_ids["customer"]:
        # Get product details first
        _, products_response = tester.test_get_products()
        product = None
        
        if isinstance(products_response, list):
            for p in products_response:
                if p["id"] == tester.created_ids["product"]:
                    product = p
                    break
        
        if product:
            sale_items = [{
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": 5,
                "selling_price": product["selling_price"],
                "total_amount": 5 * product["selling_price"]
            }]
            
            tester.test_create_sale(
                tester.created_ids["customer"],
                sale_items
            )
    
    tester.test_get_sales()
    
    # Test stock and dashboard
    tester.test_get_stock()
    tester.test_get_dashboard_stats()
    
    # Test company details
    tester.test_get_company_details()
    tester.test_update_company_details(
        f"Test Company {timestamp}",
        "999 Test Ln",
        "9876543210",
        "test@example.com",
        "TAX123456"
    )
    
    # Test user login and role-based access
    tester.test_login("user", "user123")
    tester.test_role_based_access()
    
    # Test deletion operations (admin only)
    # Login as admin again
    tester.test_login("admin", "admin123", is_admin=True)
    
    # Delete resources in reverse order of creation
    if tester.created_ids["product"]:
        tester.test_delete_product(tester.created_ids["product"])
    
    if tester.created_ids["customer"]:
        tester.test_delete_customer(tester.created_ids["customer"])
    
    if tester.created_ids["vendor"]:
        tester.test_delete_vendor(tester.created_ids["vendor"])
    
    # Print results
    print("\n" + "=" * 50)
    print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print("=" * 50)
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
