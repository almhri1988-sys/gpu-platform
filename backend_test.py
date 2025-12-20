#!/usr/bin/env python3
"""
GPU Cloud Pro Backend API Testing
Tests all critical API endpoints for the GPU rental marketplace
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional

class GPUCloudAPITester:
    def __init__(self, base_url="https://gpucloud-share.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = "", response_data: Dict = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED - {details}")
            self.failed_tests.append({"test": name, "error": details, "response": response_data})
        
        self.test_results.append({
            "test_name": name,
            "status": "PASSED" if success else "FAILED",
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def make_request(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> tuple:
        """Make HTTP request and return success status and response"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}

            return success, response_data

        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}

    def test_health_check(self):
        """Test basic health endpoints"""
        print("\n🔍 Testing Health Endpoints...")
        
        # Test root endpoint
        success, data = self.make_request('GET', '')
        self.log_test("API Root Endpoint", success, 
                     "" if success else f"Status: {data.get('status_code', 'Unknown')}")
        
        # Test health endpoint
        success, data = self.make_request('GET', 'health')
        self.log_test("Health Check Endpoint", success,
                     "" if success else f"Status: {data.get('status_code', 'Unknown')}")

    def test_seed_data(self):
        """Test data seeding"""
        print("\n🌱 Testing Data Seeding...")
        
        success, data = self.make_request('POST', 'seed')
        # Seeding can return 200 (success) or already seeded message
        is_success = success or (data.get('message') == 'Data already seeded')
        self.log_test("Seed Data", is_success,
                     "" if is_success else f"Error: {data}")

    def test_user_registration(self):
        """Test user registration"""
        print("\n👤 Testing User Registration...")
        
        # Test with new user
        test_email = f"test_{datetime.now().strftime('%H%M%S')}@gpucloud.pro"
        user_data = {
            "email": test_email,
            "password": "test123",
            "name": "Test User"
        }
        
        success, data = self.make_request('POST', 'auth/register', user_data, 200)
        if success and 'token' in data:
            self.token = data['token']
            self.user_id = data['user']['id']
        
        self.log_test("User Registration", success,
                     "" if success else f"Error: {data}")

    def test_user_login(self):
        """Test user login with existing test user"""
        print("\n🔐 Testing User Login...")
        
        login_data = {
            "email": "test@gpucloud.pro",
            "password": "test123"
        }
        
        success, data = self.make_request('POST', 'auth/login', login_data, 200)
        if success and 'token' in data:
            self.token = data['token']
            self.user_id = data['user']['id']
        
        self.log_test("User Login", success,
                     "" if success else f"Error: {data}")

    def test_auth_me(self):
        """Test getting current user info"""
        print("\n👤 Testing Auth Me...")
        
        if not self.token:
            self.log_test("Auth Me", False, "No token available")
            return
        
        success, data = self.make_request('GET', 'auth/me')
        self.log_test("Get Current User", success,
                     "" if success else f"Error: {data}")

    def test_gpu_marketplace(self):
        """Test GPU marketplace endpoints"""
        print("\n🖥️ Testing GPU Marketplace...")
        
        # Test get all GPUs
        success, data = self.make_request('GET', 'gpus')
        gpu_count = len(data) if success and isinstance(data, list) else 0
        self.log_test("Get All GPUs", success and gpu_count > 0,
                     f"Found {gpu_count} GPUs" if success else f"Error: {data}")
        
        # Test get GPUs by region
        success, data = self.make_request('GET', 'gpus?region=US East')
        region_gpu_count = len(data) if success and isinstance(data, list) else 0
        self.log_test("Get GPUs by Region", success,
                     f"Found {region_gpu_count} GPUs in US East" if success else f"Error: {data}")
        
        # Test get GPUs by model
        success, data = self.make_request('GET', 'gpus?model=RTX 4090')
        model_gpu_count = len(data) if success and isinstance(data, list) else 0
        self.log_test("Get GPUs by Model", success,
                     f"Found {model_gpu_count} RTX 4090 GPUs" if success else f"Error: {data}")
        
        # Store first GPU for instance testing
        if success and isinstance(data, list) and len(data) > 0:
            self.test_gpu_id = data[0]['id']
            self.test_gpu_price = data[0]['price_per_hour']

    def test_regions(self):
        """Test regions endpoint"""
        print("\n🌍 Testing Regions...")
        
        success, data = self.make_request('GET', 'regions')
        region_count = len(data) if success and isinstance(data, list) else 0
        self.log_test("Get Regions", success and region_count > 0,
                     f"Found {region_count} regions" if success else f"Error: {data}")

    def test_instance_management(self):
        """Test GPU instance start/stop"""
        print("\n⚡ Testing Instance Management...")
        
        if not hasattr(self, 'test_gpu_id'):
            self.log_test("Instance Management", False, "No GPU available for testing")
            return
        
        if not self.token:
            self.log_test("Instance Management", False, "No authentication token")
            return
        
        # First check user balance and add funds if needed
        success, user_data = self.make_request('GET', 'auth/me')
        if success and user_data.get('balance', 0) < self.test_gpu_price:
            print(f"⚠️ Insufficient balance (${user_data.get('balance', 0):.2f}), need ${self.test_gpu_price:.2f}")
            self.log_test("Start Instance", False, f"Insufficient balance: ${user_data.get('balance', 0):.2f} < ${self.test_gpu_price:.2f}")
            return
        
        # Test start instance
        instance_data = {"gpu_id": self.test_gpu_id}
        success, data = self.make_request('POST', 'instances/start', instance_data, 200)
        
        if success and 'id' in data:
            instance_id = data['id']
            self.log_test("Start Instance", True, f"Started instance {instance_id}")
            
            # Test get active instances
            success, active_data = self.make_request('GET', 'instances/active')
            active_count = len(active_data) if success and isinstance(active_data, list) else 0
            self.log_test("Get Active Instances", success and active_count > 0,
                         f"Found {active_count} active instances" if success else f"Error: {active_data}")
            
            # Test stop instance
            success, stop_data = self.make_request('POST', f'instances/{instance_id}/stop', {})
            self.log_test("Stop Instance", success,
                         f"Stopped with cost: ${stop_data.get('total_cost', 0):.4f}" if success else f"Error: {stop_data}")
        else:
            self.log_test("Start Instance", False, f"Error: {data}")

    def test_billing_endpoints(self):
        """Test billing and transaction endpoints"""
        print("\n💰 Testing Billing...")
        
        if not self.token:
            self.log_test("Billing Endpoints", False, "No authentication token")
            return
        
        # Test get transactions
        success, data = self.make_request('GET', 'billing/transactions')
        transaction_count = len(data) if success and isinstance(data, list) else 0
        self.log_test("Get Transactions", success,
                     f"Found {transaction_count} transactions" if success else f"Error: {data}")
        
        # Test get invoices
        success, data = self.make_request('GET', 'billing/invoices')
        invoice_count = len(data) if success and isinstance(data, list) else 0
        self.log_test("Get Invoices", success,
                     f"Found {invoice_count} invoices" if success else f"Error: {data}")

    def test_payment_checkout(self):
        """Test payment checkout creation"""
        print("\n💳 Testing Payment Checkout...")
        
        if not self.token:
            self.log_test("Payment Checkout", False, "No authentication token")
            return
        
        checkout_data = {
            "amount": 10.0,
            "origin_url": "https://gpucloud-share.preview.emergentagent.com"
        }
        
        success, data = self.make_request('POST', 'payments/create-checkout', checkout_data)
        has_url = success and 'url' in data and 'session_id' in data
        self.log_test("Create Payment Checkout", has_url,
                     "Checkout URL created" if has_url else f"Error: {data}")

    def test_all_instances(self):
        """Test get all instances"""
        print("\n📋 Testing All Instances...")
        
        if not self.token:
            self.log_test("All Instances", False, "No authentication token")
            return
        
        success, data = self.make_request('GET', 'instances')
        instance_count = len(data) if success and isinstance(data, list) else 0
        self.log_test("Get All Instances", success,
                     f"Found {instance_count} total instances" if success else f"Error: {data}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting GPU Cloud Pro API Tests...")
        print(f"Testing against: {self.base_url}")
        
        # Core functionality tests
        self.test_health_check()
        self.test_seed_data()
        
        # Authentication tests
        self.test_user_registration()
        self.test_user_login()
        self.test_auth_me()
        
        # Marketplace tests
        self.test_gpu_marketplace()
        self.test_regions()
        
        # Instance management tests
        self.test_instance_management()
        self.test_all_instances()
        
        # Billing tests
        self.test_billing_endpoints()
        self.test_payment_checkout()
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for failure in self.failed_tests:
                print(f"  - {failure['test']}: {failure['error']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = GPUCloudAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    results = {
        "timestamp": datetime.now().isoformat(),
        "base_url": tester.base_url,
        "summary": {
            "tests_run": tester.tests_run,
            "tests_passed": tester.tests_passed,
            "tests_failed": len(tester.failed_tests),
            "success_rate": round(tester.tests_passed/tester.tests_run*100, 1) if tester.tests_run > 0 else 0
        },
        "test_results": tester.test_results,
        "failed_tests": tester.failed_tests
    }
    
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend_test_results.json")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())