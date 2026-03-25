/// Widget tests for the NaviAble Flutter application.
///
/// These are lightweight smoke tests that verify the widget tree renders
/// without errors.  They do not test network calls (those are handled by
/// the provider layer) — a mock provider override is used instead.
///
/// Run with:
/// ```
/// flutter test
/// ```
library widget_test;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:naviable/main.dart';
import 'package:naviable/providers/verify_provider.dart';
import 'package:naviable/models/verification_models.dart';

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Wraps a widget in [ProviderScope] + [MaterialApp] for pump convenience.
Widget _wrap(Widget child, {List<Override> overrides = const []}) {
  return ProviderScope(
    overrides: overrides,
    child: MaterialApp(home: Scaffold(body: child)),
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

void main() {
  testWidgets('NaviAbleApp renders without throwing', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: NaviAbleApp()));
    // Allow async providers (health check) to settle without hitting the network.
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.byType(MaterialApp), findsOneWidget);
  });

  testWidgets('HomeScreen shows idle placeholder initially', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: NaviAbleApp()));
    await tester.pump(const Duration(milliseconds: 100));
    expect(
      find.textContaining('Waiting for your submission'),
      findsOneWidget,
    );
  });

  testWidgets('SubmitForm has review text field and submit button',
      (tester) async {
    await tester.pumpWidget(const ProviderScope(child: NaviAbleApp()));
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.byType(TextFormField), findsOneWidget);
    expect(find.textContaining('Verify with NaviAble AI'), findsOneWidget);
  });

  testWidgets('SubmitForm validates empty review text', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: NaviAbleApp()));
    await tester.pump(const Duration(milliseconds: 100));

    // Tap submit without filling anything — should show validation message.
    await tester.tap(find.textContaining('Verify with NaviAble AI'));
    await tester.pump();
    expect(find.textContaining('at least 10 characters'), findsOneWidget);
  });

  testWidgets('Results panel shows success state when provider has result',
      (tester) async {
    // Build a mock VerificationResponse matching the API contract.
    final mockResponse = VerificationResponse(
      status: 'success',
      data: VerificationData(
        nlpAnalysis: const NlpAnalysis(
          isGenuine: true,
          confidence: 0.87,
          label: 'Genuine Physical Detail',
        ),
        visionAnalysis: VisionAnalysis(
          objectsDetected: 2,
          features: [
            const DetectedFeature(
                className: 'ramp',
                confidence: 0.62,
                bbox: [10, 20, 150, 200]),
            const DetectedFeature(
                className: 'handrail',
                confidence: 0.55,
                bbox: [15, 25, 140, 190]),
          ],
        ),
        naviableTrustScore: 0.72,
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          // Seed the provider with a success state so we can test rendering.
          verifyProvider.overrideWith(() => _MockVerifyNotifier(mockResponse)),
        ],
        child: const NaviAbleApp(),
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.textContaining('Verification Complete'), findsOneWidget);
    expect(find.textContaining('NLP Integrity Engine'), findsOneWidget);
    expect(find.textContaining('Vision Detection'), findsOneWidget);
  });
}

// ── Mock Notifier ─────────────────────────────────────────────────────────────

/// A mock [VerifyNotifier] that starts in [VerifySuccess] state.
///
/// Used to test the success rendering path without making network calls.
class _MockVerifyNotifier extends VerifyNotifier {
  final VerificationResponse _response;

  _MockVerifyNotifier(this._response);

  @override
  VerifyState build() => VerifySuccess(_response);
}
