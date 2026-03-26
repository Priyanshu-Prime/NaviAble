/// HomeScreen — the main screen of the NaviAble Flutter web application.
///
/// This is a single-page layout designed for desktop / laptop demonstration:
///
/// ```
/// AppBar (NaviAble branding + health-check badge)
/// └── Body (responsive max-width container)
///       ├── Left column  — SubmitForm (image + text review input)
///       └── Right column — VerificationResults (gauge + analysis cards)
/// ```
///
/// On narrow screens (< 900 dp) the columns stack vertically so the app also
/// works on a tablet or large phone.
///
/// Accessibility mandate compliance (`.agent/system/CONSTRAINTS_AND_RULES.md`):
/// - All interactive elements are wrapped in [Semantics].
/// - The results panel is marked as a live region so screen readers announce
///   when new results arrive.
library home_screen;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/verification_models.dart';
import '../providers/verify_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/detection_result_card.dart';
import '../widgets/nlp_result_card.dart';
import '../widgets/submit_form.dart';
import '../widgets/trust_score_gauge.dart';

/// Breakpoint below which the two-column layout collapses to a single column.
const double _kTwoColumnBreakpoint = 900;

/// The single home screen / root route of the NaviAble app.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final healthAsync = ref.watch(healthProvider);
    final verifyState = ref.watch(verifyProvider);
    final screenWidth = MediaQuery.sizeOf(context).width;
    final isTwoColumn = screenWidth >= _kTwoColumnBreakpoint;

    return Scaffold(
      appBar: _buildAppBar(context, healthAsync),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1200),
            child: isTwoColumn
                ? _TwoColumnLayout(verifyState: verifyState)
                : _SingleColumnLayout(verifyState: verifyState),
          ),
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(
    BuildContext context,
    AsyncValue<HealthResponse?> healthAsync,
  ) {
    return AppBar(
      title: Semantics(
        header: true,
        child: const Row(
          children: [
            Text('\u267F', style: TextStyle(fontSize: 22)),
            SizedBox(width: 8),
            Text('NaviAble'),
            SizedBox(width: 6),
            Text(
              'Accessibility Verification',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w400,
                color: Colors.white70,
              ),
            ),
          ],
        ),
      ),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: 16),
          child: healthAsync.when(
            data: (health) => _HealthBadge(health: health),
            loading: () => const _HealthBadge(health: null),
            error: (_, __) => const _HealthBadge(health: null),
          ),
        ),
      ],
    );
  }
}

// ── Two-Column Layout ─────────────────────────────────────────────────────────

class _TwoColumnLayout extends StatelessWidget {

  const _TwoColumnLayout({required this.verifyState});
  final VerifyState verifyState;

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 5,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: const SubmitForm(),
              ),
            ),
          ),
          const SizedBox(width: 24),
          Expanded(
            flex: 6,
            child: _ResultsPanel(verifyState: verifyState),
          ),
        ],
      ),
    );
  }
}

// ── Single-Column Layout ──────────────────────────────────────────────────────

class _SingleColumnLayout extends StatelessWidget {

  const _SingleColumnLayout({required this.verifyState});
  final VerifyState verifyState;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: const SubmitForm(),
          ),
        ),
        const SizedBox(height: 24),
        _ResultsPanel(verifyState: verifyState),
      ],
    );
  }
}

// ── Results Panel ─────────────────────────────────────────────────────────────

class _ResultsPanel extends ConsumerWidget {

  const _ResultsPanel({required this.verifyState});
  final VerifyState verifyState;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Semantics(
      liveRegion: true,
      child: switch (verifyState) {
        VerifyIdle() => const _IdlePlaceholder(),
        VerifyLoading() => const _LoadingPanel(),
        VerifySuccess(:final response) => _SuccessPanel(response: response),
        VerifyError(:final message) => _ErrorPanel(message: message),
      },
    );
  }
}

// ── Idle Placeholder ──────────────────────────────────────────────────────────

class _IdlePlaceholder extends StatelessWidget {
  const _IdlePlaceholder();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 64, horizontal: 32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Semantics(
              image: true,
              label: 'NaviAble Dual-AI verification illustration',
              child: const Text('\uD83D\uDD0D',
                  style: TextStyle(fontSize: 64)),
            ),
            const SizedBox(height: 24),
            const Text(
              'Waiting for your submission',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: NaviAbleColors.textPrimary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            const Text(
              'Fill in the form on the left with a photo and a written '
              'review of the accessible location, then tap '
              '"Verify with NaviAble AI".',
              style: TextStyle(
                fontSize: 14,
                color: NaviAbleColors.textMuted,
                height: 1.6,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            _HowItWorksTile(
              icon: Icons.visibility_outlined,
              title: 'YOLOv11 Vision Engine',
              detail: 'Detects physical infrastructure (ramps, handrails, '
                  'tactile paving, elevators) from your photo.',
            ),
            const SizedBox(height: 12),
            _HowItWorksTile(
              icon: Icons.text_fields_rounded,
              title: 'RoBERTa NLP Engine',
              detail: 'Classifies your written review as either a genuine '
                  'physical description or generic accessibility-washing.',
            ),
            const SizedBox(height: 12),
            _HowItWorksTile(
              icon: Icons.bar_chart_rounded,
              title: 'NaviAble Trust Score',
              detail: 'Combines both signals: '
                  '60 % vision confidence + 40 % NLP confidence.',
            ),
          ],
        ),
      ),
    );
  }
}

class _HowItWorksTile extends StatelessWidget {

  const _HowItWorksTile({
    required this.icon,
    required this.title,
    required this.detail,
  });
  final IconData icon;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: NaviAbleColors.primary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, size: 22, color: NaviAbleColors.primary),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                detail,
                style: const TextStyle(
                  fontSize: 13,
                  color: NaviAbleColors.textMuted,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ── Loading Panel ─────────────────────────────────────────────────────────────

class _LoadingPanel extends StatelessWidget {
  const _LoadingPanel();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 64, horizontal: 32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Semantics(
              label: 'Running Dual-AI analysis, please wait',
              child: const CircularProgressIndicator(
                strokeWidth: 5,
                color: NaviAbleColors.primary,
              ),
            ),
            const SizedBox(height: 32),
            const Text(
              'Running Dual-AI Analysis\u2026',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: NaviAbleColors.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'YOLOv11 is scanning your image for physical features\n'
              'while RoBERTa analyses the text for genuine detail.',
              style: TextStyle(
                fontSize: 13,
                color: NaviAbleColors.textMuted,
                height: 1.6,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

// ── Success Panel ─────────────────────────────────────────────────────────────

class _SuccessPanel extends ConsumerWidget {

  const _SuccessPanel({required this.response});
  final VerificationResponse response;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = response.data;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                const Text(
                  'Verification Complete',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: NaviAbleColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Dual-AI analysis result',
                  style: TextStyle(
                    fontSize: 12,
                    color: NaviAbleColors.textMuted,
                  ),
                ),
                const SizedBox(height: 24),
                TrustScoreGauge(score: data.naviableTrustScore),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        NlpResultCard(nlpAnalysis: data.nlpAnalysis),
        const SizedBox(height: 16),
        DetectionResultCard(visionAnalysis: data.visionAnalysis),
        const SizedBox(height: 16),
        Semantics(
          label: 'Verify another location button',
          button: true,
          child: OutlinedButton.icon(
            onPressed: () => ref.read(verifyProvider.notifier).reset(),
            icon: const Icon(Icons.refresh, size: 18),
            label: const Text('Verify Another Location'),
          ),
        ),
      ],
    );
  }
}

// ── Error Panel ───────────────────────────────────────────────────────────────

class _ErrorPanel extends ConsumerWidget {

  const _ErrorPanel({required this.message});
  final String message;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      color: const Color(0xFFFFEBEE),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: NaviAbleColors.danger),
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Semantics(
              label: 'Verification error icon',
              child: const Icon(
                Icons.error_outline_rounded,
                color: NaviAbleColors.danger,
                size: 48,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Verification Failed',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: NaviAbleColors.danger,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              style: const TextStyle(
                fontSize: 13,
                color: NaviAbleColors.textMuted,
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            Semantics(
              label: 'Try again button',
              button: true,
              child: ElevatedButton.icon(
                onPressed: () => ref.read(verifyProvider.notifier).reset(),
                icon: const Icon(Icons.refresh, size: 18),
                label: const Text('Try Again'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: NaviAbleColors.danger,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Health Badge ──────────────────────────────────────────────────────────────

class _HealthBadge extends StatelessWidget {

  const _HealthBadge({required this.health});
  final HealthResponse? health;

  @override
  Widget build(BuildContext context) {
    if (health == null) {
      return Semantics(
        label: 'Backend status: connecting',
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: const [
            SizedBox(
              width: 10,
              height: 10,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Colors.white54,
              ),
            ),
            SizedBox(width: 6),
            Text(
              'Connecting\u2026',
              style: TextStyle(fontSize: 12, color: Colors.white70),
            ),
          ],
        ),
      );
    }

    final isOnline = health?.status == 'ok';
    final isDemoMode = health?.demoMode ?? false;

    return Semantics(
      label: 'Backend status: ${isOnline ? "online" : "offline"}'
          '${isDemoMode ? ", demo mode active" : ""}',
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              color: isOnline ? NaviAbleColors.accent : NaviAbleColors.danger,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            isOnline
                ? (isDemoMode ? 'Backend \u00B7 Demo Mode' : 'Backend Online')
                : 'Backend Offline',
            style: const TextStyle(fontSize: 12, color: Colors.white),
          ),
        ],
      ),
    );
  }
}
