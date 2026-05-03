/// NaviAble API Client
///
/// Encapsulates all HTTP communication with the FastAPI backend using the
/// [dio] package.  Using `dio` (over the built-in `http` package) was chosen
/// because it provides:
///
/// - [Interceptor] support for request logging and JWT token injection.
/// - Built-in `FormData` / `MultipartFile` support for the image upload.
/// - Structured error handling via [DioException].
///
/// The base URL is controlled by the compile-time constant `apiBaseUrl`
/// (set via `--dart-define=API_BASE_URL=http://localhost:8000`) so that the
/// same build artefact can target different environments without recompilation.
library api_client;

import 'package:dio/dio.dart';

import '../models/verification_models.dart';

/// Compile-time configurable backend URL.
///
/// Override at build time with:
/// ```
/// flutter run --dart-define=API_BASE_URL=http://your-server:8000
/// ```
/// or in `launch.json`:
/// ```json
/// { "args": ["--dart-define=API_BASE_URL=http://your-server:8000"] }
/// ```
const String _kApiBaseUrl =
    String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000');

/// Central API client for the NaviAble backend.
///
/// This class is a singleton provided via Riverpod in
/// `lib/providers/api_provider.dart`.  It must NOT be instantiated directly
/// in UI code — always consume it through the [apiClientProvider].
class NaviAbleApiClient {
  late final Dio _dio;

  NaviAbleApiClient() {
    _dio = Dio(
      BaseOptions(
        baseUrl: _kApiBaseUrl,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 60),
        sendTimeout: const Duration(seconds: 60),
        headers: {'Accept': 'application/json'},
      ),
    );

    // ── Request / Response Logging Interceptor ───────────────────────────
    // Logs method, path, and response time for every request.
    // Critical for benchmarking ML inference latency during demonstrations.
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          options.extra['_startTime'] = DateTime.now().millisecondsSinceEpoch;
          // ignore: avoid_print
          print('[NaviAble API] → ${options.method} ${options.uri}');
          handler.next(options);
        },
        onResponse: (response, handler) {
          final start = response.requestOptions.extra['_startTime'] as int?;
          final elapsed = start != null
              ? DateTime.now().millisecondsSinceEpoch - start
              : -1;
          // ignore: avoid_print
          print(
            '[NaviAble API] ← ${response.statusCode} '
            '${response.requestOptions.uri} (${elapsed}ms)',
          );
          handler.next(response);
        },
        onError: (DioException error, handler) {
          // ignore: avoid_print
          print(
            '[NaviAble API] ✗ ${error.requestOptions.uri} '
            '${error.response?.statusCode} — ${error.message}',
          );
          handler.next(error);
        },
      ),
    );
  }

  /// Check whether the backend is reachable and return its health status.
  ///
  /// Called by the [HomeScreen] on first load to detect demo mode and show
  /// an informational banner to the user.
  ///
  /// Returns `null` if the backend is unreachable (network error / server down).
  Future<HealthResponse?> checkHealth() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/health');
      return HealthResponse.fromJson(response.data!);
    } on DioException catch (e) {
      // ignore: avoid_print
      print('[NaviAble API] Health check failed: ${e.message}');
      return null;
    }
  }

  /// Submit a Dual-AI verification request to `POST /api/v1/verify`.
  ///
  /// The image is sent as a multipart file.  The [imageBytes] should already
  /// be compressed via `flutter_image_compress` before calling this method
  /// (handled by the [VerifyNotifier] in the provider layer).
  ///
  /// Parameters:
  /// - [imageBytes]: Compressed JPEG image bytes.
  /// - [imageFilename]: Original filename (e.g. `'photo.jpg'`).
  /// - [textReview]: The user's written accessibility review.
  /// - [locationId]: A UUID string identifying the location being reviewed.
  ///
  /// Throws a [DioException] on network/server errors.  The caller (provider)
  /// is responsible for catching this and setting error state.
  Future<VerificationResponse> verify({
    required List<int> imageBytes,
    required String imageFilename,
    required String textReview,
    required String locationId,
  }) async {
    // Demo mode: use default location (San Francisco, CA)
    // In production, these would come from the location picker UI
    const double defaultLatitude = 37.7749;
    const double defaultLongitude = -122.4194;
    const int defaultRating = 3;

    final formData = FormData.fromMap({
      'review': textReview,
      'latitude': defaultLatitude,
      'longitude': defaultLongitude,
      'rating': defaultRating,
      'image': MultipartFile.fromBytes(
        imageBytes,
        filename: imageFilename,
        contentType: DioMediaType('image', 'jpeg'),
      ),
    });

    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/verify',
      data: formData,
    );

    return VerificationResponse.fromJson(response.data!);
  }
}
