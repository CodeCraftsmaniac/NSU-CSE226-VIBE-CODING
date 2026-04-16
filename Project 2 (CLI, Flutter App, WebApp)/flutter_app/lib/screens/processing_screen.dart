import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:percent_indicator/percent_indicator.dart';

import '../models/analysis_model.dart';
import '../models/ocr_progress_model.dart';
import '../services/analysis_session_service.dart';
import '../services/websocket_service.dart';
import '../widgets/glass_widgets.dart';
import 'main_shell.dart';

class ProcessingScreen extends StatefulWidget {
  const ProcessingScreen({
    super.key,
    required this.jobId,
    required this.fileName,
    this.analysisData,
  });

  final String jobId;
  final String fileName;
  final Map<String, dynamic>? analysisData;

  @override
  State<ProcessingScreen> createState() => _ProcessingScreenState();
}

class _ProcessingScreenState extends State<ProcessingScreen>
    with SingleTickerProviderStateMixin {
  // ── State ──
  double _progress = 0.0;
  String _stage = 'Connecting…';
  String _message = 'Establishing connection to OCR engine…';
  bool _isDone = false;
  bool _hasError = false;
  String? _errorMessage;
  final List<_StageEntry> _stageLog = [];

  // ── Animations ──
  late final AnimationController _pulseCtrl;
  late final Animation<double> _pulseAnim;

  // ── WebSocket subscription ──
  StreamSubscription<OcrProgressModel>? _wsSub;

  // ── Stage icon map ──
  static const _stageIcons = <String, IconData>{
    'connecting':    Icons.wifi_rounded,
    'uploading':     Icons.cloud_upload_outlined,
    'upload':        Icons.cloud_upload_outlined,
    'ocr':           Icons.document_scanner_rounded,
    'parse':         Icons.integration_instructions_outlined,
    'parsing':       Icons.integration_instructions_outlined,
    'analyze':       Icons.analytics_outlined,
    'analysis':      Icons.analytics_outlined,
    'analyzing':     Icons.analytics_outlined,
    'complete':      Icons.check_circle_rounded,
    'done':          Icons.check_circle_rounded,
    'error':         Icons.error_outline_rounded,
    'failed':        Icons.error_outline_rounded,
  };

  // ── Friendly stage labels ──
  static const _stageLabels = <String, String>{
    'connecting':    'Connecting',
    'uploading':     'Uploading',
    'upload':        'Uploading File',
    'ocr':           'Running OCR',
    'parse':         'Parsing Transcript',
    'parsing':       'Parsing Transcript',
    'analyze':       'Analysing Degree',
    'analysis':      'Analysing Degree',
    'analyzing':     'Analysing Degree',
    'complete':      'Complete!',
    'done':          'Complete!',
    'error':         'Error',
    'failed':        'Failed',
  };

  @override
  void initState() {
    super.initState();

    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    _pulseAnim = CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut);

    if (widget.analysisData != null) {
      Future.delayed(const Duration(milliseconds: 250), _completeFromBackend);
    } else {
      Future.delayed(const Duration(milliseconds: 400), _connectWebSocket);
    }
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _wsSub?.cancel();
    webSocketService.disconnect();
    super.dispose();
  }

  // ─────────────────────────────────────────────
  // WebSocket connection
  // ─────────────────────────────────────────────

  void _connectWebSocket() {
    if (widget.jobId.isEmpty) {
      _onStreamError('Missing OCR job ID.');
      return;
    }
    final stream = webSocketService.connect(widget.jobId);
    _wsSub = stream.listen(
      _onProgress,
      onError: _onStreamError,
      onDone: _onStreamDone,
      cancelOnError: false,
    );
  }

  void _completeFromBackend() {
    if (!mounted) return;

    if (widget.analysisData != null) {
      analysisSessionService.setLatestAnalysis(widget.analysisData!);
    }

    final analysis = widget.analysisData != null
        ? AnalysisModel.fromJson(widget.analysisData!)
        : null;
    final courseCount = analysis?.courses.length ?? 0;
    final completionMessage = courseCount > 0
        ? 'Backend OCR finished successfully. $courseCount courses were processed.'
        : 'Backend OCR finished successfully.';

    setState(() {
      _progress = 1.0;
      _isDone = true;
      _stage = 'Complete!';
      _message = completionMessage;
      _stageLog.add(_StageEntry(
        stage: 'Complete!',
        message: completionMessage,
        icon: Icons.check_circle_rounded,
        isError: false,
        time: DateTime.now(),
      ));
    });

    _pulseCtrl.stop();
    Future.delayed(const Duration(seconds: 2), _navigateToDashboard);
  }

  void _onProgress(OcrProgressModel p) {
    if (!mounted) return;

    setState(() {
      _progress = p.progress.clamp(0.0, 1.0);
      _stage   = _stageLabels[p.stage.toLowerCase()] ?? p.stage;
      _message = p.message.isNotEmpty ? p.message : _stage;

      // Append to log (avoid duplicate consecutive entries)
      if (_stageLog.isEmpty ||
          _stageLog.last.stage != _stage ||
          _stageLog.last.message != _message) {
        _stageLog.add(_StageEntry(
          stage:   _stage,
          message: _message,
          icon:    _stageIcons[p.stage.toLowerCase()] ??
                   Icons.radio_button_checked,
          isError: p.hasError,
          time:    DateTime.now(),
        ));
      }

      if (p.hasError) {
        _hasError    = true;
        _errorMessage = p.error;
        _progress    = 0.0;
      } else if (p.isDone) {
        _isDone   = true;
        _progress = 1.0;
        _stage    = 'Complete!';
        _message  = 'Your transcript has been processed successfully.';
        _pulseCtrl.stop();
        // Auto-navigate after a short celebration delay
        Future.delayed(const Duration(seconds: 2), _navigateToDashboard);
      }
    });
  }

  void _onStreamError(Object error) {
    if (!mounted) return;
    setState(() {
      _hasError     = true;
      _errorMessage = error.toString();
      _stage        = 'Connection Error';
      _message      = 'Lost connection to the processing server.';
    });
  }

  void _onStreamDone() {
    if (!mounted) return;
    // Stream closed without an explicit 'done' frame → treat as done if progress is high
    if (!_isDone && !_hasError) {
      setState(() {
        if (_progress >= 0.95) {
          _isDone   = true;
          _progress = 1.0;
          _stage    = 'Complete!';
          _message  = 'Processing finished.';
          Future.delayed(const Duration(seconds: 2), _navigateToDashboard);
        } else {
          _hasError     = true;
          _errorMessage = 'Connection closed unexpectedly. Please try again.';
        }
      });
    }
  }

  // ─────────────────────────────────────────────
  // Navigation
  // ─────────────────────────────────────────────

  void _navigateToDashboard() {
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) =>
            const MainShell(initialIndex: 0),
        transitionsBuilder: (context, animation, secondaryAnimation, child) =>
            FadeTransition(opacity: animation, child: child),
        transitionDuration: const Duration(milliseconds: 600),
      ),
      (_) => false,
    );
  }

  void _retryUpload() {
    Navigator.of(context).pop(); // Go back to Upload screen
  }

  void _cancelProcessing() {
    if (widget.analysisData == null) {
      webSocketService.disconnect();
    }
    Navigator.of(context).pop();
  }

  // ─────────────────────────────────────────────
  // Build
  // ─────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBackground,
      body: Stack(
        children: [
          // ── Ambient glows ──
          Positioned(
            top: -80,
            right: -60,
            child: AuroraBlob(
              color: _hasError
                  ? kError
                  : _isDone
                      ? kSuccess
                      : kPrimary,
              size: 300,
            ),
          ),
          Positioned(
            bottom: -100,
            left: -60,
            child: AuroraBlob(
              color: _hasError
                  ? kError.withValues(alpha: 0.5)
                  : const Color(0xFF6366F1),
              size: 260,
            ),
          ),

          // ── Main content ──
          SafeArea(
            child: Column(
              children: [
                // ── App bar ──
                _buildAppBar(),

                // ── Scrollable body ──
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(20, 8, 20, 40),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        const SizedBox(height: 16),

                        // ── Central progress ring ──
                        _buildProgressRing()
                            .animate()
                            .fadeIn(delay: 200.ms, duration: 600.ms)
                            .scale(
                              begin: const Offset(0.85, 0.85),
                              end: const Offset(1.0, 1.0),
                              delay: 200.ms,
                              duration: 600.ms,
                              curve: Curves.easeOut,
                            ),

                        const SizedBox(height: 32),

                        // ── Stage label ──
                        _buildStageLabel()
                            .animate()
                            .fadeIn(delay: 300.ms, duration: 500.ms)
                            .slideY(begin: 0.2, end: 0, duration: 500.ms),

                        const SizedBox(height: 32),

                        // ── File info card ──
                        _buildFileInfoCard()
                            .animate()
                            .fadeIn(delay: 400.ms, duration: 500.ms)
                            .slideY(begin: 0.2, end: 0, duration: 500.ms),

                        const SizedBox(height: 20),

                        // ── Error card ──
                        if (_hasError)
                          _buildErrorCard()
                              .animate()
                              .fadeIn(duration: 400.ms)
                              .slideY(begin: -0.15, end: 0),

                        // ── Success card ──
                        if (_isDone && !_hasError)
                          _buildSuccessCard()
                              .animate()
                              .fadeIn(duration: 600.ms)
                              .scale(
                                begin: const Offset(0.9, 0.9),
                                end: const Offset(1.0, 1.0),
                                duration: 600.ms,
                                curve: Curves.elasticOut,
                              ),

                        const SizedBox(height: 20),

                        // ── Stage log ──
                        if (_stageLog.isNotEmpty)
                          _buildStageLog()
                              .animate()
                              .fadeIn(delay: 500.ms, duration: 500.ms)
                              .slideY(begin: 0.15, end: 0, duration: 500.ms),

                        const SizedBox(height: 24),

                        // ── Cancel / Retry buttons ──
                        if (!_isDone) _buildActionButtons(),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────
  // Section builders
  // ─────────────────────────────────────────────

  Widget _buildAppBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Row(
        children: [
          // Back / close
          if (!_isDone)
            IconButton(
              onPressed: _cancelProcessing,
              icon: const Icon(Icons.close_rounded,
                  color: kTextSecondary, size: 22),
              tooltip: 'Cancel',
            )
          else
            const SizedBox(width: 48),

          const Spacer(),

          // Title
          Text(
            'Processing',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: kTextPrimary,
                  fontWeight: FontWeight.w700,
                ),
          ),

          const Spacer(),
          const SizedBox(width: 48),
        ],
      ),
    );
  }

  Widget _buildProgressRing() {
    final ringColor = _hasError
        ? kError
        : _isDone
            ? kSuccess
            : kPrimary;

    return AnimatedBuilder(
      animation: _pulseAnim,
      builder: (context, child) {
        return Stack(
          alignment: Alignment.center,
          children: [
            // ── Outer glow ring ──
            if (!_isDone && !_hasError)
              Container(
                width: 200 + 12 * _pulseAnim.value,
                height: 200 + 12 * _pulseAnim.value,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      ringColor.withValues(alpha: 0.08 + 0.06 * _pulseAnim.value),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),

            // ── Circular progress ──
            CircularPercentIndicator(
              radius: 90,
              lineWidth: 12,
              percent: _progress,
              animation: true,
              animationDuration: 600,
              animateFromLastPercent: true,
              circularStrokeCap: CircularStrokeCap.round,
              backgroundColor: Colors.white.withValues(alpha: 0.06),
              linearGradient: _hasError
                  ? null
                  : LinearGradient(
                      colors: _isDone
                          ? [const Color(0xFF34D399), const Color(0xFF10B981)]
                          : [const Color(0xFF38BDF8), const Color(0xFF0EA5E9)],
                    ),
              progressColor: _hasError ? kError : null,
              center: _buildRingCenter(ringColor),
            ),
          ],
        );
      },
    );
  }

  Widget _buildRingCenter(Color accent) {
    if (_hasError) {
      return Container(
        width: 130,
        height: 130,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: kError.withValues(alpha: 0.08),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline_rounded, color: kError, size: 36),
            const SizedBox(height: 6),
            const Text(
              'Error',
              style: TextStyle(
                color: kError,
                fontSize: 13,
                fontWeight: FontWeight.w700,
                fontFamily: 'Outfit',
              ),
            ),
          ],
        ),
      );
    }

    if (_isDone) {
      return Container(
        width: 130,
        height: 130,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: kSuccess.withValues(alpha: 0.10),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.check_circle_rounded, color: kSuccess, size: 40),
            const SizedBox(height: 6),
            const Text(
              'Done!',
              style: TextStyle(
                color: kSuccess,
                fontSize: 14,
                fontWeight: FontWeight.w800,
                fontFamily: 'Outfit',
              ),
            ),
          ],
        ),
      );
    }

    // In-progress center
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          '${(_progress * 100).round()}%',
          style: TextStyle(
            color: accent,
            fontSize: 28,
            fontWeight: FontWeight.w800,
            fontFamily: 'Outfit',
          ),
        ),
        const SizedBox(height: 2),
        Text(
          'complete',
          style: TextStyle(
            color: kTextTertiary,
            fontSize: 12,
            fontFamily: 'Outfit',
          ),
        ),
      ],
    );
  }

  Widget _buildStageLabel() {
    final accent = _hasError
        ? kError
        : _isDone
            ? kSuccess
            : kPrimary;

    return Column(
      children: [
        // Stage pill
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 400),
          transitionBuilder: (child, anim) => FadeTransition(
            opacity: anim,
            child: SlideTransition(
              position: Tween<Offset>(
                begin: const Offset(0, 0.3),
                end: Offset.zero,
              ).animate(anim),
              child: child,
            ),
          ),
          child: Container(
            key: ValueKey(_stage),
            padding:
                const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: accent.withValues(alpha: 0.30), width: 1),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (!_isDone && !_hasError)
                  SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(accent),
                    ),
                  )
                else
                  Icon(
                    _hasError
                        ? Icons.error_rounded
                        : Icons.check_circle_rounded,
                    color: accent,
                    size: 16,
                  ),
                const SizedBox(width: 8),
                Text(
                  _stage,
                  style: TextStyle(
                    color: accent,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    fontFamily: 'Outfit',
                  ),
                ),
              ],
            ),
          ),
        ),

        const SizedBox(height: 14),

        // Dynamic message
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 350),
          child: Text(
            _message,
            key: ValueKey(_message),
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: kTextSecondary,
                  height: 1.5,
                ),
          ),
        ),
      ],
    );
  }

  Widget _buildFileInfoCard() {
    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Row(
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              color: kPrimary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.description_rounded,
                color: kPrimary, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.fileName,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: kTextPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  'Job ID: ${widget.jobId.length > 12 ? widget.jobId.substring(0, 12) : widget.jobId}…',
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: kTextTertiary, fontFamily: 'monospace'),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          // Live dot
          if (!_isDone && !_hasError)
            _PulsingDot(color: kPrimary),
          if (_isDone)
            const Icon(Icons.check_circle_rounded, color: kSuccess, size: 22),
          if (_hasError)
            const Icon(Icons.error_rounded, color: kError, size: 22),
        ],
      ),
    );
  }

  Widget _buildSuccessCard() {
    return GlassCard(
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          kSuccess.withValues(alpha: 0.15),
          kSuccess.withValues(alpha: 0.05),
          Colors.transparent,
        ],
      ),
      border: Border.all(color: kSuccess.withValues(alpha: 0.30), width: 1.5),
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          // Celebration icon
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  kSuccess.withValues(alpha: 0.25),
                  kSuccess.withValues(alpha: 0.05),
                  Colors.transparent,
                ],
              ),
            ),
            child: Center(
              child: Text(
                '🎉',
                style: const TextStyle(fontSize: 38),
              ),
            ),
          ),
          const SizedBox(height: 18),
          Text(
            'Transcript Processed!',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: kTextPrimary,
                  fontWeight: FontWeight.w800,
                ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 10),
          Text(
            'Your transcript has been analysed on the backend. Redirecting to your results…',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: kTextSecondary,
                  height: 1.5,
                ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 20),
          GradientButton(
            label: 'View Dashboard',
            icon: Icons.dashboard_rounded,
            onPressed: _navigateToDashboard,
          ),
        ],
      ),
    );
  }

  Widget _buildErrorCard() {
    return GlassCard(
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          kError.withValues(alpha: 0.12),
          kError.withValues(alpha: 0.04),
          Colors.transparent,
        ],
      ),
      border: Border.all(color: kError.withValues(alpha: 0.30), width: 1.5),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: kError.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.error_outline_rounded,
                    color: kError, size: 22),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Processing Failed',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            color: kTextPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'An error occurred during OCR processing.',
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: kTextSecondary),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (_errorMessage != null && _errorMessage!.isNotEmpty) ...[
            const SizedBox(height: 14),
            const Divider(color: kBorder),
            const SizedBox(height: 12),
            Text(
              'Error details',
              style: Theme.of(context)
                  .textTheme
                  .labelSmall
                  ?.copyWith(color: kTextTertiary, letterSpacing: 0.8),
            ),
            const SizedBox(height: 6),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.25),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                _errorMessage!,
                style: const TextStyle(
                  color: kError,
                  fontSize: 12,
                  fontFamily: 'monospace',
                  height: 1.5,
                ),
              ),
            ),
          ],
          const SizedBox(height: 18),
          GradientButton(
            label: 'Try Again',
            icon: Icons.refresh_rounded,
            onPressed: _retryUpload,
          ),
        ],
      ),
    );
  }

  Widget _buildStageLog() {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.receipt_long_rounded,
                  size: 18, color: kTextTertiary),
              const SizedBox(width: 10),
              Text(
                'Processing Log',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: kTextPrimary,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Log entries (newest first)
          ..._stageLog.reversed.take(8).toList().asMap().entries.map((e) {
            final entry = e.value;
            final isFirst = e.key == 0;
            return _LogEntry(entry: entry, isLatest: isFirst)
                .animate(key: ValueKey('${entry.time}'))
                .fadeIn(duration: 400.ms)
                .slideX(begin: 0.05, end: 0, duration: 400.ms);
          }),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (_hasError)
          ElevatedButton.icon(
            onPressed: _retryUpload,
            icon: const Icon(Icons.refresh_rounded, size: 18),
            label: const Text('Try Again'),
            style: ElevatedButton.styleFrom(
              backgroundColor: kError,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
              padding:
                  const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            ),
          )
        else
          TextButton.icon(
            onPressed: _cancelProcessing,
            icon: const Icon(Icons.cancel_outlined,
                size: 18, color: kTextTertiary),
            label: const Text(
              'Cancel',
              style: TextStyle(color: kTextTertiary, fontSize: 14),
            ),
          ),
      ],
    )
        .animate()
        .fadeIn(delay: 600.ms, duration: 400.ms);
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Stage Log Entry Model
// ═══════════════════════════════════════════════════════════════════════════════

class _StageEntry {
  const _StageEntry({
    required this.stage,
    required this.message,
    required this.icon,
    required this.isError,
    required this.time,
  });

  final String stage;
  final String message;
  final IconData icon;
  final bool isError;
  final DateTime time;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Log Entry Widget
// ═══════════════════════════════════════════════════════════════════════════════

class _LogEntry extends StatelessWidget {
  const _LogEntry({required this.entry, required this.isLatest});

  final _StageEntry entry;
  final bool isLatest;

  @override
  Widget build(BuildContext context) {
    final accent = entry.isError ? kError : (isLatest ? kPrimary : kTextTertiary);
    final timeStr =
        '${entry.time.hour.toString().padLeft(2, '0')}:${entry.time.minute.toString().padLeft(2, '0')}:${entry.time.second.toString().padLeft(2, '0')}';

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline dot + line
          Column(
            children: [
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: accent.withValues(alpha: 0.12),
                  border: Border.all(
                    color: accent.withValues(alpha: isLatest ? 0.5 : 0.2),
                    width: 1,
                  ),
                ),
                child: Icon(entry.icon, size: 14, color: accent),
              ),
            ],
          ),
          const SizedBox(width: 12),
          // Content
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      entry.stage,
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                            color: isLatest ? kTextPrimary : kTextSecondary,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const Spacer(),
                    Text(
                      timeStr,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: kTextTertiary,
                            fontSize: 11,
                            fontFamily: 'monospace',
                          ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  entry.message,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: kTextTertiary,
                        height: 1.4,
                      ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Pulsing Dot — live indicator
// ═══════════════════════════════════════════════════════════════════════════════

class _PulsingDot extends StatefulWidget {
  const _PulsingDot({required this.color});
  final Color color;

  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
    _anim = CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (context, child) => Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: widget.color.withValues(alpha: 0.5 + 0.5 * _anim.value),
          boxShadow: [
            BoxShadow(
              color: widget.color.withValues(alpha: 0.4 * _anim.value),
              blurRadius: 8,
              spreadRadius: 2,
            ),
          ],
        ),
      ),
    );
  }
}
