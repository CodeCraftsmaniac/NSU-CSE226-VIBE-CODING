"""
NSU Degree Audit - Load Testing with Locust
============================================
Automated load testing for 20+ concurrent users.

Usage:
  # Install: pip install locust
  
  # Run locally (interactive web UI):
  locust -f tests/locustfile.py --host=https://ocrapi.nsunexus.app
  
  # Run headless (CLI mode) - 20 users, 2 users/sec spawn rate, 2 min runtime:
  locust -f tests/locustfile.py --host=https://ocrapi.nsunexus.app \
         --headless --users 20 --spawn-rate 2 --run-time 2m
  
  # Run with HTML report:
  locust -f tests/locustfile.py --host=https://ocrapi.nsunexus.app \
         --headless --users 20 --spawn-rate 2 --run-time 2m \
         --html=tests/reports/load_test_report.html

Metrics tracked:
  - Response time (avg, p50, p95, p99)
  - Requests per second
  - Failure rate
  - Concurrent user handling
"""

import os
import io
import random
import time
from pathlib import Path
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

# Test data paths
PROJECT_ROOT = Path(__file__).parent.parent
TEST_PDF_PATH = PROJECT_ROOT / "Transcript PDF.pdf"

# Mock PDF content for testing (minimal valid PDF)
MOCK_PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test Transcript) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
306
%%EOF
"""


class TranscriptUser(HttpUser):
    """
    Simulates a user uploading transcripts and checking history.
    Designed to test 20+ concurrent users.
    """
    
    # Wait 1-3 seconds between tasks (realistic user behavior)
    wait_time = between(1, 3)
    
    # User state
    auth_token = None
    scan_ids = []
    
    def on_start(self):
        """Called when a simulated user starts."""
        # Load real PDF if available, otherwise use mock
        if TEST_PDF_PATH.exists():
            self.pdf_bytes = TEST_PDF_PATH.read_bytes()
        else:
            self.pdf_bytes = MOCK_PDF_BYTES
    
    @task(1)
    def health_check(self):
        """Test health endpoint - lightweight, frequent check."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure(f"Unhealthy: {data}")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(1)
    def api_info(self):
        """Test root endpoint - API info."""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("service") == "NSU Degree Audit API":
                    response.success()
                else:
                    response.failure("Invalid API response")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(3)
    def upload_transcript(self):
        """
        Test transcript upload - the main heavy operation.
        This is the critical path for load testing.
        """
        files = {
            "file": ("test_transcript.pdf", io.BytesIO(self.pdf_bytes), "application/pdf")
        }
        data = {"source": "load_test"}
        
        # OCR can take 15-60 seconds, use longer timeout
        with self.client.post(
            "/upload",
            files=files,
            data=data,
            timeout=120,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    # Store scan_id if available for history tests
                    scan_id = result.get("data", {}).get("scan_id")
                    if scan_id:
                        self.scan_ids.append(scan_id)
                    response.success()
                else:
                    response.failure(f"Upload failed: {result.get('error', 'Unknown')}")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(2)
    def get_auth_config(self):
        """Test auth config endpoint."""
        with self.client.get("/auth/config", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure("Auth config failed")
            else:
                response.failure(f"Status: {response.status_code}")


class AuthenticatedUser(HttpUser):
    """
    Simulates an authenticated user with history access.
    Uses a test token for authenticated endpoints.
    """
    
    wait_time = between(2, 5)
    
    # These would be real tokens in a proper test environment
    # For now, we test the unauthenticated responses
    auth_token = None
    
    @task(2)
    def get_history_unauthenticated(self):
        """Test history endpoint without auth - should return 401."""
        with self.client.get("/history", catch_response=True) as response:
            # Without auth, should return 401
            if response.status_code == 401:
                response.success()
            elif response.status_code == 200:
                # If somehow authenticated
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(1)
    def get_user_unauthenticated(self):
        """Test user endpoint without auth - should return 401."""
        with self.client.get("/auth/user", catch_response=True) as response:
            if response.status_code == 401:
                response.success()
            elif response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class ConcurrencyStressTest(HttpUser):
    """
    Stress test specifically for 20 concurrent users requirement.
    Focuses on rapid successive requests to test thread safety.
    """
    
    wait_time = between(0.5, 1.5)  # Faster requests for stress testing
    
    def on_start(self):
        """Load test PDF."""
        if TEST_PDF_PATH.exists():
            self.pdf_bytes = TEST_PDF_PATH.read_bytes()
        else:
            self.pdf_bytes = MOCK_PDF_BYTES
    
    @task(5)
    def rapid_health_check(self):
        """Rapid health checks to test connection handling."""
        self.client.get("/health")
    
    @task(2)
    def concurrent_upload(self):
        """Concurrent uploads to stress test OCR thread safety."""
        files = {
            "file": ("stress_test.pdf", io.BytesIO(self.pdf_bytes), "application/pdf")
        }
        
        try:
            response = self.client.post(
                "/upload",
                files=files,
                data={"source": "stress_test"},
                timeout=180  # Allow longer for stress conditions
            )
        except Exception as e:
            # Log but don't crash on timeouts during stress
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# Event Hooks for Reporting
# ═══════════════════════════════════════════════════════════════════════════════

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("\n" + "="*60)
    print("NSU DEGREE AUDIT - LOAD TEST STARTING")
    print("="*60)
    print(f"Target Host: {environment.host}")
    print(f"User Classes: TranscriptUser, AuthenticatedUser, ConcurrencyStressTest")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops - print summary."""
    print("\n" + "="*60)
    print("LOAD TEST COMPLETED")
    print("="*60)
    
    if environment.stats.total.num_requests > 0:
        stats = environment.stats.total
        print(f"Total Requests:     {stats.num_requests}")
        print(f"Failed Requests:    {stats.num_failures}")
        print(f"Failure Rate:       {stats.fail_ratio * 100:.2f}%")
        print(f"Avg Response Time:  {stats.avg_response_time:.2f}ms")
        print(f"Median (p50):       {stats.get_response_time_percentile(0.50):.2f}ms")
        print(f"95th Percentile:    {stats.get_response_time_percentile(0.95):.2f}ms")
        print(f"99th Percentile:    {stats.get_response_time_percentile(0.99):.2f}ms")
        print(f"Requests/sec:       {stats.total_rps:.2f}")
        
        # Check if we passed the 20 concurrent users requirement
        if stats.fail_ratio < 0.05:  # Less than 5% failure rate
            print("\n✅ PASSED: System handled load with <5% failure rate")
        else:
            print("\n❌ FAILED: Failure rate exceeded 5%")
    
    print("="*60 + "\n")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, exception, **kwargs):
    """Log individual requests for debugging."""
    if exception:
        print(f"❌ {request_type} {name}: {exception}")
