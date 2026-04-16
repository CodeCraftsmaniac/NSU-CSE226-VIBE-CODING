library;

export 'auth_service.dart';
export 'storage_service.dart';

/*
Compatibility shim kept so older imports resolve to the active auth/storage
services. The legacy duplicate implementation is intentionally commented out.

import 'dart:convert';
import 'dart:developer' as developer;
import 'package:http/http.dart' as http;

import 'package:shared_preferences/shared_preferences.dart';
import 'backend_config.dart';

// Backend API URL
final String apiBaseUrl = backendBaseUrl;

/// Custom exception for API errors
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  ApiException(this.message, [this.statusCode]);

  @override
  String toString() => statusCode != null
      ? 'ApiException($statusCode): $message'
      : 'ApiException: $message';

  bool get isNetworkError => statusCode == null;
  bool get isAuthError => statusCode == 401 || statusCode == 403;
  bool get isServerError => statusCode != null && statusCode! >= 500;
}

class AuthService {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  String? _sessionToken;
  Map<String, dynamic>? _currentUser;
  bool _isGuestMode = false;

  /// Check if user is authenticated
  bool get isAuthenticated => _sessionToken != null && _currentUser != null;

  /// Check if guest mode
  bool get isGuestMode => _isGuestMode && !isAuthenticated;

  /// Get current user
  Map<String, dynamic>? get currentUser => _currentUser;

  /// Get session token for API calls
  String? get sessionToken => _sessionToken;

  /// Initialize - restore session from storage
  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    _sessionToken = prefs.getString('session_token');
    _isGuestMode = prefs.getBool('guest_mode') ?? false;
    final userJson = prefs.getString('current_user');
    if (userJson != null) {
      _currentUser = json.decode(userJson);
    }
  }

  /// Set guest mode
  Future<void> setGuestMode(bool value) async {
    _isGuestMode = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('guest_mode', value);
  }

  /// Check if user has any session (authenticated or guest)
  bool get hasSession => isAuthenticated || _isGuestMode;

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
    await prefs.remove('guest_mode');
    _isGuestMode = false;
  }

  /// Sign in with Google - disabled (google_sign_in package removed)
  Future<bool> signInWithGoogle() async {
    return false;
  }

  /// Sign out
  Future<void> signOut() async {
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
    if (!isAuthenticated) {
      developer.log('getHistory called but not authenticated', name: 'AuthService');
      return [];
    }

    try {
      final response = await http.get(
        Uri.parse('$apiBaseUrl/history?limit=$limit'),
        headers: getAuthHeaders(),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 401) {
        developer.log('History: Auth token expired or invalid', name: 'AuthService');
        throw ApiException('Session expired. Please sign in again.', 401);
      }

      if (response.statusCode != 200) {
        developer.log('History failed: ${response.statusCode}', name: 'AuthService');
        throw ApiException('Failed to load history', response.statusCode);
      }

      final data = json.decode(response.body);
      if (data['success'] == true) {
        return List<Map<String, dynamic>>.from(data['history'] ?? []);
      }
      return [];
    } on http.ClientException catch (e) {
      developer.log('Network error in getHistory: $e', name: 'AuthService');
      throw ApiException('Network error. Check your connection.');
    } catch (e) {
      if (e is ApiException) rethrow;
      developer.log('Error in getHistory: $e', name: 'AuthService');
      return [];
    }
  }

  /// Get scan details
  Future<Map<String, dynamic>?> getScanDetails(String scanId) async {
    if (!isAuthenticated) {
      developer.log('getScanDetails called but not authenticated', name: 'AuthService');
      return null;
    }

    try {
      final response = await http.get(
        Uri.parse('$apiBaseUrl/history/$scanId'),
        headers: getAuthHeaders(),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 401) {
        developer.log('Scan details: Auth token expired', name: 'AuthService');
        throw ApiException('Session expired. Please sign in again.', 401);
      }

      if (response.statusCode == 404) {
        developer.log('Scan not found: $scanId', name: 'AuthService');
        throw ApiException('Scan not found', 404);
      }

      if (response.statusCode != 200) {
        throw ApiException('Failed to load scan details', response.statusCode);
      }

      final data = json.decode(response.body);
      if (data['success'] == true) {
        return data['scan'];
      }
      return null;
    } on http.ClientException catch (e) {
      developer.log('Network error in getScanDetails: $e', name: 'AuthService');
      throw ApiException('Network error. Check your connection.');
    } catch (e) {
      if (e is ApiException) rethrow;
      developer.log('Error in getScanDetails: $e', name: 'AuthService');
      return null;
    }
  }

  /// Delete a scan
  Future<bool> deleteScan(String scanId) async {
    if (!isAuthenticated) {
      developer.log('deleteScan called but not authenticated', name: 'AuthService');
      return false;
    }

    try {
      final response = await http.delete(
        Uri.parse('$apiBaseUrl/history/$scanId'),
        headers: getAuthHeaders(),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 401) {
        developer.log('Delete scan: Auth token expired', name: 'AuthService');
        throw ApiException('Session expired. Please sign in again.', 401);
      }

      if (response.statusCode == 404) {
        throw ApiException('Scan not found or already deleted', 404);
      }

      final data = json.decode(response.body);
      return data['success'] == true;
    } on http.ClientException catch (e) {
      developer.log('Network error in deleteScan: $e', name: 'AuthService');
      throw ApiException('Network error. Check your connection.');
    } catch (e) {
      if (e is ApiException) rethrow;
      developer.log('Error in deleteScan: $e', name: 'AuthService');
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
*/
