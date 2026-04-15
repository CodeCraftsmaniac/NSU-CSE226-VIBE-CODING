import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ═══════════════════════════════════════════════════════════════════════════════
// Color Utilities
// ═══════════════════════════════════════════════════════════════════════════════

Color gradeColor(String grade) {
  if (grade.startsWith('A')) return const Color(0xFF80FFBD);
  if (grade.startsWith('B')) return const Color(0xFF59C4FF);
  if (grade.startsWith('C')) return const Color(0xFFF6B75D);
  if (grade.startsWith('D')) return const Color(0xFFFF9B6A);
  if (grade == 'F') return const Color(0xFFFF7B7B);
  return const Color(0xFFAABED1);
}

// ═══════════════════════════════════════════════════════════════════════════════
// Aurora Background Blob
// ═══════════════════════════════════════════════════════════════════════════════

class AuroraBlob extends StatelessWidget {
  const AuroraBlob({super.key, required this.color, required this.size});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: [color.withValues(alpha: 0.45), color.withValues(alpha: 0)],
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Glass Card - Light Theme
// ═══════════════════════════════════════════════════════════════════════════════

class GlassCard extends StatelessWidget {
  const GlassCard({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding ?? const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: Colors.white,
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: child,
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Glass Tone (Lighter Container) - Light Theme
// ═══════════════════════════════════════════════════════════════════════════════

class GlassTone extends StatelessWidget {
  const GlassTone({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding ?? const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: child,
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Section Header - Light Theme
// ═══════════════════════════════════════════════════════════════════════════════

class SectionHeader extends StatelessWidget {
  const SectionHeader({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.subtitle,
  });

  final String eyebrow;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          eyebrow.toUpperCase(),
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: const Color(0xFF0066CC),
            letterSpacing: 1.6,
            fontWeight: FontWeight.w700,
            fontSize: 12,
          ),
        ),
        const SizedBox(height: 6),
        Text(title, style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 6),
        Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Feature Chip - Light Theme
// ═══════════════════════════════════════════════════════════════════════════════

class FeatureChip extends StatelessWidget {
  const FeatureChip({super.key, required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFEFF6FF),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFBFDBFE)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: const Color(0xFF0066CC)),
          const SizedBox(width: 8),
          Text(label, style: const TextStyle(color: Color(0xFF1E40AF), fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Stat Card - Light Theme
// ═══════════════════════════════════════════════════════════════════════════════

class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    required this.accent,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: accent.withValues(alpha: 0.08),
        border: Border.all(color: accent.withValues(alpha: 0.20)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: accent),
          const SizedBox(height: 14),
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 6),
          Text(value, style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 22, color: const Color(0xFF1E293B))),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Small Metric
// ═══════════════════════════════════════════════════════════════════════════════

class SmallMetric extends StatelessWidget {
  const SmallMetric({super.key, required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 110),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 6),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(color: const Color(0xFF1E293B)),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Strip Metric - Light Theme
// ═══════════════════════════════════════════════════════════════════════════════

class StripMetric extends StatelessWidget {
  const StripMetric({super.key, required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 6),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(color: const Color(0xFF1E293B)),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Data Pill - Light Theme
// ═══════════════════════════════════════════════════════════════════════════════

class DataPill extends StatelessWidget {
  const DataPill({
    super.key,
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: const Color(0xFF0066CC)),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: Theme.of(context).textTheme.bodyMedium),
              Text(
                value,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: const Color(0xFF1E293B)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Alert Box - Light Theme
// ═══════════════════════════════════════════════════════════════════════════════

class AlertBox extends StatelessWidget {
  const AlertBox({
    super.key,
    required this.accent,
    required this.icon,
    required this.title,
    required this.body,
  });

  final Color accent;
  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: accent.withValues(alpha: 0.08),
        border: Border.all(color: accent.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: accent),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(color: const Color(0xFF1E293B)),
                ),
                const SizedBox(height: 6),
                Text(body, style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Grade Chip
// ═══════════════════════════════════════════════════════════════════════════════

class GradeChip extends StatelessWidget {
  const GradeChip({super.key, required this.grade});

  final String grade;

  @override
  Widget build(BuildContext context) {
    final tone = gradeColor(grade);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        grade,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(color: tone),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Processing Panel - Light Theme
// ═══════════════════════════════════════════════════════════════════════════════

class ProcessingPanel extends StatelessWidget {
  const ProcessingPanel({
    super.key,
    required this.progress,
    required this.message,
  });

  final double progress;
  final String message;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Processing transcript', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(message, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 14),
          LinearProgressIndicator(
            value: progress,
            minHeight: 10,
            borderRadius: BorderRadius.circular(999),
            backgroundColor: const Color(0xFFE2E8F0),
            color: const Color(0xFF0066CC),
          ),
          const SizedBox(height: 10),
          Text('${(progress * 100).round()}% complete', style: const TextStyle(color: Color(0xFF64748B))),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// App Theme Builder - Light Professional Theme
// ═══════════════════════════════════════════════════════════════════════════════

ThemeData buildAppTheme() {
  final base = ThemeData(brightness: Brightness.light, useMaterial3: true);
  final textTheme = GoogleFonts.interTextTheme(base.textTheme).copyWith(
    displaySmall: GoogleFonts.inter(
      fontSize: 34,
      fontWeight: FontWeight.w700,
      color: const Color(0xFF1E293B),
    ),
    headlineMedium: GoogleFonts.inter(
      fontSize: 24,
      fontWeight: FontWeight.w700,
      color: const Color(0xFF1E293B),
    ),
    titleLarge: GoogleFonts.inter(
      fontSize: 20,
      fontWeight: FontWeight.w600,
      color: const Color(0xFF1E293B),
    ),
    titleMedium: GoogleFonts.inter(
      fontSize: 16,
      fontWeight: FontWeight.w600,
      color: const Color(0xFF334155),
    ),
    bodyLarge: GoogleFonts.inter(color: const Color(0xFF334155)),
    bodyMedium: GoogleFonts.inter(color: const Color(0xFF64748B)),
    labelLarge: GoogleFonts.inter(fontWeight: FontWeight.w600),
  );

  return base.copyWith(
    scaffoldBackgroundColor: const Color(0xFFF8FAFC),
    colorScheme: ColorScheme.fromSeed(
      seedColor: const Color(0xFF0066CC),
      brightness: Brightness.light,
      primary: const Color(0xFF0066CC),
      secondary: const Color(0xFF10B981),
      surface: Colors.white,
      onSurface: const Color(0xFF1E293B),
    ),
    textTheme: textTheme,
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 2,
      shadowColor: Colors.black.withValues(alpha: 0.08),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      margin: EdgeInsets.zero,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.white,
      foregroundColor: Color(0xFF1E293B),
      elevation: 0,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFF0066CC),
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
    dividerColor: const Color(0xFFE2E8F0),
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Light Background (Clean White)
// ═══════════════════════════════════════════════════════════════════════════════

class GradientBackground extends StatelessWidget {
  const GradientBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFFF8FAFC), Color(0xFFEFF6FF), Color(0xFFF1F5F9)],
        ),
      ),
      child: child,
    );
  }
}
