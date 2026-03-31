import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../widgets/glass_widgets.dart';
import '../services/supabase_service.dart';
import 'home_screen.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  bool _isLoading = false;

  Future<void> _handleGoogleSignIn() async {
    setState(() => _isLoading = true);
    
    try {
      final success = await authService.signInWithGoogle();
      if (!mounted) return;
      
      if (success) {
        _navigateToHome();
      } else {
        _showError('Sign in failed. Please try again.');
      }
    } catch (e) {
      if (mounted) {
        _showError('Sign in error: $e');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _continueAsGuest() {
    authService.setGuestMode(true);
    _navigateToHome();
  }

  void _navigateToHome() {
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) => const HomeScreen(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          return FadeTransition(opacity: animation, child: child);
        },
        transitionDuration: const Duration(milliseconds: 400),
      ),
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red.shade700,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: GradientBackground(
        child: Stack(
          children: [
            // Aurora blobs
            const Positioned(
              top: -100,
              left: -80,
              child: AuroraBlob(color: Color(0xFF0052CC), size: 300),
            ),
            const Positioned(
              bottom: -120,
              right: -60,
              child: AuroraBlob(color: Color(0xFF38BDF8), size: 280),
            ),
            const Positioned(
              top: 200,
              right: -100,
              child: AuroraBlob(color: Color(0xFF7A7CFF), size: 200),
            ),

            // Main content
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Column(
                  children: [
                    const Spacer(flex: 2),

                    // Logo
                    Container(
                      width: 100,
                      height: 100,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(30),
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [Color(0xFF38BDF8), Color(0xFF2E86DE), Color(0xFF0052CC)],
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF38BDF8).withValues(alpha: 0.4),
                            blurRadius: 32,
                            spreadRadius: 8,
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.account_balance,
                        size: 48,
                        color: Colors.white,
                      ),
                    )
                        .animate()
                        .scale(
                          begin: const Offset(0.6, 0.6),
                          end: const Offset(1.0, 1.0),
                          duration: 600.ms,
                          curve: Curves.elasticOut,
                        )
                        .fadeIn(duration: 300.ms),

                    const SizedBox(height: 32),

                    // Title
                    Text(
                      'NSU Degree Audit',
                      style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    )
                        .animate()
                        .fadeIn(delay: 200.ms, duration: 400.ms)
                        .slideY(begin: 0.3, end: 0),

                    const SizedBox(height: 12),

                    // Description
                    Text(
                      'Sign in to save your scan history across CLI, Web, and Mobile. Your data syncs to a single cloud database.',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: const Color(0xFFB4C7DA),
                        height: 1.5,
                      ),
                    )
                        .animate()
                        .fadeIn(delay: 300.ms, duration: 400.ms)
                        .slideY(begin: 0.3, end: 0),

                    const Spacer(flex: 1),

                    // Google Sign In Button
                    SizedBox(
                      width: double.infinity,
                      height: 56,
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : _handleGoogleSignIn,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.white,
                          foregroundColor: const Color(0xFF1f2937),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                          elevation: 4,
                          shadowColor: Colors.black26,
                        ),
                        child: _isLoading
                            ? const SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Image.network(
                                    'https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg',
                                    width: 24,
                                    height: 24,
                                    errorBuilder: (_, __, ___) => const Icon(
                                      Icons.g_mobiledata,
                                      size: 28,
                                      color: Color(0xFF4285F4),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  const Text(
                                    'Continue with Google',
                                    style: TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                      ),
                    )
                        .animate()
                        .fadeIn(delay: 500.ms, duration: 400.ms)
                        .slideY(begin: 0.3, end: 0),

                    const SizedBox(height: 16),

                    // Guest Button
                    SizedBox(
                      width: double.infinity,
                      height: 56,
                      child: OutlinedButton(
                        onPressed: _isLoading ? null : _continueAsGuest,
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFFB4C7DA),
                          side: BorderSide(
                            color: Colors.white.withValues(alpha: 0.2),
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.person_outline,
                              color: Colors.white.withValues(alpha: 0.7),
                            ),
                            const SizedBox(width: 12),
                            const Text(
                              'Continue as Guest',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                        .animate()
                        .fadeIn(delay: 600.ms, duration: 400.ms)
                        .slideY(begin: 0.3, end: 0),

                    const SizedBox(height: 24),

                    // Note
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.info_outline,
                          size: 14,
                          color: const Color(0xFF7A8BA6).withValues(alpha: 0.7),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Guest scans won\'t be saved to history',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: const Color(0xFF7A8BA6).withValues(alpha: 0.7),
                            fontSize: 12,
                          ),
                        ),
                      ],
                    )
                        .animate()
                        .fadeIn(delay: 700.ms, duration: 400.ms),

                    const Spacer(flex: 2),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
