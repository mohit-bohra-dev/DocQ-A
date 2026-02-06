#!/usr/bin/env python3
"""Debug upload issue by comparing with working curl command."""

import requests
import io
from src.ui_utils import APIClient

def test_with_curl_equivalent():
    """Test upload using the exact same approach as the working curl command."""
    print("Testing upload with curl-equivalent approach...")
    
    # Create a minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000074 00000 n 
0000000120 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
179
%%EOF"""
    
    try:
        # This mimics the curl command exactly
        files = {
            'file': ('test.pdf', pdf_content, 'application/pdf')
        }
        
        headers = {
            'accept': 'application/json',
            # Don't set Content-Type - let requests handle it
        }
        
        response = requests.post(
            'http://localhost:8000/upload',
            files=files,
            headers=headers,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 201:
            print("✅ Upload successful!")
            return True
        else:
            print("❌ Upload failed!")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return False

def test_api_client_debug():
    """Test APIClient with detailed debugging."""
    print("\nTesting APIClient with debugging...")
    
    # Create the same PDF content
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000074 00000 n 
0000000120 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
179
%%EOF"""
    
    try:
        client = APIClient()
        result = client.upload_document("test.pdf", pdf_content)
        
        print(f"APIClient Result: {result}")
        
        if result["success"]:
            print("✅ APIClient upload successful!")
            return True
        else:
            print("❌ APIClient upload failed!")
            return False
            
    except Exception as e:
        print(f"❌ APIClient exception: {e}")
        return False

def test_health_first():
    """Test health endpoint first."""
    print("Testing health endpoint...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Health Status: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"Health Data: {health_data}")
            return True
        else:
            print(f"Health failed: {response.text}")
            return False
    except Exception as e:
        print(f"Health check error: {e}")
        return False

def main():
    """Run debug tests."""
    print("=" * 60)
    print("DEBUG: Upload Issue Investigation")
    print("=" * 60)
    
    # Test 1: Health check
    if not test_health_first():
        print("❌ Cannot proceed - FastAPI server not responding")
        return
    
    print("✅ FastAPI server is responding")
    print("-" * 60)
    
    # Test 2: Curl equivalent
    test_with_curl_equivalent()
    print("-" * 60)
    
    # Test 3: APIClient
    test_api_client_debug()
    
    print("=" * 60)
    print("Debug tests completed")

if __name__ == "__main__":
    main()