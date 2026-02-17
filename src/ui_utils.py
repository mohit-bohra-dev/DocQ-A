"""Utility functions for the Streamlit UI."""

import requests
import time
from typing import Dict, Optional
from datetime import datetime


class APIClient:
    """Client for interacting with the FastAPI backend."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "DocumentQA-StreamlitUI/1.0"
        })
    
    def check_health(self, timeout: int = 5) -> Dict:
        """Check the health of the FastAPI backend."""
        try:
            response = self.session.get(
                f"{self.base_url}/health", 
                timeout=timeout
            )
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False, 
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except requests.exceptions.ConnectionError:
            return {
                "success": False, 
                "error": "Cannot connect to backend server. Is it running?"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False, 
                "error": "Backend server is not responding (timeout)"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False, 
                "error": f"Network error: {str(e)}"
            }
    
    def upload_document(self, file_name: str, file_content: bytes, replace_existing: bool = False, timeout: int = 60) -> Dict:
        """Upload a document to the backend."""
        try:
            # Validate inputs
            if not file_name:
                return {"success": False, "error": "File name is required"}
            
            if not file_content:
                return {"success": False, "error": "File content is empty"}
            
            # Prepare the multipart form data
            files = {"file": (file_name, file_content, "application/pdf")}
            data = {"replace_existing": str(replace_existing).lower()}
            
            # Make the request without Content-Type header (let requests handle it)
            response = requests.post(
                f"{self.base_url}/upload", 
                files=files,
                data=data,
                timeout=timeout,
                headers={"User-Agent": "DocumentQA-StreamlitUI/1.0"}
            )
            
            # Debug: Print response details
            print(f"Upload response status: {response.status_code}")
            print(f"Upload response headers: {dict(response.headers)}")
            
            if response.status_code == 201:
                return {"success": True, "data": response.json()}
            elif response.status_code == 409:
                # Document already exists
                error_data = self._parse_error_response(response)
                return {"success": False, "error": error_data, "duplicate": True}
            else:
                # Get detailed error information
                error_data = self._parse_error_response(response)
                print(f"Upload error response: {response.text}")
                return {"success": False, "error": error_data}
                
        except requests.exceptions.Timeout:
            return {
                "success": False, 
                "error": "Upload timed out. The file might be too large or the server is busy."
            }
        except requests.exceptions.RequestException as e:
            print(f"Upload request exception: {e}")
            return {"success": False, "error": f"Upload failed: {str(e)}"}
        except Exception as e:
            print(f"Unexpected upload error: {e}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def list_documents(self, timeout: int = 5) -> Dict:
        """Get list of all documents from the backend."""
        try:
            response = self.session.get(
                f"{self.base_url}/documents",
                timeout=timeout
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                error_data = self._parse_error_response(response)
                return {"success": False, "error": error_data}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to list documents: {str(e)}"}
    
    def delete_document(self, document_name: str, timeout: int = 10) -> Dict:
        """Delete a document from the backend."""
        try:
            response = self.session.delete(
                f"{self.base_url}/documents/{document_name}",
                timeout=timeout
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                error_data = self._parse_error_response(response)
                return {"success": False, "error": error_data}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to delete document: {str(e)}"}
    
    def query_documents(self, question: str, top_k: int = 5, timeout: int = 30) -> Dict:
        """Query documents via the backend."""
        try:
            payload = {"question": question, "top_k": top_k}
            response = self.session.post(
                f"{self.base_url}/query", 
                json=payload, 
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                error_data = self._parse_error_response(response)
                return {"success": False, "error": error_data}
        except requests.exceptions.Timeout:
            return {
                "success": False, 
                "error": "Query timed out. Please try a simpler question or try again later."
            }
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Query failed: {str(e)}"}
    
    def _parse_error_response(self, response: requests.Response) -> str:
        """Parse error response from the API."""
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                error_data = response.json()
                return error_data.get("detail", f"HTTP {response.status_code}")
            else:
                return f"HTTP {response.status_code}: {response.text[:200]}"
        except Exception:
            return f"HTTP {response.status_code}: Unable to parse error response"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def format_timestamp(timestamp: datetime) -> str:
    """Format timestamp for display."""
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 0:
        return timestamp.strftime("%Y-%m-%d %H:%M")
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def clean_document_name(doc_name: str) -> str:
    """Clean document name for display (remove UUID prefix if present)."""
    if "_" in doc_name:
        parts = doc_name.split("_", 1)
        if len(parts) > 1:
            return parts[1]
    return doc_name


def validate_pdf_file(file_content: bytes) -> Dict:
    """Validate PDF file content."""
    if not file_content:
        return {"valid": False, "error": "File is empty"}
    
    # Check PDF header
    if not file_content.startswith(b"%PDF-"):
        return {"valid": False, "error": "File is not a valid PDF"}
    
    # Check minimum size (PDF header + some content)
    if len(file_content) < 100:
        return {"valid": False, "error": "File appears to be corrupted or incomplete"}
    
    return {"valid": True}


class HealthChecker:
    """Health checker with caching to avoid excessive API calls."""
    
    def __init__(self, cache_duration: int = 30):
        self.cache_duration = cache_duration
        self.last_check_time: Optional[float] = None
        self.last_result: Optional[Dict] = None
        self.api_client = APIClient()
    
    def get_health_status(self, force_refresh: bool = False) -> Dict:
        """Get health status with caching."""
        current_time = time.time()
        
        # Return cached result if available and not expired
        if (not force_refresh and 
            self.last_check_time is not None and 
            self.last_result is not None and
            current_time - self.last_check_time < self.cache_duration):
            return self.last_result
        
        # Perform new health check
        result = self.api_client.check_health()
        self.last_check_time = current_time
        self.last_result = result
        
        return result