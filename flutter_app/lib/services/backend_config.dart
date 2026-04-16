const String _configuredBackendBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://ocrapi.nsunexus.app',
);

String get backendBaseUrl {
  final normalized = _configuredBackendBaseUrl.trim();
  if (normalized.endsWith('/')) {
    return normalized.substring(0, normalized.length - 1);
  }
  return normalized;
}

Uri backendUri(String path) {
  final normalizedPath = path.startsWith('/') ? path : '/$path';
  return Uri.parse(backendBaseUrl).resolve(normalizedPath);
}

Uri backendWebSocketUri(String path) {
  final normalizedPath = path.startsWith('/') ? path : '/$path';
  final base = Uri.parse(backendBaseUrl);
  final scheme = base.scheme == 'https' ? 'wss' : 'ws';
  return base.replace(
    scheme: scheme,
    path: normalizedPath,
    queryParameters: null,
    fragment: null,
  );
}
