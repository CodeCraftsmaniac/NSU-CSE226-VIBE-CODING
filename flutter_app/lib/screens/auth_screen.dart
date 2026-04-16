import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../services/auth_service.dart';
import '../widgets/glass_widgets.dart';
import 'main_shell.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen>
    with SingleTickerProviderStateMixin {
  bool _isLoading = false;
  String? _errorMessage;
  late final AnimationController _pulseCtrl;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleGoogleSignIn() async {
    if (_isLoading) return;
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final error = await authService.signInWithGoogle();
      if (!mounted) return;

      if (error == null) {
        // Success — user cancelled returns null too, but currentUser will be set
        if (authService.isAuthenticated) {
          Navigator.of(context).pushReplacement(
            PageRouteBuilder(
              pageBuilder: (context, animation, secondaryAnimation) => const MainShell(),
              transitionsBuilder: (context, animation, secondaryAnimation, child) =>
                  FadeTransition(opacity: animation, child: child),
              transitionDuration: const Duration(milliseconds: 500),
            ),
          );
        }
        // else user just cancelled — do nothing, stay on auth screen
      } else {
        setState(() => _errorMessage = error);
      }
    } catch (e) {
      if (mounted) setState(() => _errorMessage = 'Unexpected error. Please try again.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleGuestMode() async {
    if (_isLoading) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      await authService.continueAsGuest();
      if (!mounted) return;

      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) => const MainShell(),
          transitionsBuilder: (context, animation, secondaryAnimation, child) =>
              FadeTransition(opacity: animation, child: child),
          transitionDuration: const Duration(milliseconds: 500),
        ),
      );
    } catch (_) {
      if (mounted) {
        setState(
            () => _errorMessage = 'Could not start guest mode. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      backgroundColor: kBackground,
      body: Stack(
        children: [
          // ── Ambient glow blobs ──
          Positioned(
            top: -size.height * 0.12,
            left: -size.width * 0.20,
            child: AuroraBlob(color: kPrimary, size: size.width * 0.80),
          ),
          Positioned(
            bottom: -size.height * 0.18,
            right: -size.width * 0.20,
            child: AuroraBlob(color: const Color(0xFF6366F1), size: size.width * 0.70),
          ),
          Positioned(
            top: size.height * 0.42,
            left: -size.width * 0.08,
            child: AuroraBlob(color: kSuccess, size: size.width * 0.38),
          ),

          // ── Main content ──
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 40),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // ── Logo ──
                    _buildLogo(),
                    const SizedBox(height: 40),

                    // ── App title ──
                    Text(
                      'North South University',
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            color: kTextSecondary,
                            letterSpacing: 1.4,
                            fontSize: 13,
                          ),
                      textAlign: TextAlign.center,
                    )
                        .animate()
                        .fadeIn(delay: 300.ms, duration: 500.ms)
                        .slideY(begin: 0.3, end: 0, duration: 500.ms, curve: Curves.easeOut),

                    const SizedBox(height: 10),

                    ShaderMask(
                      shaderCallback: (bounds) => const LinearGradient(
                        colors: [Color(0xFF38BDF8), Color(0xFF818CF8)],
                      ).createShader(bounds),
                      child: Text(
                        'Degree Audit',
                        style: Theme.of(context).textTheme.displaySmall?.copyWith(
                              color: Colors.white,
                              fontWeight: FontWeight.w900,
                              letterSpacing: -1.0,
                            ),
                        textAlign: TextAlign.center,
                      ),
                    )
                        .animate()
                        .fadeIn(delay: 380.ms, duration: 500.ms)
                        .slideY(begin: 0.3, end: 0, duration: 500.ms, curve: Curves.easeOut),

                    const SizedBox(height: 14),

                    Text(
                      'Upload your transcript. Get a complete degree audit\nwith CGPA, credits, and graduation readiness.',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: kTextSecondary,
                            height: 1.6,
                          ),
                      textAlign: TextAlign.center,
                    )
                        .animate()
                        .fadeIn(delay: 450.ms, duration: 500.ms)
                        .slideY(begin: 0.2, end: 0, duration: 500.ms, curve: Curves.easeOut),

                    const SizedBox(height: 48),

                    // ── Feature pills ──
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      alignment: WrapAlignment.center,
                      children: const [
                        FeatureChip(icon: Icons.document_scanner_rounded, label: 'AI OCR'),
                        FeatureChip(icon: Icons.analytics_rounded, label: 'Degree Audit'),
                        FeatureChip(icon: Icons.school_rounded, label: 'Graduation Check'),
                        FeatureChip(icon: Icons.lock_rounded, label: 'Secure'),
                      ],
                    )
                        .animate()
                        .fadeIn(delay: 520.ms, duration: 500.ms)
                        .slideY(begin: 0.2, end: 0, duration: 500.ms, curve: Curves.easeOut),

                    const SizedBox(height: 52),

                    // ── Error banner ──
                    if (_errorMessage != null)
                      _ErrorBanner(message: _errorMessage!)
                          .animate()
                          .fadeIn(duration: 300.ms)
                          .slideY(begin: -0.15, end: 0),

                    if (_errorMessage != null) const SizedBox(height: 18),

                    // ── Google Sign-In button ──
                    _GoogleSignInButton(
                      isLoading: _isLoading,
                      onPressed: _isLoading ? null : _handleGoogleSignIn,
                    )
                        .animate()
                        .fadeIn(delay: 600.ms, duration: 500.ms)
                        .slideY(begin: 0.3, end: 0, duration: 500.ms, curve: Curves.easeOut),

                    const SizedBox(height: 14),

                    _GuestModeButton(
                      isLoading: _isLoading,
                      onPressed: _isLoading ? null : _handleGuestMode,
                    )
                        .animate()
                        .fadeIn(delay: 650.ms, duration: 500.ms)
                        .slideY(begin: 0.3, end: 0, duration: 500.ms, curve: Curves.easeOut),

                    const SizedBox(height: 20),

                    // ── Privacy note ──
                    Text(
                      'By continuing, you agree to our Terms of Service\nand acknowledge our Privacy Policy.',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: kTextTertiary,
                            height: 1.6,
                          ),
                      textAlign: TextAlign.center,
                    )
                        .animate()
                        .fadeIn(delay: 700.ms, duration: 400.ms),

                    const SizedBox(height: 40),

                    // ── Footer badge ──
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.04),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.verified_rounded, size: 14, color: kSuccess),
                          const SizedBox(width: 8),
                          Text(
                            'NSU Degree Audit Engine  •  v1.0',
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(color: kTextTertiary, fontSize: 11),
                          ),
                        ],
                      ),
                    ).animate().fadeIn(delay: 800.ms, duration: 400.ms),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLogo() {
    return AnimatedBuilder(
      animation: _pulseCtrl,
      builder: (context, child) {
        return Container(
          width: 120,
          height: 120,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(36),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF38BDF8), Color(0xFF0EA5E9), Color(0xFF0052CC)],
            ),
            boxShadow: [
              BoxShadow(
                color: kPrimary.withValues(alpha: 0.20 + 0.22 * _pulseCtrl.value),
                blurRadius: 32 + 16 * _pulseCtrl.value,
                spreadRadius: 2 + 5 * _pulseCtrl.value,
              ),
            ],
          ),
          child: Stack(
            alignment: Alignment.center,
            children: [
              const Icon(
                Icons.account_balance_rounded,
                size: 56,
                color: Colors.white,
              ),
              Positioned(
                right: 14,
                bottom: 14,
                child: Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: kSuccess,
                    shape: BoxShape.circle,
                    border: Border.all(color: const Color(0xFF0F172A), width: 2.5),
                    boxShadow: [
                      BoxShadow(
                        color: kSuccess.withValues(alpha: 0.5),
                        blurRadius: 8,
                        spreadRadius: 1,
                      ),
                    ],
                  ),
                  child: const Icon(Icons.check_rounded, size: 16, color: Colors.white),
                ),
              ),
            ],
          ),
        );
      },
    )
        .animate()
        .scale(
          begin: const Offset(0.5, 0.5),
          end: const Offset(1.0, 1.0),
          duration: 800.ms,
          curve: Curves.elasticOut,
        )
        .fadeIn(duration: 500.ms);
  }
}

class _GuestModeButton extends StatelessWidget {
  const _GuestModeButton({
    required this.isLoading,
    required this.onPressed,
  });

  final bool isLoading;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: const Icon(Icons.person_outline_rounded, size: 20),
        label: Text(
          isLoading ? 'Please wait...' : 'Continue as Guest',
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            fontFamily: 'Outfit',
          ),
        ),
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(54),
          foregroundColor: kTextSecondary,
          side: BorderSide(color: Colors.white.withValues(alpha: 0.24)),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          backgroundColor: Colors.white.withValues(alpha: 0.03),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Google Sign-In Button
// ═══════════════════════════════════════════════════════════════════════════════

class _GoogleSignInButton extends StatefulWidget {
  const _GoogleSignInButton({
    required this.isLoading,
    required this.onPressed,
  });

  final bool isLoading;
  final VoidCallback? onPressed;

  @override
  State<_GoogleSignInButton> createState() => _GoogleSignInButtonState();
}

class _GoogleSignInButtonState extends State<_GoogleSignInButton> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: widget.onPressed != null ? (_) => setState(() => _pressed = true) : null,
      onTapUp: widget.onPressed != null
          ? (_) {
              setState(() => _pressed = false);
              widget.onPressed!();
            }
          : null,
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedScale(
        scale: _pressed ? 0.97 : 1.0,
        duration: const Duration(milliseconds: 100),
        child: SizedBox(
          width: double.infinity,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(18),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                height: 62,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: widget.onPressed == null
                        ? [
                            Colors.white.withValues(alpha: 0.04),
                            Colors.white.withValues(alpha: 0.02),
                          ]
                        : [
                            Colors.white.withValues(alpha: _pressed ? 0.14 : 0.10),
                            Colors.white.withValues(alpha: _pressed ? 0.06 : 0.04),
                          ],
                  ),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: _pressed ? 0.25 : 0.18),
                    width: 1.5,
                  ),
                  boxShadow: widget.onPressed == null
                      ? []
                      : [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.25),
                            blurRadius: 20,
                            offset: const Offset(0, 6),
                          ),
                        ],
                ),
                child: Center(
                  child: widget.isLoading
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            valueColor: AlwaysStoppedAnimation<Color>(kPrimary),
                          ),
                        )
                      : Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            // Google logo
                            _GoogleLogo(),
                            const SizedBox(width: 14),
                            Text(
                              'Continue with Google',
                              style: TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.w700,
                                color: kTextPrimary,
                                letterSpacing: -0.2,
                                fontFamily: 'Outfit',
                              ),
                            ),
                          ],
                        ),
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
// Google Logo (SVG-like painted widget)
// ═══════════════════════════════════════════════════════════════════════════════

class _GoogleLogo extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 26,
      height: 26,
      child: CustomPaint(painter: _GoogleLogoPainter()),
    );
  }
}

class _GoogleLogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = size.width / 2;

    // Clip to circle
    canvas.clipRRect(RRect.fromRectAndRadius(
      Rect.fromCircle(center: Offset(cx, cy), radius: r),
      Radius.circular(r),
    ));

    // White background
    canvas.drawCircle(
      Offset(cx, cy),
      r,
      Paint()..color = Colors.white,
    );

    // Google G segments (simplified, four-color)
    final rect = Rect.fromCircle(center: Offset(cx, cy), radius: r * 0.70);

    final bluePaint = Paint()..color = const Color(0xFF4285F4);
    final redPaint = Paint()..color = const Color(0xFFEA4335);
    final yellowPaint = Paint()..color = const Color(0xFFFBBC05);
    final greenPaint = Paint()..color = const Color(0xFF34A853);

    // Blue (right arc)
    canvas.drawArc(rect, -0.2, 1.6, false,
        bluePaint..style = PaintingStyle.stroke..strokeWidth = r * 0.32);

    // Red (top-left arc)
    canvas.drawArc(rect, 3.66, 1.8, false,
        redPaint..style = PaintingStyle.stroke..strokeWidth = r * 0.32);

    // Yellow (bottom arc)
    canvas.drawArc(rect, 2.30, 1.38, false,
        yellowPaint..style = PaintingStyle.stroke..strokeWidth = r * 0.32);

    // Green (bottom-right arc)
    canvas.drawArc(rect, 1.38, 0.94, false,
        greenPaint..style = PaintingStyle.stroke..strokeWidth = r * 0.32);

    // White horizontal bar (the G crossbar)
    final barLeft = cx;
    final barRight = cx + r * 0.68;
    final barY = cy + r * 0.02;
    canvas.drawRect(
      Rect.fromLTRB(barLeft, barY - r * 0.15, barRight, barY + r * 0.15),
      Paint()..color = const Color(0xFF4285F4),
    );

    // White center hole
    canvas.drawCircle(
      Offset(cx, cy),
      r * 0.40,
      Paint()..color = Colors.white,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Error Banner
// ═══════════════════════════════════════════════════════════════════════════════

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message});
  final String message;

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
        crossAxisAlignment: CrossAxisAlignment.start,
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
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
