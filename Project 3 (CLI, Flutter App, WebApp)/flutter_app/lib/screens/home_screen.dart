import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../widgets/glass_widgets.dart';

// Cloud Run backend API with custom domain
const defaultApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://ocrapi.nsunexus.app',
);

double asDouble(dynamic value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}

int asInt(dynamic value) {
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

String asString(dynamic value) => value?.toString() ?? '';

Map<String, dynamic> asMap(dynamic value) =>
    value is Map<String, dynamic> ? value : <String, dynamic>{};

List<dynamic> asList(dynamic value) => value is List ? value : <dynamic>[];

enum UploadStage { idle, uploading, ready, failure }

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  static const progressMessages = <String>[
    'Booting premium OCR pipeline',
    'Securing transcript upload',
    'Extracting course rows and grades',
    'Resolving retakes and credit signals',
    'Composing degree audit story',
  ];

  late final TextEditingController endpointController;
  Timer? progressTimer;
  Map<String, dynamic>? data;
  String apiBaseUrl = defaultApiBaseUrl;
  String statusMessage =
      'Pick a transcript and the app will call the same web API logic.';
  String? errorMessage;
  String? selectedFileName;
  UploadStage stage = UploadStage.idle;
  double progress = 0;
  int selectedLevel = 1;
  int progressIndex = 0;

  @override
  void initState() {
    super.initState();
    endpointController = TextEditingController(text: apiBaseUrl);
  }

  @override
  void dispose() {
    progressTimer?.cancel();
    endpointController.dispose();
    super.dispose();
  }

  Future<void> pickTranscript() async {
    final selection = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['pdf', 'png', 'jpg', 'jpeg'],
      withData: false,
    );
    if (selection == null || selection.files.single.path == null) return;

    final file = File(selection.files.single.path!);
    selectedFileName = selection.files.single.name;
    startProgress();

    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse(apiBaseUrl).resolve('/upload'),
      )..files.add(await http.MultipartFile.fromPath('file', file.path));

      final response = await request.send();
      final body = await response.stream.bytesToString();
      final decoded = jsonDecode(body) as Map<String, dynamic>;
      if (response.statusCode >= 400 || decoded['success'] != true) {
        throw Exception(decoded['error'] ?? 'The server rejected the upload.');
      }
      if (!mounted) return;

      progressTimer?.cancel();
      setState(() {
        data = asMap(decoded['data']);
        stage = UploadStage.ready;
        progress = 1;
        selectedLevel = 1;
        errorMessage = null;
        statusMessage = 'Analysis is ready. Explore Level 1, 2, and 3 below.';
      });
    } catch (error) {
      if (!mounted) return;
      progressTimer?.cancel();
      setState(() {
        stage = UploadStage.failure;
        progress = 0;
        data = null;
        errorMessage = error.toString().replaceFirst('Exception: ', '');
        statusMessage = 'Upload failed. Review the error and try again.';
      });
    }
  }

  void startProgress() {
    progressTimer?.cancel();
    setState(() {
      data = null;
      stage = UploadStage.uploading;
      progress = 0.08;
      progressIndex = 0;
      errorMessage = null;
      statusMessage = progressMessages.first;
    });
    progressTimer = Timer.periodic(const Duration(milliseconds: 650), (_) {
      if (!mounted) return;
      setState(() {
        progress = (progress + 0.07).clamp(0.08, 0.92);
        progressIndex = (progressIndex + 1) % progressMessages.length;
        statusMessage = progressMessages[progressIndex];
      });
    });
  }

  Future<void> editEndpoint() async {
    endpointController.text = apiBaseUrl;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 20,
          bottom: MediaQuery.of(context).viewInsets.bottom + 24,
        ),
        child: GlassCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('API Endpoint', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(
                'Point the app to local Flask, the emulator bridge, or the deployed Vercel backend.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              TextField(controller: endpointController),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () {
                    setState(() {
                      apiBaseUrl = endpointController.text.trim().isEmpty
                          ? defaultApiBaseUrl
                          : endpointController.text.trim();
                    });
                    Navigator.of(context).pop();
                  },
                  child: const Text('Save Endpoint'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: GradientBackground(
        child: Stack(
          children: [
            const Positioned(top: -120, left: -90, child: AuroraBlob(color: Color(0xFF0FA3FF), size: 250)),
            const Positioned(top: 220, right: -70, child: AuroraBlob(color: Color(0xFFF6B75D), size: 220)),
            const Positioned(bottom: -120, left: 40, child: AuroraBlob(color: Color(0xFF7A7CFF), size: 280)),
            SafeArea(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 32),
                child: buildContent(context),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget buildContent(BuildContext context) {
    final theme = Theme.of(context);
    final info = asMap(data?['ocr_info']);
    final level1 = asMap(data?['level1']);
    final level2 = asMap(data?['level2']);
    final courses = asList(data?['courses']);

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
                      borderRadius: BorderRadius.circular(18),
                      gradient: const LinearGradient(colors: [Color(0xFF57C5FF), Color(0xFF0058A8)]),
                    ),
                    child: const Icon(Icons.auto_awesome, color: Colors.white),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('North South University', style: theme.textTheme.bodyMedium),
                        Text('Degree Audit Mobile Suite', style: theme.textTheme.titleLarge),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: editEndpoint,
                    icon: const Icon(Icons.settings_outlined, color: Color(0xFF7A8BA6)),
                    tooltip: 'API Settings',
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                'Academic transcript analysis with the same backend logic as the website, rebuilt for a sharper mobile experience.',
                style: theme.textTheme.bodyLarge?.copyWith(fontSize: 15, height: 1.5),
              ),
              const SizedBox(height: 16),
              const Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  FeatureChip(icon: Icons.document_scanner_outlined, label: 'PDF and image upload'),
                  FeatureChip(icon: Icons.stacked_bar_chart, label: 'Three audit levels'),
                  FeatureChip(icon: Icons.workspace_premium, label: 'Premium mobile UI'),
                ],
              ),
              const SizedBox(height: 18),
              GlassTone(
                child: Row(
                  children: [
                    const Icon(Icons.cloud_done_outlined, color: Color(0xFF57C5FF)),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        apiBaseUrl,
                        style: theme.textTheme.bodyMedium?.copyWith(color: Colors.white),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: stage == UploadStage.uploading ? null : pickTranscript,
                  icon: const Icon(Icons.file_open_outlined),
                  label: const Padding(
                    padding: EdgeInsets.symmetric(vertical: 14),
                    child: Text('Pick Transcript'),
                  ),
                ),
              ),
            ],
          ),
        ),
        if (selectedFileName != null) ...[
          const SizedBox(height: 18),
          GlassCard(
            child: Row(
              children: [
                const Icon(Icons.insert_drive_file_outlined, color: Color(0xFF57C5FF)),
                const SizedBox(width: 12),
                Expanded(child: Text(selectedFileName!, style: theme.textTheme.titleMedium?.copyWith(color: Colors.white))),
              ],
            ),
          ),
        ],
        if (stage == UploadStage.uploading) ...[
          const SizedBox(height: 18),
          ProcessingPanel(progress: progress, message: statusMessage),
        ],
        if (stage == UploadStage.failure && errorMessage != null) ...[
          const SizedBox(height: 18),
          AlertBox(accent: const Color(0xFFFF7B7B), icon: Icons.error_outline, title: 'Upload failed', body: errorMessage!),
        ],
        if (data != null) ...[
          const SizedBox(height: 24),
          SectionHeader(
            eyebrow: 'Result cockpit',
            title: 'Transcript intelligence at a glance',
            subtitle: statusMessage,
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(child: StatCard(label: 'Resolved courses', value: '${courses.length}', icon: Icons.layers_outlined, accent: const Color(0xFF57C5FF))),
              const SizedBox(width: 12),
              Expanded(child: StatCard(label: 'Earned credits', value: asDouble(level1['earned_credits']).toStringAsFixed(1), icon: Icons.stacked_line_chart, accent: const Color(0xFFF6B75D))),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: StatCard(label: 'Calculated CGPA', value: asDouble(level2['cgpa']).toStringAsFixed(2), icon: Icons.insights_outlined, accent: const Color(0xFF80FFBD))),
              const SizedBox(width: 12),
              Expanded(child: StatCard(label: 'OCR confidence', value: '${asDouble(info['confidence']).toStringAsFixed(1)}%', icon: Icons.track_changes_outlined, accent: const Color(0xFFA699FF))),
            ],
          ),
          const SizedBox(height: 14),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('OCR snapshot', style: theme.textTheme.titleMedium?.copyWith(color: Colors.white)),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    DataPill(icon: Icons.memory_outlined, label: 'Engine', value: asString(info['engine']).isEmpty ? 'Unknown' : asString(info['engine'])),
                    DataPill(icon: Icons.person_outline, label: 'Student', value: asString(info['student_name']).isEmpty ? 'Not captured' : asString(info['student_name'])),
                    DataPill(icon: Icons.badge_outlined, label: 'Student ID', value: asString(info['student_id']).isEmpty ? 'Not captured' : asString(info['student_id'])),
                  ],
                ),
                if (asDouble(info['total_credits_from_pdf']) > 0 || asDouble(info['cgpa_from_pdf']) > 0) ...[
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(child: StripMetric(label: 'Official PDF credits', value: asDouble(info['total_credits_from_pdf']) > 0 ? asDouble(info['total_credits_from_pdf']).toStringAsFixed(1) : 'n/a')),
                      const SizedBox(width: 12),
                      Expanded(child: StripMetric(label: 'Official PDF CGPA', value: asDouble(info['cgpa_from_pdf']) > 0 ? asDouble(info['cgpa_from_pdf']).toStringAsFixed(2) : 'n/a')),
                    ],
                  ),
                ],
              ],
            ),
          ),
          if (data!['cgpa_warning'] != null) ...[
            const SizedBox(height: 14),
            AlertBox(
              accent: const Color(0xFFF6B75D),
              icon: Icons.warning_amber_rounded,
              title: 'CGPA mismatch detected',
              body: 'PDF ${asDouble(asMap(data!['cgpa_warning'])['pdf_value']).toStringAsFixed(2)} | Calculated ${asDouble(asMap(data!['cgpa_warning'])['calculated_value']).toStringAsFixed(2)} | Difference ${asDouble(asMap(data!['cgpa_warning'])['difference']).toStringAsFixed(2)}',
            ),
          ],
          const SizedBox(height: 18),
          SegmentedButton<int>(
            showSelectedIcon: false,
            segments: const [
              ButtonSegment(value: 1, label: Text('Level 1')),
              ButtonSegment(value: 2, label: Text('Level 2')),
              ButtonSegment(value: 3, label: Text('Level 3')),
            ],
            selected: {selectedLevel},
            onSelectionChanged: (value) => setState(() => selectedLevel = value.first),
          ),
          const SizedBox(height: 16),
          buildLevelPanel(),
          const SizedBox(height: 18),
          buildSemesterPanel(),
          const SizedBox(height: 18),
          buildOcrPanel(),
        ],
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
              SmallMetric(label: 'Total entries', value: '${asInt(level1['total_entries'])}'),
              SmallMetric(label: 'Unique courses', value: '${asInt(level1['unique_courses'])}'),
              SmallMetric(label: 'Attempted credits', value: asDouble(level1['total_credits_attempted']).toStringAsFixed(1)),
              SmallMetric(label: 'Earned credits', value: asDouble(level1['earned_credits']).toStringAsFixed(1)),
              SmallMetric(label: 'Failed credits', value: asDouble(level1['failed_credits']).toStringAsFixed(1)),
              SmallMetric(label: 'Retakes', value: '${asInt(level1['retakes_count'])}'),
            ],
          ),
          const SizedBox(height: 16),
          Text('Graduation runway', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white)),
          const SizedBox(height: 10),
          LinearProgressIndicator(value: (asDouble(level1['progress_130']) / 100).clamp(0, 1), minHeight: 14, borderRadius: BorderRadius.circular(999), backgroundColor: Colors.white.withValues(alpha: 0.08)),
          const SizedBox(height: 10),
          Text('${asDouble(level1['earned_credits']).toStringAsFixed(1)} of 130 credits completed • ${asDouble(level1['progress_130']).toStringAsFixed(1)}%', style: Theme.of(context).textTheme.bodyMedium),
          if (retakes.isNotEmpty) ...[
            const SizedBox(height: 18),
            Text('Retake intelligence', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white)),
            const SizedBox(height: 10),
            ...retakes.map((item) {
              final retake = asMap(item);
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: GlassTone(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(asString(retake['code']), style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white)),
                      const SizedBox(height: 6),
                      Wrap(spacing: 6, children: asList(retake['grades']).map((grade) => GradeChip(grade: asString(grade))).toList().cast<Widget>()),
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
              SmallMetric(label: 'CGPA', value: asDouble(level2['cgpa']).toStringAsFixed(2)),
              SmallMetric(label: 'GPA credits', value: '${asInt(level2['gpa_credits'])}'),
              SmallMetric(label: 'Quality points', value: asDouble(level2['total_quality_points']).toStringAsFixed(2)),
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
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white),
                  ),
                ),
                Text(asString(level2['stars']), style: const TextStyle(fontSize: 20)),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Grade distribution',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white),
          ),
          const SizedBox(height: 10),
          if (gradeDistribution.isEmpty)
            Text('No grade distribution available.', style: Theme.of(context).textTheme.bodyMedium)
          else
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: gradeDistribution.entries.map((entry) {
                return GlassTone(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
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
              body: '${asString(waiver['level'])} ${asString(waiver['name'])} appears available from the current calculated CGPA.',
            )
          else
            const AlertBox(
              accent: Color(0xFF57C5FF),
              icon: Icons.info_outline,
              title: 'Scholarship status',
              body: 'No tuition waiver threshold is currently met from the calculated results.',
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
              SmallMetric(label: 'Program', value: asString(level3['program']).isEmpty ? 'Unknown' : asString(level3['program'])),
              SmallMetric(label: 'Mandatory progress', value: '${asDouble(level3['mandatory_progress']).toStringAsFixed(1)}%'),
            ],
          ),
          const SizedBox(height: 16),
          AlertBox(
            accent: level3['graduation_ready'] == true ? const Color(0xFF80FFBD) : const Color(0xFFF6B75D),
            icon: level3['graduation_ready'] == true ? Icons.verified : Icons.rule_folder_outlined,
            title: asString(level3['program_name']).isEmpty ? 'Program insight' : asString(level3['program_name']),
            body: level3['graduation_ready'] == true
                ? 'This audit looks graduation-ready based on the available rules and credits.'
                : asString(level3['note']).isNotEmpty
                    ? asString(level3['note'])
                    : 'Mandatory and elective requirements still need attention.',
          ),
          const SizedBox(height: 16),
          Text(
            'Missing mandatory courses',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white),
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
            style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white),
          ),
          const SizedBox(height: 10),
          if (electives.isEmpty)
            Text('No elective groups were loaded for this program.', style: Theme.of(context).textTheme.bodyMedium)
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
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              color: details['satisfied'] == true
                                  ? const Color(0xFF80FFBD).withValues(alpha: 0.16)
                                  : const Color(0xFFF6B75D).withValues(alpha: 0.16),
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text(details['satisfied'] == true ? 'Satisfied' : 'Pending'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text('${asInt(details['completed'])} of ${asInt(details['required'])} required completed'),
                      if (asList(details['courses']).isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: asList(details['courses']).map((course) => GradeChip(grade: asString(course))).toList().cast<Widget>(),
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
            Text('No semester grouping is available.', style: Theme.of(context).textTheme.bodyMedium)
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
                              asString(semester['name']).isEmpty ? 'Semester' : asString(semester['name']),
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white),
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
                                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.white),
                                ),
                              ),
                              Text('${asDouble(course['credits']).toStringAsFixed(1)} cr'),
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
              SmallMetric(label: 'Raw text rows', value: '${asInt(info['raw_text_count'])}'),
              SmallMetric(label: 'OCR engine', value: asString(info['engine']).isEmpty ? 'Unknown' : asString(info['engine'])),
              SmallMetric(label: 'Confidence', value: '${asDouble(info['confidence']).toStringAsFixed(1)}%'),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Extracted text preview',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white),
          ),
          const SizedBox(height: 10),
          if (extractedTexts.isEmpty)
            Text('No extracted raw text was returned.', style: Theme.of(context).textTheme.bodyMedium)
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
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: const Color(0xFFE5F3FF)),
                  ),
                ),
              );
            }),
        ],
      ),
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
          style: Theme.of(context).textTheme.titleLarge?.copyWith(color: Colors.white),
        ),
      ],
    );
  }
}
