import '../models/analysis_model.dart';

class AnalysisSessionService {
  static final AnalysisSessionService _instance =
      AnalysisSessionService._internal();

  factory AnalysisSessionService() => _instance;

  AnalysisSessionService._internal();

  Map<String, dynamic>? _latestRawAnalysis;
  AnalysisModel? _latestAnalysis;

  AnalysisModel? get latestAnalysis => _latestAnalysis;
  Map<String, dynamic>? get latestRawAnalysis => _latestRawAnalysis;
  bool get hasAnalysis => _latestAnalysis != null;

  void setLatestAnalysis(Map<String, dynamic> rawAnalysis) {
    _latestRawAnalysis = Map<String, dynamic>.from(rawAnalysis);
    _latestAnalysis = AnalysisModel.fromJson(_latestRawAnalysis!);
  }

  void clear() {
    _latestRawAnalysis = null;
    _latestAnalysis = null;
  }
}

final analysisSessionService = AnalysisSessionService();
