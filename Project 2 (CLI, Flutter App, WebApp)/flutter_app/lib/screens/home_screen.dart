import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../services/analysis_session_service.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart' hide ApiException;
import '../widgets/glass_widgets.dart';
import 'auth_screen.dart';
import 'history_screen.dart';
import 'upload_screen.dart';

double asDouble(dynamic value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}

int asInt(dynamic value) {
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

String asString(dynamic value) => value?.toString() ?? '';

Map<String, dynamic> asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return value.cast<String, dynamic>();
  return const <String, dynamic>{};
}

List<dynamic> asList(dynamic value) => value is List ? value : <dynamic>[];

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, this.initialData});

  /// Optional initial data from history screen
  final Map<String, dynamic>? initialData;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Map<String, dynamic>? data;
  bool _isLoading = true;
  String? errorMessage;
  int selectedLevel = 1;
  bool _isSigningIn = false;

  @override
  void initState() {
    super.initState();
    _loadAnalysis();
  }

  @override
  void dispose() {
    super.dispose();
  }

  Future<void> _loadAnalysis() async {
    final initialData = widget.initialData != null
        ? Map<String, dynamic>.from(widget.initialData!)
        : null;
    final cached = initialData ?? analysisSessionService.latestRawAnalysis;

    setState(() {
      data = cached;
      _isLoading = true;
      errorMessage = null;
    });

    if (cached != null && !authService.isAuthenticated) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
      return;
    }

    if (!authService.isAuthenticated) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
      return;
    }

    try {
      final raw = await apiService.getAnalysis();
      analysisSessionService.setLatestAnalysis(raw);
      if (!mounted) return;

      setState(() {
        data = analysisSessionService.latestRawAnalysis;
        _isLoading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        data = cached;
        errorMessage = cached == null ? e.message : null;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        data = cached;
        errorMessage = cached == null
            ? 'Could not load backend analysis. Pull down to retry.'
            : null;
        _isLoading = false;
      });
    }
  }

  void _openUpload() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const UploadScreen()),
    );
  }

  void _openHistoryOrAuth() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => authService.isAuthenticated
            ? const HistoryScreen()
            : const AuthScreen(),
      ),
    );
  }

  Future<void> _handleGoogleSignIn() async {
    if (_isSigningIn) return;

    setState(() => _isSigningIn = true);

    try {
      final error = await authService.signInWithGoogle();
      if (!mounted) return;

      if (error != null) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error), backgroundColor: kError));
      } else {
        await _loadAnalysis();
      }
    } finally {
      if (mounted) {
        setState(() => _isSigningIn = false);
      }
    }
  }

  Future<void> _handleSignOut() async {
    await authService.logout();
    if (mounted) {
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _loadAnalysis,
      color: kPrimary,
      backgroundColor: kSurface,
      child: Stack(
        children: [
          const Positioned(
            top: -80,
            left: -60,
            child: AuroraBlob(color: kPrimary, size: 260),
          ),
          const Positioned(
            bottom: -90,
            right: -60,
            child: AuroraBlob(color: kSuccess, size: 240),
          ),
          SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 100),
            child: buildContent(context),
          ),
        ],
      ),
    );
  }

  Widget buildContent(BuildContext context) {
    final theme = Theme.of(context);
    final info = asMap(data?['ocr_info']);
    final level1 = asMap(data?['level1']);
    final level2 = asMap(data?['level2']);
    final level3 = asMap(data?['level3']);
    final courses = asList(data?['courses']);
    final user = authService.currentUser;
    final userHasAvatar = (user?.avatarUrl?.isNotEmpty ?? false);
    final studentName = asString(info['student_name']).isNotEmpty
        ? asString(info['student_name'])
        : 'Backend Analysis';
    final departmentName = asString(info['department_full_name']).isNotEmpty
        ? asString(info['department_full_name'])
        : asString(info['department_name']);
    final backendEngine = asString(info['engine']).isNotEmpty
        ? asString(info['engine'])
        : 'Backend OCR';
    final unknownCourses = asList(
      info['unknown_courses'],
    ).map(asString).where((value) => value.isNotEmpty).toList();

    if (_isLoading) {
      return Column(
        children: [
          _buildShimmerCard(height: 220),
          const SizedBox(height: 18),
          _buildShimmerCard(height: 96),
          const SizedBox(height: 18),
          _buildShimmerCard(height: 240),
        ],
      );
    }

    if (data == null) {
      return Padding(
        padding: const EdgeInsets.only(top: 60),
        child: EmptyState(
          icon: errorMessage != null
              ? Icons.cloud_off_rounded
              : Icons.upload_file_rounded,
          title: errorMessage != null
              ? 'Results unavailable'
              : 'No transcript analysis yet',
          subtitle:
              errorMessage ??
              'Upload a transcript and this screen will show the same backend OCR result structure as the website.',
          accent: errorMessage != null ? kError : kPrimary,
          action: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              GradientButton(
                label: 'Upload Transcript',
                icon: Icons.upload_file_rounded,
                onPressed: _openUpload,
                width: 230,
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: _openHistoryOrAuth,
                icon: Icon(
                  authService.isAuthenticated
                      ? Icons.history_rounded
                      : Icons.login_rounded,
                ),
                label: Text(
                  authService.isAuthenticated ? 'Open History' : 'Sign In',
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(14),
                      gradient: const LinearGradient(
                        colors: [Color(0xFF0066CC), Color(0xFF0284C7)],
                      ),
                    ),
                    child: const Icon(
                      Icons.cloud_done_rounded,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Backend OCR Results',
                          style: theme.textTheme.bodyMedium,
                        ),
                        Text(studentName, style: theme.textTheme.titleLarge),
                        if (departmentName.isNotEmpty)
                          Text(
                            departmentName,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: kTextSecondary,
                            ),
                          ),
                      ],
                    ),
                  ),
                  if (authService.isAuthenticated)
                    PopupMenuButton<String>(
                      offset: const Offset(0, 40),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          CircleAvatar(
                            radius: 16,
                            backgroundImage: userHasAvatar
                                ? NetworkImage(user!.avatarUrl!)
                                : null,
                            backgroundColor: const Color(0xFF0066CC),
                            child: !userHasAvatar
                                ? Text(
                                    (user?.displayName.isNotEmpty == true
                                            ? user!.displayName[0].toUpperCase()
                                            : '?')
                                        .toString(),
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  )
                                : null,
                          ),
                          const SizedBox(width: 4),
                          const Icon(
                            Icons.arrow_drop_down,
                            color: Color(0xFF64748B),
                          ),
                        ],
                      ),
                      itemBuilder: (context) => [
                        const PopupMenuItem(
                          value: 'history',
                          child: Row(
                            children: [
                              Icon(Icons.history, size: 20),
                              SizedBox(width: 12),
                              Text('Scan History'),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'signout',
                          child: Row(
                            children: [
                              Icon(Icons.logout, size: 20),
                              SizedBox(width: 12),
                              Text('Sign Out'),
                            ],
                          ),
                        ),
                      ],
                      onSelected: (value) {
                        if (value == 'history') {
                          _openHistoryOrAuth();
                        } else if (value == 'signout') {
                          _handleSignOut();
                        }
                      },
                    )
                  else
                    InkWell(
                      onTap: _isSigningIn ? null : _handleGoogleSignIn,
                      borderRadius: BorderRadius.circular(20),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF4285F4), Color(0xFF1a73e8)],
                          ),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: _isSigningIn
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.login,
                                    size: 16,
                                    color: Colors.white,
                                  ),
                                  SizedBox(width: 6),
                                  Text(
                                    'Sign in',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                'This screen renders the same backend-produced OCR and audit output shape used by the website.',
                style: theme.textTheme.bodyLarge?.copyWith(
                  fontSize: 15,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  const FeatureChip(
                    icon: Icons.document_scanner_outlined,
                    label: 'Backend OCR',
                  ),
                  FeatureChip(icon: Icons.memory_rounded, label: backendEngine),
                  FeatureChip(
                    icon: Icons.insights_outlined,
                    label:
                        'CGPA ${asDouble(level2['cgpa']).toStringAsFixed(2)}',
                  ),
                  FeatureChip(
                    icon: Icons.school_outlined,
                    label:
                        '${asDouble(level1['earned_credits']).toStringAsFixed(1)} credits',
                  ),
                ],
              ),
              const SizedBox(height: 18),
              GlassTone(
                child: Row(
                  children: [
                    const Icon(
                      Icons.cloud_done_outlined,
                      color: Color(0xFF0066CC),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Processed on backend and stored in the active analysis session.',
                        style: theme.textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _openUpload,
                  icon: const Icon(Icons.file_upload_outlined),
                  label: const Padding(
                    padding: EdgeInsets.symmetric(vertical: 14),
                    child: Text('Upload Another Transcript'),
                  ),
                ),
              ),
            ],
          ),
        ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.08, end: 0),
        if (errorMessage != null) ...[
          const SizedBox(height: 18),
          AlertBox(
            accent: kWarning,
            icon: Icons.info_outline_rounded,
            title: 'Using cached backend results',
            body: errorMessage!,
          ),
        ],
        if (unknownCourses.isNotEmpty) ...[
          const SizedBox(height: 18),
          AlertBox(
            accent: kError,
            icon: Icons.warning_amber_rounded,
            title:
                '${unknownCourses.length} unknown course${unknownCourses.length == 1 ? '' : 's'} detected',
            body:
                '${unknownCourses.take(8).join(', ')}${unknownCourses.length > 8 ? ' +' : ''} These may affect degree-audit accuracy.',
          ),
        ],
        if (data!['cgpa_warning'] != null) ...[
          const SizedBox(height: 18),
          AlertBox(
            accent: kWarning,
            icon: Icons.warning_rounded,
            title: 'CGPA verification warning',
            body:
                'PDF ${asDouble(asMap(data!['cgpa_warning'])['pdf_value']).toStringAsFixed(2)} | Calculated ${asDouble(asMap(data!['cgpa_warning'])['calculated_value']).toStringAsFixed(2)} | Diff ${asDouble(asMap(data!['cgpa_warning'])['difference']).toStringAsFixed(2)}',
          ),
        ],
        const SizedBox(height: 24),
        SectionHeader(
          eyebrow: 'Analysis Results',
          title: asString(level3['program_name']).isNotEmpty
              ? asString(level3['program_name'])
              : 'Transcript Summary',
          subtitle:
              'Level 1, Level 2, and Level 3 come directly from the backend analysis payload.',
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: StatCard(
                label: 'Courses',
                value: '${courses.length}',
                icon: Icons.layers_outlined,
                accent: const Color(0xFF0066CC),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: StatCard(
                label: 'Credits Earned',
                value: asDouble(level1['earned_credits']).toStringAsFixed(1),
                icon: Icons.stacked_line_chart,
                accent: const Color(0xFF10B981),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: StatCard(
                label: 'CGPA',
                value: asDouble(level2['cgpa']).toStringAsFixed(2),
                icon: Icons.insights_outlined,
                accent: const Color(0xFF8B5CF6),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: StatCard(
                label: 'Confidence',
                value: '${asDouble(info['confidence']).toStringAsFixed(1)}%',
                icon: Icons.track_changes_outlined,
                accent: const Color(0xFFF59E0B),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('OCR Details', style: theme.textTheme.titleMedium),
              const SizedBox(height: 10),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  DataPill(
                    icon: Icons.memory_outlined,
                    label: 'Engine',
                    value: asString(info['engine']).isEmpty
                        ? 'Unknown'
                        : asString(info['engine']),
                  ),
                  DataPill(
                    icon: Icons.person_outline,
                    label: 'Student',
                    value: asString(info['student_name']).isEmpty
                        ? 'Not captured'
                        : asString(info['student_name']),
                  ),
                  DataPill(
                    icon: Icons.badge_outlined,
                    label: 'Student ID',
                    value: asString(info['student_id']).isEmpty
                        ? 'Not captured'
                        : asString(info['student_id']),
                  ),
                ],
              ),
              if (asDouble(info['total_credits_from_pdf']) > 0 ||
                  asDouble(info['cgpa_from_pdf']) > 0) ...[
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: StripMetric(
                        label: 'PDF Credits',
                        value: asDouble(info['total_credits_from_pdf']) > 0
                            ? asDouble(
                                info['total_credits_from_pdf'],
                              ).toStringAsFixed(1)
                            : 'n/a',
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: StripMetric(
                        label: 'PDF CGPA',
                        value: asDouble(info['cgpa_from_pdf']) > 0
                            ? asDouble(info['cgpa_from_pdf']).toStringAsFixed(2)
                            : 'n/a',
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 18),
        SegmentedButton<int>(
          showSelectedIcon: false,
          style: ButtonStyle(
            backgroundColor: WidgetStateProperty.resolveWith((states) {
              if (states.contains(WidgetState.selected)) {
                return const Color(0xFF0066CC);
              }
              return Colors.white;
            }),
            foregroundColor: WidgetStateProperty.resolveWith((states) {
              if (states.contains(WidgetState.selected)) {
                return Colors.white;
              }
              return const Color(0xFF64748B);
            }),
          ),
          segments: const [
            ButtonSegment(value: 1, label: Text('Level 1')),
            ButtonSegment(value: 2, label: Text('Level 2')),
            ButtonSegment(value: 3, label: Text('Level 3')),
          ],
          selected: {selectedLevel},
          onSelectionChanged: (value) =>
              setState(() => selectedLevel = value.first),
        ),
        const SizedBox(height: 16),
        buildLevelPanel(),
        const SizedBox(height: 18),
        buildSemesterPanel(),
        const SizedBox(height: 18),
        buildOcrPanel(),
      ],
    );
  }

  Widget buildLevelPanel() {
    switch (selectedLevel) {
      case 1:
        return buildLevelOne();
      case 2:
        return buildLevelTwo();
      default:
        return buildLevelThree();
    }
  }

  Widget buildLevelOne() {
    final level1 = asMap(data!['level1']);
    final retakes = asList(level1['retakes']);
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          titleLine('Level 1 · Credit tally'),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SmallMetric(
                label: 'Total entries',
                value: '${asInt(level1['total_entries'])}',
              ),
              SmallMetric(
                label: 'Unique courses',
                value: '${asInt(level1['unique_courses'])}',
              ),
              SmallMetric(
                label: 'Attempted credits',
                value: asDouble(
                  level1['total_credits_attempted'],
                ).toStringAsFixed(1),
              ),
              SmallMetric(
                label: 'Earned credits',
                value: asDouble(level1['earned_credits']).toStringAsFixed(1),
              ),
              SmallMetric(
                label: 'Failed credits',
                value: asDouble(level1['failed_credits']).toStringAsFixed(1),
              ),
              SmallMetric(
                label: 'Retakes',
                value: '${asInt(level1['retakes_count'])}',
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Graduation runway',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(color: Colors.white),
          ),
          const SizedBox(height: 10),
          LinearProgressIndicator(
            value: (asDouble(level1['progress_130']) / 100).clamp(0, 1),
            minHeight: 14,
            borderRadius: BorderRadius.circular(999),
            backgroundColor: Colors.white.withValues(alpha: 0.08),
          ),
          const SizedBox(height: 10),
          Text(
            '${asDouble(level1['earned_credits']).toStringAsFixed(1)} of 130 credits completed • ${asDouble(level1['progress_130']).toStringAsFixed(1)}%',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (retakes.isNotEmpty) ...[
            const SizedBox(height: 18),
            Text(
              'Retake intelligence',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(color: Colors.white),
            ),
            const SizedBox(height: 10),
            ...retakes.map((item) {
              final retake = asMap(item);
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: GlassTone(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        asString(retake['code']),
                        style: Theme.of(
                          context,
                        ).textTheme.titleMedium?.copyWith(color: Colors.white),
                      ),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 6,
                        children: asList(retake['grades'])
                            .map((grade) => GradeChip(grade: asString(grade)))
                            .toList()
                            .cast<Widget>(),
                      ),
                      const SizedBox(height: 8),
                      Text('Best attempt kept: ${asString(retake['best'])}'),
                    ],
                  ),
                ),
              );
            }),
          ],
        ],
      ),
    );
  }

  Widget buildLevelTwo() {
    final level2 = asMap(data!['level2']);
    final gradeDistribution = asMap(level2['grade_distribution']);
    final waiver = asMap(level2['waiver']);
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          titleLine('Level 2 · CGPA analysis'),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SmallMetric(
                label: 'CGPA',
                value: asDouble(level2['cgpa']).toStringAsFixed(2),
              ),
              SmallMetric(
                label: 'GPA credits',
                value: '${asInt(level2['gpa_credits'])}',
              ),
              SmallMetric(
                label: 'Quality points',
                value: asDouble(
                  level2['total_quality_points'],
                ).toStringAsFixed(2),
              ),
            ],
          ),
          const SizedBox(height: 16),
          GlassTone(
            child: Row(
              children: [
                const Icon(Icons.workspace_premium, color: Color(0xFFF6B75D)),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Academic standing: ${asString(level2['standing']).isEmpty ? 'Not available' : asString(level2['standing'])}',
                    style: Theme.of(
                      context,
                    ).textTheme.titleMedium?.copyWith(color: Colors.white),
                  ),
                ),
                Text(
                  asString(level2['stars']),
                  style: const TextStyle(fontSize: 20),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Grade distribution',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(color: Colors.white),
          ),
          const SizedBox(height: 10),
          if (gradeDistribution.isEmpty)
            Text(
              'No grade distribution available.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: gradeDistribution.entries.map((entry) {
                return GlassTone(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 12,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      GradeChip(grade: entry.key),
                      const SizedBox(width: 10),
                      Text('${entry.value} courses'),
                    ],
                  ),
                );
              }).toList(),
            ),
          const SizedBox(height: 16),
          if (waiver.isNotEmpty)
            AlertBox(
              accent: const Color(0xFF80FFBD),
              icon: Icons.card_giftcard,
              title: 'Waiver opportunity',
              body:
                  '${asString(waiver['level'])} ${asString(waiver['name'])} appears available from the current calculated CGPA.',
            )
          else
            const AlertBox(
              accent: Color(0xFF57C5FF),
              icon: Icons.info_outline,
              title: 'Scholarship status',
              body:
                  'No tuition waiver threshold is currently met from the calculated results.',
            ),
        ],
      ),
    );
  }

  Widget buildLevelThree() {
    final level3 = asMap(data!['level3']);
    final missingMandatory = asList(level3['mandatory_missing']);
    final electives = asMap(level3['elective_status']);
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          titleLine('Level 3 · Degree audit'),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SmallMetric(
                label: 'Program',
                value: asString(level3['program']).isEmpty
                    ? 'Unknown'
                    : asString(level3['program']),
              ),
              SmallMetric(
                label: 'Mandatory progress',
                value:
                    '${asDouble(level3['mandatory_progress']).toStringAsFixed(1)}%',
              ),
            ],
          ),
          const SizedBox(height: 16),
          AlertBox(
            accent: level3['graduation_ready'] == true
                ? const Color(0xFF80FFBD)
                : const Color(0xFFF6B75D),
            icon: level3['graduation_ready'] == true
                ? Icons.verified
                : Icons.rule_folder_outlined,
            title: asString(level3['program_name']).isEmpty
                ? 'Program insight'
                : asString(level3['program_name']),
            body: level3['graduation_ready'] == true
                ? 'This audit looks graduation-ready based on the available rules and credits.'
                : asString(level3['note']).isNotEmpty
                ? asString(level3['note'])
                : 'Mandatory and elective requirements still need attention.',
          ),
          const SizedBox(height: 16),
          Text(
            'Missing mandatory courses',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(color: Colors.white),
          ),
          const SizedBox(height: 10),
          if (missingMandatory.isEmpty)
            Text(
              'No mandatory gaps were found from the loaded knowledge base.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: missingMandatory.map((course) {
                return DataPill(
                  icon: Icons.bookmark_remove_outlined,
                  label: 'Missing',
                  value: asString(course),
                );
              }).toList(),
            ),
          const SizedBox(height: 18),
          Text(
            'Elective groups',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(color: Colors.white),
          ),
          const SizedBox(height: 10),
          if (electives.isEmpty)
            Text(
              'No elective groups were loaded for this program.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ...electives.entries.map((entry) {
              final details = asMap(entry.value);
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: GlassTone(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              entry.key,
                              style: Theme.of(context).textTheme.titleMedium
                                  ?.copyWith(color: Colors.white),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: details['satisfied'] == true
                                  ? const Color(
                                      0xFF80FFBD,
                                    ).withValues(alpha: 0.16)
                                  : const Color(
                                      0xFFF6B75D,
                                    ).withValues(alpha: 0.16),
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text(
                              details['satisfied'] == true
                                  ? 'Satisfied'
                                  : 'Pending',
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '${asInt(details['completed'])} of ${asInt(details['required'])} required completed',
                      ),
                      if (asList(details['courses']).isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: asList(details['courses'])
                              .map(
                                (course) => GradeChip(grade: asString(course)),
                              )
                              .toList()
                              .cast<Widget>(),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget buildSemesterPanel() {
    final semesters = asList(data!['semesters']);
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          titleLine('Semester timeline'),
          const SizedBox(height: 12),
          if (semesters.isEmpty)
            Text(
              'No semester grouping is available.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ...semesters.map((item) {
              final semester = asMap(item);
              final courses = asList(semester['courses']);
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: GlassTone(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              asString(semester['name']).isEmpty
                                  ? 'Semester'
                                  : asString(semester['name']),
                              style: Theme.of(context).textTheme.titleMedium
                                  ?.copyWith(color: Colors.white),
                            ),
                          ),
                          Text('${courses.length} courses'),
                        ],
                      ),
                      const SizedBox(height: 10),
                      ...courses.map((courseItem) {
                        final course = asMap(courseItem);
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Row(
                            children: [
                              Expanded(
                                child: Text(
                                  asString(course['code']),
                                  style: Theme.of(context).textTheme.bodyLarge
                                      ?.copyWith(color: Colors.white),
                                ),
                              ),
                              Text(
                                '${asDouble(course['credits']).toStringAsFixed(1)} cr',
                              ),
                              const SizedBox(width: 10),
                              GradeChip(grade: asString(course['grade'])),
                            ],
                          ),
                        );
                      }),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget buildOcrPanel() {
    final info = asMap(data!['ocr_info']);
    final extractedTexts = asList(data!['extracted_texts']);
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          titleLine('OCR telemetry'),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SmallMetric(
                label: 'Raw text rows',
                value: '${asInt(info['raw_text_count'])}',
              ),
              SmallMetric(
                label: 'OCR engine',
                value: asString(info['engine']).isEmpty
                    ? 'Unknown'
                    : asString(info['engine']),
              ),
              SmallMetric(
                label: 'Confidence',
                value: '${asDouble(info['confidence']).toStringAsFixed(1)}%',
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Extracted text preview',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(color: Colors.white),
          ),
          const SizedBox(height: 10),
          if (extractedTexts.isEmpty)
            Text(
              'No extracted raw text was returned.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ...extractedTexts.take(12).map((line) {
              final text = asString(line).trim();
              if (text.isEmpty) {
                return const SizedBox.shrink();
              }
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: GlassTone(
                  child: Text(
                    text,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: const Color(0xFFE5F3FF),
                    ),
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildShimmerCard({required double height}) {
    return Container(
      height: height,
      width: double.infinity,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: kSurface,
      ),
      child: ShimmerBox(height: height, borderRadius: 20),
    );
  }

  Widget titleLine(String title) {
    return Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: const BoxDecoration(
            color: Color(0xFF57C5FF),
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 10),
        Text(
          title,
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(color: Colors.white),
        ),
      ],
    );
  }
}
