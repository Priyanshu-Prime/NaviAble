/// DetectionResultCard — displays the YOLOv11 vision analysis output.
///
/// Shows the number of detected features as chips and lists each detection
/// with a confidence progress bar.  All accessibility features comply with
/// the mandate in `.agent/system/CONSTRAINTS_AND_RULES.md`.
library detection_result_card;

import 'package:flutter/material.dart';

import '../models/verification_models.dart';
import '../theme/app_theme.dart';

/// Per-class colour map — each accessibility feature class has a distinct
/// colour to make the bounding box chips visually distinct.
const Map<String, Color> _kClassColors = {
  'ramp':               Color(0xFF4CC9F0),
  'handrail':           Color(0xFFF72585),
  'flat_entrance':      Color(0xFF7209B7),
  'accessible_doorway': Color(0xFF4361EE),
  'tactile_paving':     Color(0xFF3A0CA3),
  'elevator':           Color(0xFF4895EF),
  'accessible_parking': Color(0xFF560BAD),
};

Color _colorFor(String cls) =>
    _kClassColors[cls] ?? NaviAbleColors.accent;

/// Card widget showing the YOLO vision detector output.
class DetectionResultCard extends StatelessWidget {
  final VisionAnalysis visionAnalysis;

  const DetectionResultCard({super.key, required this.visionAnalysis});

  @override
  Widget build(BuildContext context) {
    final detected = visionAnalysis.objectsDetected;
    final hasFeatures = detected > 0;

    return Semantics(
      label: 'Vision Detection result. '
          '${hasFeatures ? "$detected accessibility feature${detected == 1 ? "" : "s"} found" : "No accessibility features detected"}.',
      child: Card(
        color: const Color(0xFFE3F2FD),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: Color(0xFFBBDEFB), width: 1.5),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Header ─────────────────────────────────────────────
              Row(
                children: [
                  const Text('👁️', style: TextStyle(fontSize: 20)),
                  const SizedBox(width: 8),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Vision Detection',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const Text(
                        'YOLOv11 · mAP@0.5: 47.29% (Epoch 25)',
                        style: TextStyle(
                          fontSize: 11,
                          color: NaviAbleColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // ── Verdict ─────────────────────────────────────────────
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: hasFeatures
                      ? const Color(0xFFC8E6C9)
                      : const Color(0xFFFFF9C4),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  hasFeatures
                      ? '✅ $detected feature${detected == 1 ? "" : "s"} found'
                      : '⚠️ No features detected',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: hasFeatures
                        ? const Color(0xFF1B5E20)
                        : const Color(0xFF795548),
                  ),
                ),
              ),

              // ── Feature chips ───────────────────────────────────────
              if (hasFeatures) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: visionAnalysis.features.map((f) {
                    final conf = (f.confidence * 100).round();
                    final color = _colorFor(f.className);
                    return Semantics(
                      label:
                          '${f.className.replaceAll("_", " ")}, $conf% confidence',
                      child: Chip(
                        label: Text(
                          '${f.className.replaceAll("_", " ")}  $conf%',
                        ),
                        backgroundColor: color.withOpacity(0.15),
                        labelStyle: TextStyle(
                          color: color,
                          fontWeight: FontWeight.w600,
                          fontSize: 12,
                        ),
                        side: BorderSide(color: color.withOpacity(0.4)),
                      ),
                    );
                  }).toList(),
                ),
              ],

              // ── Confidence list ─────────────────────────────────────
              if (hasFeatures) ...[
                const SizedBox(height: 12),
                ...visionAnalysis.features.map((feat) {
                  final conf = feat.confidence;
                  final pct = (conf * 100).round();
                  final color = _colorFor(feat.className);

                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      children: [
                        Container(
                          width: 10,
                          height: 10,
                          decoration: BoxDecoration(
                            color: color,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 8),
                        SizedBox(
                          width: 120,
                          child: Text(
                            feat.className.replaceAll('_', ' '),
                            style: const TextStyle(fontSize: 12),
                          ),
                        ),
                        Expanded(
                          child: Semantics(
                            label:
                                '${feat.className.replaceAll("_", " ")} $pct percent confidence',
                            excludeSemantics: true,
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: conf,
                                minHeight: 6,
                                backgroundColor: NaviAbleColors.border,
                                valueColor:
                                    AlwaysStoppedAnimation<Color>(color),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '$pct%',
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  );
                }),
              ],

              const SizedBox(height: 8),

              // ── Explanation ─────────────────────────────────────────
              Text(
                hasFeatures
                    ? 'Physical accessibility infrastructure was detected '
                        'in the uploaded image.'
                    : 'No accessibility features were detected above the '
                        '50% confidence threshold.',
                style: const TextStyle(
                  fontSize: 12,
                  color: NaviAbleColors.textMuted,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
