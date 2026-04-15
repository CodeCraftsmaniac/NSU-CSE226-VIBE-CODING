import 'dart:convert';
import 'dart:developer' as developer;

import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/user_model.dart';
import 'api_service.dart' hide ApiException;
import 'storage_service.dart';

class ApiException implements Exception {
  ApiException(this.message, [this.statusCode]);

  final String message;
  final int? statusCode;

  @override
  String toString() => statusCode != null
      ? 'ApiException($statusCode): $message'
      : 'ApiException: $message';

  bool get isNetworkError => statusCode == null;
  bool get isAuthError => statusCode == 401 || statusCode == 403;
  bool get isServerError => statusCode != null && statusCode! >= 500;
}

class AuthService extends ChangeNotifier {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  UserModel? _currentUser;
  bool _initialized = false;
  bool _isLoading = false;
  bool _authConfigFetched = false;
  bool _supabaseInitialized = false;

  static const String _apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://ocrapi.nsunexus.app',
  );

  static const String _defaultGoogleWebClientId = String.fromEnvironment(
    'GOOGLE_WEB_CLIENT_ID',
    defaultValue:
        '656129640010-k1f9dl8cbadngqdm8dnribi9doon67ko.apps.googleusercontent.com',
  );
  static const String _defaultSupabaseUrl = String.fromEnvironment(
    'SUPABASE_URL',
    defaultValue: '',
  );
  static const String _defaultSupabaseAnonKey = String.fromEnvironment(
    'SUPABASE_ANON_KEY',
    defaultValue: '',
  );

  String _googleWebClientId = _defaultGoogleWebClientId;
  String _supabaseUrl = _defaultSupabaseUrl;
  String _supabaseAnonKey = _defaultSupabaseAnonKey;

  bool get isAuthenticated => _currentUser != null;
  bool get initialized => _initialized;
  bool get isLoading => _isLoading;
  UserModel? get currentUser => _currentUser;

  Future<void> initialize() async {
    try {
      var restoredFromSupabase = false;

      final providerError = await _ensureAuthProvidersReady();
      if (providerError != null) {
        developer.log('Auth provider bootstrap skipped: $providerError',
            name: 'AuthService');
      }

      if (_supabaseInitialized) {
        final session = Supabase.instance.client.auth.currentSession;
        final supabaseUser = Supabase.instance.client.auth.currentUser;

        if (session != null && supabaseUser != null) {
          final userJson = await _resolveAuthenticatedUser(
            token: session.accessToken,
            supabaseUser: supabaseUser,
          );

          await storageService.saveToken(session.accessToken);
          await storageService.saveUser(userJson);
          apiService.setToken(session.accessToken);
          _currentUser = UserModel.fromJson(userJson);
          restoredFromSupabase = true;

          developer.log(
            'Session restored from Supabase for ${_currentUser?.email}',
            name: 'AuthService',
          );
        }
      }

      if (!restoredFromSupabase) {
        final token = await storageService.getToken();
        final userJson = await storageService.getUser();

        if (token != null && userJson != null) {
          final enriched = await _enrichUserFromBackend(
            token: token,
            fallbackUser: userJson,
          );

          _currentUser = UserModel.fromJson(enriched);
          apiService.setToken(token);
          await storageService.saveUser(enriched);

          developer.log(
            'Session restored from secure storage for ${_currentUser?.email}',
            name: 'AuthService',
          );
        }
      }
    } catch (e) {
      developer.log('Session restore failed: $e', name: 'AuthService');
      await storageService.clear();
    } finally {
      _initialized = true;
      notifyListeners();
    }
  }

  Future<String?> signInWithGoogle() async {
    _isLoading = true;
    notifyListeners();

    try {
      final configError = await _ensureAuthProvidersReady();
      if (configError != null) {
        return configError;
      }

      final googleSignIn = GoogleSignIn(
        serverClientId: _googleWebClientId.isEmpty ? null : _googleWebClientId,
        scopes: const ['email', 'profile'],
      );

      final googleUser = await googleSignIn.signIn();
      if (googleUser == null) {
        return null;
      }

      final googleAuth = await googleUser.authentication;
      final idToken = googleAuth.idToken;
      final accessToken = googleAuth.accessToken;

      if (idToken == null || idToken.isEmpty) {
        return 'Google sign-in failed: could not get ID token.';
      }

      final response = await Supabase.instance.client.auth.signInWithIdToken(
        provider: OAuthProvider.google,
        idToken: idToken,
        accessToken: accessToken,
      );

      final session =
          response.session ?? Supabase.instance.client.auth.currentSession;
      final supabaseUser =
          response.user ?? Supabase.instance.client.auth.currentUser;

      if (session == null || supabaseUser == null) {
        return 'Google sign-in failed. Please try again.';
      }

      final userJson = await _resolveAuthenticatedUser(
        token: session.accessToken,
        supabaseUser: supabaseUser,
        googleUser: googleUser,
      );

      await storageService.saveToken(session.accessToken);
      await storageService.saveUser(userJson);
      apiService.setToken(session.accessToken);

      _currentUser = UserModel.fromJson(userJson);
      notifyListeners();

      developer.log(
        'Native Google auth success for ${_currentUser?.email}',
        name: 'AuthService',
      );
      return null;
    } on AuthException catch (e) {
      developer.log('Google sign-in AuthException: ${e.message}',
          name: 'AuthService');
      return _friendlyGoogleError(e.message);
    } catch (e) {
      final err = e.toString();
      if (err.contains('ApiException: 10') || err.contains('DEVELOPER_ERROR')) {
        return 'Google Sign-In configuration error (code 10). '
            'Verify Android package and SHA-1 fingerprint in Google Cloud credentials.';
      }
      if (err.contains('ApiException: 12501') ||
          err.contains('SIGN_IN_CANCELLED')) {
        return null;
      }
      if (err.contains('ApiException: 7') || err.contains('NETWORK_ERROR')) {
        return 'Network error. Check your internet connection and try again.';
      }

      developer.log('signInWithGoogle unexpected error: $e',
          name: 'AuthService');
      return 'Unexpected error during sign-in. Please try again.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<Map<String, dynamic>> _resolveAuthenticatedUser({
    required String token,
    required User supabaseUser,
    GoogleSignInAccount? googleUser,
  }) async {
    final metadata = supabaseUser.userMetadata ?? const <String, dynamic>{};
    final fallbackUser = <String, dynamic>{
      'id': supabaseUser.id,
      'email': supabaseUser.email ?? googleUser?.email ?? '',
      'name': metadata['full_name']?.toString() ??
          metadata['name']?.toString() ??
          googleUser?.displayName ??
          '',
      'avatar_url': metadata['avatar_url']?.toString() ??
          metadata['picture']?.toString() ??
          googleUser?.photoUrl ??
          '',
      'provider': supabaseUser.appMetadata['provider']?.toString() ??
          metadata['provider']?.toString() ??
          'google',
    };

    return _enrichUserFromBackend(token: token, fallbackUser: fallbackUser);
  }

  Future<Map<String, dynamic>> _enrichUserFromBackend({
    required String token,
    required Map<String, dynamic> fallbackUser,
  }) async {
    final safeFallback = <String, dynamic>{
      ...fallbackUser,
      'id': fallbackUser['id']?.toString() ?? '',
      'email': fallbackUser['email']?.toString() ?? '',
      'name': fallbackUser['name']?.toString() ?? '',
      'avatar_url': fallbackUser['avatar_url']?.toString() ?? '',
      'provider': fallbackUser['provider']?.toString() ?? 'google',
    };

    try {
      final response = await http.get(
        Uri.parse('$_apiBaseUrl/auth/user'),
        headers: {
          'Authorization': 'Bearer $token',
        },
      ).timeout(const Duration(seconds: 20));

      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        final user = body is Map<String, dynamic> ? body['user'] : null;
        if (user is Map) {
          return {
            ...safeFallback,
            ...user.cast<String, dynamic>(),
          };
        }
      }
    } catch (e) {
      developer.log('Failed to enrich user profile from backend: $e',
          name: 'AuthService');
    }

    return safeFallback;
  }

  Future<String?> _ensureAuthProvidersReady() async {
    if (!_authConfigFetched) {
      final hasStaticConfig =
          _supabaseUrl.isNotEmpty && _supabaseAnonKey.isNotEmpty;
      if (hasStaticConfig) {
        _authConfigFetched = true;
      } else {
        await _fetchAuthConfig();
      }
    }

    if (_supabaseUrl.isEmpty || _supabaseAnonKey.isEmpty) {
      return 'Supabase auth is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY '
          'or expose them via /auth/config.';
    }

    if (_supabaseInitialized) {
      return null;
    }

    try {
      await Supabase.initialize(
        url: _supabaseUrl,
        anonKey: _supabaseAnonKey,
      );
      _supabaseInitialized = true;
      return null;
    } catch (e) {
      final lower = e.toString().toLowerCase();
      if (lower.contains('already') && lower.contains('initial')) {
        _supabaseInitialized = true;
        return null;
      }

      developer.log('Supabase initialize failed: $e', name: 'AuthService');
      return 'Could not initialize secure sign-in. Please try again.';
    }
  }

  Future<void> _fetchAuthConfig() async {
    try {
      final response = await http
          .get(Uri.parse('$_apiBaseUrl/auth/config'))
          .timeout(const Duration(seconds: 20));

      if (response.statusCode != 200) {
        developer.log(
          'Auth config request failed: ${response.statusCode}',
          name: 'AuthService',
        );
        return;
      }

      final body = json.decode(response.body);
      if (body is! Map<String, dynamic>) {
        return;
      }

      final configRaw = body['config'];
      final config = configRaw is Map ? configRaw.cast<String, dynamic>() : body;

      final remoteSupabaseUrl = _pickString(
        config,
        const ['supabase_url', 'supabaseUrl'],
      );
      final remoteSupabaseKey = _pickString(
        config,
        const ['supabase_key', 'supabaseKey'],
      );
      final remoteGoogleClientId = _pickString(
        config,
        const ['google_client_id', 'googleClientId'],
      );

      if (remoteSupabaseUrl.isNotEmpty) {
        _supabaseUrl = remoteSupabaseUrl;
      }
      if (remoteSupabaseKey.isNotEmpty) {
        _supabaseAnonKey = remoteSupabaseKey;
      }
      if (remoteGoogleClientId.isNotEmpty) {
        _googleWebClientId = remoteGoogleClientId;
      }

      if (_supabaseUrl.isNotEmpty && _supabaseAnonKey.isNotEmpty) {
        _authConfigFetched = true;
      }
    } catch (e) {
      developer.log('Failed to fetch auth config: $e', name: 'AuthService');
    }
  }

  String _pickString(Map<String, dynamic> source, List<String> keys) {
    for (final key in keys) {
      final value = source[key];
      if (value is String && value.trim().isNotEmpty) {
        return value.trim();
      }
    }
    return '';
  }

  String _friendlyGoogleError(String message) {
    final msg = message.toLowerCase();
    if (msg.contains('popup_closed') || msg.contains('canceled')) {
      return 'Google sign-in was cancelled.';
    }
    if (msg.contains('network') || msg.contains('connection')) {
      return 'Network error. Please check your internet connection.';
    }
    if (msg.contains('disabled') || msg.contains('not enabled')) {
      return 'Google sign-in is not enabled for this project.';
    }
    return 'Google sign-in failed. Please try again.';
  }

  Future<void> trySilentSignIn() async {
    // Session restore is handled in initialize().
  }

  Map<String, String> _authHeaders(String token) {
    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };
  }

  Future<List<Map<String, dynamic>>> getHistory({int limit = 50}) async {
    if (!isAuthenticated) {
      developer.log('getHistory called but user is not authenticated',
          name: 'AuthService');
      return [];
    }

    final token = await storageService.getToken();
    if (token == null || token.isEmpty) {
      throw ApiException('Session expired. Please sign in again.', 401);
    }

    try {
      final response = await http.get(
        Uri.parse('$_apiBaseUrl/history?limit=$limit'),
        headers: _authHeaders(token),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 401 || response.statusCode == 403) {
        throw ApiException(
            'Session expired. Please sign in again.', response.statusCode);
      }

      if (response.statusCode != 200) {
        throw ApiException('Failed to load history', response.statusCode);
      }

      final data = json.decode(response.body);
      if (data is Map<String, dynamic> && data['success'] == true) {
        final rows = data['history'];
        if (rows is List) {
          return rows
              .whereType<Map>()
              .map((row) => row.cast<String, dynamic>())
              .toList();
        }
      }
      return [];
    } on http.ClientException catch (e) {
      developer.log('Network error in getHistory: $e', name: 'AuthService');
      throw ApiException('Network error. Check your connection.');
    }
  }

  Future<Map<String, dynamic>?> getScanDetails(String scanId) async {
    if (!isAuthenticated) {
      developer.log('getScanDetails called but user is not authenticated',
          name: 'AuthService');
      return null;
    }

    final token = await storageService.getToken();
    if (token == null || token.isEmpty) {
      throw ApiException('Session expired. Please sign in again.', 401);
    }

    try {
      final response = await http.get(
        Uri.parse('$_apiBaseUrl/history/$scanId'),
        headers: _authHeaders(token),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 401 || response.statusCode == 403) {
        throw ApiException(
            'Session expired. Please sign in again.', response.statusCode);
      }

      if (response.statusCode == 404) {
        throw ApiException('Scan not found', 404);
      }

      if (response.statusCode != 200) {
        throw ApiException('Failed to load scan details', response.statusCode);
      }

      final data = json.decode(response.body);
      if (data is Map<String, dynamic> && data['success'] == true) {
        final scan = data['scan'];
        if (scan is Map) {
          return scan.cast<String, dynamic>();
        }
      }

      return null;
    } on http.ClientException catch (e) {
      developer.log('Network error in getScanDetails: $e', name: 'AuthService');
      throw ApiException('Network error. Check your connection.');
    }
  }

  Future<bool> deleteScan(String scanId) async {
    if (!isAuthenticated) {
      developer.log('deleteScan called but user is not authenticated',
          name: 'AuthService');
      return false;
    }

    final token = await storageService.getToken();
    if (token == null || token.isEmpty) {
      throw ApiException('Session expired. Please sign in again.', 401);
    }

    try {
      final response = await http.delete(
        Uri.parse('$_apiBaseUrl/history/$scanId'),
        headers: _authHeaders(token),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 401 || response.statusCode == 403) {
        throw ApiException(
            'Session expired. Please sign in again.', response.statusCode);
      }

      if (response.statusCode == 404) {
        throw ApiException('Scan not found or already deleted', 404);
      }

      final data = json.decode(response.body);
      if (data is Map<String, dynamic>) {
        return data['success'] == true;
      }
      return false;
    } on http.ClientException catch (e) {
      developer.log('Network error in deleteScan: $e', name: 'AuthService');
      throw ApiException('Network error. Check your connection.');
    }
  }

  Future<void> signOut() async => logout();

  Future<void> logout() async {
    _isLoading = true;
    notifyListeners();

    try {
      try {
        final googleSignIn = GoogleSignIn(
          serverClientId: _googleWebClientId.isEmpty ? null : _googleWebClientId,
        );
        if (await googleSignIn.isSignedIn()) {
          await googleSignIn.signOut();
        }
      } catch (e) {
        developer.log('Google sign-out skipped: $e', name: 'AuthService');
      }

      try {
        await Supabase.instance.client.auth.signOut();
      } catch (e) {
        developer.log('Supabase sign-out skipped: $e', name: 'AuthService');
      }

      await storageService.clear();
      apiService.setToken(null);
      _currentUser = null;
      developer.log('User signed out.', name: 'AuthService');
    } catch (e) {
      developer.log('Logout error: $e', name: 'AuthService');
      _currentUser = null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}

final authService = AuthService();