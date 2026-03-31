"""
CLI Authentication Module
==========================
Google OAuth authentication for CLI using device flow.
Stores tokens locally for persistent sessions.

Usage:
  from cli_auth import CLIAuth
  
  auth = CLIAuth()
  if auth.login():
      print(f"Logged in as {auth.user['email']}")
      
  history = auth.get_history()
  auth.logout()
"""

import os
import json
import time
import webbrowser
from pathlib import Path
from typing import Optional, Dict, List, Any

import requests

# Token storage location
TOKEN_FILE = Path.home() / '.nsu_audit_cli_token.json'

# API Configuration
API_BASE_URL = os.environ.get("CLOUD_API_URL", "https://ocrapi.nsunexus.app")


class CLIAuth:
    """
    CLI Authentication handler using backend API.
    Supports Google OAuth via device flow pattern.
    """
    
    def __init__(self):
        self.token: Optional[str] = None
        self.user: Optional[Dict] = None
        self._load_token()
    
    def _load_token(self):
        """Load saved token from file."""
        if TOKEN_FILE.exists():
            try:
                data = json.loads(TOKEN_FILE.read_text())
                self.token = data.get('token')
                self.user = data.get('user')
                
                # Validate token is still valid
                if self.token and not self._validate_token():
                    self.token = None
                    self.user = None
                    TOKEN_FILE.unlink(missing_ok=True)
            except Exception:
                pass
    
    def _save_token(self):
        """Save token to file."""
        if self.token and self.user:
            TOKEN_FILE.write_text(json.dumps({
                'token': self.token,
                'user': self.user,
                'saved_at': time.time()
            }, indent=2))
    
    def _validate_token(self) -> bool:
        """Check if current token is valid."""
        if not self.token:
            return False
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/auth/user",
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.user = data.get('user')
                    return True
            return False
        except Exception:
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.token is not None and self.user is not None
    
    def login_with_email(self, email: str, name: str = "CLI User") -> bool:
        """
        Simple login with email (for CLI convenience).
        Creates/gets user account and returns token.
        """
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/google",
                json={
                    'email': email,
                    'name': name,
                    'provider': 'cli'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.token = data.get('token')
                    self.user = data.get('user')
                    self._save_token()
                    return True
            return False
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def login_interactive(self) -> bool:
        """
        Interactive login - prompts user for email.
        For full Google OAuth, user should use web app first.
        """
        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║              NSU DEGREE AUDIT - CLI LOGIN                    ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print("║  Enter your NSU email to link your CLI to your account.     ║")
        print("║  For full Google OAuth, log in via web app first.           ║")
        print("╚══════════════════════════════════════════════════════════════╝\n")
        
        email = input("Enter your email: ").strip()
        if not email:
            print("Email cannot be empty.")
            return False
        
        if '@' not in email:
            print("Invalid email format.")
            return False
        
        name = input("Enter your name (optional): ").strip() or "CLI User"
        
        print("\nAuthenticating...")
        if self.login_with_email(email, name):
            print(f"✅ Logged in as {self.user.get('name', email)}")
            return True
        else:
            print("❌ Authentication failed")
            return False
    
    def logout(self):
        """Clear authentication."""
        self.token = None
        self.user = None
        TOKEN_FILE.unlink(missing_ok=True)
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
                timeout=30
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
                timeout=30
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
                timeout=30
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
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('stats', {})
            return {}
        except Exception:
            return {}


# Global auth instance
cli_auth = CLIAuth()
