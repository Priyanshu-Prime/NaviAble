/// NaviAble API Client
///
/// Encapsulates all HTTP communication with the FastAPI backend using the
/// [dio] package. Using `dio` (over the built-in `http` package) provides:
/// - [Interceptor] support for request logging and JWT token injection.
/// - Built-in `FormData` / `MultipartFile` support for image uploads.
/// - Structured error handling via [DioException].
library api_client;

import 'package:dio/dio.dart';

import '../models/place_models.dart';
import '../models/verification_models.dart';

/// Compile-time configurable backend URL.
///
/// Override at build time with:
/// ```
/// flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
/// flutter run --dart-define=API_BASE_URL=http://192.168.x.y:8000
/// ```
const String kApiBaseUrl =
    String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');

/// Central API client for the NaviAble backend.
///
/// This class is a singleton provided via Riverpod in `lib/api/providers.dart`.
/// It must NOT be instantiated directly in UI code — always consume it through
/// the [apiClientProvider].
class NaviAbleApiClient {
  late final Dio _dio;

  NaviAbleApiClient() {
    _dio = Dio(
      BaseOptions(
        baseUrl: kApiBaseUrl,
        connectTimeout: const Duration(seconds: 20),
        receiveTimeout: const Duration(seconds: 60),
        sendTimeout: const Duration(seconds: 60),
        headers: {'Accept': 'application/json'},
      ),
    );

    // ── Request / Response Logging Interceptor ───────────────────────────
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

  /// Check whether the backend is reachable.
  Future<HealthResponse?> health() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>('/healthz');
      return HealthResponse.fromJson(r.data!);
    } catch (_) {
      return null;
    }
  }

  /// Find nearby places within a radius.
  ///
  /// Returns a list of places (both from DB and Google Places) merged and
  /// overlaid with trust data.
  Future<List<PlaceSummary>> nearbyPlaces({
    required double latitude,
    required double longitude,
    int radiusM = 800,
    String? keyword,
  }) async {
    final r = await _dio.get<List<dynamic>>(
      '/api/v1/places/nearby',
      queryParameters: {
        'latitude': latitude,
        'longitude': longitude,
        'radius_m': radiusM,
        if (keyword != null && keyword.isNotEmpty) 'keyword': keyword,
      },
    );
    return r.data!
        .map((e) => PlaceSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Search for places by query.
  ///
  /// Returns autocomplete predictions with optional lat/lon bias.
  Future<List<PlaceAutocomplete>> searchPlaces(
    String query, {
    double? latitude,
    double? longitude,
  }) async {
    final r = await _dio.get<List<dynamic>>(
      '/api/v1/places/search',
      queryParameters: {
        'query': query,
        if (latitude != null) 'latitude': latitude,
        if (longitude != null) 'longitude': longitude,
      },
    );
    return r.data!
        .map((e) => PlaceAutocomplete.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Get full details for a place by ID or name.
  ///
  /// Supports both Google Place IDs and place names. The backend will:
  /// 1. Try to find by google_place_id first
  /// 2. Fall back to Google Places API if not found locally
  /// 3. Search database by name as final fallback
  Future<PlaceDetail> placeDetail(String placeIdentifier) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/v1/places/$placeIdentifier',
    );
    return PlaceDetail.fromJson(r.data!);
  }

  /// Search places in the database by name.
  ///
  /// Use this when a place is not available in Google Places.
  Future<List<PlaceSummary>> searchPlacesInDatabase(String query) async {
    final r = await _dio.get<List<dynamic>>(
      '/api/v1/places/search/db',
      queryParameters: {'query': query},
    );
    return r.data!
        .map((e) => PlaceSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Get places with reviews within a radius.
  ///
  /// Returns only places that have public reviews, sorted by distance.
  Future<List<PlaceSummary>> reviewedNearby({
    required double latitude,
    required double longitude,
    int radiusM = 5000,
  }) async {
    final r = await _dio.get<List<dynamic>>(
      '/api/v1/places/reviewed/nearby',
      queryParameters: {
        'latitude': latitude,
        'longitude': longitude,
        'radius_m': radiusM,
      },
    );
    return r.data!
        .map((e) => PlaceSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Submit a Dual-AI verification request.
  ///
  /// Parameters:
  /// - [imageBytes]: Compressed JPEG image bytes.
  /// - [imageFilename]: Original filename (e.g. `'photo.jpg'`).
  /// - [review]: The user's written accessibility review.
  /// - [rating]: User's rating (1-5 stars).
  /// - [googlePlaceId]: Optional explicit place ID.
  /// - [latitude]: Optional device GPS latitude.
  /// - [longitude]: Optional device GPS longitude.
  /// - [address]: Optional address string for reverse geocoding.
  ///
  /// The backend resolves location via priority chain:
  /// 1. googlePlaceId (explicit user choice)
  /// 2. (latitude, longitude) from device
  /// 3. EXIF GPS from the image
  /// 4. Reverse-geocode of address string
  Future<VerificationResponse> verify({
    required List<int> imageBytes,
    required String imageFilename,
    required String review,
    required int rating,
    String? googlePlaceId,
    double? latitude,
    double? longitude,
    String? address,
  }) async {
    final form = FormData.fromMap({
      'image': MultipartFile.fromBytes(
        imageBytes,
        filename: imageFilename,
        contentType: DioMediaType('image', 'jpeg'),
      ),
      'review': review,
      'rating': rating,
      if (googlePlaceId != null) 'google_place_id': googlePlaceId,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (address != null) 'address': address,
    });
    final r = await _dio.post<Map<String, dynamic>>('/api/v1/verify', data: form);
    return VerificationResponse.fromJson(r.data!);
  }
}
