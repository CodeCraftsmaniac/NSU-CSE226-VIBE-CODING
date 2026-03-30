/// NSU Degree Audit - Supabase Service
/// ====================================
/// Handles authentication and database operations via backend API.

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:google_sign_in/google_sign_in.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Backend API URL
const String apiBaseUrl = 'https://ocrapi.nsunexus.app';

class AuthService {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  String? _sessionToken;
  Map<String, dynamic>? _currentUser;
  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: ['email', 'profile'],
  );

  /// Check if user is authenticated
  bool get isAuthenticated => _sessionToken != null && _currentUser != null;

  /// Get current user
  Map<String, dynamic>? get currentUser => _currentUser;

  /// Get session token for API calls
  String? get sessionToken => _sessionToken;

  /// Initialize - restore session from storage
  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    _sessionToken = prefs.getString('session_token');
    final userJson = prefs.getString('current_user');
    if (userJson != null) {
      _currentUser = json.decode(userJson);
    }
  }

  /// Save session to storage
  Future<void> _saveSession() async {
    final prefs = await SharedPreferences.getInstance();
    if (_sessionToken != null) {
      await prefs.setString('session_token', _sessionToken!);
    }
    if (_currentUser != null) {
      await prefs.setString('current_user', json.encode(_currentUser));
    }
  }

  /// Clear session from storage
  Future<void> _clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('session_token');
    await prefs.remove('current_user');
  }

  /// Sign in with Google
  Future<Map<String, dynamic>?> signInWithGoogle() async {
    try {
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
      if (googleUser == null) {
        return null; // User cancelled
      }

      // Call backend to create/get user
      final response = await http.post(
        Uri.parse('$apiBaseUrl/auth/google'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'email': googleUser.email,
          'name': googleUser.displayName ?? '',
          'avatar_url': googleUser.photoUrl,
        }),
      );

      final data = json.decode(response.body);

      if (data['success'] == true) {
        _currentUser = data['user'];
        _sessionToken = data['token'];
        await _saveSession();
        return _currentUser;
      }

      throw Exception(data['error'] ?? 'Authentication failed');
    } catch (e) {
      rethrow;
    }
  }

  /// Sign out
  Future<void> signOut() async {
    await _googleSignIn.signOut();
    _sessionToken = null;
    _currentUser = null;
    await _clearSession();
  }

  /// Get auth headers for API calls
  Map<String, String> getAuthHeaders() {
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (_sessionToken != null) {
      headers['Authorization'] = 'Bearer $_sessionToken';
    }
    return headers;
  }

  /// Get scan history
  Future<List<Map<String, dynamic>>> getHistory({int limit = 50}) async {
    if (!isAuthenticated) return [];

    try {
      final response = await http.get(
        Uri.parse('$apiBaseUrl/history?limit=$limit'),
        headers: getAuthHeaders(),
      );

      final data = json.decode(response.body);
      if (data['success'] == true) {
        return List<Map<String, dynamic>>.from(data['history'] ?? []);
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  /// Get scan details
  Future<Map<String, dynamic>?> getScanDetails(String scanId) async {
    if (!isAuthenticated) return null;

    try {
      final response = await http.get(
        Uri.parse('$apiBaseUrl/history/$scanId'),
        headers: getAuthHeaders(),
      );

      final data = json.decode(response.body);
      if (data['success'] == true) {
        return data['scan'];
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  /// Delete a scan
  Future<bool> deleteScan(String scanId) async {
    if (!isAuthenticated) return false;

    try {
      final response = await http.delete(
        Uri.parse('$apiBaseUrl/history/$scanId'),
        headers: getAuthHeaders(),
      );

      final data = json.decode(response.body);
      return data['success'] == true;
    } catch (e) {
      return false;
    }
  }

  /// Refresh user data
  Future<void> refreshUser() async {
    if (!isAuthenticated) return;

    try {
      final response = await http.get(
        Uri.parse('$apiBaseUrl/auth/user'),
        headers: getAuthHeaders(),
      );

      final data = json.decode(response.body);
      if (data['success'] == true && data['user'] != null) {
        _currentUser = data['user'];
        await _saveSession();
      }
    } catch (e) {
      // Ignore errors
    }
  }
}

/// Global instance
final authService = AuthService();

