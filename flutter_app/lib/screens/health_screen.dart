import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:percent_indicator/percent_indicator.dart';

import '../models/health_model.dart';
import '../services/api_service.dart';
import '../widgets/glass_widgets.dart';

class HealthScreen extends StatefulWidget {
  const HealthScreen({super.key});

  @override
  State<HealthScreen> createState() => _HealthScreenState();
}

class _HealthScreenState extends State<HealthScreen>
    with AutomaticKeepAliveClientMixin, SingleTickerProviderStateMixin {
  @override
  bool get wantKeepAlive => true;

  // ── State ──
  HealthModel? _health;
  bool _isLoading = true;
  bool _isRefreshing = false;
  String? _error;

  // ── Uptime counter (client-side ticker) ──
  int _uptimeTicker = 0;

  // ── Latency history (last N readings per layer) ──
  final _backendHistory  = <int>[];
  final _dbHistory       = <int>[];
  final _ocrHistory      = <int>[];
  static const _historyMax = 20;

  // ── Timers ──
  Timer? _pollTimer;
  Timer? _uptimeTimer;

  // ── Animation ──
  late final AnimationController _pulseCtrl;

  @override
  void initState() {
    super.initState();

    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _fetchHealth();
    _startPolling();
    _startUptimeTicker();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _uptimeTimer?.cancel();
    _pulseCtrl.dispose();
    super.dispose();
  }

  // ─────────────────────────────────────────────
  // Data fetching
  // ─────────────────────────────────────────────

  Future<void> _fetchHealth({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _isLoading = _health == null;
        _isRefreshing = _health != null;
        _error = null;
      });
    }

    try {
      final raw = await apiService.getHealth();
      if (!mounted) return;

      final model = HealthModel.fromJson(raw);

      // Append latency history
      _appendHistory(_backendHistory, model.backend.latencyMs);
      _appendHistory(_dbHistory, model.database.latencyMs);
      _appendHistory(_ocrHistory, model.ocr.latencyMs);

      // Reset uptime ticker to server value
      _uptimeTicker = model.uptimeSeconds;

      setState(() {
        _health = model;
        _isLoading = false;
        _isRefreshing = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        if (_health == null) {
          _health = HealthModel.error();
          _error = 'Could not reach health endpoint.';
        }
        _isLoading = false;
        _isRefreshing = false;
      });
    }
  }

  void _appendHistory(List<int> list, int value) {
    list.add(value);
    if (list.length > _historyMax) list.removeAt(0);
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (mounted) _fetchHealth(silent: true);
    });
  }

  void _startUptimeTicker() {
    _uptimeTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted && _health != null) {
        setState(() => _uptimeTicker++);
      }
    });
  }

  Future<void> _onRefresh() => _fetchHealth();

  // ─────────────────────────────────────────────
  // Helpers
  // ─────────────────────────────────────────────

  String _formatUptime(int seconds) {
    final d = seconds ~/ 86400;
    final h = (seconds % 86400) ~/ 3600;
    final m = (seconds % 3600) ~/ 60;
    final s = seconds % 60;
    if (d > 0) return '${d}d ${h}h ${m}m';
    if (h > 0) return '${h}h ${m}m ${s}s';
    if (m > 0) return '${m}m ${s}s';
    return '${s}s';
  }

  Color _statusColor(String status) {
    switch (status.toLowerCase()) {
      case 'up':
      case 'healthy':
      case 'ok':
      case 'operational':
      case 'connected':
      case 'active':
      case 'ready':
        return kSuccess;
      case 'degraded':
      case 'slow':
      case 'not_configured':
        return kWarning;
      case 'down':
      case 'unhealthy':
      case 'unreachable':
      case 'disconnected':
        return kError;
      default:
        return kTextTertiary;
    }
  }

  String _statusLabel(String status) {
    switch (status.toLowerCase()) {
      case 'up':
      case 'healthy':
      case 'ok':
      case 'operational':
      case 'connected':
      case 'active':
      case 'ready':
        return 'Operational';
      case 'degraded':
      case 'slow':
      case 'not_configured':
        return 'Degraded';
      case 'down':
      case 'unhealthy':
      case 'disconnected':
        return 'Down';
      case 'unreachable':
        return 'Unreachable';
      default:
        return 'Unknown';
    }
  }

  Color _latencyColor(int ms) {
    if (ms <= 100) return kSuccess;
    if (ms <= 400) return kWarning;
    return kError;
  }

  double _latencyPercent(int ms) => (ms / 1000.0).clamp(0.0, 1.0);

  // ─────────────────────────────────────────────
  // Build
  // ─────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    super.build(context);

    return RefreshIndicator(
      onRefresh: _onRefresh,
      color: kPrimary,
      backgroundColor: kSurface,
      child: Stack(
        children: [
          // ── Ambient glows ──
          const Positioned(
            top: -80,
            right: -60,
            child: AuroraBlob(color: kWarning, size: 240),
          ),
          const Positioned(
            bottom: -80,
            left: -60,
            child: AuroraBlob(color: kSuccess, size: 220),
          ),
          Positioned(
            top: 300,
            right: -40,
            child: AuroraBlob(color: kPrimary, size: 180),
          ),

          // ── Main scroll ──
          CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 100),
                sliver: SliverList(
                  delegate: SliverChildListDelegate(
                    _isLoading ? _buildShimmer() : _buildContent(),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────
  // Content builder
  // ─────────────────────────────────────────────

  List<Widget> _buildContent() {
    final h = _health;
    if (h == null) return [_buildError('No data available.')];

    return [
      // ── Overall status hero ──
      _OverallStatusCard(
        health: h,
        uptimeSeconds: _uptimeTicker,
        isRefreshing: _isRefreshing,
        pulseCtrl: _pulseCtrl,
        formatUptime: _formatUptime,
        statusColor: _statusColor,
        statusLabel: _statusLabel,
      )
          .animate()
          .fadeIn(duration: 500.ms)
          .slideY(begin: 0.2, end: 0, duration: 500.ms, curve: Curves.easeOut),

      const SizedBox(height: 20),

      // ── Error banner if needed ──
      if (_error != null)
        _buildErrorBanner(_error!)
            .animate()
            .fadeIn(duration: 300.ms)
            .slideY(begin: -0.15, end: 0),

      if (_error != null) const SizedBox(height: 16),

      // ── Poll indicator ──
      _PollIndicator(isRefreshing: _isRefreshing)
          .animate()
          .fadeIn(delay: 100.ms, duration: 400.ms),

      const SizedBox(height: 20),

      // ── Section header ──
      SectionHeader(
        eyebrow: 'Layer Status',
        title: 'Infrastructure Health',
      ).animate().fadeIn(delay: 150.ms, duration: 400.ms),

      const SizedBox(height: 16),

      // ── Backend layer ──
      _LayerCard(
        label: 'Backend API',
        subtitle: 'FastAPI server & routing',
        icon: Icons.cloud_rounded,
        accent: kPrimary,
        layer: h.backend,
        history: _backendHistory,
        latencyColor: _latencyColor,
        latencyPercent: _latencyPercent,
        statusColor: _statusColor,
        statusLabel: _statusLabel,
      )
          .animate()
          .fadeIn(delay: 200.ms, duration: 450.ms)
          .slideY(begin: 0.15, end: 0, duration: 450.ms, curve: Curves.easeOut),

      const SizedBox(height: 14),

      // ── Database layer ──
      _LayerCard(
        label: 'Database',
        subtitle: 'PostgreSQL / Supabase',
        icon: Icons.storage_rounded,
        accent: const Color(0xFF818CF8),
        layer: h.database,
        history: _dbHistory,
        latencyColor: _latencyColor,
        latencyPercent: _latencyPercent,
        statusColor: _statusColor,
        statusLabel: _statusLabel,
      )
          .animate()
          .fadeIn(delay: 270.ms, duration: 450.ms)
          .slideY(begin: 0.15, end: 0, duration: 450.ms, curve: Curves.easeOut),

      const SizedBox(height: 14),

      // ── OCR Engine layer ──
      _LayerCard(
        label: 'OCR Engine',
        subtitle: 'AI transcript extraction',
        icon: Icons.document_scanner_rounded,
        accent: kWarning,
        layer: h.ocr,
        history: _ocrHistory,
        latencyColor: _latencyColor,
        latencyPercent: _latencyPercent,
        statusColor: _statusColor,
        statusLabel: _statusLabel,
      )
          .animate()
          .fadeIn(delay: 340.ms, duration: 450.ms)
          .slideY(begin: 0.15, end: 0, duration: 450.ms, curve: Curves.easeOut),

      const SizedBox(height: 24),

      // ── Latency comparison ──
      _LatencyComparison(
        backend: h.backend.latencyMs,
        database: h.database.latencyMs,
        ocr: h.ocr.latencyMs,
        latencyColor: _latencyColor,
      )
          .animate()
          .fadeIn(delay: 400.ms, duration: 450.ms)
          .slideY(begin: 0.15, end: 0, duration: 450.ms, curve: Curves.easeOut),

      const SizedBox(height: 24),

      // ── Polling info footer ──
      _PollingFooter()
          .animate()
          .fadeIn(delay: 460.ms, duration: 400.ms),
    ];
  }

  Widget _buildErrorBanner(String message) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: kError.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: kError.withValues(alpha: 0.30), width: 1),
      ),
      child: Row(
        children: [
          const Icon(Icons.wifi_off_rounded, color: kError, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                color: kError,
                fontSize: 13,
                fontWeight: FontWeight.w500,
                fontFamily: 'Outfit',
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildError(String message) {
    return Padding(
      padding: const EdgeInsets.only(top: 60),
      child: EmptyState(
        icon: Icons.monitor_heart_outlined,
        title: 'Health data unavailable',
        subtitle: message,
        accent: kError,
        action: ElevatedButton.icon(
          onPressed: _fetchHealth,
          icon: const Icon(Icons.refresh_rounded, size: 18),
          label: const Text('Retry'),
          style: ElevatedButton.styleFrom(
            backgroundColor: kError,
            foregroundColor: Colors.white,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────
  // Shimmer loading
  // ─────────────────────────────────────────────

  List<Widget> _buildShimmer() => [
        const SizedBox(height: 8),
        _shimmer(height: 200),
        const SizedBox(height: 20),
        _shimmer(height: 36, width: 200),
        const SizedBox(height: 20),
        _shimmer(height: 24, width: 140),
        const SizedBox(height: 14),
        _shimmer(height: 130),
        const SizedBox(height: 14),
        _shimmer(height: 130),
        const SizedBox(height: 14),
        _shimmer(height: 130),
        const SizedBox(height: 20),
        _shimmer(height: 160),
      ];

  Widget _shimmer({required double height, double? width}) => Container(
        height: height,
        width: width ?? double.infinity,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          color: kSurface,
        ),
        child: ShimmerBox(height: height, borderRadius: 20),
      );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Overall Status Hero Card
// ═══════════════════════════════════════════════════════════════════════════════

class _OverallStatusCard extends StatelessWidget {
  const _OverallStatusCard({
    required this.health,
    required this.uptimeSeconds,
    required this.isRefreshing,
    required this.pulseCtrl,
    required this.formatUptime,
    required this.statusColor,
    required this.statusLabel,
  });

  final HealthModel health;
  final int uptimeSeconds;
  final bool isRefreshing;
  final AnimationController pulseCtrl;
  final String Function(int) formatUptime;
  final Color Function(String) statusColor;
  final String Function(String) statusLabel;

  @override
  Widget build(BuildContext context) {
    final accent = statusColor(health.overallStatus);
    final label = statusLabel(health.overallStatus);
    final isHealthy = health.isHealthy;

    return ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: AnimatedBuilder(
          animation: pulseCtrl,
          builder: (context, child) => Container(
            width: double.infinity,
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  accent.withValues(alpha: 0.15 + 0.05 * pulseCtrl.value),
                  accent.withValues(alpha: 0.04),
                  Colors.white.withValues(alpha: 0.03),
                ],
                stops: const [0.0, 0.5, 1.0],
              ),
              border: Border.all(
                color: accent.withValues(alpha: 0.30 + 0.10 * pulseCtrl.value),
                width: 1.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: accent.withValues(alpha: 0.10 + 0.06 * pulseCtrl.value),
                  blurRadius: 40,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              children: [
                // ── Top row: icon + label + status ──
                Row(
                  children: [
                    // Pulsing status circle
                    Stack(
                      alignment: Alignment.center,
                      children: [
                        Container(
                          width: 70 + 6 * pulseCtrl.value,
                          height: 70 + 6 * pulseCtrl.value,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: RadialGradient(
                              colors: [
                                accent.withValues(alpha: 
                                    0.18 + 0.10 * pulseCtrl.value),
                                Colors.transparent,
                              ],
                            ),
                          ),
                        ),
                        Container(
                          width: 58,
                          height: 58,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: accent.withValues(alpha: 0.15),
                            border: Border.all(
                              color: accent.withValues(alpha: 0.40),
                              width: 2,
                            ),
                          ),
                          child: Icon(
                            isHealthy
                                ? Icons.check_circle_outline_rounded
                                : Icons.warning_amber_rounded,
                            color: accent,
                            size: 28,
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(width: 20),

                    // Title + label
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'System Status',
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(
                                    color: kTextTertiary,
                                    letterSpacing: 0.8),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            label,
                            style: Theme.of(context)
                                .textTheme
                                .headlineMedium
                                ?.copyWith(
                                  color: accent,
                                  fontWeight: FontWeight.w800,
                                  fontSize: 26,
                                ),
                          ),
                          const SizedBox(height: 6),
                          // Three layer dots summary
                          Row(
                            children: [
                              _SmallDot(status: health.backend.status),
                              const SizedBox(width: 6),
                              _SmallDot(status: health.database.status),
                              const SizedBox(width: 6),
                              _SmallDot(status: health.ocr.status),
                              const SizedBox(width: 8),
                              Text(
                                '3 layers monitored',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(color: kTextTertiary),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),

                    // Refreshing indicator
                    if (isRefreshing)
                      SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(accent),
                        ),
                      ),
                  ],
                ),

                const SizedBox(height: 24),
                const Divider(color: kBorder, height: 1),
                const SizedBox(height: 20),

                // ── Uptime + meta row ──
                Row(
                  children: [
                    Expanded(
                      child: _MetaCell(
                        icon: Icons.timer_outlined,
                        label: 'Uptime',
                        value: formatUptime(uptimeSeconds),
                        accent: kSuccess,
                      ),
                    ),
                    Container(width: 1, height: 40, color: kBorder),
                    Expanded(
                      child: _MetaCell(
                        icon: Icons.speed_rounded,
                        label: 'Avg Latency',
                        value: _avgLatency(),
                        accent: kPrimary,
                      ),
                    ),
                    Container(width: 1, height: 40, color: kBorder),
                    Expanded(
                      child: _MetaCell(
                        icon: Icons.update_rounded,
                        label: 'Poll Rate',
                        value: 'Every 3s',
                        accent: kWarning,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _avgLatency() {
    final total =
        health.backend.latencyMs + health.database.latencyMs + health.ocr.latencyMs;
    final avg = total ~/ 3;
    return '${avg}ms';
  }
}

class _SmallDot extends StatelessWidget {
  const _SmallDot({required this.status});
  final String status;

  Color get _color {
    switch (status.toLowerCase()) {
      case 'up':
      case 'healthy':
      case 'ok':
      case 'operational':
      case 'connected':
      case 'active':
      case 'ready':
        return kSuccess;
      case 'degraded':
      case 'slow':
      case 'not_configured':
        return kWarning;
      default:
        return kError;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: _color,
        boxShadow: [
          BoxShadow(color: _color.withValues(alpha: 0.6), blurRadius: 4, spreadRadius: 1),
        ],
      ),
    );
  }
}

class _MetaCell extends StatelessWidget {
  const _MetaCell({
    required this.icon,
    required this.label,
    required this.value,
    required this.accent,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: accent, size: 20),
        const SizedBox(height: 6),
        Text(
          value,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: kTextPrimary,
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: Theme.of(context)
              .textTheme
              .bodySmall
              ?.copyWith(color: kTextTertiary, fontSize: 11),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Poll Indicator
// ═══════════════════════════════════════════════════════════════════════════════

class _PollIndicator extends StatelessWidget {
  const _PollIndicator({required this.isRefreshing});
  final bool isRefreshing;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          child: isRefreshing
              ? SizedBox(
                  key: const ValueKey('loading'),
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor:
                        AlwaysStoppedAnimation<Color>(kPrimary.withValues(alpha: 0.7)),
                  ),
                )
              : const Icon(
                  key: ValueKey('check'),
                  Icons.sync_rounded,
                  color: kSuccess,
                  size: 16,
                ),
        ),
        const SizedBox(width: 8),
        Text(
          isRefreshing ? 'Fetching live data…' : 'Auto-refreshing every 3 seconds',
          style: Theme.of(context)
              .textTheme
              .bodySmall
              ?.copyWith(color: kTextTertiary, fontSize: 12),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Layer Card
// ═══════════════════════════════════════════════════════════════════════════════

class _LayerCard extends StatefulWidget {
  const _LayerCard({
    required this.label,
    required this.subtitle,
    required this.icon,
    required this.accent,
    required this.layer,
    required this.history,
    required this.latencyColor,
    required this.latencyPercent,
    required this.statusColor,
    required this.statusLabel,
  });

  final String label;
  final String subtitle;
  final IconData icon;
  final Color accent;
  final LayerHealth layer;
  final List<int> history;
  final Color Function(int) latencyColor;
  final double Function(int) latencyPercent;
  final Color Function(String) statusColor;
  final String Function(String) statusLabel;

  @override
  State<_LayerCard> createState() => _LayerCardState();
}

class _LayerCardState extends State<_LayerCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final sc = widget.statusColor(widget.layer.status);
    final sl = widget.statusLabel(widget.layer.status);
    final lc = widget.latencyColor(widget.layer.latencyMs);
    final lp = widget.latencyPercent(widget.layer.latencyMs);

    return GestureDetector(
      onTap: () => setState(() => _expanded = !_expanded),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  widget.accent.withValues(alpha: 0.08),
                  Colors.white.withValues(alpha: 0.03),
                ],
              ),
              border: Border.all(
                color: widget.accent.withValues(alpha: 0.22),
                width: 1,
              ),
            ),
            child: Column(
              children: [
                // ── Main row ──
                Padding(
                  padding: const EdgeInsets.all(18),
                  child: Row(
                    children: [
                      // Icon
                      Container(
                        width: 48,
                        height: 48,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(14),
                          gradient: LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              widget.accent.withValues(alpha: 0.22),
                              widget.accent.withValues(alpha: 0.08),
                            ],
                          ),
                          border: Border.all(
                            color: widget.accent.withValues(alpha: 0.30),
                            width: 1,
                          ),
                        ),
                        child: Icon(widget.icon,
                            color: widget.accent, size: 24),
                      ),

                      const SizedBox(width: 14),

                      // Label + subtitle
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              widget.label,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    color: kTextPrimary,
                                    fontWeight: FontWeight.w700,
                                  ),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              widget.subtitle,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(color: kTextTertiary),
                            ),
                          ],
                        ),
                      ),

                      // Status badge
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          // Status dot + label
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              _AnimatedStatusDot(
                                color: sc,
                                isOk: widget.layer.isUp,
                              ),
                              const SizedBox(width: 6),
                              Text(
                                sl,
                                style: TextStyle(
                                  color: sc,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  fontFamily: 'Outfit',
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          // Latency
                          Text(
                            '${widget.layer.latencyMs}ms',
                            style: TextStyle(
                              color: lc,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              fontFamily: 'Outfit',
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(width: 10),

                      // Expand chevron
                      Icon(
                        _expanded
                            ? Icons.keyboard_arrow_up_rounded
                            : Icons.keyboard_arrow_down_rounded,
                        color: kTextTertiary,
                        size: 20,
                      ),
                    ],
                  ),
                ),

                // ── Latency bar ──
                Padding(
                  padding: const EdgeInsets.fromLTRB(18, 0, 18, 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'Latency',
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(
                                    color: kTextTertiary, fontSize: 11),
                          ),
                          Text(
                            _latencyLabel(widget.layer.latencyMs),
                            style: TextStyle(
                              color: lc,
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              fontFamily: 'Outfit',
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      LinearPercentIndicator(
                        percent: lp,
                        lineHeight: 6,
                        animation: true,
                        animationDuration: 600,
                        animateFromLastPercent: true,
                        backgroundColor: Colors.white.withValues(alpha: 0.06),
                        progressColor: lc,
                        barRadius: const Radius.circular(999),
                        padding: EdgeInsets.zero,
                        trailing: const SizedBox.shrink(),
                        leading: const SizedBox.shrink(),
                      ),
                    ],
                  ),
                ),

                // ── Expanded details ──
                AnimatedSize(
                  duration: const Duration(milliseconds: 300),
                  curve: Curves.easeInOut,
                  child: _expanded
                      ? _LayerExpandedDetails(
                          layer: widget.layer,
                          history: widget.history,
                          latencyColor: widget.latencyColor,
                          accent: widget.accent,
                        )
                      : const SizedBox.shrink(),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _latencyLabel(int ms) {
    if (ms <= 50) return 'Excellent';
    if (ms <= 100) return 'Good';
    if (ms <= 300) return 'Fair';
    if (ms <= 600) return 'Slow';
    return 'Critical';
  }
}

class _LayerExpandedDetails extends StatelessWidget {
  const _LayerExpandedDetails({
    required this.layer,
    required this.history,
    required this.latencyColor,
    required this.accent,
  });

  final LayerHealth layer;
  final List<int> history;
  final Color Function(int) latencyColor;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final maxHistory = history.isEmpty ? 0 : history.reduce((a, b) => a > b ? a : b);
    final avg = history.isEmpty
        ? 0
        : history.fold(0, (sum, v) => sum + v) ~/ history.length;
    final min = history.isEmpty ? 0 : history.reduce((a, b) => a < b ? a : b);
    final max = history.isEmpty ? 0 : history.reduce((a, b) => a > b ? a : b);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(color: kBorder, height: 1),
          const SizedBox(height: 16),

          // ── Latency stats ──
          Row(
            children: [
              Expanded(
                  child: _StatMini(label: 'Current', value: '${layer.latencyMs}ms', accent: accent)),
              const SizedBox(width: 8),
              Expanded(
                  child: _StatMini(label: 'Avg', value: '${avg}ms', accent: kPrimary)),
              const SizedBox(width: 8),
              Expanded(
                  child: _StatMini(label: 'Min', value: '${min}ms', accent: kSuccess)),
              const SizedBox(width: 8),
              Expanded(
                  child: _StatMini(label: 'Max', value: '${max}ms', accent: kError)),
            ],
          ),

          // ── History sparkline ──
          if (history.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              'LATENCY HISTORY',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: kTextTertiary,
                    letterSpacing: 1.2,
                  ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: 48,
              child: _SparkLine(
                values: history.map((v) => v.toDouble()).toList(),
                maxVal: maxHistory.toDouble() > 0
                    ? maxHistory.toDouble()
                    : 100,
                color: accent,
              ),
            ),
          ],

          // ── Extra message ──
          if (layer.message != null && layer.message!.isNotEmpty) ...[
            const SizedBox(height: 14),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.04),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: kBorder),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline_rounded,
                      size: 15, color: kTextTertiary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      layer.message!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: kTextSecondary,
                          ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _StatMini extends StatelessWidget {
  const _StatMini({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: kBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(color: kTextTertiary, fontSize: 10),
          ),
          const SizedBox(height: 3),
          Text(
            value,
            style: TextStyle(
              color: accent,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              fontFamily: 'Outfit',
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Sparkline painter
// ═══════════════════════════════════════════════════════════════════════════════

class _SparkLine extends StatelessWidget {
  const _SparkLine({
    required this.values,
    required this.maxVal,
    required this.color,
  });

  final List<double> values;
  final double maxVal;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: const Size(double.infinity, 48),
      painter: _SparkLinePainter(
        values: values,
        maxVal: maxVal,
        color: color,
      ),
    );
  }
}

class _SparkLinePainter extends CustomPainter {
  _SparkLinePainter({
    required this.values,
    required this.maxVal,
    required this.color,
  });

  final List<double> values;
  final double maxVal;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;

    final paint = Paint()
      ..color = color
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [color.withValues(alpha: 0.35), color.withValues(alpha: 0.02)],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..style = PaintingStyle.fill;

    final step = size.width / (values.length - 1).clamp(1, double.infinity);
    final path = Path();
    final fillPath = Path();

    for (int i = 0; i < values.length; i++) {
      final x = i * step;
      final normalised = maxVal > 0 ? (values[i] / maxVal) : 0.0;
      final y = size.height - (normalised * size.height).clamp(2.0, size.height - 2);

      if (i == 0) {
        path.moveTo(x, y);
        fillPath.moveTo(x, size.height);
        fillPath.lineTo(x, y);
      } else {
        final prev = values[i - 1];
        final prevX = (i - 1) * step;
        final prevNorm = maxVal > 0 ? (prev / maxVal) : 0.0;
        final prevY =
            size.height - (prevNorm * size.height).clamp(2.0, size.height - 2);
        final cpX = (prevX + x) / 2;
        path.cubicTo(cpX, prevY, cpX, y, x, y);
        fillPath.cubicTo(cpX, prevY, cpX, y, x, y);
      }
    }

    fillPath.lineTo((values.length - 1) * step, size.height);
    fillPath.close();

    canvas.drawPath(fillPath, fillPaint);
    canvas.drawPath(path, paint);

    // Draw dots at each data point
    final dotPaint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    for (int i = 0; i < values.length; i++) {
      final x = i * step;
      final normalised = maxVal > 0 ? (values[i] / maxVal) : 0.0;
      final y = size.height - (normalised * size.height).clamp(2.0, size.height - 2);
      canvas.drawCircle(Offset(x, y), 2.5, dotPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _SparkLinePainter old) =>
      old.values != values || old.color != color;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Animated Status Dot
// ═══════════════════════════════════════════════════════════════════════════════

class _AnimatedStatusDot extends StatefulWidget {
  const _AnimatedStatusDot({required this.color, required this.isOk});
  final Color color;
  final bool isOk;

  @override
  State<_AnimatedStatusDot> createState() => _AnimatedStatusDotState();
}

class _AnimatedStatusDotState extends State<_AnimatedStatusDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _anim = CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut);
    if (widget.isOk) _ctrl.repeat(reverse: true);
  }

  @override
  void didUpdateWidget(covariant _AnimatedStatusDot oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isOk && !_ctrl.isAnimating) {
      _ctrl.repeat(reverse: true);
    } else if (!widget.isOk && _ctrl.isAnimating) {
      _ctrl.stop();
      _ctrl.value = 0;
    }
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
      builder: (context, child) => Stack(
        alignment: Alignment.center,
        children: [
          // Outer ring (pulsing)
          if (widget.isOk)
            Container(
              width: 16 + 4 * _anim.value,
              height: 16 + 4 * _anim.value,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: widget.color
                    .withValues(alpha: 0.20 * (1 - _anim.value)),
              ),
            ),
          // Inner dot
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: widget.color,
              boxShadow: [
                BoxShadow(
                  color: widget.color
                      .withValues(alpha: 0.4 + 0.3 * _anim.value),
                  blurRadius: 6 + 4 * _anim.value,
                  spreadRadius: 1,
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
// Latency Comparison Card
// ═══════════════════════════════════════════════════════════════════════════════

class _LatencyComparison extends StatelessWidget {
  const _LatencyComparison({
    required this.backend,
    required this.database,
    required this.ocr,
    required this.latencyColor,
  });

  final int backend;
  final int database;
  final int ocr;
  final Color Function(int) latencyColor;

  @override
  Widget build(BuildContext context) {
    final maxMs = [backend, database, ocr]
        .reduce((a, b) => a > b ? a : b)
        .clamp(1, 9999);

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionHeader(
            eyebrow: 'Performance',
            title: 'Latency Comparison',
          ),
          const SizedBox(height: 20),

          _LatencyBar(
            label: 'Backend API',
            icon: Icons.cloud_rounded,
            value: backend,
            maxVal: maxMs,
            color: latencyColor(backend),
          ),
          const SizedBox(height: 14),

          _LatencyBar(
            label: 'Database',
            icon: Icons.storage_rounded,
            value: database,
            maxVal: maxMs,
            color: latencyColor(database),
          ),
          const SizedBox(height: 14),

          _LatencyBar(
            label: 'OCR Engine',
            icon: Icons.document_scanner_rounded,
            value: ocr,
            maxVal: maxMs,
            color: latencyColor(ocr),
          ),

          const SizedBox(height: 20),
          const Divider(color: kBorder),
          const SizedBox(height: 14),

          // Legend
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _LegendChip(color: kSuccess, label: '≤100ms Excellent'),
              const SizedBox(width: 12),
              _LegendChip(color: kWarning, label: '≤400ms Fair'),
              const SizedBox(width: 12),
              _LegendChip(color: kError, label: '>400ms Slow'),
            ],
          ),
        ],
      ),
    );
  }
}

class _LatencyBar extends StatelessWidget {
  const _LatencyBar({
    required this.label,
    required this.icon,
    required this.value,
    required this.maxVal,
    required this.color,
  });

  final String label;
  final IconData icon;
  final int value;
  final int maxVal;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final pct = maxVal > 0 ? (value / maxVal).clamp(0.0, 1.0) : 0.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 15, color: color),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                label,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: kTextSecondary),
              ),
            ),
            Text(
              '${value}ms',
              style: TextStyle(
                color: color,
                fontSize: 13,
                fontWeight: FontWeight.w700,
                fontFamily: 'Outfit',
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        LinearPercentIndicator(
          percent: pct,
          lineHeight: 8,
          animation: true,
          animationDuration: 700,
          animateFromLastPercent: true,
          backgroundColor: Colors.white.withValues(alpha: 0.06),
          progressColor: color,
          barRadius: const Radius.circular(999),
          padding: EdgeInsets.zero,
          trailing: const SizedBox.shrink(),
          leading: const SizedBox.shrink(),
        ),
      ],
    );
  }
}

class _LegendChip extends StatelessWidget {
  const _LegendChip({required this.color, required this.label});
  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(shape: BoxShape.circle, color: color),
        ),
        const SizedBox(width: 5),
        Text(
          label,
          style: Theme.of(context)
              .textTheme
              .bodySmall
              ?.copyWith(color: kTextTertiary, fontSize: 10),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Polling Footer
// ═══════════════════════════════════════════════════════════════════════════════

class _PollingFooter extends StatelessWidget {
  const _PollingFooter();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        padding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: kBorder),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.radar_rounded, size: 14, color: kPrimary),
            const SizedBox(width: 8),
            Text(
              'Live monitoring • ocrapi.nsunexus.app/health/realtime',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: kTextTertiary,
                    fontSize: 11,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
