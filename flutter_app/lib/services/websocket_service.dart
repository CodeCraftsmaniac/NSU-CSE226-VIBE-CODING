import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'backend_config.dart';
import '../models/ocr_progress_model.dart';

class WebSocketService {
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal();

  WebSocketChannel? _channel;
  StreamController<OcrProgressModel>? _controller;

  Stream<OcrProgressModel> connect(String jobId) {
    disconnect();
    _controller = StreamController<OcrProgressModel>.broadcast();

    try {
      final uri = backendWebSocketUri('/ws/ocr/$jobId');
      _channel = WebSocketChannel.connect(uri);

      _channel!.stream.listen(
        (message) {
          try {
            final payload = message.toString();
            if (payload == 'pong') {
              return;
            }

            final json = jsonDecode(payload) as Map<String, dynamic>;
            if (json['type']?.toString().toLowerCase() == 'heartbeat') {
              return;
            }
            final progress = OcrProgressModel.fromJson(json);
            if (!(_controller?.isClosed ?? true)) {
              _controller!.add(progress);
              if (progress.isDone || progress.hasError) {
                _controller!.close();
              }
            }
          } catch (_) {
            // ignore parse errors
          }
        },
        onError: (error) {
          if (!(_controller?.isClosed ?? true)) {
            _controller!.addError(error);
            _controller!.close();
          }
        },
        onDone: () {
          if (!(_controller?.isClosed ?? true)) {
            _controller!.close();
          }
        },
      );
    } catch (e) {
      _controller!.addError(e);
      _controller!.close();
    }

    return _controller!.stream;
  }

  void disconnect() {
    _channel?.sink.close();
    _channel = null;
    _controller?.close();
    _controller = null;
  }
}

final webSocketService = WebSocketService();
