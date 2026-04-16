import 'dart:typed_data';
import 'dart:ui';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:image_picker/image_picker.dart';

import '../services/api_service.dart';
import '../services/analysis_session_service.dart';
import '../widgets/glass_widgets.dart';
import 'processing_screen.dart';

class UploadScreen extends StatefulWidget {
  const UploadScreen({super.key});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen>
    with AutomaticKeepAliveClientMixin, SingleTickerProviderStateMixin {
  @override
  bool get wantKeepAlive => true;

  final bool _isDragOver = false;
  bool _isUploading = false;
  String? _errorMessage;

  late final AnimationController _pulseCtrl;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    super.dispose();
  }

  // ─────────────────────────────────────────────
  // File picking methods
  // ─────────────────────────────────────────────

  Future<void> _pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'png', 'jpg', 'jpeg', 'csv'],
        withData: kIsWeb,
      );
      if (result == null || result.files.isEmpty) return;
      final file = result.files.single;
      await _uploadFile(
        fileName: file.name,
        filePath: file.path,
        bytes: file.bytes,
      );
    } catch (e) {
      _setError('Could not open file picker: $e');
    }
  }

  Future<void> _pickFromGallery() async {
    if (kIsWeb) {
      await _pickFile();
      return;
    }
    try {
      final picker = ImagePicker();
      final image = await picker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 95,
      );
      if (image == null) return;
      await _uploadFile(
        fileName: image.name,
        filePath: image.path,
      );
    } catch (e) {
      _setError('Could not open gallery: $e');
    }
  }

  Future<void> _pickFromCamera() async {
    if (kIsWeb) {
      _setError('Camera is not available in web mode.');
      return;
    }
    try {
      final picker = ImagePicker();
      final image = await picker.pickImage(
        source: ImageSource.camera,
        imageQuality: 95,
      );
      if (image == null) return;
      await _uploadFile(
        fileName: image.name,
        filePath: image.path,
      );
    } catch (e) {
      _setError('Could not open camera: $e');
    }
  }

  // ─────────────────────────────────────────────
  // Upload logic
  // ─────────────────────────────────────────────

  Future<void> _uploadFile({
    required String fileName,
    String? filePath,
    List<int>? bytes,
  }) async {
    setState(() {
      _isUploading = true;
      _errorMessage = null;
    });

    try {
      // Ensure filename has extension
      final ext = fileName.contains('.') 
        ? fileName.split('.').last.toLowerCase()
        : 'pdf';
      final safeFileName = fileName.contains('.') 
        ? fileName 
        : '$fileName.$ext';
      
      final response = await apiService.uploadFile(
        safeFileName,
        filePath: filePath,
        bytes: bytes != null ? Uint8List.fromList(bytes) : null,
      );

      if (!mounted) return;

      final success = response['success'] == true;
      final rawAnalysis = response['data'];
      if (!success || rawAnalysis is! Map) {
        throw ApiException(
          response['error']?.toString() ?? 'OCR processing failed.',
        );
      }

      final analysisData = rawAnalysis.cast<String, dynamic>();
      analysisSessionService.setLatestAnalysis(analysisData);
      final jobId = response['job_id']?.toString() ?? 'completed';

      await Navigator.of(context).push(
        PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              ProcessingScreen(
                jobId: jobId,
                fileName: safeFileName,
                analysisData: analysisData,
              ),
          transitionsBuilder: (context, animation, secondaryAnimation, child) => SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 1.0),
              end: Offset.zero,
            ).animate(
              CurvedAnimation(parent: animation, curve: Curves.easeOutCubic),
            ),
            child: child,
          ),
          transitionDuration: const Duration(milliseconds: 450),
        ),
      );
    } on ApiException catch (e) {
      _setError(e.message);
    } catch (e) {
      _setError('Upload failed. Please check your connection and try again.');
    } finally {
      if (mounted) setState(() => _isUploading = false);
    }
  }

  void _setError(String msg) {
    if (!mounted) return;
    setState(() => _errorMessage = msg);
  }

  // ─────────────────────────────────────────────
  // Build
  // ─────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Stack(
      children: [
        // ── Ambient glows ──
        const Positioned(
          top: -60,
          left: -60,
          child: AuroraBlob(color: kSuccess, size: 260),
        ),
        const Positioned(
          bottom: -80,
          right: -60,
          child: AuroraBlob(color: kPrimary, size: 240),
        ),

        // ── Content ──
        SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 100),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Header ──
              _buildHeader()
                  .animate()
                  .fadeIn(duration: 400.ms)
                  .slideY(begin: 0.2, end: 0, duration: 400.ms),

              const SizedBox(height: 28),

              // ── Error banner ──
              if (_errorMessage != null)
                _ErrorBanner(
                  message: _errorMessage!,
                  onDismiss: () => setState(() => _errorMessage = null),
                )
                    .animate()
                    .fadeIn(duration: 300.ms)
                    .slideY(begin: -0.2, end: 0),

              if (_errorMessage != null) const SizedBox(height: 16),

              // ── Drop Zone ──
              _DropZone(
                isDragOver: _isDragOver,
                isUploading: _isUploading,
                pulseCtrl: _pulseCtrl,
                onTap: _isUploading ? null : _pickFile,
              )
                  .animate()
                  .fadeIn(delay: 100.ms, duration: 500.ms)
                  .scale(
                    begin: const Offset(0.96, 0.96),
                    end: const Offset(1.0, 1.0),
                    delay: 100.ms,
                    duration: 500.ms,
                    curve: Curves.easeOut,
                  ),

              const SizedBox(height: 24),

              // ── OR divider ──
              const LabeledDivider(label: 'or choose a source')
                  .animate()
                  .fadeIn(delay: 200.ms, duration: 400.ms),

              const SizedBox(height: 24),

              // ── Source buttons ──
              _buildSourceButtons()
                  .animate()
                  .fadeIn(delay: 280.ms, duration: 400.ms)
                  .slideY(begin: 0.15, end: 0, duration: 400.ms),

              const SizedBox(height: 28),

              // ── Supported formats ──
              _buildFormatsCard()
                  .animate()
                  .fadeIn(delay: 380.ms, duration: 400.ms)
                  .slideY(begin: 0.15, end: 0, duration: 400.ms),

              const SizedBox(height: 24),

              // ── Tips card ──
              _buildTipsCard()
                  .animate()
                  .fadeIn(delay: 450.ms, duration: 400.ms)
                  .slideY(begin: 0.15, end: 0, duration: 400.ms),
            ],
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────
  // Section builders
  // ─────────────────────────────────────────────

  Widget _buildHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            GlowIcon(
              icon: Icons.upload_file_rounded,
              accent: kSuccess,
              size: 48,
              iconSize: 24,
            ),
            const SizedBox(width: 14),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Upload Transcript',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        color: kTextPrimary,
                        fontWeight: FontWeight.w800,
                      ),
                ),
                Text(
                  'PDF, image, or CSV • backend-powered OCR',
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: kTextSecondary),
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSourceButtons() {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _SourceButton(
                icon: Icons.photo_library_outlined,
                label: 'Gallery',
                subtitle: 'Pick an image',
                accent: const Color(0xFF818CF8),
                onTap: _isUploading ? null : _pickFromGallery,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _SourceButton(
                icon: Icons.camera_alt_outlined,
                label: 'Camera',
                subtitle: 'Take a photo',
                accent: kWarning,
                onTap: _isUploading || kIsWeb ? null : _pickFromCamera,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _SourceButton(
                icon: Icons.folder_outlined,
                label: 'Files',
                subtitle: 'Pick PDF, image, or CSV',
                accent: kPrimary,
                onTap: _isUploading ? null : _pickFile,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildFormatsCard() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.insert_drive_file_outlined,
                  color: kPrimary, size: 20),
              const SizedBox(width: 10),
              Text(
                'Supported Formats',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: kTextPrimary,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: const [
              _FormatChip(
                  label: 'PDF', icon: Icons.picture_as_pdf_rounded, color: kError),
              _FormatChip(
                  label: 'JPG/JPEG', icon: Icons.image_rounded, color: kPrimary),
              _FormatChip(
                  label: 'PNG', icon: Icons.image_rounded, color: kSuccess),
              _FormatChip(
                  label: 'CSV', icon: Icons.table_chart_rounded, color: kWarning),
            ],
          ),
          const SizedBox(height: 12),
          const Divider(color: kBorder, height: 1),
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(Icons.security_rounded, color: kSuccess, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Your transcript is processed securely and never shared.',
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: kTextSecondary),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTipsCard() {
    const tips = [
      (Icons.check_circle_outline_rounded, 'Use the official NSU transcript PDF for best accuracy'),
      (Icons.check_circle_outline_rounded, 'Ensure the image is well-lit and not blurry'),
      (Icons.check_circle_outline_rounded, 'Make sure all pages of your transcript are included'),
      (Icons.check_circle_outline_rounded, 'Avoid cropping or editing the transcript file'),
    ];

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.lightbulb_outline_rounded,
                  color: kWarning, size: 20),
              const SizedBox(width: 10),
              Text(
                'Tips for Best Results',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: kTextPrimary,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ...tips.map(
            (t) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(t.$1, size: 16, color: kSuccess),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      t.$2,
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: kTextSecondary, height: 1.4),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Drop Zone Widget
// ═══════════════════════════════════════════════════════════════════════════════

class _DropZone extends StatelessWidget {
  const _DropZone({
    required this.isDragOver,
    required this.isUploading,
    required this.pulseCtrl,
    this.onTap,
  });

  final bool isDragOver;
  final bool isUploading;
  final AnimationController pulseCtrl;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final accent = isDragOver ? kSuccess : kPrimary;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedBuilder(
        animation: pulseCtrl,
        builder: (context, child) {
          return ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                width: double.infinity,
                height: 220,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(24),
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: isDragOver
                        ? [
                            kSuccess.withValues(alpha: 0.20),
                            kSuccess.withValues(alpha: 0.08),
                          ]
                        : [
                            kPrimary.withValues(alpha: 
                                0.08 + 0.04 * pulseCtrl.value),
                            Colors.white.withValues(alpha: 0.03),
                          ],
                  ),
                  border: Border.all(
                    color: accent.withValues(alpha: 
                        isDragOver ? 0.70 : 0.30 + 0.15 * pulseCtrl.value),
                    width: isDragOver ? 2.5 : 1.5,
                    strokeAlign: BorderSide.strokeAlignInside,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: accent.withValues(alpha: 
                          0.10 + 0.08 * pulseCtrl.value),
                      blurRadius: 30,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: isUploading
                    ? _buildUploading(context)
                    : _buildIdle(context, accent),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildIdle(BuildContext context, Color accent) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Upload icon with glow
        AnimatedBuilder(
          animation: pulseCtrl,
          builder: (context, child) => Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  accent.withValues(alpha: 0.20 + 0.10 * pulseCtrl.value),
                  Colors.transparent,
                ],
              ),
            ),
            child: Center(
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: accent.withValues(alpha: 0.12),
                  border: Border.all(
                    color: accent.withValues(alpha: 0.35),
                    width: 1.5,
                  ),
                ),
                child: Icon(
                  isDragOver
                      ? Icons.file_download_rounded
                      : Icons.cloud_upload_outlined,
                  color: accent,
                  size: 28,
                ),
              ),
            ),
          ),
        ),

        const SizedBox(height: 16),

        Text(
          isDragOver ? 'Drop to upload' : 'Tap to upload transcript',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: kTextPrimary,
                fontWeight: FontWeight.w700,
              ),
        ),

        const SizedBox(height: 6),

        Text(
          'PDF, JPG, PNG, or CSV • Up to 16 MB',
          style: Theme.of(context)
              .textTheme
              .bodySmall
              ?.copyWith(color: kTextTertiary),
        ),

        const SizedBox(height: 16),

        Container(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 9),
          decoration: BoxDecoration(
            color: accent.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: accent.withValues(alpha: 0.30), width: 1),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.add_rounded, color: accent, size: 16),
              const SizedBox(width: 6),
              Text(
                'Choose file',
                style: TextStyle(
                  color: accent,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  fontFamily: 'Outfit',
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildUploading(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        SizedBox(
          width: 56,
          height: 56,
          child: CircularProgressIndicator(
            strokeWidth: 3,
            valueColor: AlwaysStoppedAnimation<Color>(kPrimary),
            backgroundColor: kPrimary.withValues(alpha: 0.15),
          ),
        ),
        const SizedBox(height: 20),
        Text(
          'Uploading transcript…',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: kTextPrimary,
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: 6),
        Text(
          'Sending to OCR engine. Please wait.',
          style: Theme.of(context)
              .textTheme
              .bodySmall
              ?.copyWith(color: kTextTertiary),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Source Button
// ═══════════════════════════════════════════════════════════════════════════════

class _SourceButton extends StatefulWidget {
  const _SourceButton({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.accent,
    this.onTap,
  });

  final IconData icon;
  final String label;
  final String subtitle;
  final Color accent;
  final VoidCallback? onTap;

  @override
  State<_SourceButton> createState() => _SourceButtonState();
}

class _SourceButtonState extends State<_SourceButton> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final enabled = widget.onTap != null;

    return GestureDetector(
      onTapDown: enabled ? (_) => setState(() => _pressed = true) : null,
      onTapUp: enabled
          ? (_) {
              setState(() => _pressed = false);
              widget.onTap!();
            }
          : null,
      onTapCancel: enabled ? () => setState(() => _pressed = false) : null,
      child: AnimatedScale(
        scale: _pressed ? 0.94 : 1.0,
        duration: const Duration(milliseconds: 100),
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 200),
          opacity: enabled ? 1.0 : 0.4,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(18),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
              child: Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      widget.accent.withValues(alpha: 0.12),
                      widget.accent.withValues(alpha: 0.04),
                    ],
                  ),
                  border: Border.all(
                    color: widget.accent.withValues(alpha: 0.28),
                    width: 1,
                  ),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: widget.accent.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(widget.icon,
                          color: widget.accent, size: 22),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      widget.label,
                      style: Theme.of(context)
                          .textTheme
                          .labelLarge
                          ?.copyWith(
                            color: kTextPrimary,
                            fontWeight: FontWeight.w700,
                            fontSize: 13,
                          ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      widget.subtitle,
                      textAlign: TextAlign.center,
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(
                            color: kTextTertiary,
                            fontSize: 10,
                          ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Format Chip
// ═══════════════════════════════════════════════════════════════════════════════

class _FormatChip extends StatelessWidget {
  const _FormatChip({
    required this.label,
    required this.icon,
    required this.color,
  });

  final String label;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.28), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: color),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: kTextPrimary,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              fontFamily: 'Outfit',
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Error Banner
// ═══════════════════════════════════════════════════════════════════════════════

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message, required this.onDismiss});

  final String message;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
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
          const Icon(Icons.error_outline_rounded, color: kError, size: 18),
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
          GestureDetector(
            onTap: onDismiss,
            child: const Icon(Icons.close_rounded,
                color: kTextTertiary, size: 18),
          ),
        ],
      ),
    );
  }
}
