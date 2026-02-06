#!/usr/bin/env python3
"""Test script to debug the upload issue."""

import requests
import os
from src.ui_utils import APIClient

def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Health check status: {response.status_code}")
        if response.status_code == 200:
            print(f"Health check response: {response.json()}")
            return True
        else:
            print(f"Health check failed: {response.text}")
            return False
    except Exception as e:
        print(f"Health check error: {e}")
        return False

def test_upload_with_requests():
    """Test upload directly with requests library."""
    print("\nTesting upload with requests library...")
    
    # Create a simple test PDF content
    test_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
    
    try:
        files = {"file": ("test.pdf", test_pdf_content, "application/pdf")}
        response = requests.post(
            "http://localhost:8000/upload",
            files=files,
            timeout=30
        )
        
        print(f"Upload status: {response.status_code}")
        print(f"Upload headers: {dict(response.headers)}")
        print(f"Upload response: {response.text}")
        
        return response.status_code == 201
        
    except Exception as e:
        print(f"Upload error: {e}")
        return False

def test_upload_with_api_client():
    """Test upload with APIClient."""
    print("\nTesting upload with APIClient...")
    
    # Create a simple test PDF content
    test_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
    
    try:
        client = APIClient()
        result = client.upload_document("test.pdf", test_pdf_content)
        
        print(f"APIClient result: {result}")
        return result["success"]
        
    except Exception as e:
        print(f"APIClient error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("Testing Document Upload Functionality")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_health_check():
        print("❌ Health check failed. Make sure FastAPI server is running.")
        return
    
    print("✅ Health check passed")
    
    # Test 2: Direct requests upload
    if test_upload_with_requests():
        print("✅ Direct requests upload passed")
    else:
        print("❌ Direct requests upload failed")
    
    # Test 3: APIClient upload
    if test_upload_with_api_client():
        print("✅ APIClient upload passed")
    else:
        print("❌ APIClient upload failed")
    
    print("\n" + "=" * 50)
    print("Test completed")

if __name__ == "__main__":
    main()