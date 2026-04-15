import 'dart:convert';
import 'dart:developer' as developer;
// ignore_for_file: body_might_complete_normally_catch_error

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

import '../models/user_model.dart';
import 'api_service.dart';
import 'storage_service.dart';

// ─────────────────────────────────────────────────────────────────────────────
// AuthService
// ─────────────────────────────────────────────────────────────────────────────

class AuthService extends ChangeNotifier {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  // ── State ──
  UserModel? _currentUser;
  bool _initialized = false;
  bool _isLoading = false;

  static const String _apiBaseUrl = 'https://ocrapi.nsunexus.app';

  // ── Public getters ──
  bool get isAuthenticated => _currentUser != null;
  bool get initialized => _initialized;
  bool get isLoading => _isLoading;
  UserModel? get currentUser => _currentUser;

  // ─────────────────────────────────────────────
  // Initialization — restore session from secure storage
  // ─────────────────────────────────────────────

  Future<void> initialize() async {
    try {
      final token = await storageService.getToken();
      final userJson = await storageService.getUser();
      if (token != null && userJson != null) {
        _currentUser = UserModel.fromJson(userJson);
        apiService.setToken(token);
        developer.log('Session restored for ${_currentUser?.email}',
            name: 'AuthService');
      }
    } catch (e) {
      developer.log('Session restore failed: $e', name: 'AuthService');
      // Clear any corrupt storage
      await storageService.clear();
    } finally {
      _initialized = true;
      notifyListeners();
    }
  }

  // ─────────────────────────────────────────────
  // Google Sign-In
  // ─────────────────────────────────────────────

  /// Signs the user in via browser-based Google OAuth device flow.
  /// Returns null on success; returns an error message string on failure.
  Future<String?> signInWithGoogle() async {
    _isLoading = true;
    notifyListeners();

    try {
      // 1) Request a device code from backend.
      final codeResponse = await http
          .post(Uri.parse('$_apiBaseUrl/auth/device/code'))
          .timeout(const Duration(seconds: 20));

      if (codeResponse.statusCode != 200) {
        developer.log(
          'Device code request failed: ${codeResponse.statusCode}',
          name: 'AuthService',
        );
        return 'Could not start Google sign-in. Please try again.';
      }

      final codeData = json.decode(codeResponse.body) as Map<String, dynamic>;
      final deviceCode = codeData['device_code']?.toString();
      final verificationUrl = codeData['verification_url']?.toString();
      final expiresIn = (codeData['expires_in'] as num?)?.toInt() ?? 600;
      final interval = (codeData['interval'] as num?)?.toInt() ?? 2;

      if (deviceCode == null || verificationUrl == null) {
        return 'Invalid login response from server.';
      }

      // 2) Open external browser for Google OAuth (same flow as web/CLI).
      final uri = Uri.parse(verificationUrl);
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched) {
        return 'Could not open browser for Google sign-in.';
      }

      // 3) Poll backend for completion.
      final pollError = await _pollDeviceCode(
        deviceCode: deviceCode,
        expiresInSeconds: expiresIn,
        pollIntervalSeconds: interval,
      );

      return pollError;

    } catch (e) {
      developer.log('signInWithGoogle unexpected error: $e', name: 'AuthService');
      return 'Unexpected error during sign-in. Please try again.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Poll backend device flow until user completes browser authentication.
  Future<String?> _pollDeviceCode({
    required String deviceCode,
    required int expiresInSeconds,
    required int pollIntervalSeconds,
  }) async {
    final deadline = DateTime.now().add(Duration(seconds: expiresInSeconds));
    final pollEvery = Duration(seconds: pollIntervalSeconds.clamp(1, 10));

    try {
      while (DateTime.now().isBefore(deadline)) {
        await Future.delayed(pollEvery);

        final response = await http
            .post(
              Uri.parse('$_apiBaseUrl/auth/device/poll'),
              headers: {'Content-Type': 'application/json'},
              body: json.encode({'device_code': deviceCode}),
            )
            .timeout(const Duration(seconds: 20));

        if (response.statusCode == 410) {
          return 'Login session expired. Please try again.';
        }

        if (response.statusCode != 200) {
          final body = json.decode(response.body) as Map<String, dynamic>?;
          return body?['detail']?.toString() ??
              'Sign-in failed (${response.statusCode}).';
        }

        final body = json.decode(response.body) as Map<String, dynamic>;
        final status = body['status']?.toString();

        if (status == 'pending') {
          continue;
        }

        if (status == 'complete') {
          final token = body['token']?.toString();
          final userJson = body['user'] as Map<String, dynamic>?;

          if (token == null || token.isEmpty || userJson == null) {
            return 'Sign-in completed but token data is invalid.';
          }

          await storageService.saveToken(token);
          await storageService.saveUser(userJson);
          apiService.setToken(token);

          _currentUser = UserModel.fromJson(userJson);
          notifyListeners();
          developer.log(
            'Device auth success. User: ${_currentUser?.email}',
            name: 'AuthService',
          );
          return null;
        }

        return body['detail']?.toString() ??
            body['message']?.toString() ??
            'Sign-in failed. Please try again.';
      }

      return 'Sign-in timed out. Please complete login faster and try again.';
    } on http.ClientException catch (e) {
      developer.log('Network error in device auth poll: $e', name: 'AuthService');
      return 'Network error. Check your connection and try again.';
    } catch (e) {
      developer.log('Device auth poll error: $e', name: 'AuthService');
      return 'Could not reach the server. Please try again.';
    }
  }

  // ─────────────────────────────────────────────
  // Silent sign-in (restore Google session on app start)
  // ─────────────────────────────────────────────

  Future<void> trySilentSignIn() async {
    // Browser/device-code login has no silent sign-in state to restore.
    return;
  }

  // ─────────────────────────────────────────────
  // Sign Out
  // ─────────────────────────────────────────────

  Future<void> logout() async {
    _isLoading = true;
    notifyListeners();

    try {
      await storageService.clear();
      apiService.setToken(null);
      _currentUser = null;
      developer.log('User signed out.', name: 'AuthService');
    } catch (e) {
      developer.log('Logout error: $e', name: 'AuthService');
      // Force clear even on error
      _currentUser = null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}

// ── Global singleton ──
final authService = AuthService();
