import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';

import '../services/auth_service.dart';
import '../widgets/glass_widgets.dart';
import 'history_screen.dart';
import 'courses_screen.dart';
import 'dashboard_screen.dart';
import 'upload_screen.dart';
import 'health_screen.dart';
import 'auth_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key, this.initialIndex = 0});

  final int initialIndex;

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell>
    with SingleTickerProviderStateMixin {
  late int _currentIndex;
  late final PageController _pageController;

  // Navigation items definition
  static const _navItems = [
    _NavItem(
      label: 'Results',
      icon: Icons.analytics_outlined,
      activeIcon: Icons.analytics_rounded,
      accent: kPrimary,
    ),
    _NavItem(
      label: 'Courses',
      icon: Icons.menu_book_outlined,
      activeIcon: Icons.menu_book_rounded,
      accent: Color(0xFF818CF8),
    ),
    _NavItem(
      label: 'Upload',
      icon: Icons.upload_file_outlined,
      activeIcon: Icons.upload_file_rounded,
      accent: kSuccess,
    ),
    _NavItem(
      label: 'Health',
      icon: Icons.monitor_heart_outlined,
      activeIcon: Icons.monitor_heart_rounded,
      accent: kWarning,
    ),
  ];

  final _screens = const [
    DashboardScreen(),
    CoursesScreen(),
    UploadScreen(),
    HealthScreen(),
  ];

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.initialIndex;
    _pageController = PageController(initialPage: _currentIndex);
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _onNavTap(int index) {
    HapticFeedback.selectionClick();
    setState(() => _currentIndex = index);
    _pageController.animateToPage(
      index,
      duration: const Duration(milliseconds: 350),
      curve: Curves.easeInOut,
    );
  }

  Future<void> _handleLogout() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: kSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: kBorder),
        ),
        title: const Text(
          'Sign Out',
          style: TextStyle(color: kTextPrimary, fontWeight: FontWeight.w700),
        ),
        content: const Text(
          'Are you sure you want to sign out?',
          style: TextStyle(color: kTextSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel', style: TextStyle(color: kTextSecondary)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: kError),
            child: const Text('Sign Out',
                style: TextStyle(fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );

    if (confirm == true && mounted) {
      await authService.logout();
      if (!mounted) return;
      _navigateToAuthScreen();
    }
  }

  Future<void> _handleExitGuestMode() async {
    await authService.exitGuestMode();
    if (!mounted) return;
    _navigateToAuthScreen();
  }

  void _navigateToAuthScreen() {
    Navigator.of(context).pushAndRemoveUntil(
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) => const AuthScreen(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) =>
            FadeTransition(opacity: animation, child: child),
        transitionDuration: const Duration(milliseconds: 500),
      ),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = authService.currentUser;
    final isGuest = authService.isGuestMode;

    return ChangeNotifierProvider.value(
      value: authService,
      child: Scaffold(
        backgroundColor: kBackground,
        // ── Top App Bar ──
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          systemOverlayStyle: SystemUiOverlayStyle.light,
          titleSpacing: 20,
          title: Row(
            children: [
              // Logo mark
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(10),
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [Color(0xFF38BDF8), Color(0xFF0052CC)],
                  ),
                ),
                child: const Icon(
                  Icons.account_balance_rounded,
                  size: 18,
                  color: Colors.white,
                ),
              ),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'NSU Degree Audit',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: kTextPrimary,
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                        ),
                  ),
                  Text(
                    _navItems[_currentIndex].label,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: _navItems[_currentIndex].accent,
                          fontSize: 11,
                        ),
                  ),
                ],
              ),
            ],
          ),
          actions: [
            // ── User avatar / menu ──
            PopupMenuButton<String>(
              offset: const Offset(0, 48),
              color: kSurface,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
                side: const BorderSide(color: kBorder),
              ),
              itemBuilder: (ctx) {
                if (isGuest) {
                  return [
                    const PopupMenuItem(
                      enabled: false,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Guest Mode',
                            style: TextStyle(
                              color: kTextPrimary,
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                            ),
                          ),
                          Text(
                            'Sign in to sync history and profile',
                            style: TextStyle(color: kTextSecondary, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                    const PopupMenuDivider(),
                    const PopupMenuItem(
                      value: 'signin',
                      child: Row(
                        children: [
                          Icon(Icons.login_rounded, color: kPrimary, size: 18),
                          SizedBox(width: 12),
                          Text(
                            'Sign In with Google',
                            style: TextStyle(color: kTextPrimary, fontSize: 14),
                          ),
                        ],
                      ),
                    ),
                    const PopupMenuItem(
                      value: 'exit_guest',
                      child: Row(
                        children: [
                          Icon(Icons.logout_rounded, color: kError, size: 18),
                          SizedBox(width: 12),
                          Text(
                            'Exit Guest Mode',
                            style: TextStyle(color: kError, fontSize: 14),
                          ),
                        ],
                      ),
                    ),
                  ];
                }

                return [
                  PopupMenuItem(
                    enabled: false,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user?.displayName ?? 'Student',
                          style: const TextStyle(
                              color: kTextPrimary,
                              fontWeight: FontWeight.w700,
                              fontSize: 14),
                        ),
                        Text(
                          user?.email ?? '',
                          style: const TextStyle(
                              color: kTextSecondary, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  const PopupMenuDivider(),
                  const PopupMenuItem(
                    value: 'history',
                    child: Row(
                      children: [
                        Icon(Icons.history_rounded,
                            color: kPrimary, size: 18),
                        SizedBox(width: 12),
                        Text('Scan History',
                            style: TextStyle(color: kTextPrimary, fontSize: 14)),
                      ],
                    ),
                  ),
                  const PopupMenuItem(
                    value: 'logout',
                    child: Row(
                      children: [
                        Icon(Icons.logout_rounded, color: kError, size: 18),
                        SizedBox(width: 12),
                        Text('Sign Out',
                            style: TextStyle(color: kError, fontSize: 14)),
                      ],
                    ),
                  ),
                ];
              },
              onSelected: (value) {
                if (value == 'logout') _handleLogout();
                if (value == 'history') {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const HistoryScreen()),
                  );
                }
                if (value == 'signin') _navigateToAuthScreen();
                if (value == 'exit_guest') _handleExitGuestMode();
              },
              child: Padding(
                padding: const EdgeInsets.only(right: 16),
                child: _UserAvatar(
                  name: isGuest ? 'Guest' : user?.displayName ?? '?',
                ),
              ),
            ),
          ],
        ),

        // ── Page body ──
        body: PageView(
          controller: _pageController,
          physics: const NeverScrollableScrollPhysics(),
          children: _screens,
        ),

        // ── Bottom Navigation Bar ──
        bottomNavigationBar: _buildBottomNav(),
      ),
    );
  }

  Widget _buildBottomNav() {
    return Container(
      decoration: BoxDecoration(
        color: kSurface,
        border: const Border(top: BorderSide(color: kBorder, width: 1)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.3),
            blurRadius: 20,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          child: Row(
            children: List.generate(
              _navItems.length,
              (index) => Expanded(
                child: _NavBarItem(
                  item: _navItems[index],
                  isSelected: _currentIndex == index,
                  onTap: () => _onNavTap(index),
                ).animate(key: ValueKey('nav_$index')),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Nav Item Model
// ═══════════════════════════════════════════════════════════════════════════════

class _NavItem {
  const _NavItem({
    required this.label,
    required this.icon,
    required this.activeIcon,
    required this.accent,
  });

  final String label;
  final IconData icon;
  final IconData activeIcon;
  final Color accent;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Individual Nav Bar Item
// ═══════════════════════════════════════════════════════════════════════════════

class _NavBarItem extends StatelessWidget {
  const _NavBarItem({
    required this.item,
    required this.isSelected,
    required this.onTap,
  });

  final _NavItem item;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeInOut,
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: isSelected
              ? item.accent.withValues(alpha: 0.12)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Icon with indicator dot
            Stack(
              alignment: Alignment.center,
              children: [
                // Glow ring behind icon when selected
                if (isSelected)
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 250),
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          item.accent.withValues(alpha: 0.20),
                          Colors.transparent,
                        ],
                      ),
                    ),
                  ),
                Icon(
                  isSelected ? item.activeIcon : item.icon,
                  color: isSelected ? item.accent : kTextTertiary,
                  size: 24,
                ),
              ],
            ),
            const SizedBox(height: 4),
            // Label
            AnimatedDefaultTextStyle(
              duration: const Duration(milliseconds: 200),
              style: TextStyle(
                fontSize: 11,
                fontWeight:
                    isSelected ? FontWeight.w700 : FontWeight.w400,
                color: isSelected ? item.accent : kTextTertiary,
                fontFamily: 'Outfit',
              ),
              child: Text(item.label),
            ),
          ],
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// User Avatar Widget
// ═══════════════════════════════════════════════════════════════════════════════

class _UserAvatar extends StatelessWidget {
  const _UserAvatar({required this.name});

  final String name;

  @override
  Widget build(BuildContext context) {
    final initials = name.trim().isEmpty
        ? '?'
        : name
            .trim()
            .split(' ')
            .where((w) => w.isNotEmpty)
            .take(2)
            .map((w) => w[0].toUpperCase())
            .join();

    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF38BDF8), Color(0xFF6366F1)],
        ),
        border: Border.all(
          color: kPrimary.withValues(alpha: 0.4),
          width: 2,
        ),
      ),
      child: Center(
        child: Text(
          initials,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 13,
            fontWeight: FontWeight.w700,
            fontFamily: 'Outfit',
          ),
        ),
      ),
    );
  }
}
