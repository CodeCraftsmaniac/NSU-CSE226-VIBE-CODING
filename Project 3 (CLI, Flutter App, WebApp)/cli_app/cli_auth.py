"""
CLI Authentication Module
==========================
Browser-based Google OAuth authentication for CLI.
Uses the SAME Supabase auth flow as the website.
Opens browser → User signs in with Google → Captures token.

Usage:
  from cli_auth import CLIAuth
  
  auth = CLIAuth()
  if auth.login():
      print(f"Logged in as {auth.user['email']}")
      
  history = auth.get_history()
  auth.logout()
"""

import os
import sys
import json
import time
import socket
import signal
import threading
import webbrowser
import urllib.parse
import uuid
from pathlib import Path
from typing import Optional, Dict, List, Any
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

# Token storage location
TOKEN_FILE = Path.home() / '.nsu_audit_cli_token.json'

# API Configuration
API_BASE_URL = os.environ.get("CLOUD_API_URL", "https://ocrapi.nsunexus.app")

# Web App URL (for OAuth redirect)
WEB_APP_URL = "https://ocr.nsunexus.app"

# Supabase Configuration (same as website)
SUPABASE_URL = "https://kmbltplmjdkjlbungbbh.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImttYmx0cGxtamRramxidW5nYmJoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc2Mjc1MDksImV4cCI6MjA4MzIwMzUwOX0.IRoQ306ElYZh8WoTN1dXMVr9mSd20-RPxwKYZ6M6Lcg"

# Connection timeout
API_TIMEOUT = 15

# Local callback server port
CALLBACK_PORT = 54321

# Global flag for interrupt handling
_interrupt_requested = False


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from browser."""
    
    def log_message(self, format, *args):
        pass  # Suppress HTTP logs
    
    def do_GET(self):
        """Handle GET request with OAuth tokens."""
        # Parse the URL fragment/query
        parsed = urllib.parse.urlparse(self.path)
        
        # Check if this is the callback page
        if parsed.path == '/callback':
            # Send success HTML that extracts token from fragment
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>NSU Degree Audit - Authentication</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
               color: white; display: flex; justify-content: center; align-items: center;
               height: 100vh; margin: 0; }
        .container { text-align: center; padding: 40px; background: rgba(255,255,255,0.1);
                     border-radius: 20px; backdrop-filter: blur(10px); }
        h1 { color: #38bdf8; margin-bottom: 20px; }
        .success { color: #4ade80; font-size: 48px; }
        .message { margin-top: 20px; color: #94a3b8; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #38bdf8; 
                   border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite;
                   margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container" id="loading">
        <h1>🎓 NSU Degree Audit</h1>
        <div class="spinner"></div>
        <p>Processing authentication...</p>
    </div>
    <div class="container" id="success" style="display:none;">
        <div class="success">✓</div>
        <h1>Authentication Successful!</h1>
        <p class="message">You can close this window and return to the CLI.</p>
    </div>
    <div class="container" id="error" style="display:none;">
        <div class="success" style="color:#ef4444;">✗</div>
        <h1>Authentication Failed</h1>
        <p class="message" id="error-message">Please try again.</p>
    </div>
    <script>
        // Extract tokens from URL hash
        const hash = window.location.hash.substring(1);
        const params = new URLSearchParams(hash);
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');
        
        if (accessToken) {
            // Send token to local server
            fetch('/token?access_token=' + encodeURIComponent(accessToken) + 
                  '&refresh_token=' + encodeURIComponent(refreshToken || ''))
                .then(response => response.json())
                .then(data => {
                    document.getElementById('loading').style.display = 'none';
                    if (data.success) {
                        document.getElementById('success').style.display = 'block';
                        setTimeout(() => window.close(), 2000);
                    } else {
                        document.getElementById('error').style.display = 'block';
                        document.getElementById('error-message').textContent = data.error || 'Unknown error';
                    }
                })
                .catch(err => {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('error').style.display = 'block';
                    document.getElementById('error-message').textContent = err.message;
                });
        } else {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('error').style.display = 'block';
            document.getElementById('error-message').textContent = 'No access token received';
        }
    </script>
</body>
</html>
"""
            self.wfile.write(html.encode())
        
        elif parsed.path == '/token':
            # Receive the token from the callback page
            query = urllib.parse.parse_qs(parsed.query)
            access_token = query.get('access_token', [None])[0]
            refresh_token = query.get('refresh_token', [None])[0]
            
            if access_token:
                # Store token in server instance
                self.server.access_token = access_token
                self.server.refresh_token = refresh_token
                self.server.auth_complete = True
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode())
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': 'No token'}).encode())
        
        else:
            self.send_response(404)
            self.end_headers()


class CLIAuth:
    """
    CLI Authentication handler using Supabase OAuth.
    Uses browser-based Google sign-in (same as website).
    """
    
    def __init__(self):
        self.token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user: Optional[Dict] = None
        self._supabase = None
        self._load_token()
    
    def _get_supabase(self):
        """Get Supabase client."""
        if self._supabase is None:
            try:
                from supabase import create_client
                self._supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            except ImportError:
                return None
        return self._supabase
    
    def _load_token(self):
        """Load saved token from file."""
        if TOKEN_FILE.exists():
            try:
                data = json.loads(TOKEN_FILE.read_text())
                self.token = data.get('token')
                self.refresh_token = data.get('refresh_token')
                self.user = data.get('user')
                
                # Validate token is still valid
                if self.token and not self._validate_token():
                    # Try to refresh
                    if self.refresh_token and self._refresh_session():
                        pass  # Refreshed successfully
                    else:
                        self._clear_token()
            except Exception:
                pass
    
    def _save_token(self):
        """Save token to file."""
        if self.token and self.user:
            TOKEN_FILE.write_text(json.dumps({
                'token': self.token,
                'refresh_token': self.refresh_token,
                'user': self.user,
                'saved_at': time.time()
            }, indent=2))
    
    def _clear_token(self):
        """Clear saved token."""
        self.token = None
        self.refresh_token = None
        self.user = None
        TOKEN_FILE.unlink(missing_ok=True)
    
    def _validate_token(self) -> bool:
        """Check if current token is valid via Supabase."""
        if not self.token:
            return False
        
        supabase = self._get_supabase()
        if not supabase:
            # Fallback to API validation
            return self._validate_token_via_api()
        
        try:
            # Validate with Supabase
            user_response = supabase.auth.get_user(self.token)
            if user_response and user_response.user:
                user = user_response.user
                self.user = {
                    'id': user.id,
                    'email': user.email,
                    'name': user.user_metadata.get('full_name') or user.user_metadata.get('name', ''),
                    'avatar_url': user.user_metadata.get('avatar_url', ''),
                    'provider': 'google'
                }
                return True
        except Exception:
            pass
        return False
    
    def _validate_token_via_api(self) -> bool:
        """Validate token via backend API."""
        try:
            response = requests.get(
                f"{API_BASE_URL}/auth/user",
                headers=self._get_headers(),
                timeout=API_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.user = data.get('user')
                    return True
        except Exception:
            pass
        return False
    
    def _refresh_session(self) -> bool:
        """Refresh the session using refresh token."""
        if not self.refresh_token:
            return False
        
        supabase = self._get_supabase()
        if not supabase:
            return False
        
        try:
            response = supabase.auth.refresh_session(self.refresh_token)
            if response and response.session:
                self.token = response.session.access_token
                self.refresh_token = response.session.refresh_token
                if response.user:
                    self.user = {
                        'id': response.user.id,
                        'email': response.user.email,
                        'name': response.user.user_metadata.get('full_name', ''),
                        'avatar_url': response.user.user_metadata.get('avatar_url', ''),
                        'provider': 'google'
                    }
                self._save_token()
                return True
        except Exception:
            pass
        return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers (without Content-Type for multipart uploads)."""
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
    
    def _get_json_headers(self) -> Dict[str, str]:
        """Get headers for JSON requests."""
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.token is not None and self.user is not None
    
    def _find_free_port(self) -> int:
        """Find a free port for the callback server."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful interrupt."""
        global _interrupt_requested
        _interrupt_requested = False
        
        def signal_handler(signum, frame):
            global _interrupt_requested
            _interrupt_requested = True
            print("\n⚠️  Authentication cancelled by user.")
        
        # Handle Ctrl+C
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
    
    def login_with_google(self) -> bool:
        """
        Login with Google OAuth using Device Code Flow.
        
        Like GitHub CLI / Supabase CLI:
        1. Request a device code from backend
        2. Open browser with verification URL
        3. User signs in with Google on web
        4. CLI polls backend until auth completes
        
        No localhost servers or redirects needed!
        """
        global _interrupt_requested
        self._setup_signal_handlers()
        
        print("\n🔐 Starting Google Sign-In...")
        print()
        
        # Step 1: Request device code
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/device/code",
                timeout=API_TIMEOUT
            )
            
            if response.status_code != 200:
                print("❌ Failed to start authentication")
                print("\n💡 TIP: Try Quick Email Login (option 2) instead.")
                return False
            
            data = response.json()
            device_code = data['device_code']
            user_code = data['user_code']
            verification_url = data['verification_url']
            expires_in = data['expires_in']
            poll_interval = data.get('interval', 2)
            
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server. Check your internet connection.")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        # Step 2: Display code and open browser
        print("╔════════════════════════════════════════════════════════════╗")
        print("║               ONE-TIME AUTHENTICATION CODE                 ║")
        print("╠════════════════════════════════════════════════════════════╣")
        print(f"║                        {user_code}                        ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print()
        print(f"🌐 Opening: {verification_url}")
        print()
        print("   Sign in with Google in your browser.")
        print("   This code expires in 10 minutes.")
        print()
        print("⏳ Waiting for authentication... (Press Ctrl+C to cancel)")
        
        try:
            webbrowser.open(verification_url)
        except Exception:
            print("   Could not open browser. Please visit the URL manually.")
        
        # Step 3: Poll for completion
        start_time = time.time()
        spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        spinner_idx = 0
        
        while (time.time() - start_time) < expires_in:
            if _interrupt_requested:
                print("\n")
                return False
            
            # Show spinner
            print(f"\r{spinner_chars[spinner_idx]} Waiting for browser sign-in...", end='', flush=True)
            spinner_idx = (spinner_idx + 1) % len(spinner_chars)
            
            time.sleep(poll_interval)
            
            try:
                poll_response = requests.post(
                    f"{API_BASE_URL}/auth/device/poll",
                    json={'device_code': device_code},
                    timeout=API_TIMEOUT
                )
                
                poll_data = poll_response.json()
                
                if poll_data.get('status') == 'complete':
                    print("\r                                        ")  # Clear line
                    self.token = poll_data['token']
                    self.user = poll_data['user']
                    self._save_token()
                    
                    print("✅ Logged in successfully!")
                    print(f"   Welcome, {self.user.get('name') or self.user.get('email')}!")
                    return True
                    
                elif poll_data.get('status') == 'expired':
                    print("\r                                        ")
                    print("❌ Authentication code expired")
                    return False
                    
            except Exception:
                # Network error, continue polling
                pass
        
        print("\r                                        ")
        print("❌ Authentication timed out")
        return False
    
    def _sync_user_to_backend(self):
        """Sync user to backend database (creates user if doesn't exist)."""
        if not self.user:
            return
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/auth/user",
                headers=self._get_headers(),
                timeout=API_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('user', {}).get('db_id'):
                    self.user['db_id'] = data['user']['db_id']
        except Exception:
            pass
    
    def login_interactive(self) -> bool:
        """
        Interactive login with multiple options.
        """
        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║              NSU DEGREE AUDIT - CLI LOGIN                    ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print("║  Sign in with your Google account to sync your history      ║")
        print("║  across CLI, Web App, and Mobile App.                        ║")
        print("╚══════════════════════════════════════════════════════════════╝\n")
        
        print("  [1] 🔐 Sign in with Google (opens browser)")
        print("  [2] 📧 Sign in with Email (quick login)")
        print("  [3] ❌ Cancel")
        print()
        
        choice = input("Select option [1-3]: ").strip()
        
        if choice == "1":
            return self.login_with_google()
        elif choice == "2":
            return self._login_with_email_interactive()
        else:
            print("Login cancelled.")
            return False
    
    def _login_with_email_interactive(self) -> bool:
        """Quick email-based login."""
        print("\n📧 Quick Email Login")
        print("   (Your scans will be linked to this email)\n")
        
        email = input("Enter your email: ").strip()
        if not email or '@' not in email:
            print("Invalid email format.")
            return False
        
        name = input("Enter your name (optional): ").strip() or "CLI User"
        
        print("\n⏳ Authenticating...")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/google",
                json={'email': email, 'name': name, 'provider': 'cli'},
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.token = data.get('token')
                    self.user = data.get('user')
                    self._save_token()
                    print(f"✅ Logged in as {self.user.get('name', email)}")
                    return True
                else:
                    print(f"❌ {data.get('error', 'Login failed')}")
            else:
                print(f"❌ Server error (status {response.status_code})")
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server. Check your internet connection.")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        return False
    
    def logout(self):
        """Clear authentication."""
        supabase = self._get_supabase()
        if supabase and self.token:
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
        
        self._clear_token()
        print("✅ Logged out successfully")
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get user's scan history."""
        if not self.is_authenticated:
            return []
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/history",
                params={'limit': limit},
                headers=self._get_headers(),
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('history', [])
            return []
        except Exception:
            return []
    
    def get_scan_details(self, scan_id: str) -> Optional[Dict]:
        """Get detailed scan by ID."""
        if not self.is_authenticated:
            return None
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/history/{scan_id}",
                headers=self._get_headers(),
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('scan')
            return None
        except Exception:
            return None
    
    def delete_scan(self, scan_id: str) -> bool:
        """Delete a scan from history."""
        if not self.is_authenticated:
            return False
        
        try:
            response = requests.delete(
                f"{API_BASE_URL}/history/{scan_id}",
                headers=self._get_headers(),
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('success', False)
            return False
        except Exception:
            return False
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics."""
        if not self.is_authenticated:
            return {}
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/auth/user",
                headers=self._get_headers(),
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('user', {}).get('stats', {})
            return {}
        except Exception:
            return {}


# Global auth instance
cli_auth = CLIAuth()
