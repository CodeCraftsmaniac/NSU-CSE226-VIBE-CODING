import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'storage_service.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  ApiException(this.message, [this.statusCode]);
  @override
  String toString() => message;
  bool get isAuthError => statusCode == 401 || statusCode == 403;
}

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: 'https://ocrapi.nsunexus.app',
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 60),
      headers: {'Content-Type': 'application/json'},
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await storageService.getToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (err, handler) {
        final msg = err.response?.data?['detail'] ??
            err.response?.data?['message'] ??
            err.message ??
            'Unknown error';
        handler.reject(DioException(
          requestOptions: err.requestOptions,
          error: ApiException(msg.toString(), err.response?.statusCode),
          type: err.type,
          response: err.response,
        ));
      },
    ));
  }

  late final Dio _dio;

  void setToken(String? token) {
    if (token != null) {
      _dio.options.headers['Authorization'] = 'Bearer $token';
    } else {
      _dio.options.headers.remove('Authorization');
    }
  }

  Future<Map<String, dynamic>> _unwrap(Future<Response> call) async {
    try {
      final res = await call;
      return res.data as Map<String, dynamic>;
    } on DioException catch (e) {
      final original = e.error;
      if (original is ApiException) throw original;
      final msg = e.response?.data?['detail'] ??
          e.response?.data?['message'] ??
          e.message ??
          'Request failed';
      throw ApiException(msg.toString(), e.response?.statusCode);
    }
  }

  Future<Map<String, dynamic>> login(String email, String password) =>
      _unwrap(_dio.post('/api/v1/user/login',
          data: {'email': email, 'password': password}));

  Future<Map<String, dynamic>> register(
          String email, String password, String name) =>
      _unwrap(_dio.post('/api/v1/user/register',
          data: {'email': email, 'password': password, 'name': name}));

  Future<Map<String, dynamic>> uploadFile(
    String fileName, {
    Uint8List? bytes,
    String? filePath,
  }) async {
    MultipartFile multipartFile;
    if (bytes != null) {
      multipartFile = MultipartFile.fromBytes(bytes, filename: fileName);
    } else if (filePath != null) {
      multipartFile = await MultipartFile.fromFile(filePath, filename: fileName);
    } else {
      throw ApiException('No file data provided');
    }
    return _unwrap(_dio.post(
      '/api/v1/upload/file',
      data: FormData.fromMap({'file': multipartFile}),
      options: Options(contentType: 'multipart/form-data'),
    ));
  }

  Future<Map<String, dynamic>> getAnalysis() =>
      _unwrap(_dio.get('/api/v1/analysis/latest'));

  Future<Map<String, dynamic>> getScansRaw() =>
      _unwrap(_dio.get('/api/v1/user/scans'));

  Future<Map<String, dynamic>> getHealth() async {
    try {
      return await _unwrap(
          Dio().get('https://ocrapi.nsunexus.app/health/realtime'));
    } catch (_) {
      return {'status': 'unreachable'};
    }
  }
}

final apiService = ApiService();
