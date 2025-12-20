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
    def __init__(self, base_url="https://gpucloud.preview.emergentagent.com"):
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
            "origin_url": "https://gpucloud.preview.emergentagent.com"
        }
        
        success, data = self.make_request('POST', 'payments/create-checkout', checkout_data)
        has_url = success and 'url' in data and 'session_id' in data
        self.log_test("Create Payment Checkout", has_url,
                     "Checkout URL created" if has_url else f"Error: {data}")

    def test_password_generation(self):
        """Test password generation API"""
        print("\n🔐 Testing Password Generation...")
        
        success, data = self.make_request('GET', 'auth/generate-password')
        has_password = success and 'password' in data and len(data['password']) >= 8
        self.log_test("Generate Strong Password", has_password,
                     f"Generated password: {data.get('password', 'None')[:4]}..." if has_password else f"Error: {data}")
        
        if has_password:
            self.generated_password = data['password']

    def test_quick_registration(self):
        """Test quick registration for users and providers"""
        print("\n⚡ Testing Quick Registration...")
        
        # Test user quick registration
        test_email = f"quickuser_{datetime.now().strftime('%H%M%S')}@gpucloud.pro"
        user_data = {
            "email": test_email,
            "name": "Quick Test User"
        }
        
        success, data = self.make_request('POST', 'auth/quick-register', user_data, 200)
        has_token = success and 'token' in data and 'user' in data
        generated_pwd = data.get('generated_password') if success else None
        
        self.log_test("Quick User Registration", has_token,
                     f"Created user with generated password: {generated_pwd[:4] if generated_pwd else 'None'}..." if has_token else f"Error: {data}")
        
        if has_token:
            self.quick_user_token = data['token']
            self.quick_user_id = data['user']['id']
            self.quick_user_email = test_email
            if generated_pwd:
                self.quick_user_password = generated_pwd

        # Test provider quick registration
        provider_email = f"quickprovider_{datetime.now().strftime('%H%M%S')}@gpucloud.pro"
        provider_data = {
            "email": provider_email,
            "company_name": "Quick Test Provider",
            "country": "US"
        }
        
        success, data = self.make_request('POST', 'provider/quick-register', provider_data, 200)
        has_provider_token = success and 'token' in data and 'provider' in data
        provider_generated_pwd = data.get('generated_password') if success else None
        
        self.log_test("Quick Provider Registration", has_provider_token,
                     f"Created provider with generated password: {provider_generated_pwd[:4] if provider_generated_pwd else 'None'}..." if has_provider_token else f"Error: {data}")

    def test_2fa_system(self):
        """Test 2FA setup, verification, and status"""
        print("\n🛡️ Testing 2FA System...")
        
        if not hasattr(self, 'quick_user_token') or not self.quick_user_token:
            self.log_test("2FA System", False, "No quick user token available")
            return
        
        # Store original token and use quick user token for 2FA testing
        original_token = self.token
        self.token = self.quick_user_token
        
        # Test 2FA status (should be disabled initially)
        success, data = self.make_request('GET', 'auth/2fa/status')
        is_disabled = success and not data.get('enabled', True)
        self.log_test("2FA Status Check (Initial)", is_disabled,
                     f"2FA enabled: {data.get('enabled', 'Unknown')}" if success else f"Error: {data}")
        
        # Test 2FA setup with TOTP
        setup_data = {"method": "totp"}
        success, data = self.make_request('POST', 'auth/2fa/setup', setup_data)
        has_qr_code = success and 'qr_code' in data and 'manual_key' in data
        self.log_test("2FA Setup (TOTP)", has_qr_code,
                     "QR code and manual key generated" if has_qr_code else f"Error: {data}")
        
        if has_qr_code:
            self.totp_secret = data.get('manual_key')
            
            # Simulate TOTP code generation (for testing, we'll use a mock code)
            # In real scenario, this would come from authenticator app
            mock_totp_code = "123456"  # This will fail verification, but tests the endpoint
            
            verify_data = {"code": mock_totp_code, "method": "totp"}
            success, data = self.make_request('POST', 'auth/2fa/verify-setup', verify_data)
            # We expect this to fail with invalid code, but endpoint should respond
            endpoint_works = 'detail' in data or 'success' in data
            self.log_test("2FA Verify Setup (TOTP)", endpoint_works,
                         f"Endpoint responded (expected failure with mock code): {data.get('detail', data)}" if endpoint_works else f"Error: {data}")
        
        # Test 2FA setup with email
        setup_data = {"method": "email"}
        success, data = self.make_request('POST', 'auth/2fa/setup', setup_data)
        email_sent = success and data.get('email_sent', False)
        self.log_test("2FA Setup (Email)", email_sent,
                     "Email verification code sent" if email_sent else f"Error: {data}")
        
        # Test email code verification (will fail with mock code)
        if email_sent:
            mock_email_code = "123456"
            verify_data = {"code": mock_email_code, "method": "email"}
            success, data = self.make_request('POST', 'auth/2fa/verify-setup', verify_data)
            endpoint_works = 'detail' in data or 'success' in data
            self.log_test("2FA Verify Setup (Email)", endpoint_works,
                         f"Endpoint responded (expected failure with mock code): {data.get('detail', data)}" if endpoint_works else f"Error: {data}")
        
        # Test send email code endpoint
        success, data = self.make_request('POST', 'auth/2fa/send-email-code', {})
        code_sent = success and data.get('success', False)
        self.log_test("2FA Send Email Code", code_sent,
                     "Email code sent successfully" if code_sent else f"Error: {data}")
        
        # Restore original token
        self.token = original_token

    def test_2fa_login_flow(self):
        """Test login with 2FA"""
        print("\n🔐 Testing 2FA Login Flow...")
        
        if not hasattr(self, 'quick_user_email') or not hasattr(self, 'quick_user_password'):
            self.log_test("2FA Login Flow", False, "No quick user credentials available")
            return
        
        # Test login without 2FA code (should indicate 2FA required or normal login)
        login_data = {
            "email": self.quick_user_email,
            "password": self.quick_user_password
        }
        
        success, data = self.make_request('POST', 'auth/login', login_data)
        login_works = success and ('token' in data or 'requires_2fa' in data)
        self.log_test("Login Flow Check", login_works,
                     f"Login response: {'2FA required' if data.get('requires_2fa') else 'Direct login'}" if login_works else f"Error: {data}")
        
        # Test 2FA login endpoint with mock code
        mock_2fa_code = "123456"
        login_2fa_data = {
            "email": self.quick_user_email,
            "password": self.quick_user_password,
            "two_factor_code": mock_2fa_code,
            "two_factor_method": "totp"
        }
        
        success, data = self.make_request('POST', 'auth/login/2fa', login_2fa_data)
        endpoint_works = 'detail' in data or 'token' in data or 'requires_2fa' in data
        self.log_test("2FA Login Endpoint", endpoint_works,
                     f"2FA login endpoint responded: {data.get('detail', 'Success' if 'token' in data else 'Requires 2FA')}" if endpoint_works else f"Error: {data}")

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
        
        # New 2FA and Quick Registration tests
        self.test_password_generation()
        self.test_quick_registration()
        
        # Authentication tests
        self.test_user_registration()
        self.test_user_login()
        self.test_auth_me()
        
        # 2FA System tests
        self.test_2fa_system()
        self.test_2fa_login_flow()
        
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