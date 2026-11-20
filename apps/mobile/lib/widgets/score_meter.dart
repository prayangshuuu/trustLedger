import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../design/theme.dart';

/// Animated 300-900 score gauge with band-coloured segments.
/// The animation is skipped when the user asked the system to reduce motion.
class ScoreMeter extends StatelessWidget {
  const ScoreMeter({
    super.key,
    required this.score,
    required this.label,
    this.color = TColor.navy,
    this.duration = const Duration(milliseconds: TMotion.scoreReveal),
  });

  final int score;
  final String label;
  final Color color;
  final Duration duration;

  @override
  Widget build(BuildContext context) {
    final reduce = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    final target = score.toDouble().clamp(300.0, 900.0);
    return Semantics(
      label: '$score, $label',
      excludeSemantics: true,
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: reduce ? target : 300, end: target),
        duration: reduce ? Duration.zero : duration,
        curve: Curves.easeOutCubic,
        builder: (context, value, _) => Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: TLayout.meterWidth,
              height: TLayout.meterHeight,
              child: CustomPaint(painter: _GaugePainter(value)),
            ),
            Text(
              value.round().toString(),
              key: const Key('score_value'),
              style: const TextStyle(fontSize: TType.display, fontWeight: TFont.bold, color: TColor.navy, height: 1.1),
            ),
            Text(
              label,
              style: TextStyle(fontSize: TType.title, fontWeight: TFont.bold, color: color),
            ),
          ],
        ),
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  _GaugePainter(this.value);

  final double value;
  static const _bands = [
    (300.0, 550.0, TColor.bandBuilding),
    (550.0, 650.0, TColor.gold),
    (650.0, 750.0, TColor.teal),
    (750.0, 900.0, TColor.good),
  ];

  double _angle(double v) => math.pi + (v - 300) / 600 * math.pi;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height - 6);
    final radius = size.width / 2 - TSpace.lg;
    final rect = Rect.fromCircle(center: center, radius: radius);
    for (final (lo, hi, color) in _bands) {
      final paint = Paint()
        ..color = color.withValues(alpha: 0.85)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 18;
      canvas.drawArc(rect, _angle(lo), _angle(hi) - _angle(lo) - 0.02, false, paint);
    }
    final a = _angle(value);
    final needle = Paint()
      ..color = TColor.navy
      ..strokeWidth = 4
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(center, center + Offset(math.cos(a), math.sin(a)) * (radius - 26), needle);
    canvas.drawCircle(center, 7, Paint()..color = TColor.navy);
  }

  @override
  bool shouldRepaint(_GaugePainter old) => old.value != value;
}
