import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../models/analysis_model.dart';
import '../models/course_model.dart';
import '../services/auth_service.dart' hide ApiException;
import '../services/analysis_session_service.dart';
import '../services/api_service.dart';
import '../widgets/glass_widgets.dart';
import 'auth_screen.dart';

class CoursesScreen extends StatefulWidget {
  const CoursesScreen({super.key});

  @override
  State<CoursesScreen> createState() => _CoursesScreenState();
}

class _CoursesScreenState extends State<CoursesScreen>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  // ── Data ──
  AnalysisModel? _analysis;
  bool _isLoading = true;
  String? _error;
  bool _isGuest = false;

  // ── Filter state ──
  String _searchQuery = '';
  String? _selectedGradeFilter;   // null = all
  String? _selectedSubjectFilter; // null = all
  String? _selectedSemesterFilter; // null = all
  bool _showFailedOnly = false;
  bool _showRetakesOnly = false;

  // ── Sort ──
  _SortMode _sortMode = _SortMode.semester;
  bool _sortAscending = false;

  final _searchCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();

  // ── Grade groups for filter ──
  static const _gradeGroups = ['A', 'B', 'C', 'D', 'F', 'W'];

  @override
  void initState() {
    super.initState();
    _loadData();
    _searchCtrl.addListener(() {
      setState(() => _searchQuery = _searchCtrl.text.trim().toLowerCase());
    });
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
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
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = cachedAnalysis == null
            ? 'Failed to load courses. Pull down to refresh.'
            : null;
        _analysis = cachedAnalysis;
        _isLoading = false;
      });
    }
  }

  void _navigateToAuth() {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const AuthScreen()),
    );
  }

  // ─────────────────────────────────────────────
  // Filtering & sorting logic
  // ─────────────────────────────────────────────

  List<CourseModel> get _filteredCourses {
    if (_analysis == null) return [];
    var list = List<CourseModel>.from(_analysis!.courses);

    // Search
    if (_searchQuery.isNotEmpty) {
      list = list.where((c) {
        return c.code.toLowerCase().contains(_searchQuery) ||
            c.name.toLowerCase().contains(_searchQuery) ||
            c.semester.toLowerCase().contains(_searchQuery) ||
            c.grade.toLowerCase().contains(_searchQuery);
      }).toList();
    }

    // Grade group filter
    if (_selectedGradeFilter != null) {
      list = list
          .where((c) => c.grade.startsWith(_selectedGradeFilter!))
          .toList();
    }

    // Subject filter
    if (_selectedSubjectFilter != null) {
      list = list
          .where((c) => c.subjectCode == _selectedSubjectFilter)
          .toList();
    }

    // Semester filter
    if (_selectedSemesterFilter != null) {
      list = list
          .where((c) => c.semester == _selectedSemesterFilter)
          .toList();
    }

    // Special toggles
    if (_showFailedOnly) list = list.where((c) => c.isFailed).toList();
    if (_showRetakesOnly) list = list.where((c) => c.isRetake).toList();

    // Sort
    list.sort((a, b) {
      int cmp;
      switch (_sortMode) {
        case _SortMode.code:
          cmp = a.code.compareTo(b.code);
          break;
        case _SortMode.grade:
          cmp = a.grade.compareTo(b.grade);
          break;
        case _SortMode.credits:
          cmp = a.credits.compareTo(b.credits);
          break;
        case _SortMode.semester:
          cmp = a.semester.compareTo(b.semester);
          break;
      }
      return _sortAscending ? cmp : -cmp;
    });

    return list;
  }

  List<String> get _availableSubjects {
    if (_analysis == null) return [];
    final subjects = _analysis!.courses.map((c) => c.subjectCode).toSet().toList();
    subjects.sort();
    return subjects.where((s) => s.isNotEmpty).toList();
  }

  List<String> get _availableSemesters {
    if (_analysis == null) return [];
    final sems = _analysis!.courses.map((c) => c.semester).toSet().toList();
    sems.sort((a, b) => b.compareTo(a)); // newest first
    return sems.where((s) => s.isNotEmpty).toList();
  }

  bool get _hasActiveFilters =>
      _selectedGradeFilter != null ||
      _selectedSubjectFilter != null ||
      _selectedSemesterFilter != null ||
      _showFailedOnly ||
      _showRetakesOnly ||
      _searchQuery.isNotEmpty;

  void _clearFilters() {
    setState(() {
      _searchQuery = '';
      _searchCtrl.clear();
      _selectedGradeFilter = null;
      _selectedSubjectFilter = null;
      _selectedSemesterFilter = null;
      _showFailedOnly = false;
      _showRetakesOnly = false;
    });
  }

  // ─────────────────────────────────────────────
  // Sort sheet
  // ─────────────────────────────────────────────

  void _showSortSheet() {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => _SortSheet(
        current: _sortMode,
        ascending: _sortAscending,
        onChanged: (mode, asc) {
          setState(() {
            _sortMode = mode;
            _sortAscending = asc;
          });
          Navigator.pop(context);
        },
      ),
    );
  }

  // ─────────────────────────────────────────────
  // Filter sheet
  // ─────────────────────────────────────────────

  void _showFilterSheet() {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => _FilterSheet(
        gradeGroups: _gradeGroups,
        subjects: _availableSubjects,
        semesters: _availableSemesters,
        selectedGrade: _selectedGradeFilter,
        selectedSubject: _selectedSubjectFilter,
        selectedSemester: _selectedSemesterFilter,
        showFailedOnly: _showFailedOnly,
        showRetakesOnly: _showRetakesOnly,
        onApply: (grade, subject, semester, failed, retakes) {
          setState(() {
            _selectedGradeFilter = grade;
            _selectedSubjectFilter = subject;
            _selectedSemesterFilter = semester;
            _showFailedOnly = failed;
            _showRetakesOnly = retakes;
          });
          Navigator.pop(context);
        },
      ),
    );
  }

  // ─────────────────────────────────────────────
  // Build
  // ─────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    super.build(context);

    return RefreshIndicator(
      onRefresh: _loadData,
      color: kPrimary,
      backgroundColor: kSurface,
      child: Stack(
        children: [
          // ── Ambient glows ──
          const Positioned(
            top: -80,
            left: -60,
            child: AuroraBlob(color: Color(0xFF818CF8), size: 260),
          ),
          const Positioned(
            bottom: -80,
            right: -60,
            child: AuroraBlob(color: kPrimary, size: 220),
          ),

          // ── Main content ──
          CustomScrollView(
            controller: _scrollCtrl,
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              // ── Search + filter bar ──
              SliverPersistentHeader(
                pinned: true,
                delegate: _SearchBarDelegate(
                  child: _buildSearchBar(),
                ),
              ),

              // ── Body ──
              if (_isLoading)
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 100),
                  sliver: SliverList(
                    delegate: SliverChildListDelegate(_buildShimmer()),
                  ),
                )
              else if (_isGuest)
                SliverFillRemaining(
                  child: _buildGuestState(),
                )
              else if (_error != null)
                SliverFillRemaining(
                  child: _buildError(),
                )
              else if (_analysis == null || _analysis!.courses.isEmpty)
                SliverFillRemaining(
                  child: _buildEmpty(),
                )
              else
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 100),
                  sliver: SliverList(
                    delegate: SliverChildListDelegate(
                      _buildCourseList(),
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
  // Search bar
  // ─────────────────────────────────────────────

  Widget _buildSearchBar() {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          color: kBackground.withValues(alpha: 0.85),
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // ── Search row ──
              Row(
                children: [
                  Expanded(
                    child: Container(
                      height: 46,
                      decoration: BoxDecoration(
                        color: kSurface,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: kBorder),
                      ),
                      child: TextField(
                        controller: _searchCtrl,
                        style: const TextStyle(
                            color: kTextPrimary,
                            fontSize: 14,
                            fontFamily: 'Outfit'),
                        decoration: InputDecoration(
                          hintText: 'Search courses…',
                          hintStyle: const TextStyle(
                              color: kTextTertiary,
                              fontSize: 14,
                              fontFamily: 'Outfit'),
                          prefixIcon: const Icon(Icons.search_rounded,
                              color: kTextTertiary, size: 20),
                          suffixIcon: _searchQuery.isNotEmpty
                              ? IconButton(
                                  onPressed: () {
                                    _searchCtrl.clear();
                                    setState(() => _searchQuery = '');
                                  },
                                  icon: const Icon(Icons.close_rounded,
                                      color: kTextTertiary, size: 18),
                                )
                              : null,
                          border: InputBorder.none,
                          contentPadding: const EdgeInsets.symmetric(
                              horizontal: 0, vertical: 14),
                          isDense: true,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),

                  // ── Filter button ──
                  _IconBtn(
                    icon: Icons.tune_rounded,
                    active: _hasActiveFilters,
                    onTap: _showFilterSheet,
                    accent: kPrimary,
                  ),
                  const SizedBox(width: 8),

                  // ── Sort button ──
                  _IconBtn(
                    icon: Icons.sort_rounded,
                    active: false,
                    onTap: _showSortSheet,
                    accent: const Color(0xFF818CF8),
                  ),
                ],
              ),

              // ── Active filter chips ──
              if (_hasActiveFilters) ...[
                const SizedBox(height: 8),
                SizedBox(
                  height: 32,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: [
                      // Clear all chip
                      _FilterTag(
                        label: 'Clear all',
                        icon: Icons.close_rounded,
                        accent: kError,
                        onRemove: _clearFilters,
                      ),
                      if (_selectedGradeFilter != null)
                        _FilterTag(
                          label: 'Grade: $_selectedGradeFilter',
                          accent: gradeColor(_selectedGradeFilter!),
                          onRemove: () => setState(
                              () => _selectedGradeFilter = null),
                        ),
                      if (_selectedSubjectFilter != null)
                        _FilterTag(
                          label: 'Subject: $_selectedSubjectFilter',
                          accent: const Color(0xFF818CF8),
                          onRemove: () => setState(
                              () => _selectedSubjectFilter = null),
                        ),
                      if (_selectedSemesterFilter != null)
                        _FilterTag(
                          label: _selectedSemesterFilter!,
                          accent: kPrimary,
                          onRemove: () => setState(
                              () => _selectedSemesterFilter = null),
                        ),
                      if (_showFailedOnly)
                        _FilterTag(
                          label: 'Failed only',
                          accent: kError,
                          onRemove: () =>
                              setState(() => _showFailedOnly = false),
                        ),
                      if (_showRetakesOnly)
                        _FilterTag(
                          label: 'Retakes only',
                          accent: kWarning,
                          onRemove: () =>
                              setState(() => _showRetakesOnly = false),
                        ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────
  // Course list
  // ─────────────────────────────────────────────

  List<Widget> _buildCourseList() {
    final courses = _filteredCourses;

    if (courses.isEmpty) {
      return [
        const SizedBox(height: 40),
        EmptyState(
          icon: Icons.search_off_rounded,
          title: 'No courses match',
          subtitle:
              'Try adjusting your search or filters to find what you\'re looking for.',
          accent: kPrimary,
          action: TextButton.icon(
            onPressed: _clearFilters,
            icon: const Icon(Icons.filter_alt_off_rounded, size: 18),
            label: const Text('Clear filters'),
            style: TextButton.styleFrom(foregroundColor: kPrimary),
          ),
        ),
      ];
    }

    final widgets = <Widget>[];

    // ── Stats bar ──
    widgets.add(_buildStatsBar(courses));
    widgets.add(const SizedBox(height: 16));

    // ── Course cards, grouped by semester ──
    final grouped = _groupBySemester(courses);

    var delay = 0;
    for (final entry in grouped.entries) {
      // Semester header
      widgets.add(
        _SemesterHeader(semester: entry.key)
            .animate(delay: delay.ms)
            .fadeIn(duration: 350.ms)
            .slideX(begin: -0.05, end: 0, duration: 350.ms),
      );
      delay += 30;
      widgets.add(const SizedBox(height: 10));

      // Course cards
      for (final course in entry.value) {
        widgets.add(
          CourseCard(course: course)
              .animate(delay: delay.ms)
              .fadeIn(duration: 350.ms)
              .slideY(begin: 0.08, end: 0, duration: 350.ms),
        );
        delay = (delay + 40).clamp(0, 600);
        widgets.add(const SizedBox(height: 10));
      }

      widgets.add(const SizedBox(height: 8));
    }

    return widgets;
  }

  Map<String, List<CourseModel>> _groupBySemester(List<CourseModel> courses) {
    final map = <String, List<CourseModel>>{};
    for (final c in courses) {
      final key = c.semester.isNotEmpty ? c.semester : 'Unknown Semester';
      map.putIfAbsent(key, () => []).add(c);
    }
    return map;
  }

  Widget _buildStatsBar(List<CourseModel> courses) {
    final total = courses.length;
    final passed = courses.where((c) => !c.isFailed).length;
    final failed = courses.where((c) => c.isFailed).length;
    final totalCredits =
        courses.fold<double>(0, (sum, c) => sum + c.credits);

    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            gradient: LinearGradient(
              colors: [
                Colors.white.withValues(alpha: 0.06),
                Colors.white.withValues(alpha: 0.02),
              ],
            ),
            border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _StatCell(label: 'Showing', value: '$total', accent: kPrimary),
              _Divider(),
              _StatCell(label: 'Passed', value: '$passed', accent: kSuccess),
              _Divider(),
              _StatCell(
                  label: 'Failed',
                  value: '$failed',
                  accent: failed > 0 ? kError : kTextTertiary),
              _Divider(),
              _StatCell(
                  label: 'Credits',
                  value: totalCredits.toStringAsFixed(1),
                  accent: const Color(0xFF818CF8)),
            ],
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────
  // Loading / Error / Empty
  // ─────────────────────────────────────────────

  List<Widget> _buildShimmer() => [
        const SizedBox(height: 8),
        _shimmer(height: 50),
        const SizedBox(height: 16),
        _shimmer(height: 22, width: 120),
        const SizedBox(height: 10),
        _shimmer(height: 90),
        const SizedBox(height: 10),
        _shimmer(height: 90),
        const SizedBox(height: 10),
        _shimmer(height: 90),
        const SizedBox(height: 16),
        _shimmer(height: 22, width: 140),
        const SizedBox(height: 10),
        _shimmer(height: 90),
        const SizedBox(height: 10),
        _shimmer(height: 90),
      ];

  Widget _shimmer({required double height, double? width}) => Container(
        height: height,
        width: width ?? double.infinity,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: kSurface,
        ),
        child: ShimmerBox(height: height, borderRadius: 14),
      );

  Widget _buildError() => EmptyState(
        icon: Icons.cloud_off_rounded,
        title: 'Could not load courses',
        subtitle: _error ?? 'Pull down to refresh.',
        accent: kError,
        action: ElevatedButton.icon(
          onPressed: _loadData,
          icon: const Icon(Icons.refresh_rounded, size: 18),
          label: const Text('Retry'),
          style: ElevatedButton.styleFrom(
            backgroundColor: kError,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12)),
          ),
        ),
      );

  Widget _buildEmpty() => EmptyState(
        icon: Icons.menu_book_outlined,
        title: 'No courses yet',
        subtitle:
            'Upload your NSU transcript to see your course history here.',
        accent: const Color(0xFF818CF8),
      );

  Widget _buildGuestState() => EmptyState(
        icon: Icons.lock_outline_rounded,
        title: 'Guest mode is active',
        subtitle: 'Sign in with Google to view your personalized course history.',
        accent: kPrimary,
        action: GradientButton(
          label: 'Sign In with Google',
          icon: Icons.login_rounded,
          onPressed: _navigateToAuth,
          width: 230,
        ),
      );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Sort mode enum
// ═══════════════════════════════════════════════════════════════════════════════

enum _SortMode { semester, code, grade, credits }

// ═══════════════════════════════════════════════════════════════════════════════
// Course Card
// ═══════════════════════════════════════════════════════════════════════════════

class CourseCard extends StatefulWidget {
  const CourseCard({super.key, required this.course});
  final CourseModel course;

  @override
  State<CourseCard> createState() => _CourseCardState();
}

class _CourseCardState extends State<CourseCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final c = widget.course;
    final accent = gradeColor(c.grade);
    final hasBadge = c.isFailed || c.isRetake;

    return GestureDetector(
      onTap: () => setState(() => _expanded = !_expanded),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeInOut,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(18),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    (c.isFailed ? kError : accent).withValues(alpha: 0.07),
                    Colors.white.withValues(alpha: 0.03),
                  ],
                ),
                border: Border.all(
                  color: c.isFailed
                      ? kError.withValues(alpha: 0.30)
                      : c.isRetake
                          ? kWarning.withValues(alpha: 0.30)
                          : Colors.white.withValues(alpha: 0.08),
                  width: 1,
                ),
              ),
              child: Column(
                children: [
                  // ── Main row ──
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // ── Subject badge ──
                        Container(
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(13),
                            gradient: LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                accent.withValues(alpha: 0.20),
                                accent.withValues(alpha: 0.08),
                              ],
                            ),
                            border: Border.all(
                                color: accent.withValues(alpha: 0.30), width: 1),
                          ),
                          child: Center(
                            child: Text(
                              c.subjectCode.isEmpty
                                  ? '?'
                                  : c.subjectCode.length > 3
                                      ? c.subjectCode.substring(0, 3)
                                      : c.subjectCode,
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w800,
                                color: accent,
                                fontFamily: 'Outfit',
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 14),

                        // ── Course info ──
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Code + warning badges
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.center,
                                children: [
                                  Text(
                                    c.code,
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleSmall
                                        ?.copyWith(
                                          color: kTextPrimary,
                                          fontWeight: FontWeight.w800,
                                          fontSize: 15,
                                        ),
                                  ),
                                  if (hasBadge) ...[
                                    const SizedBox(width: 8),
                                    if (c.isFailed)
                                      _MiniTag(label: 'Failed', color: kError),
                                    if (c.isRetake && !c.isFailed) ...[
                                      const SizedBox(width: 4),
                                      _MiniTag(label: 'Retake', color: kWarning),
                                    ],
                                  ],
                                ],
                              ),
                              if (c.name.isNotEmpty) ...[
                                const SizedBox(height: 4),
                                Text(
                                  c.name,
                                  style: Theme.of(context)
                                      .textTheme
                                      .bodySmall
                                      ?.copyWith(color: kTextSecondary),
                                  maxLines: _expanded ? 3 : 1,
                                  overflow: _expanded
                                      ? TextOverflow.visible
                                      : TextOverflow.ellipsis,
                                ),
                              ],
                              const SizedBox(height: 8),
                              // Meta row
                              Row(
                                children: [
                                  _MetaChip(
                                    icon: Icons.calendar_today_outlined,
                                    label: c.semester.isNotEmpty
                                        ? c.semester
                                        : 'N/A',
                                  ),
                                  const SizedBox(width: 8),
                                  _MetaChip(
                                    icon: Icons.credit_card_outlined,
                                    label: '${c.credits} cr',
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(width: 10),

                        // ── Grade + expand icon ──
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            GradeChip(grade: c.grade),
                            const SizedBox(height: 8),
                            Icon(
                              _expanded
                                  ? Icons.keyboard_arrow_up_rounded
                                  : Icons.keyboard_arrow_down_rounded,
                              color: kTextTertiary,
                              size: 18,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),

                  // ── Expanded details ──
                  AnimatedSize(
                    duration: const Duration(milliseconds: 280),
                    curve: Curves.easeInOut,
                    child: _expanded
                        ? _ExpandedDetails(course: c, accent: accent)
                        : const SizedBox.shrink(),
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

class _ExpandedDetails extends StatelessWidget {
  const _ExpandedDetails({required this.course, required this.accent});
  final CourseModel course;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(color: kBorder, height: 1),
          const SizedBox(height: 14),

          // Detail grid
          Row(
            children: [
              Expanded(
                child: _DetailCell(
                    label: 'Course Code', value: course.code),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _DetailCell(
                    label: 'Credit Hours',
                    value: '${course.credits}'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _DetailCell(
                    label: 'Grade', value: course.grade),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _DetailCell(
                    label: 'Semester', value: course.semester),
              ),
            ],
          ),
          if (course.isFailed || course.isRetake) ...[
            const SizedBox(height: 14),
            if (course.isFailed)
              AlertBox(
                accent: kError,
                icon: Icons.warning_amber_rounded,
                title: 'Course Failed',
                body:
                    'This course has a failing grade. Consider retaking it.',
              ),
            if (course.isRetake && !course.isFailed) ...[
              AlertBox(
                accent: kWarning,
                icon: Icons.refresh_rounded,
                title: 'Course Retaken',
                body:
                    'This course appears more than once in your transcript.',
              ),
            ],
          ],
        ],
      ),
    );
  }
}

class _DetailCell extends StatelessWidget {
  const _DetailCell({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: kBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: kTextTertiary, fontSize: 11)),
          const SizedBox(height: 4),
          Text(value,
              style: Theme.of(context)
                  .textTheme
                  .titleSmall
                  ?.copyWith(
                      color: kTextPrimary, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Semester Header
// ═══════════════════════════════════════════════════════════════════════════════

class _SemesterHeader extends StatelessWidget {
  const _SemesterHeader({required this.semester});
  final String semester;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: kPrimary.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: kPrimary.withValues(alpha: 0.25), width: 1),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.calendar_month_rounded,
                  size: 13, color: kPrimary),
              const SizedBox(width: 6),
              Text(
                semester,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: kPrimary,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.3,
                    ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 10),
        const Expanded(child: Divider(color: kBorder)),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Sort Sheet
// ═══════════════════════════════════════════════════════════════════════════════

class _SortSheet extends StatefulWidget {
  const _SortSheet({
    required this.current,
    required this.ascending,
    required this.onChanged,
  });

  final _SortMode current;
  final bool ascending;
  final void Function(_SortMode, bool) onChanged;

  @override
  State<_SortSheet> createState() => _SortSheetState();
}

class _SortSheetState extends State<_SortSheet> {
  late _SortMode _mode;
  late bool _asc;

  @override
  void initState() {
    super.initState();
    _mode = widget.current;
    _asc = widget.ascending;
  }

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: Container(
          decoration: BoxDecoration(
            color: kSurface.withValues(alpha: 0.95),
            borderRadius:
                const BorderRadius.vertical(top: Radius.circular(24)),
            border: const Border(top: BorderSide(color: kBorder, width: 1)),
          ),
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Handle
              Center(
                child: Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: kBorder,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
              ),
              const SizedBox(height: 20),

              Text('Sort by',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: kTextPrimary, fontWeight: FontWeight.w700)),
              const SizedBox(height: 16),

              ...[
                (_SortMode.semester, 'Semester', Icons.calendar_month_rounded),
                (_SortMode.code, 'Course Code', Icons.sort_by_alpha_rounded),
                (_SortMode.grade, 'Grade', Icons.grade_rounded),
                (_SortMode.credits, 'Credits', Icons.credit_card_rounded),
              ].map((item) => _SortTile(
                    label: item.$2,
                    icon: item.$3,
                    selected: _mode == item.$1,
                    ascending: _asc,
                    onTap: () => setState(() {
                      if (_mode == item.$1) {
                        _asc = !_asc;
                      } else {
                        _mode = item.$1;
                        _asc = false;
                      }
                    }),
                  )),

              const SizedBox(height: 20),
              GradientButton(
                label: 'Apply Sort',
                onPressed: () => widget.onChanged(_mode, _asc),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SortTile extends StatelessWidget {
  const _SortTile({
    required this.label,
    required this.icon,
    required this.selected,
    required this.ascending,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool selected;
  final bool ascending;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: selected ? kPrimary.withValues(alpha: 0.12) : Colors.transparent,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: selected ? kPrimary.withValues(alpha: 0.35) : kBorder,
            width: 1,
          ),
        ),
        child: Row(
          children: [
            Icon(icon,
                color: selected ? kPrimary : kTextSecondary, size: 20),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                label,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: selected ? kTextPrimary : kTextSecondary,
                      fontWeight:
                          selected ? FontWeight.w600 : FontWeight.w400,
                    ),
              ),
            ),
            if (selected)
              Icon(
                ascending
                    ? Icons.arrow_upward_rounded
                    : Icons.arrow_downward_rounded,
                color: kPrimary,
                size: 18,
              ),
          ],
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Filter Sheet
// ═══════════════════════════════════════════════════════════════════════════════

class _FilterSheet extends StatefulWidget {
  const _FilterSheet({
    required this.gradeGroups,
    required this.subjects,
    required this.semesters,
    required this.selectedGrade,
    required this.selectedSubject,
    required this.selectedSemester,
    required this.showFailedOnly,
    required this.showRetakesOnly,
    required this.onApply,
  });

  final List<String> gradeGroups;
  final List<String> subjects;
  final List<String> semesters;
  final String? selectedGrade;
  final String? selectedSubject;
  final String? selectedSemester;
  final bool showFailedOnly;
  final bool showRetakesOnly;
  final void Function(
    String? grade,
    String? subject,
    String? semester,
    bool failedOnly,
    bool retakesOnly,
  ) onApply;

  @override
  State<_FilterSheet> createState() => _FilterSheetState();
}

class _FilterSheetState extends State<_FilterSheet> {
  late String? _grade;
  late String? _subject;
  late String? _semester;
  late bool _failedOnly;
  late bool _retakesOnly;

  @override
  void initState() {
    super.initState();
    _grade = widget.selectedGrade;
    _subject = widget.selectedSubject;
    _semester = widget.selectedSemester;
    _failedOnly = widget.showFailedOnly;
    _retakesOnly = widget.showRetakesOnly;
  }

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: Container(
          decoration: BoxDecoration(
            color: kSurface.withValues(alpha: 0.95),
            borderRadius:
                const BorderRadius.vertical(top: Radius.circular(24)),
            border: const Border(top: BorderSide(color: kBorder, width: 1)),
          ),
          padding: EdgeInsets.fromLTRB(
              20, 12, 20, MediaQuery.of(context).viewInsets.bottom + 32),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Handle
                Center(
                  child: Container(
                    width: 36,
                    height: 4,
                    decoration: BoxDecoration(
                      color: kBorder,
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                Row(
                  children: [
                    Text('Filters',
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(
                                color: kTextPrimary,
                                fontWeight: FontWeight.w700)),
                    const Spacer(),
                    TextButton(
                      onPressed: () => setState(() {
                        _grade = null;
                        _subject = null;
                        _semester = null;
                        _failedOnly = false;
                        _retakesOnly = false;
                      }),
                      style: TextButton.styleFrom(
                          foregroundColor: kError,
                          padding: EdgeInsets.zero),
                      child: const Text('Reset',
                          style: TextStyle(fontSize: 13)),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // ── Grade filter ──
                _FilterSection(label: 'Grade'),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: widget.gradeGroups.map((g) {
                    final selected = _grade == g;
                    final color = gradeColor(g);
                    return GestureDetector(
                      onTap: () =>
                          setState(() => _grade = selected ? null : g),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 9),
                        decoration: BoxDecoration(
                          color: selected
                              ? color.withValues(alpha: 0.20)
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(999),
                          border: Border.all(
                            color: selected
                                ? color.withValues(alpha: 0.50)
                                : kBorder,
                            width: 1,
                          ),
                        ),
                        child: Text(
                          'Grade $g',
                          style: TextStyle(
                            color: selected ? color : kTextSecondary,
                            fontSize: 13,
                            fontWeight: selected
                                ? FontWeight.w700
                                : FontWeight.w400,
                            fontFamily: 'Outfit',
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),

                const SizedBox(height: 24),

                // ── Subject filter ──
                if (widget.subjects.isNotEmpty) ...[
                  _FilterSection(label: 'Subject'),
                  const SizedBox(height: 10),
                  SizedBox(
                    height: 42,
                    child: ListView(
                      scrollDirection: Axis.horizontal,
                      children: [
                        _SubjectChip(
                          label: 'All',
                          selected: _subject == null,
                          onTap: () =>
                              setState(() => _subject = null),
                        ),
                        ...widget.subjects.map(
                          (s) => _SubjectChip(
                            label: s,
                            selected: _subject == s,
                            onTap: () => setState(
                                () => _subject = _subject == s ? null : s),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                ],

                // ── Semester filter ──
                if (widget.semesters.isNotEmpty) ...[
                  _FilterSection(label: 'Semester'),
                  const SizedBox(height: 10),
                  SizedBox(
                    height: 42,
                    child: ListView(
                      scrollDirection: Axis.horizontal,
                      children: [
                        _SubjectChip(
                          label: 'All',
                          selected: _semester == null,
                          onTap: () =>
                              setState(() => _semester = null),
                        ),
                        ...widget.semesters.map(
                          (s) => _SubjectChip(
                            label: s,
                            selected: _semester == s,
                            onTap: () => setState(() =>
                                _semester = _semester == s ? null : s),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                ],

                // ── Toggles ──
                _FilterSection(label: 'Quick Filters'),
                const SizedBox(height: 10),
                _ToggleRow(
                  label: 'Failed courses only',
                  icon: Icons.close_rounded,
                  accent: kError,
                  value: _failedOnly,
                  onChanged: (v) {
                    setState(() {
                      _failedOnly = v;
                      if (v) _retakesOnly = false;
                    });
                  },
                ),
                const SizedBox(height: 8),
                _ToggleRow(
                  label: 'Retaken courses only',
                  icon: Icons.refresh_rounded,
                  accent: kWarning,
                  value: _retakesOnly,
                  onChanged: (v) {
                    setState(() {
                      _retakesOnly = v;
                      if (v) _failedOnly = false;
                    });
                  },
                ),

                const SizedBox(height: 28),

                GradientButton(
                  label: 'Apply Filters',
                  onPressed: () => widget.onApply(
                    _grade,
                    _subject,
                    _semester,
                    _failedOnly,
                    _retakesOnly,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Persistent Header Delegate for search bar
// ═══════════════════════════════════════════════════════════════════════════════

class _SearchBarDelegate extends SliverPersistentHeaderDelegate {
  const _SearchBarDelegate({required this.child});
  final Widget child;

  @override
  Widget build(
      BuildContext context, double shrinkOffset, bool overlapsContent) {
    return child;
  }

  @override
  double get maxExtent => 80;

  @override
  double get minExtent => 80;

  @override
  bool shouldRebuild(covariant _SearchBarDelegate oldDelegate) => false;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Small helper widgets
// ═══════════════════════════════════════════════════════════════════════════════

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
        borderRadius: BorderRadius.circular(5),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 9,
          fontWeight: FontWeight.w800,
          color: color,
          fontFamily: 'Outfit',
        ),
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 12, color: kTextTertiary),
        const SizedBox(width: 4),
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

class _IconBtn extends StatelessWidget {
  const _IconBtn({
    required this.icon,
    required this.active,
    required this.onTap,
    required this.accent,
  });

  final IconData icon;
  final bool active;
  final VoidCallback onTap;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 46,
        height: 46,
        decoration: BoxDecoration(
          color: active ? accent.withValues(alpha: 0.15) : kSurface,
          borderRadius: BorderRadius.circular(13),
          border: Border.all(
            color: active ? accent.withValues(alpha: 0.40) : kBorder,
            width: 1,
          ),
        ),
        child: Icon(icon,
            color: active ? accent : kTextSecondary, size: 20),
      ),
    );
  }
}

class _FilterTag extends StatelessWidget {
  const _FilterTag({
    required this.label,
    this.icon,
    required this.accent,
    required this.onRemove,
  });

  final String label;
  final IconData? icon;
  final Color accent;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onRemove,
      child: Container(
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: accent.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: accent.withValues(alpha: 0.30), width: 1),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, size: 12, color: accent),
              const SizedBox(width: 5),
            ],
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: accent,
                fontFamily: 'Outfit',
              ),
            ),
            if (icon == null) ...[
              const SizedBox(width: 5),
              Icon(Icons.close_rounded, size: 12, color: accent),
            ],
          ],
        ),
      ),
    );
  }
}

class _StatCell extends StatelessWidget {
  const _StatCell({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          value,
          style: TextStyle(
            color: accent,
            fontSize: 16,
            fontWeight: FontWeight.w800,
            fontFamily: 'Outfit',
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(
            color: kTextTertiary,
            fontSize: 10,
            fontFamily: 'Outfit',
          ),
        ),
      ],
    );
  }
}

class _Divider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 1,
      height: 28,
      color: kBorder,
    );
  }
}

class _FilterSection extends StatelessWidget {
  const _FilterSection({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      label.toUpperCase(),
      style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: kTextTertiary,
            letterSpacing: 1.2,
            fontWeight: FontWeight.w700,
          ),
    );
  }
}

class _SubjectChip extends StatelessWidget {
  const _SubjectChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? kPrimary.withValues(alpha: 0.20) : Colors.transparent,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: selected ? kPrimary.withValues(alpha: 0.50) : kBorder,
            width: 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? kPrimary : kTextSecondary,
            fontSize: 13,
            fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
            fontFamily: 'Outfit',
          ),
        ),
      ),
    );
  }
}

class _ToggleRow extends StatelessWidget {
  const _ToggleRow({
    required this.label,
    required this.icon,
    required this.accent,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final IconData icon;
  final Color accent;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => onChanged(!value),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color:
              value ? accent.withValues(alpha: 0.10) : Colors.transparent,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: value ? accent.withValues(alpha: 0.35) : kBorder,
            width: 1,
          ),
        ),
        child: Row(
          children: [
            Icon(icon,
                color: value ? accent : kTextSecondary, size: 18),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                label,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: value ? kTextPrimary : kTextSecondary,
                      fontWeight:
                          value ? FontWeight.w600 : FontWeight.w400,
                    ),
              ),
            ),
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 44,
              height: 24,
              decoration: BoxDecoration(
                color: value ? accent : kSurface,
                borderRadius: BorderRadius.circular(999),
                border: Border.all(
                    color: value ? accent : kBorder, width: 1),
              ),
              child: AnimatedAlign(
                duration: const Duration(milliseconds: 200),
                alignment:
                    value ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.all(3),
                  width: 18,
                  height: 18,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
