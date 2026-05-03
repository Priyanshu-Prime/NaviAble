/// Riverpod State Providers for the NaviAble verification workflow.
///
/// This file contains all state management logic separated from the UI layer.
/// The UI (screens + widgets) should only:
///   1. Watch providers with `ref.watch(...)`.
///   2. Call notifier methods with `ref.read(verifyProvider.notifier).submit(...)`.
///
/// Keeping business logic in providers and not in widgets makes the code
/// testable without a Flutter widget tree.
library providers;

import 'dart:typed_data';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';

import '../api/api_client.dart';
import '../models/verification_models.dart';

// ── API Client Provider ─────────────────────────────────────────────────────

/// Provides the singleton [NaviAbleApiClient] instance.
///
/// Using a [Provider] (not a [StateProvider]) because the API client is
/// stateless — it holds no mutable state beyond the [Dio] instance
/// configuration which is set once at construction.
final apiClientProvider = Provider<NaviAbleApiClient>(
  (_) => NaviAbleApiClient(),
);

// ── Health State ────────────────────────────────────────────────────────────

/// Async provider that fetches backend health on first access.
///
/// `keepAlive: true` ensures the health result is not discarded when the
/// widget reading it is removed (e.g., during navigation).
final healthProvider = FutureProvider.autoDispose<HealthResponse?>(
  (ref) => ref.watch(apiClientProvider).health(),
);

// ── Verification State ──────────────────────────────────────────────────────

/// Union type representing the current state of the verification workflow.
///
/// Using a sealed class hierarchy (rather than a single class with nullable
/// fields) makes `switch` expressions exhaustive and eliminates null checks
/// in the UI layer.
sealed class VerifyState {
  const VerifyState();
}

/// The user has not yet submitted a form.
final class VerifyIdle extends VerifyState {
  const VerifyIdle();
}

/// A verification request is in flight.
final class VerifyLoading extends VerifyState {
  const VerifyLoading();
}

/// Verification completed successfully.
final class VerifySuccess extends VerifyState {
  const VerifySuccess(this.response);
  final VerificationResponse response;
}

/// Verification failed due to a network or server error.
final class VerifyError extends VerifyState {
  const VerifyError(this.message);
  final String message;
}

// ── Verify Notifier ─────────────────────────────────────────────────────────

/// [Notifier] that manages the [VerifyState] lifecycle.
///
/// Separating the mutation logic into a [Notifier] means:
/// 1. The state transition graph is defined in one place.
/// 2. Widget tests can pass a mock [NaviAbleApiClient] without touching UI code.
class VerifyNotifier extends Notifier<VerifyState> {
  @override
  VerifyState build() => const VerifyIdle();

  /// Submit a review for Dual-AI verification.
  ///
  /// This method:
  /// 1. Compresses the raw [imageBytes] to JPEG at 85 % quality to reduce
  ///    file size before upload.  This is critical to prevent CUDA OOM on
  ///    the target GTX 1650 Ti (4 GB VRAM).
  /// 2. Calls the API and transitions state accordingly.
  ///
  /// Parameters:
  /// - [imageBytes]: Raw image bytes from [ImagePicker].
  /// - [imageFilename]: Original filename for the multipart field.
  /// - [review]: The user's written review text.
  /// - [rating]: The user's accessibility rating (1-5 stars).
  Future<void> submit({
    required List<int> imageBytes,
    required String imageFilename,
    required String review,
    required int rating,
  }) async {
    state = const VerifyLoading();

    try {
      // ── Step 1: Compress image ─────────────────────────────────────────
      // Compress to max 1024×1024, 85% JPEG quality.
      // This drastically reduces upload size while preserving enough
      // detail for YOLOv11 to detect ramps, handrails, etc.
      final compressed = await FlutterImageCompress.compressWithList(
        Uint8List.fromList(imageBytes),
        minWidth: 1024,
        minHeight: 1024,
        quality: 85,
        format: CompressFormat.jpeg,
      );

      // ── Step 2: Call API ──────────────────────────────────────────────
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.verify(
        imageBytes: compressed,
        imageFilename: imageFilename,
        review: review,
        rating: rating,
      );

      state = VerifySuccess(response);
    } on Exception catch (e) {
      // Defensive catch-all: network errors, JSON parse errors, etc.
      state = VerifyError(e.toString().replaceAll('Exception: ', ''));
    }
  }

  /// Reset the state back to [VerifyIdle] so the user can submit a new review.
  void reset() => state = const VerifyIdle();
}

/// The global provider for the verification workflow.
///
/// Widgets read the current [VerifyState] with:
/// ```dart
/// final verifyState = ref.watch(verifyProvider);
/// ```
/// and trigger submission with:
/// ```dart
/// ref.read(verifyProvider.notifier).submit(...)
/// ```
final verifyProvider = NotifierProvider<VerifyNotifier, VerifyState>(
  VerifyNotifier.new,
);
