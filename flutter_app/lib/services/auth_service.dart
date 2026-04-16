import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/user_model.dart';
import 'api_service.dart' hide ApiException;
import 'analysis_session_service.dart';
import 'backend_config.dart';
import 'storage_service.dart';

// Auth and session orchestration for Google Sign-In, Supabase, and local restore.

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
  // Singleton service instance shared across UI layers.
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  UserModel? _currentUser;
  bool _initialized = false;
  bool _isLoading = false;
  bool _authConfigFetched = false;
  bool _supabaseInitialized = false;
  bool _guestMode = false;

  // Persisted key used to restore guest-mode sessions.
  static const String _guestModePrefKey = 'guest_mode';

  static String get _apiBaseUrl => backendBaseUrl;

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
  String _androidGoogleClientId = '';
  String _iosGoogleClientId = '';
  String _supabaseUrl = _defaultSupabaseUrl;
  String _supabaseAnonKey = _defaultSupabaseAnonKey;

  bool get isAuthenticated => _currentUser != null;
  bool get isGuestMode => _guestMode && !isAuthenticated;
  bool get hasSession => isAuthenticated || isGuestMode;
  bool get initialized => _initialized;
  bool get isLoading => _isLoading;
  UserModel? get currentUser => _currentUser;

  Future<void> initialize() async {
    try {
      _guestMode = await _readGuestModeFromPrefs();
      if (_guestMode) {
        _currentUser = null;
        apiService.setToken(null);
        await storageService.clear();
        developer.log(
          'Guest mode restored from previous session.',
          name: 'AuthService',
        );
        return;
      }

      var restoredFromSupabase = false;

      final providerError = await _ensureAuthProvidersReady();
      if (providerError != null) {
        developer.log(
          'Auth provider bootstrap skipped: $providerError',
          name: 'AuthService',
        );
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

      if (_currentUser != null) {
        await _setGuestMode(false);
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
    if (_isLoading) {
      return 'Sign-in is already in progress. Please wait a moment.';
    }

    _isLoading = true;
    notifyListeners();

    try {
      final configError = await _ensureAuthProvidersReady();
      if (configError != null) {
        return configError;
      }

      final primaryClientId = _getPlatformClientId();
      final fallbackClientId = _defaultGoogleWebClientId.trim();
      final attemptedClientIds = <String>{};

      developer.log(
        'Google Sign-In attempt on platform: ${kIsWeb ? "Web" : (Platform.isAndroid ? "Android" : "iOS")}',
        name: 'AuthService',
      );

      String? lastError;
      for (final clientId in [primaryClientId, fallbackClientId]) {
        if (clientId.isEmpty || attemptedClientIds.contains(clientId)) {
          continue;
        }

        attemptedClientIds.add(clientId);
        developer.log(
          'Attempting sign-in with client ID: ${clientId.substring(0, 20)}...',
          name: 'AuthService',
        );

        final result = await _signInWithClientId(clientId);
        if (result.error == null) {
          if (result.authenticated) {
            _googleWebClientId = clientId;
            await _setGuestMode(false);
          }
          return null;
        }

        lastError = result.error;
        developer.log('Sign-in failed: $lastError', name: 'AuthService');

        if (!result.retryWithDefaultClient) {
          break;
        }
      }

      return lastError ?? 'Google sign-in failed. Please try again.';
    } on AuthException catch (e) {
      developer.log(
        'Google sign-in AuthException: ${e.message}',
        name: 'AuthService',
      );
      return _friendlyGoogleError(e.message);
    } catch (e, st) {
      developer.log(
        'signInWithGoogle unexpected error: $e',
        name: 'AuthService',
        stackTrace: st,
      );
      return _friendlyGoogleRuntimeError(e.toString());
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  String _getPlatformClientId() {
    if (!kIsWeb) {
      if (Platform.isAndroid) {
        final androidClientId = _androidGoogleClientId.trim();
        if (androidClientId.isNotEmpty) {
          return androidClientId;
        }
      } else if (Platform.isIOS) {
        final iosClientId = _iosGoogleClientId.trim();
        if (iosClientId.isNotEmpty) {
          return iosClientId;
        }
      }

      // Fallback to native platform configuration files.
      return '';
    }

    // For web, use the web client ID
    return _googleWebClientId.trim().isNotEmpty
        ? _googleWebClientId.trim()
        : _defaultGoogleWebClientId.trim();
  }

  Future<_GoogleSignInResult> _signInWithClientId(String clientId) async {
    try {
      // For mobile, don't pass serverClientId - let it use google-services.json
      final googleSignIn = GoogleSignIn(
        serverClientId: clientId.isEmpty ? null : clientId,
        scopes: const ['email', 'profile'],
      );

      try {
        if (await googleSignIn.isSignedIn()) {
          await googleSignIn.signOut();
        }
      } catch (e) {
        developer.log(
          'Pre-sign-in Google session reset skipped: $e',
          name: 'AuthService',
        );
      }

      final googleUser = await googleSignIn.signIn();
      if (googleUser == null) {
        return const _GoogleSignInResult(error: null, authenticated: false);
      }

      final googleAuth = await googleUser.authentication;
      final idToken = googleAuth.idToken;
      final accessToken = googleAuth.accessToken;

      if (idToken == null || idToken.isEmpty) {
        return const _GoogleSignInResult(
          error: 'Google sign-in failed: could not get ID token.',
        );
      }

      final response = await Supabase.instance.client.auth.signInWithIdToken(
        provider: OAuthProvider.google,
        idToken: idToken,
        accessToken: accessToken,
      );

      Session? session =
          response.session ?? Supabase.instance.client.auth.currentSession;
      User? supabaseUser =
          response.user ?? Supabase.instance.client.auth.currentUser;

      if (session == null || supabaseUser == null) {
        for (
          var i = 0;
          i < 3 && (session == null || supabaseUser == null);
          i++
        ) {
          await Future<void>.delayed(const Duration(milliseconds: 300));
          session ??= Supabase.instance.client.auth.currentSession;
          supabaseUser ??= Supabase.instance.client.auth.currentUser;
        }
      }

      if (session == null || supabaseUser == null) {
        return const _GoogleSignInResult(
          error: 'Google sign-in failed. Could not create a secure session.',
        );
      }

      final userJson = await _resolveAuthenticatedUser(
        token: session.accessToken,
        supabaseUser: supabaseUser,
        googleUser: googleUser,
      );

      _currentUser = UserModel.fromJson(userJson);
      apiService.setToken(session.accessToken);
      await _persistSessionSafely(
        token: session.accessToken,
        userJson: userJson,
      );
      notifyListeners();

      developer.log(
        'Native Google auth success for ${_currentUser?.email}',
        name: 'AuthService',
      );
      return const _GoogleSignInResult(error: null, authenticated: true);
    } catch (e, st) {
      final err = e.toString();
      developer.log(
        'Google sign-in failed for client ID $clientId: $err',
        name: 'AuthService',
        stackTrace: st,
      );
      return _GoogleSignInResult(
        error: _friendlyGoogleRuntimeError(err),
        retryWithDefaultClient: _shouldRetryWithDefaultClient(err, clientId),
      );
    }
  }

  Future<void> _persistSessionSafely({
    required String token,
    required Map<String, dynamic> userJson,
  }) async {
    try {
      await storageService.saveToken(token);
      await storageService.saveUser(userJson);
    } catch (e) {
      developer.log('Session persistence skipped: $e', name: 'AuthService');
    }
  }

  bool _shouldRetryWithDefaultClient(String error, String attemptedClientId) {
    if (attemptedClientId == _defaultGoogleWebClientId.trim()) {
      return false;
    }

    final msg = error.toLowerCase();
    return msg.contains('developer_error') ||
        msg.contains('apiexception: 10') ||
        msg.contains('12500') ||
        msg.contains('invalid_audience') ||
        msg.contains('id token') ||
        msg.contains('oauth');
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
      'name':
          metadata['full_name']?.toString() ??
          metadata['name']?.toString() ??
          googleUser?.displayName ??
          '',
      'avatar_url':
          metadata['avatar_url']?.toString() ??
          metadata['picture']?.toString() ??
          googleUser?.photoUrl ??
          '',
      'provider':
          supabaseUser.appMetadata['provider']?.toString() ??
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
      final response = await http
          .get(
            Uri.parse('$_apiBaseUrl/auth/user'),
            headers: {'Authorization': 'Bearer $token'},
          )
          .timeout(const Duration(seconds: 20));

      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        final user = body is Map<String, dynamic> ? body['user'] : null;
        if (user is Map) {
          return {...safeFallback, ...user.cast<String, dynamic>()};
        }
      }
    } catch (e) {
      developer.log(
        'Failed to enrich user profile from backend: $e',
        name: 'AuthService',
      );
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
      await Supabase.initialize(url: _supabaseUrl, anonKey: _supabaseAnonKey);
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
      final config = configRaw is Map
          ? configRaw.cast<String, dynamic>()
          : body;

      final remoteSupabaseUrl = _pickString(config, const [
        'supabase_url',
        'supabaseUrl',
      ]);
      final remoteSupabaseKey = _pickString(config, const [
        'supabase_key',
        'supabaseKey',
      ]);
      final remoteGoogleClientId = _pickString(config, const [
        'google_client_id',
        'googleClientId',
      ]);
      final remoteAndroidClientId = _pickString(config, const [
        'google_client_id_android',
        'androidClientId',
      ]);
      final remoteIosClientId = _pickString(config, const [
        'google_client_id_ios',
        'iosClientId',
      ]);

      if (remoteSupabaseUrl.isNotEmpty) {
        _supabaseUrl = remoteSupabaseUrl;
      }
      if (remoteSupabaseKey.isNotEmpty) {
        _supabaseAnonKey = remoteSupabaseKey;
      }
      if (_googleWebClientId.isEmpty &&
          _isLikelyGoogleClientId(remoteGoogleClientId)) {
        _googleWebClientId = remoteGoogleClientId;
      }
      if (remoteAndroidClientId.isNotEmpty) {
        _androidGoogleClientId = remoteAndroidClientId;
      }
      if (remoteIosClientId.isNotEmpty) {
        _iosGoogleClientId = remoteIosClientId;
      }

      if (_supabaseUrl.isNotEmpty && _supabaseAnonKey.isNotEmpty) {
        _authConfigFetched = true;
      }
    } catch (e) {
      developer.log('Failed to fetch auth config: $e', name: 'AuthService');
    }
  }

  bool _isLikelyGoogleClientId(String value) {
    final trimmed = value.trim();
    return trimmed.contains('.apps.googleusercontent.com');
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

  String _friendlyGoogleRuntimeError(String message) {
    final msg = message.toLowerCase();

    if (msg.contains('apiexception: 10') || msg.contains('developer_error')) {
      return 'Google Sign-In configuration error (code 10). '
          'Please verify package name and SHA-1 in Google Cloud credentials.';
    }
    if (msg.contains('apiexception: 12501') ||
        msg.contains('apiexception: 12502') ||
        msg.contains('sign_in_cancelled')) {
      return 'Google sign-in was cancelled.';
    }
    if (msg.contains('apiexception: 7') || msg.contains('network_error')) {
      return 'Network error. Check your internet connection and try again.';
    }
    if (msg.contains('apiexception: 16') ||
        msg.contains('sign_in_required') ||
        msg.contains('google play services')) {
      return 'Google Play Services is unavailable. Update Play Services and try again.';
    }
    if (msg.contains('encryptedsharedpreferences') ||
        msg.contains('keystore') ||
        msg.contains('flutter_secure_storage')) {
      return 'Sign-in succeeded but secure session storage failed. '
          'Restart the app and try again.';
    }

    return 'Unexpected error during sign-in. Please try again.';
  }

  Future<bool> _readGuestModeFromPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getBool(_guestModePrefKey) ?? false;
    } catch (e) {
      developer.log(
        'Failed to read guest mode preference: $e',
        name: 'AuthService',
      );
      return false;
    }
  }

  Future<void> _setGuestMode(bool enabled) async {
    _guestMode = enabled;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_guestModePrefKey, enabled);
    } catch (e) {
      developer.log(
        'Failed to persist guest mode preference: $e',
        name: 'AuthService',
      );
    }
  }

  Future<void> continueAsGuest() async {
    if (_isLoading) {
      return;
    }

    _isLoading = true;
    notifyListeners();

    try {
      await _setGuestMode(true);
      _currentUser = null;
      apiService.setToken(null);
      analysisSessionService.clear();

      await _signOutProvidersSafely();
      await storageService.clear();
      developer.log('Guest mode enabled.', name: 'AuthService');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> exitGuestMode() async {
    if (!_guestMode) {
      return;
    }

    await _setGuestMode(false);
    notifyListeners();
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
      developer.log(
        'getHistory called but user is not authenticated',
        name: 'AuthService',
      );
      return [];
    }

    final token = await storageService.getToken();
    if (token == null || token.isEmpty) {
      throw ApiException('Session expired. Please sign in again.', 401);
    }

    try {
      final response = await http
          .get(
            Uri.parse('$_apiBaseUrl/history?limit=$limit'),
            headers: _authHeaders(token),
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 401 || response.statusCode == 403) {
        throw ApiException(
          'Session expired. Please sign in again.',
          response.statusCode,
        );
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
      developer.log(
        'getScanDetails called but user is not authenticated',
        name: 'AuthService',
      );
      return null;
    }

    final token = await storageService.getToken();
    if (token == null || token.isEmpty) {
      throw ApiException('Session expired. Please sign in again.', 401);
    }

    try {
      final response = await http
          .get(
            Uri.parse('$_apiBaseUrl/history/$scanId'),
            headers: _authHeaders(token),
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 401 || response.statusCode == 403) {
        throw ApiException(
          'Session expired. Please sign in again.',
          response.statusCode,
        );
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
      developer.log(
        'deleteScan called but user is not authenticated',
        name: 'AuthService',
      );
      return false;
    }

    final token = await storageService.getToken();
    if (token == null || token.isEmpty) {
      throw ApiException('Session expired. Please sign in again.', 401);
    }

    try {
      final response = await http
          .delete(
            Uri.parse('$_apiBaseUrl/history/$scanId'),
            headers: _authHeaders(token),
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 401 || response.statusCode == 403) {
        throw ApiException(
          'Session expired. Please sign in again.',
          response.statusCode,
        );
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
      await _signOutProvidersSafely();

      await storageService.clear();
      apiService.setToken(null);
      analysisSessionService.clear();
      _currentUser = null;
      await _setGuestMode(false);
      developer.log('User signed out.', name: 'AuthService');
    } catch (e) {
      developer.log('Logout error: $e', name: 'AuthService');
      _currentUser = null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> _signOutProvidersSafely() async {
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

    if (_supabaseInitialized) {
      try {
        await Supabase.instance.client.auth.signOut();
      } catch (e) {
        developer.log('Supabase sign-out skipped: $e', name: 'AuthService');
      }
    }
  }
}

final authService = AuthService();

class _GoogleSignInResult {
  const _GoogleSignInResult({
    required this.error,
    this.authenticated = false,
    this.retryWithDefaultClient = false,
  });

  final String? error;
  final bool authenticated;
  final bool retryWithDefaultClient;
}
