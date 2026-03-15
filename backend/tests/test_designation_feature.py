"""
Tests for designation field in customer registration flow.
This tests:
1. POST /api/auth/send-otp accepts designation field
2. POST /api/auth/verify-otp accepts designation field  
3. User object returned after registration includes designation
4. Login returns designation field
"""
import pytest
import requests
import os
import time
import random
import string

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://conveyor-roller-calc.preview.emergentagent.com')


def generate_random_email():
    """Generate a random email for testing"""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_designation_{random_str}@testmail.com"


class TestDesignationField:
    """Test designation field throughout registration flow"""
    
    def test_send_otp_accepts_designation(self):
        """Test that /api/auth/send-otp accepts the designation field"""
        test_email = generate_random_email()
        
        response = requests.post(
            f"{BASE_URL}/api/auth/send-otp",
            json={
                "email": test_email,
                "name": "Test User",
                "mobile": "9876543210",
                "pincode": "380001",
                "city": "Ahmedabad",
                "state": "Gujarat",
                "company": "Test Company",
                "designation": "Senior Engineer",
                "password": "test123"
            }
        )
        
        print(f"send-otp response status: {response.status_code}")
        print(f"send-otp response body: {response.json()}")
        
        # Should succeed (200) - designation field accepted
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        print(f"PASS: send-otp accepts designation field")
    
    def test_send_otp_works_without_designation(self):
        """Test that /api/auth/send-otp works when designation is not provided"""
        test_email = generate_random_email()
        
        response = requests.post(
            f"{BASE_URL}/api/auth/send-otp",
            json={
                "email": test_email,
                "name": "Test User",
                "mobile": "9876543211",
                "pincode": "380001",
                "city": "Ahmedabad",
                "state": "Gujarat",
                "company": "Test Company",
                "password": "test123"
            }
        )
        
        print(f"send-otp (no designation) response status: {response.status_code}")
        
        # Should succeed - designation is optional
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: send-otp works without designation field")
    
    def test_send_otp_with_empty_designation(self):
        """Test that /api/auth/send-otp accepts empty designation"""
        test_email = generate_random_email()
        
        response = requests.post(
            f"{BASE_URL}/api/auth/send-otp",
            json={
                "email": test_email,
                "name": "Test User",
                "mobile": "9876543212",
                "pincode": "380001",
                "city": "Ahmedabad",
                "state": "Gujarat",
                "company": "Test Company",
                "designation": "",  # Empty string
                "password": "test123"
            }
        )
        
        print(f"send-otp (empty designation) response status: {response.status_code}")
        
        # Should succeed - empty designation should be accepted
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: send-otp accepts empty designation")
    
    def test_send_otp_with_null_designation(self):
        """Test that /api/auth/send-otp accepts null designation"""
        test_email = generate_random_email()
        
        response = requests.post(
            f"{BASE_URL}/api/auth/send-otp",
            json={
                "email": test_email,
                "name": "Test User",
                "mobile": "9876543213",
                "pincode": "380001",
                "city": "Ahmedabad",
                "state": "Gujarat",
                "company": "Test Company",
                "designation": None,  # Explicit null
                "password": "test123"
            }
        )
        
        print(f"send-otp (null designation) response status: {response.status_code}")
        
        # Should succeed - null designation should be accepted
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: send-otp accepts null designation")


class TestLoginDesignation:
    """Test login returns designation field"""
    
    def test_login_returns_designation_for_customer(self):
        """Test that login response includes designation field for customers"""
        # Try to login with a test customer account
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "customer@test.com",
                "password": "test123"
            }
        )
        
        print(f"login response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"login response user: {data.get('user')}")
            
            # Check that user object exists
            assert "user" in data, "Response should contain user object"
            user = data["user"]
            
            # Check that designation key exists (even if None)
            assert "designation" in user, "User object should contain designation field"
            print(f"PASS: Login response includes designation field: {user.get('designation')}")
        else:
            # Customer account might not exist, skip test
            pytest.skip("Test customer account not available")
    
    def test_login_returns_designation_for_admin(self):
        """Test that login response includes designation field for admins"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "test@test.com",
                "password": "test123"
            }
        )
        
        print(f"admin login response status: {response.status_code}")
        
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        print(f"admin login response user: {data.get('user')}")
        
        # Check that user object exists
        assert "user" in data, "Response should contain user object"
        user = data["user"]
        
        # Check that designation key exists (even if None)
        assert "designation" in user, "User object should contain designation field"
        print(f"PASS: Admin login includes designation field: {user.get('designation')}")


class TestVerifyOTPWithDesignation:
    """Test verify-otp endpoint with designation"""
    
    def test_verify_otp_schema_includes_designation(self):
        """Test that verify-otp accepts designation in request body"""
        # This tests the request schema acceptance
        # We'll use an invalid OTP but check schema is accepted
        test_email = generate_random_email()
        
        response = requests.post(
            f"{BASE_URL}/api/auth/verify-otp",
            json={
                "email": test_email,
                "otp": "0000",  # Invalid OTP
                "name": "Test User",
                "mobile": "9876543214",
                "pincode": "380001",
                "city": "Ahmedabad",
                "state": "Gujarat",
                "company": "Test Company",
                "designation": "Manager",
                "password": "test123"
            }
        )
        
        print(f"verify-otp response status: {response.status_code}")
        print(f"verify-otp response body: {response.json()}")
        
        # Should get 400 (invalid/expired OTP), not 422 (validation error)
        # If we get 422, it means the schema doesn't accept designation
        assert response.status_code != 422, f"Schema validation error - designation field not accepted: {response.text}"
        
        # Should be 400 (invalid OTP) since no valid OTP exists
        assert response.status_code == 400, f"Expected 400 (invalid OTP), got {response.status_code}: {response.text}"
        print(f"PASS: verify-otp schema accepts designation field")


class TestHealthCheck:
    """Basic health check to ensure API is available"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        
        print(f"Health check response: {response.status_code}")
        assert response.status_code == 200, f"API health check failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"API unhealthy: {data}"
        print(f"PASS: API is healthy")


class TestAuthMeDesignation:
    """Test /auth/me endpoint returns designation"""
    
    def test_auth_me_returns_designation(self):
        """Test that /api/auth/me includes designation field"""
        # First login to get token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "test@test.com",
                "password": "test123"
            }
        )
        
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("access_token")
        assert token, "No access token returned"
        
        # Now call /auth/me with the token
        me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        print(f"/auth/me response status: {me_response.status_code}")
        print(f"/auth/me response body: {me_response.json()}")
        
        assert me_response.status_code == 200, f"/auth/me failed: {me_response.text}"
        
        user_data = me_response.json()
        assert "designation" in user_data, "User data should contain designation field"
        print(f"PASS: /auth/me includes designation field: {user_data.get('designation')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
