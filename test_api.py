#!/usr/bin/env python3
"""
Test script for the MedGemma Health Agent
"""
import requests
import json
import time

def test_health_agent(base_url="http://localhost:8000"):
    """Test the health agent endpoints"""
    
    print("🧪 Testing MedGemma Health Agent")
    print(f"Base URL: {base_url}")
    
    # Test 1: Health check endpoint
    print("\n1. Testing health check endpoint...")
    try:
        response = requests.get(f"{base_url}/health-check", timeout=10)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test 2: Simple medical query
    print("\n2. Testing medical query...")
    test_query = {
        "query": "What are the common symptoms of diabetes?",
        "max_tokens": 256
    }
    
    try:
        print(f"   Query: {test_query['query']}")
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/health",
            json=test_query,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Medical query successful")
            print(f"   Response time: {response_time:.2f} seconds")
            print(f"   Response preview: {result['response'][:100]}...")
        else:
            print(f"❌ Medical query failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Medical query error: {e}")
        return False
    
    # Test 3: Invalid request
    print("\n3. Testing error handling...")
    try:
        response = requests.post(
            f"{base_url}/health",
            json={"invalid": "request"},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 400:
            print("✅ Error handling working correctly")
            print(f"   Error response: {response.json()}")
        else:
            print(f"⚠️  Unexpected response for invalid request: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
    
    print("\n🎉 All tests completed!")
    return True

if __name__ == "__main__":
    success = test_health_agent()
    exit(0 if success else 1)

# Deploy with docker on Linux:
