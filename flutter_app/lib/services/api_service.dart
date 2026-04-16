import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';
import 'dart:io';
import 'dart:typed_data';
import 'backend_config.dart';
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
    _dio = Dio(
      BaseOptions(
        baseUrl: backendBaseUrl,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 60),
        headers: {'Content-Type': 'application/json'},
      ),
    );
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await storageService.getToken();
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (err, handler) {
          final msg =
              err.response?.data?['detail'] ??
              err.response?.data?['message'] ??
              err.response?.data?['error'] ??
              err.message ??
              'Unknown error';
          handler.reject(
            DioException(
              requestOptions: err.requestOptions,
              error: ApiException(msg.toString(), err.response?.statusCode),
              type: err.type,
              response: err.response,
            ),
          );
        },
      ),
    );
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
      final msg =
          e.response?.data?['detail'] ??
          e.response?.data?['message'] ??
          e.response?.data?['error'] ??
          e.message ??
          'Request failed';
      throw ApiException(msg.toString(), e.response?.statusCode);
    }
  }

  Future<Map<String, dynamic>> login(String email, String password) async {
    throw ApiException(
      'Password login is not supported. Use Google sign-in instead.',
    );
  }

  Future<Map<String, dynamic>> register(
    String email,
    String password,
    String name,
  ) async {
    throw ApiException(
      'Password registration is not supported. Use Google sign-in instead.',
    );
  }

  Future<Map<String, dynamic>> uploadFile(
    String fileName, {
    Uint8List? bytes,
    String? filePath,
  }) async {
    // Ensure filename has extension
    final ext = fileName.contains('.')
        ? fileName.split('.').last.toLowerCase()
        : 'pdf';
    final safeFileName = fileName.contains('.') ? fileName : '$fileName.$ext';

    // Determine content type based on extension
    MediaType contentType;
    switch (ext) {
      case 'pdf':
        contentType = MediaType('application', 'pdf');
        break;
      case 'png':
        contentType = MediaType('image', 'png');
        break;
      case 'jpg':
      case 'jpeg':
        contentType = MediaType('image', 'jpeg');
        break;
      case 'csv':
        contentType = MediaType('text', 'csv');
        break;
      default:
        contentType = MediaType('application', 'octet-stream');
    }

    MultipartFile multipartFile;

    // Priority: bytes > filePath
    if (bytes != null && bytes.isNotEmpty) {
      // Use bytes directly (works on all platforms)
      multipartFile = MultipartFile.fromBytes(
        bytes,
        filename: safeFileName,
        contentType: contentType,
      );
    } else if (filePath != null && filePath.isNotEmpty) {
      // Read file as bytes first (more reliable on mobile)
      try {
        final file = File(filePath);
        if (!await file.exists()) {
          throw ApiException('File not found: $filePath');
        }
        final fileBytes = await file.readAsBytes();
        if (fileBytes.isEmpty) {
          throw ApiException('File is empty');
        }
        multipartFile = MultipartFile.fromBytes(
          fileBytes,
          filename: safeFileName,
          contentType: contentType,
        );
      } catch (e) {
        throw ApiException('Could not read file: $e');
      }
    } else {
      throw ApiException('No file data provided');
    }

    try {
      return await _unwrap(
        _dio.post(
          '/upload',
          data: FormData.fromMap({
            'file': multipartFile,
            'source': 'flutter',
            'ocr_engine': 'auto',
          }),
          options: Options(
            contentType: 'multipart/form-data',
            sendTimeout: const Duration(seconds: 120),
            receiveTimeout: const Duration(seconds: 120),
          ),
        ),
      );
    } catch (e) {
      if (e is DioException) {
        if (e.type == DioExceptionType.sendTimeout) {
          throw ApiException('Upload timeout. Please check your connection.');
        } else if (e.type == DioExceptionType.connectionTimeout) {
          throw ApiException('Connection timeout. Please try again.');
        }
      }
      rethrow;
    }
  }

  Future<Map<String, dynamic>> getAnalysis() =>
      _unwrap(_dio.get('/api/v1/analysis/latest'));

  Future<Map<String, dynamic>> getScansRaw() => _unwrap(_dio.get('/history'));

  Future<Map<String, dynamic>> getHealth() async {
    try {
      return await _unwrap(
        Dio().get(backendUri('/health/realtime').toString()),
      );
    } catch (_) {
      return {'status': 'unreachable'};
    }
  }
}

final apiService = ApiService();
