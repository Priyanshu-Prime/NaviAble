/// NlpResultCard — displays the RoBERTa NLP analysis result.
///
/// Every interactive element is wrapped in a [Semantics] widget as required
/// by `.agent/system/CONSTRAINTS_AND_RULES.md`.
library nlp_result_card;

import 'package:flutter/material.dart';

import '../models/verification_models.dart';
import '../theme/app_theme.dart';

/// Card widget showing the NLP Integrity Engine output.
class NlpResultCard extends StatelessWidget {
  final NlpAnalysis nlpAnalysis;

  const NlpResultCard({super.key, required this.nlpAnalysis});

  @override
  Widget build(BuildContext context) {
    final isGenuine = nlpAnalysis.isGenuine;
    final percent = (nlpAnalysis.confidence * 100).round();
    final cardColor =
        isGenuine ? const Color(0xFFF1F8E9) : const Color(0xFFFFFDE7);
    final borderColor =
        isGenuine ? const Color(0xFFA5D6A7) : const Color(0xFFFFE082);

    return Semantics(
      label: 'NLP Integrity Engine result. '
          '${isGenuine ? "Genuine review" : "Generic review"}. '
          'Confidence: $percent percent. '
          'Label: ${nlpAnalysis.label}.',
      child: Card(
        color: cardColor,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: borderColor, width: 1.5),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Header ─────────────────────────────────────────────
              Row(
                children: [
                  const Text('🔤', style: TextStyle(fontSize: 20)),
                  const SizedBox(width: 8),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'NLP Integrity Engine',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        'RoBERTa · Fine-tuned on 402 labelled reviews',
                        style: const TextStyle(
                          fontSize: 11,
                          color: NaviAbleColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // ── Badge + Label ───────────────────────────────────────
              Row(
                children: [
                  _VerdictBadge(isGenuine: isGenuine),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      nlpAnalysis.label,
                      style: const TextStyle(
                        fontSize: 12,
                        fontStyle: FontStyle.italic,
                        color: NaviAbleColors.textMuted,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // ── Confidence bar ──────────────────────────────────────
              Row(
                children: [
                  const Text(
                    'Confidence',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: NaviAbleColors.textMuted,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Semantics(
                      label: 'NLP confidence $percent percent',
                      excludeSemantics: true,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: nlpAnalysis.confidence,
                          minHeight: 8,
                          backgroundColor: NaviAbleColors.border,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            NaviAbleColors.primary,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '$percent%',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // ── Explanation ─────────────────────────────────────────
              Text(
                isGenuine
                    ? 'The review contains specific, verifiable accessibility '
                        'details — not generic praise.'
                    : 'The review lacks specific physical detail and may not '
                        'reliably indicate accessibility.',
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

/// Small verdict badge showing Genuine / Generic.
class _VerdictBadge extends StatelessWidget {
  final bool isGenuine;

  const _VerdictBadge({required this.isGenuine});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: isGenuine
            ? const Color(0xFFC8E6C9)
            : const Color(0xFFFFF9C4),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        isGenuine ? '✅ Genuine' : '⚠️ Generic',
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: isGenuine
              ? const Color(0xFF1B5E20)
              : const Color(0xFF795548),
        ),
      ),
    );
  }
}
