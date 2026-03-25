/// TrustScoreGauge — animated circular gauge for the NaviAble Trust Score.
///
/// Uses a [CustomPainter] to draw two arcs:
/// 1. A grey background track.
/// 2. A coloured foreground arc proportional to the [score].
///
/// The gauge colour transitions from [NaviAbleColors.danger] (red, score < 0.4)
/// through [NaviAbleColors.warning] (amber, 0.4–0.69) to [NaviAbleColors.accent]
/// (teal, ≥ 0.70), giving an immediate visual signal of verification quality.
///
/// The entire widget is wrapped in a [Semantics] node to make the score
/// accessible to screen readers, satisfying the accessibility mandate in
/// `.agent/system/CONSTRAINTS_AND_RULES.md`.
library trust_score_gauge;

import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Animated circular gauge displaying the NaviAble Trust Score.
class TrustScoreGauge extends StatefulWidget {
  /// Trust score in the range [0.0, 1.0].
  final double score;

  /// Diameter of the gauge in logical pixels.  Defaults to 180.
  final double size;

  const TrustScoreGauge({
    super.key,
    required this.score,
    this.size = 180,
  });

  @override
  State<TrustScoreGauge> createState() => _TrustScoreGaugeState();
}

class _TrustScoreGaugeState extends State<TrustScoreGauge>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scoreAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    _scoreAnimation = Tween<double>(begin: 0, end: widget.score).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
    _controller.forward();
  }

  @override
  void didUpdateWidget(TrustScoreGauge oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.score != widget.score) {
      _scoreAnimation = Tween<double>(
        begin: _scoreAnimation.value,
        end: widget.score,
      ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));
      _controller
        ..reset()
        ..forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final percent = (widget.score * 100).round();
    final gaugeColor = _colorForScore(widget.score);
    final verdict = _verdictText(widget.score);

    return Semantics(
      label: 'NaviAble Trust Score: $percent out of 100. $verdict.',
      excludeSemantics: true,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedBuilder(
            animation: _scoreAnimation,
            builder: (_, __) => CustomPaint(
              size: Size.square(widget.size),
              painter: _GaugePainter(
                score: _scoreAnimation.value,
                color: _colorForScore(_scoreAnimation.value),
              ),
              child: SizedBox.square(
                dimension: widget.size,
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        '${(_scoreAnimation.value * 100).round()}',
                        style: TextStyle(
                          fontSize: widget.size * 0.18,
                          fontWeight: FontWeight.w800,
                          color: _colorForScore(_scoreAnimation.value),
                        ),
                      ),
                      Text(
                        '/ 100',
                        style: TextStyle(
                          fontSize: widget.size * 0.08,
                          color: NaviAbleColors.textMuted,
                        ),
                      ),
                      Text(
                        'TRUST SCORE',
                        style: TextStyle(
                          fontSize: widget.size * 0.065,
                          color: NaviAbleColors.textMuted,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            verdict,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: gaugeColor,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            '60 % vision · 40 % NLP',
            style: const TextStyle(
              fontSize: 11,
              color: NaviAbleColors.textMuted,
            ),
          ),
        ],
      ),
    );
  }
}

/// [CustomPainter] that draws the gauge arcs.
class _GaugePainter extends CustomPainter {
  final double score;
  final Color color;

  const _GaugePainter({required this.score, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width / 2) * 0.82;
    const strokeWidth = 14.0;
    const startAngle = -math.pi * 0.75; // start at ~7 o'clock
    const sweepFull = math.pi * 1.5;    // 270-degree arc

    final trackPaint = Paint()
      ..color = NaviAbleColors.border
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final scorePaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    // Background track
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepFull,
      false,
      trackPaint,
    );

    // Foreground score arc
    if (score > 0) {
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweepFull * score.clamp(0.0, 1.0),
        false,
        scorePaint,
      );
    }
  }

  @override
  bool shouldRepaint(_GaugePainter old) =>
      old.score != score || old.color != color;
}

/// Colour for a given trust score value.
Color _colorForScore(double score) {
  if (score >= 0.70) return NaviAbleColors.accent;
  if (score >= 0.40) return NaviAbleColors.warning;
  return NaviAbleColors.danger;
}

/// Verdict text for a given trust score value.
String _verdictText(double score) {
  if (score >= 0.70) return 'Strong evidence of accessibility';
  if (score >= 0.40) return 'Partial accessibility evidence';
  return 'Insufficient evidence';
}
