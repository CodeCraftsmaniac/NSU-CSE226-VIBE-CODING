import 'package:flutter/material.dart';

import 'home_screen.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) => const HomeScreen();
}

/*
Legacy dashboard implementation retained only as commented reference. The
active app now routes dashboard/result traffic through HomeScreen so the app
shows the same backend result structure as the website.

import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:percent_indicator/percent_indicator.dart';

import '../models/analysis_model.dart';
import '../models/course_model.dart';
import '../services/auth_service.dart' hide ApiException;
import '../services/analysis_session_service.dart';
import '../services/api_service.dart';
import '../widgets/glass_widgets.dart';
import 'auth_screen.dart';
import 'courses_screen.dart';
import 'upload_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  AnalysisModel? _analysis;
  bool _isLoading = true;
  String? _error;
  bool _isGuest = false;

  @override
  void initState() {
    super.initState();
    _loadAnalysis();
  }

  Future<void> _loadAnalysis() async {
    final cachedAnalysis = analysisSessionService.latestAnalysis;

    setState(() {
      _analysis = cachedAnalysis;
      _isLoading = true;
      _isGuest = false;
      _error = null;
    });

    if (cachedAnalysis != null && !authService.isAuthenticated) {
      setState(() {
        _analysis = cachedAnalysis;
        _isLoading = false;
      });
      return;
    }

    if (authService.isGuestMode) {
      setState(() {
        _analysis = null;
        _isGuest = true;
        _isLoading = false;
      });
      return;
    }

    try {
      final raw = await apiService.getAnalysis();
      analysisSessionService.setLatestAnalysis(raw);
      if (!mounted) return;
      setState(() {
        _analysis = analysisSessionService.latestAnalysis;
        _isLoading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = cachedAnalysis == null ? e.message : null;
        _analysis = cachedAnalysis;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = cachedAnalysis == null
            ? 'Failed to load analysis. Pull down to refresh.'
            : null;
        _analysis = cachedAnalysis;
        _isLoading = false;
      });
    }
  }

  void _navigateToUpload() {
    // Switch to upload tab in the shell via PageView
    final shell = context.findAncestorStateOfType<State>();
    if (shell == null) return;
    // Fallback: push directly
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const UploadScreen()),
    );
  }

  void _navigateToCourses() {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const CoursesScreen()),
    );
  }

  void _navigateToAuth() {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const AuthScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return RefreshIndicator(
      onRefresh: _loadAnalysis,
      color: kPrimary,
      backgroundColor: kSurface,
      child: Stack(
        children: [
          // ── Ambient background glows ──
          const Positioned(
            top: -80,
            right: -60,
            child: AuroraBlob(color: kPrimary, size: 280),
          ),
          const Positioned(
            top: 200,
            left: -80,
            child: AuroraBlob(color: Color(0xFF6366F1), size: 200),
          ),

          // ── Scrollable content ──
          CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 100),
                sliver: SliverList(
                  delegate: SliverChildListDelegate(
                    _isLoading
                        ? _buildShimmer()
                      : _isGuest
                        ? [_buildGuestState()]
                        : _error != null
                            ? [_buildError()]
                            : _analysis == null
                                ? [_buildNoData()]
                                : _buildContent(_analysis!),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ──────────────────────────────────────────────
  // CONTENT SECTIONS
  // ──────────────────────────────────────────────

  List<Widget> _buildContent(AnalysisModel a) {
    return [
      // ── Hero Card ──
      _HeroCard(analysis: a).animate().fadeIn(duration: 500.ms).slideY(
          begin: 0.2, end: 0, duration: 500.ms, curve: Curves.easeOut),

      const SizedBox(height: 24),

      // ── Degree Progress + Key Stats ──
      Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Ring chart
          _DegreeRingCard(analysis: a)
              .animate()
              .fadeIn(delay: 100.ms, duration: 500.ms)
              .slideY(begin: 0.2, end: 0, duration: 500.ms, curve: Curves.easeOut),

          const SizedBox(width: 14),

          // Key stats column
          Expanded(
            child: Column(
              children: [
                StatCard(
                  label: 'Earned Credits',
                  value: '${a.earnedCredits}',
                  icon: Icons.stars_rounded,
                  accent: kPrimary,
                  subtitle: 'of 130 required',
                ),
                const SizedBox(height: 12),
                StatCard(
                  label: 'Total Courses',
                  value: '${a.courses.length}',
                  icon: Icons.menu_book_rounded,
                  accent: const Color(0xFF818CF8),
                  subtitle: '${a.courses.where((c) => c.isFailed).length} failed',
                ),
                const SizedBox(height: 12),
                StatCard(
                  label: 'Remaining',
                  value: '${a.remainingCredits} cr',
                  icon: Icons.flag_rounded,
                  accent: a.remainingCredits <= 20 ? kSuccess : kWarning,
                  subtitle: 'to graduate',
                ),
              ],
            )
                .animate()
                .fadeIn(delay: 150.ms, duration: 500.ms)
                .slideY(begin: 0.2, end: 0, duration: 500.ms, curve: Curves.easeOut),
          ),
        ],
      ),

      const SizedBox(height: 24),

      // ── Quick Actions ──
      _QuickActions(
        onUpload: _navigateToUpload,
        onCourses: _navigateToCourses,
      )
          .animate()
          .fadeIn(delay: 200.ms, duration: 500.ms)
          .slideY(begin: 0.2, end: 0, duration: 500.ms, curve: Curves.easeOut),

      const SizedBox(height: 24),

      // ── Level-1 Stats Strip ──
      _StatsStrip(analysis: a)
          .animate()
          .fadeIn(delay: 250.ms, duration: 500.ms)
          .slideY(begin: 0.15, end: 0, duration: 500.ms, curve: Curves.easeOut),

      const SizedBox(height: 24),

      // ── Recent Courses ──
      _RecentCourses(courses: a.courses, onViewAll: _navigateToCourses)
          .animate()
          .fadeIn(delay: 300.ms, duration: 500.ms)
          .slideY(begin: 0.15, end: 0, duration: 500.ms, curve: Curves.easeOut),

      // ── Graduation Status ──
      if (a.summary.isNotEmpty) ...[
        const SizedBox(height: 24),
        _GraduationStatus(analysis: a)
            .animate()
            .fadeIn(delay: 350.ms, duration: 500.ms)
            .slideY(begin: 0.15, end: 0, duration: 500.ms, curve: Curves.easeOut),
      ],
    ];
  }

  // ──────────────────────────────────────────────
  // LOADING / ERROR / EMPTY
  // ──────────────────────────────────────────────

  List<Widget> _buildShimmer() => [
        const SizedBox(height: 8),
        _shimmerCard(height: 200),
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(child: _shimmerCard(height: 180)),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                children: [
                  _shimmerCard(height: 80),
                  const SizedBox(height: 12),
                  _shimmerCard(height: 80),
                  const SizedBox(height: 12),
                  _shimmerCard(height: 80),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),
        _shimmerCard(height: 100),
        const SizedBox(height: 20),
        _shimmerCard(height: 140),
        const SizedBox(height: 20),
        _shimmerCard(height: 260),
      ];

  Widget _shimmerCard({required double height}) => Container(
        height: height,
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 0),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          color: kSurface,
        ),
        child: ShimmerBox(height: height, borderRadius: 20),
      );

  Widget _buildError() => Padding(
        padding: const EdgeInsets.only(top: 60),
        child: EmptyState(
          icon: Icons.cloud_off_rounded,
          title: 'Could not load data',
          subtitle: _error ?? 'Something went wrong. Pull down to try again.',
          accent: kError,
          action: ElevatedButton.icon(
            onPressed: _loadAnalysis,
            icon: const Icon(Icons.refresh_rounded, size: 18),
            label: const Text('Retry'),
            style: ElevatedButton.styleFrom(
              backgroundColor: kError,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ),
      );

  Widget _buildNoData() => Padding(
        padding: const EdgeInsets.only(top: 60),
        child: EmptyState(
          icon: Icons.school_outlined,
          title: 'No transcript uploaded',
          subtitle:
              'Upload your NSU transcript to see your degree audit, CGPA, and graduation progress.',
          accent: kPrimary,
          action: GradientButton(
            label: 'Upload Transcript',
            icon: Icons.upload_file_rounded,
            onPressed: _navigateToUpload,
            width: 220,
          ),
        ),
      );

  Widget _buildGuestState() => Padding(
        padding: const EdgeInsets.only(top: 60),
        child: EmptyState(
          icon: Icons.lock_outline_rounded,
          title: 'Guest mode is active',
          subtitle:
              'Sign in with Google to sync your profile and see your saved dashboard data.',
          accent: kPrimary,
          action: GradientButton(
            label: 'Sign In with Google',
            icon: Icons.login_rounded,
            onPressed: _navigateToAuth,
            width: 230,
          ),
        ),
      );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Hero Card
// ═══════════════════════════════════════════════════════════════════════════════

class _HeroCard extends StatelessWidget {
  const _HeroCard({required this.analysis});
  final AnalysisModel analysis;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                kPrimary.withValues(alpha: 0.18),
                const Color(0xFF6366F1).withValues(alpha: 0.10),
                Colors.white.withValues(alpha: 0.04),
              ],
              stops: const [0.0, 0.5, 1.0],
            ),
            border: Border.all(
              color: kPrimary.withValues(alpha: 0.25),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: kPrimary.withValues(alpha: 0.12),
                blurRadius: 40,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Top row: label + CGPA badge ──
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: kPrimary.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(999),
                            border: Border.all(
                                color: kPrimary.withValues(alpha: 0.30), width: 1),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.account_balance_rounded,
                                  size: 13, color: kPrimary),
                              const SizedBox(width: 6),
                              Text(
                                'North South University',
                                style: Theme.of(context)
                                    .textTheme
                                    .labelSmall
                                    ?.copyWith(
                                      color: kPrimary,
                                      fontWeight: FontWeight.w600,
                                      letterSpacing: 0.3,
                                    ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 14),
                        Text(
                          analysis.studentName,
                          style: Theme.of(context)
                              .textTheme
                              .headlineMedium
                              ?.copyWith(
                                color: kTextPrimary,
                                fontWeight: FontWeight.w800,
                                height: 1.15,
                              ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (analysis.studentId.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            'ID: ${analysis.studentId}',
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(color: kTextSecondary),
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(width: 16),
                  // CGPA Badge
                  _CgpaBadge(cgpa: analysis.cgpa),
                ],
              ),

              const SizedBox(height: 20),
              const Divider(color: kBorder, height: 1),
              const SizedBox(height: 20),

              // ── Info pills row ──
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  if (analysis.department.isNotEmpty)
                    _InfoPill(
                      icon: Icons.business_rounded,
                      label: analysis.department,
                      accent: kPrimary,
                    ),
                  _InfoPill(
                    icon: Icons.credit_card_rounded,
                    label: '${analysis.earnedCredits} credits earned',
                    accent: kSuccess,
                  ),
                  _InfoPill(
                    icon: Icons.flag_rounded,
                    label: '${analysis.remainingCredits} remaining',
                    accent: kWarning,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CgpaBadge extends StatelessWidget {
  const _CgpaBadge({required this.cgpa});
  final double cgpa;

  Color get _color {
    if (cgpa >= 3.7) return kSuccess;
    if (cgpa >= 3.0) return kPrimary;
    if (cgpa >= 2.5) return kWarning;
    return kError;
  }

  String get _label {
    if (cgpa >= 3.7) return 'High Dist.';
    if (cgpa >= 3.5) return 'Distinction';
    if (cgpa >= 3.0) return 'Good';
    if (cgpa >= 2.5) return 'Average';
    return 'At Risk';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: _color.withValues(alpha: 0.12),
        border: Border.all(color: _color.withValues(alpha: 0.35), width: 1.5),
      ),
      child: Column(
        children: [
          Text(
            'CGPA',
            style: Theme.of(context)
                .textTheme
                .labelSmall
                ?.copyWith(color: _color.withValues(alpha: 0.8)),
          ),
          const SizedBox(height: 4),
          Text(
            cgpa.toStringAsFixed(2),
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: _color,
                  fontWeight: FontWeight.w800,
                  fontSize: 26,
                ),
          ),
          const SizedBox(height: 4),
          Text(
            _label,
            style: Theme.of(context)
                .textTheme
                .labelSmall
                ?.copyWith(color: kTextTertiary, fontSize: 10),
          ),
        ],
      ),
    );
  }
}

class _InfoPill extends StatelessWidget {
  const _InfoPill({
    required this.icon,
    required this.label,
    required this.accent,
  });
  final IconData icon;
  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: accent.withValues(alpha: 0.22), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: accent),
          const SizedBox(width: 6),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: kTextPrimary,
                  fontWeight: FontWeight.w500,
                ),
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Degree Progress Ring Card
// ═══════════════════════════════════════════════════════════════════════════════

class _DegreeRingCard extends StatefulWidget {
  const _DegreeRingCard({required this.analysis});
  final AnalysisModel analysis;

  @override
  State<_DegreeRingCard> createState() => _DegreeRingCardState();
}

class _DegreeRingCardState extends State<_DegreeRingCard>
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
    _anim = CurvedAnimation(parent: _ctrl, curve: Curves.easeOutCubic);
    Future.delayed(const Duration(milliseconds: 300), () {
      if (mounted) _ctrl.forward();
    });
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final progress = widget.analysis.graduationProgress;
    final pct = (progress * 100).round();

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Graduation',
            style: Theme.of(context)
                .textTheme
                .labelSmall
                ?.copyWith(color: kTextTertiary, letterSpacing: 0.8),
          ),
          const SizedBox(height: 2),
          Text(
            'Progress',
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(color: kTextPrimary, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 16),
          AnimatedBuilder(
            animation: _anim,
            builder: (context, child) => CircularPercentIndicator(
              radius: 72,
              lineWidth: 10.0,
              percent: progress * _anim.value,
              animation: false,
              center: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '$pct%',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          color: kTextPrimary,
                          fontWeight: FontWeight.w800,
                          fontSize: 22,
                        ),
                  ),
                  Text(
                    'done',
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: kTextTertiary),
                  ),
                ],
              ),
              progressColor: pct >= 100
                  ? kSuccess
                  : pct >= 75
                      ? kPrimary
                      : kWarning,
              backgroundColor: Colors.white.withValues(alpha: 0.06),
              circularStrokeCap: CircularStrokeCap.round,
            ),
          ),
          const SizedBox(height: 14),
          Text(
            '${widget.analysis.earnedCredits} / 130',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: kTextSecondary,
                  fontWeight: FontWeight.w600,
                ),
          ),
          const SizedBox(height: 2),
          Text(
            'credits',
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(color: kTextTertiary),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Quick Actions
// ═══════════════════════════════════════════════════════════════════════════════

class _QuickActions extends StatelessWidget {
  const _QuickActions({required this.onUpload, required this.onCourses});
  final VoidCallback onUpload;
  final VoidCallback onCourses;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(
          eyebrow: 'Quick Actions',
          title: 'What do you need?',
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: _ActionButton(
                label: 'Upload New\nTranscript',
                icon: Icons.upload_file_rounded,
                accent: kSuccess,
                onTap: onUpload,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _ActionButton(
                label: 'View All\nCourses',
                icon: Icons.menu_book_rounded,
                accent: const Color(0xFF818CF8),
                onTap: onCourses,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ActionButton extends StatefulWidget {
  const _ActionButton({
    required this.label,
    required this.icon,
    required this.accent,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final Color accent;
  final VoidCallback onTap;

  @override
  State<_ActionButton> createState() => _ActionButtonState();
}

class _ActionButtonState extends State<_ActionButton> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        widget.onTap();
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedScale(
        scale: _pressed ? 0.96 : 1.0,
        duration: const Duration(milliseconds: 100),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(18),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
            child: Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    widget.accent.withValues(alpha: 0.15),
                    widget.accent.withValues(alpha: 0.05),
                  ],
                ),
                border: Border.all(
                    color: widget.accent.withValues(alpha: 0.30), width: 1.5),
              ),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: widget.accent.withValues(alpha: 0.18),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(widget.icon,
                        color: widget.accent, size: 22),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      widget.label,
                      style: Theme.of(context)
                          .textTheme
                          .titleSmall
                          ?.copyWith(
                            color: kTextPrimary,
                            fontWeight: FontWeight.w700,
                            height: 1.3,
                          ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Stats Strip
// ═══════════════════════════════════════════════════════════════════════════════

class _StatsStrip extends StatelessWidget {
  const _StatsStrip({required this.analysis});
  final AnalysisModel analysis;

  @override
  Widget build(BuildContext context) {
    final failedCourses =
        analysis.courses.where((c) => c.isFailed).length;
    final retakeCourses =
        analysis.courses.where((c) => c.isRetake).length;
    final passedCourses = analysis.courses
        .where((c) => !c.isFailed)
        .length;

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionHeader(eyebrow: 'Summary', title: 'Academic Overview'),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: SmallMetric(
                  label: 'Passed',
                  value: '$passedCourses',
                  accent: kSuccess,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: SmallMetric(
                  label: 'Failed',
                  value: '$failedCourses',
                  accent: failedCourses > 0 ? kError : kTextTertiary,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: SmallMetric(
                  label: 'Retakes',
                  value: '$retakeCourses',
                  accent: retakeCourses > 0 ? kWarning : kTextTertiary,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: SmallMetric(
                  label: 'Subjects',
                  value: '${_countSubjects(analysis.courses)}',
                  accent: const Color(0xFF818CF8),
                ),
              ),
            ],
          ),

          if (failedCourses > 0) ...[
            const SizedBox(height: 16),
            AlertBox(
              accent: kError,
              icon: Icons.warning_amber_rounded,
              title: '$failedCourses failed course${failedCourses > 1 ? 's' : ''} detected',
              body:
                  'These courses may need to be retaken to meet graduation requirements.',
            ),
          ],

          if (analysis.level2.isNotEmpty) ...[
            const SizedBox(height: 16),
            const Divider(color: kBorder),
            const SizedBox(height: 12),
            _Level2Highlights(level2: analysis.level2),
          ],
        ],
      ),
    );
  }

  int _countSubjects(List<CourseModel> courses) {
    final subjects = <String>{};
    for (final c in courses) {
      subjects.add(c.subjectCode);
    }
    return subjects.length;
  }
}

class _Level2Highlights extends StatelessWidget {
  const _Level2Highlights({required this.level2});
  final Map<String, dynamic> level2;

  @override
  Widget build(BuildContext context) {
    final waiverEligible = level2['waiver_eligible'] == true ||
        level2['cgpa_waiver_eligible'] == true;
    final waiverCredits = _parseInt(
        level2['waiver_credits'] ?? level2['eligible_waiver_credits']);
    final gradStatus =
        level2['graduation_status']?.toString() ?? '';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'ADVANCED ANALYSIS',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: kPrimary,
                letterSpacing: 1.4,
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: 12),
        if (waiverEligible)
          AlertBox(
            accent: kSuccess,
            icon: Icons.card_giftcard_rounded,
            title: 'CGPA Waiver Eligible!',
            body: waiverCredits > 0
                ? 'You may waive up to $waiverCredits credit hours based on your CGPA.'
                : 'Your CGPA qualifies you for a credit waiver. Check with your advisor.',
          ),
        if (gradStatus.isNotEmpty) ...[
          const SizedBox(height: 12),
          AlertBox(
            accent: gradStatus.toLowerCase().contains('eligible')
                ? kSuccess
                : kPrimary,
            icon: gradStatus.toLowerCase().contains('eligible')
                ? Icons.school_rounded
                : Icons.info_outline_rounded,
            title: 'Graduation Status',
            body: gradStatus,
          ),
        ],
      ],
    );
  }

  static int _parseInt(dynamic v) {
    if (v is num) return v.toInt();
    return int.tryParse(v?.toString() ?? '') ?? 0;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Recent Courses
// ═══════════════════════════════════════════════════════════════════════════════

class _RecentCourses extends StatelessWidget {
  const _RecentCourses({
    required this.courses,
    required this.onViewAll,
  });

  final List<CourseModel> courses;
  final VoidCallback onViewAll;

  @override
  Widget build(BuildContext context) {
    // Sort by semester (newest first approximation) and take top 5
    final sorted = [...courses];
    // Show failed and retake courses first for visibility
    sorted.sort((a, b) {
      if (a.isFailed && !b.isFailed) return -1;
      if (!a.isFailed && b.isFailed) return 1;
      if (a.isRetake && !b.isRetake) return -1;
      if (!a.isRetake && b.isRetake) return 1;
      return b.semester.compareTo(a.semester);
    });
    final preview = sorted.take(5).toList();

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionHeader(
            eyebrow: 'Courses',
            title: 'Recent Activity',
            action: TextButton(
              onPressed: onViewAll,
              style: TextButton.styleFrom(
                foregroundColor: kPrimary,
                padding: EdgeInsets.zero,
                minimumSize: const Size(0, 32),
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('View all',
                      style: TextStyle(
                          fontSize: 13, fontWeight: FontWeight.w600)),
                  SizedBox(width: 4),
                  Icon(Icons.arrow_forward_ios_rounded, size: 12),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (preview.isEmpty)
            Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Text(
                  'No courses found',
                  style: Theme.of(context)
                      .textTheme
                      .bodyMedium
                      ?.copyWith(color: kTextTertiary),
                ),
              ),
            )
          else
            ...preview.asMap().entries.map((e) {
              return Column(
                children: [
                  _CourseTile(course: e.value)
                      .animate(delay: (e.key * 60).ms)
                      .fadeIn(duration: 400.ms)
                      .slideX(begin: 0.05, end: 0, duration: 400.ms),
                  if (e.key < preview.length - 1)
                    const Divider(color: kBorder, height: 1),
                ],
              );
            }),
          if (courses.length > 5) ...[
            const SizedBox(height: 12),
            Center(
              child: TextButton(
                onPressed: onViewAll,
                style: TextButton.styleFrom(foregroundColor: kPrimary),
                child: Text(
                  'See all ${courses.length} courses →',
                  style: const TextStyle(
                      fontSize: 13, fontWeight: FontWeight.w600),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _CourseTile extends StatelessWidget {
  const _CourseTile({required this.course});
  final CourseModel course;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          // Subject icon
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: gradeColor(course.grade).withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Center(
              child: Text(
                course.subjectCode.isEmpty
                    ? '?'
                    : course.subjectCode.substring(
                        0,
                        course.subjectCode.length.clamp(0, 3),
                      ),
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  color: gradeColor(course.grade),
                  fontFamily: 'Outfit',
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          // Course info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      course.code,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            color: kTextPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(width: 6),
                    if (course.isFailed)
                      _MiniTag(label: 'Failed', color: kError),
                    if (course.isRetake && !course.isFailed)
                      _MiniTag(label: 'Retake', color: kWarning),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  course.name.isNotEmpty ? course.name : course.semester,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: kTextSecondary,
                      ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          // Grade + credits
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              GradeChip(grade: course.grade),
              const SizedBox(height: 4),
              Text(
                '${course.credits} cr',
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: kTextTertiary),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MiniTag extends StatelessWidget {
  const _MiniTag({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 9,
          fontWeight: FontWeight.w700,
          color: color,
          fontFamily: 'Outfit',
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Graduation Status
// ═══════════════════════════════════════════════════════════════════════════════

class _GraduationStatus extends StatelessWidget {
  const _GraduationStatus({required this.analysis});
  final AnalysisModel analysis;

  @override
  Widget build(BuildContext context) {
    final isReady = analysis.graduationProgress >= 1.0;
    final accent = isReady ? kSuccess : kPrimary;

    return GlassCard(
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          accent.withValues(alpha: 0.12),
          accent.withValues(alpha: 0.04),
          Colors.transparent,
        ],
      ),
      border: Border.all(color: accent.withValues(alpha: 0.25), width: 1),
      child: Row(
        children: [
          GlowIcon(
            icon: isReady
                ? Icons.celebration_rounded
                : Icons.timeline_rounded,
            accent: accent,
            size: 60,
            iconSize: 30,
          ),
          const SizedBox(width: 18),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isReady ? '🎓 Ready to Graduate!' : 'On Track',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: kTextPrimary,
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  isReady
                      ? 'You have completed all required credits. Congratulations!'
                      : 'You need ${analysis.remainingCredits} more credits to complete your degree.',
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: kTextSecondary, height: 1.5),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
*/
