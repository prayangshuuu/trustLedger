import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme.dart';

/// Animated 300-900 score gauge with band-coloured segments.
class ScoreMeter extends StatelessWidget {
  const ScoreMeter({
    super.key,
    required this.score,
    required this.label,
    this.color = TLColors.navy,
    this.duration = const Duration(milliseconds: 1800),
  });

  final int score;
  final String label;
  final Color color;
  final Duration duration;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 300, end: score.toDouble().clamp(300, 900)),
      duration: duration,
      curve: Curves.easeOutCubic,
      builder: (context, value, _) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(width: 280, height: 150, child: CustomPaint(painter: _GaugePainter(value))),
          Text(
            value.round().toString(),
            key: const Key('score_value'),
            style: const TextStyle(fontSize: 52, fontWeight: FontWeight.w700, color: TLColors.navy, height: 1.1),
          ),
          Text(
            label,
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: color),
          ),
        ],
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  _GaugePainter(this.value);

  final double value;
  static const _bands = [
    (300.0, 550.0, TLColors.warn),
    (550.0, 650.0, TLColors.gold),
    (650.0, 750.0, TLColors.teal),
    (750.0, 900.0, TLColors.good),
  ];

  double _angle(double v) => math.pi + (v - 300) / 600 * math.pi;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height - 6);
    final radius = size.width / 2 - 16;
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
      ..color = TLColors.navy
      ..strokeWidth = 4
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(center, center + Offset(math.cos(a), math.sin(a)) * (radius - 26), needle);
    canvas.drawCircle(center, 7, Paint()..color = TLColors.navy);
  }

  @override
  bool shouldRepaint(_GaugePainter old) => old.value != value;
}
