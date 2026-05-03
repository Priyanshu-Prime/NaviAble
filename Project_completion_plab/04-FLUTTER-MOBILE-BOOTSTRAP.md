# Phase 04 — Flutter mobile bootstrap (Android + iOS, Google Maps + Places keys, deps, routing skeleton)

**Status:** not started
**Depends on:** phases 01–03 (backend has place-aware endpoints)
**Affects:** `frontend/` — adds `android/`, `ios/`, modifies `pubspec.yaml`, `lib/main.dart`, adds `lib/core/`, `lib/api/`, `lib/screens/`

## Goal

The Flutter project today is **web-only**. We need a mobile app. This phase
adds Android + iOS platform folders, wires Google Maps + Places API keys
correctly, installs every plugin we'll need in phases 05–07, sets up a
proper router (so phase 05 just adds screens to it), and centralises the
backend client.

We **do not** delete the web target — keeping it makes desktop demos easy.

---

## Deliverables

### 1. Add Android + iOS platforms

```bash
cd frontend
flutter create --platforms=android,ios --org=ai.naviable .
# This is non-destructive — existing lib/ and web/ are kept.
```

After this, `frontend/android/` and `frontend/ios/Runner/` exist.

### 2. Update `pubspec.yaml`

Replace the `dependencies:` block (keep `dev_dependencies:` as-is):

```yaml
dependencies:
  flutter:
    sdk: flutter

  # State
  flutter_riverpod: ^2.5.1
  riverpod_annotation: ^2.3.5

  # HTTP
  dio: ^5.4.3

  # Maps + Geo
  google_maps_flutter: ^2.7.0
  geolocator: ^12.0.0
  geocoding: ^3.0.0
  flutter_polyline_points: ^2.1.0
  google_maps_flutter_platform_interface: ^2.7.0

  # Image
  image_picker: ^1.1.2
  flutter_image_compress: ^2.2.0
  native_exif: ^0.6.2          # reads EXIF on-device for early validation
  cached_network_image: ^3.3.1

  # Routing
  go_router: ^14.2.0

  # Utility
  uuid: ^4.4.0
  collection: ^1.18.0
  intl: ^0.19.0
  cupertino_icons: ^1.0.8

  # Permissions
  permission_handler: ^11.3.1

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^4.0.0
  build_runner: ^2.4.11
  riverpod_generator: ^2.4.0
```

Run:

```bash
cd frontend && flutter pub get
```

### 3. Android wiring

#### `frontend/android/app/build.gradle.kts` (or `build.gradle`)

In `android { defaultConfig { ... } }`:

```gradle
minSdkVersion = 23   // google_maps_flutter requires ≥21; 23 covers permission_handler
compileSdkVersion 34
targetSdkVersion 34
```

#### `frontend/android/app/src/main/AndroidManifest.xml`

Above `<application>`:

```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
<uses-permission android:name="android.permission.CAMERA"/>
<uses-feature android:name="android.hardware.location.gps"/>
```

Inside `<application>` (before `</application>`):

```xml
<meta-data
    android:name="com.google.android.geo.API_KEY"
    android:value="${MAPS_API_KEY}"/>
```

This reads `MAPS_API_KEY` from `gradle.properties` so it isn't checked in.
Add to `frontend/android/local.properties`:

```properties
MAPS_API_KEY=YOUR_ANDROID_MAPS_SDK_KEY_HERE
```

And in `frontend/android/app/build.gradle.kts`, inside `defaultConfig`:

```gradle
manifestPlaceholders["MAPS_API_KEY"] = (project.findProperty("MAPS_API_KEY") ?: "") as String
```

#### Network security (allow `http://10.0.2.2:8000` in debug for emulator)

Create `frontend/android/app/src/main/res/xml/network_security_config.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <base-config cleartextTrafficPermitted="false">
    <trust-anchors>
      <certificates src="system"/>
    </trust-anchors>
  </base-config>
  <domain-config cleartextTrafficPermitted="true">
    <domain includeSubdomains="true">10.0.2.2</domain>
    <domain includeSubdomains="true">localhost</domain>
    <domain includeSubdomains="true">127.0.0.1</domain>
  </domain-config>
</network-security-config>
```

Reference it in `<application android:networkSecurityConfig="@xml/network_security_config" ...>`.

### 4. iOS wiring

#### `frontend/ios/Runner/Info.plist`

Add:

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>NaviAble uses your location to show nearby accessible places and tag your contributions.</string>
<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>NaviAble uses your location to show nearby accessible places and tag your contributions.</string>
<key>NSCameraUsageDescription</key>
<string>NaviAble uses the camera to capture accessibility feature photos.</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>NaviAble accesses your photo library so you can submit existing photos as accessibility evidence.</string>
<key>io.flutter.embedded_views_preview</key>
<true/>
```

#### `frontend/ios/Runner/AppDelegate.swift`

```swift
import UIKit
import Flutter
import GoogleMaps

@UIApplicationMain
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GMSServices.provideAPIKey(
      ProcessInfo.processInfo.environment["MAPS_API_KEY_IOS"] ?? "YOUR_IOS_MAPS_KEY"
    )
    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
}
```

For a hardcoded fallback during dev, replace the env-var read with the
literal key string. **Restrict the iOS Maps key to your bundle ID in
Google Cloud Console**.

### 5. Backend client + env

Replace `frontend/lib/api/api_client.dart` with the place-aware client:

```dart
import 'package:dio/dio.dart';
import '../models/place_models.dart';
import '../models/verification_models.dart';

const String kApiBaseUrl =
    String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');

class NaviAbleApiClient {
  final Dio _dio;

  NaviAbleApiClient()
      : _dio = Dio(BaseOptions(
          baseUrl: kApiBaseUrl,
          connectTimeout: const Duration(seconds: 20),
          receiveTimeout: const Duration(seconds: 60),
          sendTimeout: const Duration(seconds: 60),
          headers: {'Accept': 'application/json'},
        ));

  Future<HealthResponse?> health() async {
    try {
      final r = await _dio.get<Map<String, dynamic>>('/healthz');
      return HealthResponse.fromJson(r.data!);
    } catch (_) {
      return null;
    }
  }

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
    return r.data!.map((e) => PlaceSummary.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<PlaceAutocomplete>> searchPlaces(String query, {double? lat, double? lon}) async {
    final r = await _dio.get<List<dynamic>>(
      '/api/v1/places/search',
      queryParameters: {
        'query': query,
        if (lat != null) 'latitude': lat,
        if (lon != null) 'longitude': lon,
      },
    );
    return r.data!.map((e) => PlaceAutocomplete.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<PlaceDetail> placeDetail(String googlePlaceId) async {
    final r = await _dio.get<Map<String, dynamic>>('/api/v1/places/$googlePlaceId');
    return PlaceDetail.fromJson(r.data!);
  }

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
      'image': MultipartFile.fromBytes(imageBytes,
          filename: imageFilename,
          contentType: DioMediaType('image', 'jpeg')),
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
```

### 6. Models

Create `frontend/lib/models/place_models.dart`:

```dart
class PlaceSummary {
  final String? id;
  final String googlePlaceId;
  final String name;
  final String? formattedAddress;
  final double latitude;
  final double longitude;
  final List<String> googleTypes;
  final double aggregateTrust;
  final int publicCount;
  final int contributionCount;
  final bool hasData;

  PlaceSummary({
    required this.id,
    required this.googlePlaceId,
    required this.name,
    required this.formattedAddress,
    required this.latitude,
    required this.longitude,
    required this.googleTypes,
    required this.aggregateTrust,
    required this.publicCount,
    required this.contributionCount,
    required this.hasData,
  });

  factory PlaceSummary.fromJson(Map<String, dynamic> j) => PlaceSummary(
        id: j['id']?.toString(),
        googlePlaceId: j['google_place_id'] as String,
        name: j['name'] as String,
        formattedAddress: j['formatted_address'] as String?,
        latitude: (j['latitude'] as num).toDouble(),
        longitude: (j['longitude'] as num).toDouble(),
        googleTypes: (j['google_types'] as List? ?? []).cast<String>(),
        aggregateTrust: (j['aggregate_trust'] as num).toDouble(),
        publicCount: j['public_count'] as int,
        contributionCount: j['contribution_count'] as int,
        hasData: j['has_data'] as bool,
      );
}

class PlaceAutocomplete {
  final String googlePlaceId;
  final String description;
  final String mainText;
  final String? secondaryText;
  PlaceAutocomplete({
    required this.googlePlaceId,
    required this.description,
    required this.mainText,
    required this.secondaryText,
  });
  factory PlaceAutocomplete.fromJson(Map<String, dynamic> j) => PlaceAutocomplete(
        googlePlaceId: j['google_place_id'] as String,
        description: j['description'] as String,
        mainText: j['main_text'] as String,
        secondaryText: j['secondary_text'] as String?,
      );
}

class ContributionPin {
  final String id;
  final String? placeId;
  final double latitude;
  final double longitude;
  final double trustScore;
  final String visibilityStatus;
  final int rating;
  final String textNote;
  final String? imageUrl;

  ContributionPin({
    required this.id,
    required this.placeId,
    required this.latitude,
    required this.longitude,
    required this.trustScore,
    required this.visibilityStatus,
    required this.rating,
    required this.textNote,
    required this.imageUrl,
  });

  factory ContributionPin.fromJson(Map<String, dynamic> j) => ContributionPin(
        id: j['id'] as String,
        placeId: j['place_id']?.toString(),
        latitude: (j['latitude'] as num).toDouble(),
        longitude: (j['longitude'] as num).toDouble(),
        trustScore: (j['trust_score'] as num).toDouble(),
        visibilityStatus: j['visibility_status'] as String,
        rating: j['rating'] as int,
        textNote: j['text_note'] as String,
        imageUrl: j['image_url'] as String?,
      );
}

class PlaceDetail extends PlaceSummary {
  final List<ContributionPin> contributions;
  PlaceDetail({
    required super.id,
    required super.googlePlaceId,
    required super.name,
    required super.formattedAddress,
    required super.latitude,
    required super.longitude,
    required super.googleTypes,
    required super.aggregateTrust,
    required super.publicCount,
    required super.contributionCount,
    required super.hasData,
    required this.contributions,
  });

  factory PlaceDetail.fromJson(Map<String, dynamic> j) {
    final base = PlaceSummary.fromJson(j);
    return PlaceDetail(
      id: base.id,
      googlePlaceId: base.googlePlaceId,
      name: base.name,
      formattedAddress: base.formattedAddress,
      latitude: base.latitude,
      longitude: base.longitude,
      googleTypes: base.googleTypes,
      aggregateTrust: base.aggregateTrust,
      publicCount: base.publicCount,
      contributionCount: base.contributionCount,
      hasData: base.hasData,
      contributions: (j['contributions'] as List? ?? [])
          .map((c) => ContributionPin.fromJson(c as Map<String, dynamic>))
          .toList(),
    );
  }
}
```

Update `frontend/lib/models/verification_models.dart` to include
`placeId` + `placeName` (additive — old fields stay):

```dart
factory VerificationResponse.fromJson(Map<String, dynamic> json) {
  // ... existing parsing ...
  return VerificationResponse(
    id: json['id'] as String,
    placeId: json['place_id']?.toString(),
    placeName: json['place_name'] as String?,
    trustScore: (json['trust_score'] as num).toDouble(),
    visionScore: (json['vision_score'] as num).toDouble(),
    nlpScore: (json['nlp_score'] as num).toDouble(),
    visibilityStatus: json['visibility_status'] as String,
    detectedFeatures: detectedFeatures,
  );
}
```

(Add the two fields to the constructor and class members.)

### 7. Routing skeleton

Replace `frontend/lib/main.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'screens/map_screen.dart';
import 'screens/place_detail_screen.dart';
import 'screens/contribute_screen.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: NaviAbleApp()));
}

final _router = GoRouter(
  initialLocation: '/map',
  routes: [
    GoRoute(path: '/map', builder: (_, __) => const MapScreen()),
    GoRoute(
      path: '/place/:gid',
      builder: (_, st) => PlaceDetailScreen(googlePlaceId: st.pathParameters['gid']!),
    ),
    GoRoute(
      path: '/contribute',
      builder: (_, st) {
        final extra = st.extra as Map<String, dynamic>?;
        return ContributeScreen(
          presetGooglePlaceId: extra?['gid'] as String?,
          presetPlaceName: extra?['name'] as String?,
        );
      },
    ),
  ],
);

class NaviAbleApp extends StatelessWidget {
  const NaviAbleApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'NaviAble',
      debugShowCheckedModeBanner: false,
      theme: NaviAbleTheme.light,
      darkTheme: NaviAbleTheme.dark,
      routerConfig: _router,
    );
  }
}
```

Add **placeholder** screens so this compiles before phases 05–07:

`frontend/lib/screens/map_screen.dart`:
```dart
import 'package:flutter/material.dart';
class MapScreen extends StatelessWidget {
  const MapScreen({super.key});
  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: Text('MapScreen — phase 05')));
}
```

`frontend/lib/screens/place_detail_screen.dart`:
```dart
import 'package:flutter/material.dart';
class PlaceDetailScreen extends StatelessWidget {
  final String googlePlaceId;
  const PlaceDetailScreen({super.key, required this.googlePlaceId});
  @override
  Widget build(BuildContext context) =>
      Scaffold(body: Center(child: Text('Place: $googlePlaceId — phase 07')));
}
```

`frontend/lib/screens/contribute_screen.dart`:
```dart
import 'package:flutter/material.dart';
class ContributeScreen extends StatelessWidget {
  final String? presetGooglePlaceId;
  final String? presetPlaceName;
  const ContributeScreen({super.key, this.presetGooglePlaceId, this.presetPlaceName});
  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: Text('Contribute — phase 06')));
}
```

Add a dark theme stub in `frontend/lib/theme/app_theme.dart` if missing:

```dart
class NaviAbleTheme {
  static final ThemeData light = ThemeData(useMaterial3: true, brightness: Brightness.light);
  static final ThemeData dark  = ThemeData(useMaterial3: true, brightness: Brightness.dark);
}
class NaviAbleColors {
  static const Color primary    = Color(0xFF1565C0);
  static const Color accent     = Color(0xFF2E7D32);
  static const Color warning    = Color(0xFFF9A825);
  static const Color danger     = Color(0xFFC62828);
  static const Color textPrimary= Color(0xFF1A1A1A);
  static const Color textMuted  = Color(0xFF666666);
}
```

### 8. Riverpod provider for the API client

Create `frontend/lib/api/providers.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_client.dart';

final apiClientProvider = Provider<NaviAbleApiClient>((ref) => NaviAbleApiClient());
```

### 9. Update `run.sh` to allow `android` / `ios` device IDs

The existing `run.sh` already passes through any device ID. Just confirm
by running:

```bash
flutter devices
FLUTTER_DEVICE=<device_id_from_above> ./run.sh
```

For Android emulator targeting the host backend, use `API_BASE_URL=http://10.0.2.2:8000`.
For iOS Simulator, use `API_BASE_URL=http://localhost:8000` (Simulator shares the host network).
For a physical phone on Wi-Fi, use the Mac's LAN IP — `API_BASE_URL=http://192.168.x.y:8000`.

---

## Acceptance criteria

- [ ] `cd frontend && flutter pub get` succeeds with zero unresolved deps.
- [ ] `flutter run -d <android-emulator>` builds and shows the placeholder
      "MapScreen — phase 05" without runtime crash.
- [ ] `flutter run -d <ios-simulator>` likewise.
- [ ] `flutter build apk --debug` succeeds.
- [ ] `flutter build ios --no-codesign --debug` succeeds.
- [ ] On Android emulator with backend running, `curl http://10.0.2.2:8000/healthz`
      from the Dart side (via DioLogger) returns 200.
- [ ] All three placeholder routes (`/map`, `/place/:gid`, `/contribute`) navigate.

## Smoke commands

```bash
# Setup
cd frontend
flutter create --platforms=android,ios --org=ai.naviable .
flutter pub get

# Build verification
flutter build apk --debug
flutter build ios --no-codesign --debug

# Run on emulator (start one first via Android Studio)
FLUTTER_DEVICE=$(flutter devices --machine | jq -r '.[0].id') ./../run.sh

# From the running app, navigate to /map then /place/abc — both should render placeholders.
```

## Pitfalls

- The `--org=ai.naviable` choice fixes the bundle/package id forever. If
  you later try to change it, both Maps API key restrictions and
  push-notification certificates need updating.
- `google_maps_flutter` on Android requires `minSdkVersion >= 21`. Setting
  it lower at the top-level breaks the build silently — the error appears
  inside `google_maps_flutter_android`.
- iOS Simulator does NOT have a real GPS. Use a custom location: in Xcode
  → Debug → Simulate Location → "Custom Location…" or pick a city preset.
- `geolocator` on Android 13+ requires both `ACCESS_FINE_LOCATION` and the
  runtime permission flow. `permission_handler` handles the request; the
  manifest entry above declares it.
- Two separate Maps API keys are wise: one restricted to Android package +
  SHA-1, one restricted to iOS bundle id. Restrict APIs to "Maps SDK for
  Android" / "Maps SDK for iOS" only — these keys are visible in the app
  binary and shouldn't unlock Places API or Geocoding.
- The Android key in `local.properties` is git-ignored; the iOS key in
  `AppDelegate.swift` is NOT. Read it from a `.xcconfig` or env var if
  the repo is public.
