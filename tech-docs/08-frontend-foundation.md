# Phase 08 — Frontend Foundation (Flutter Web)

## Goal

Set up the Flutter Web project so subsequent feature phases (contribution
flow in 09, map in 10) drop into a known structure with a working state
layer, HTTP client, theme, and a baseline of WCAG 2.1 AA compliance. The
report is explicit on this last point: *"It would have been embarrassing
to build an accessibility platform that itself failed an accessibility
audit, and the team treated this as a hard requirement from the first
sprint rather than as a polish item."* This phase establishes that
baseline.

## Prerequisites

- Flutter 3.19+ stable channel.
- Backend's `/healthz` reachable from the dev environment (phase 02).

## Current state

`frontend/` already exists with `lib/{api,models,providers,screens,theme,widgets}/`
plus `pubspec.yaml`. Treat this layout as authoritative; do not introduce
parallel structures (`lib/services/`, `lib/state/`, etc.).

## Deliverables

### 1. Dependencies

Pin in `pubspec.yaml`:

| Package                   | Why                                            |
|---------------------------|------------------------------------------------|
| `flutter_riverpod`        | State management with `AsyncValue`             |
| `riverpod_annotation`     | Code generation for cleaner provider definitions |
| `dio`                     | HTTP client with interceptors                  |
| `freezed`                 | Sealed/data classes for models                 |
| `json_serializable`       | Model serialisation                            |
| `flutter_map`             | OpenStreetMap renderer (chosen over Google for licensing) |
| `latlong2`                | Geographic primitives                          |
| `geolocator`              | Browser geolocation                            |
| `image_picker`            | Photo capture / file picker on web             |
| `accessibility_tools`     | Dev-time WCAG checker (debug mode only)        |

Avoid `http` (the spec mandates Dio). Avoid `provider` (we use Riverpod;
mixing them confuses the next maintainer).

### 2. App entry & routing

`lib/main.dart`:

```dart
void main() {
  runApp(const ProviderScope(child: NaviAbleApp()));
}

class NaviAbleApp extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = ref.watch(themeProvider);
    return MaterialApp(
      title: 'NaviAble',
      theme: theme,
      onGenerateRoute: AppRouter.onGenerateRoute,
      debugShowCheckedModeBanner: false,
    );
  }
}
```

Two top-level routes for MVP: `/` (map view, phase 10) and `/contribute`
(contribution form, phase 09). Wire a `NavigationBar` (Material 3) at
the bottom — large hit targets are an accessibility requirement, not a
visual choice.

### 3. Dio client + interceptors

`lib/api/api_client.dart`:

```dart
final apiClientProvider = Provider<Dio>((ref) {
  final dio = Dio(BaseOptions(
    baseUrl: const String.fromEnvironment('API_BASE_URL',
        defaultValue: 'http://localhost:8000'),
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 30),  // model inference can take a few seconds
  ));
  dio.interceptors.add(_RequestIdInterceptor());
  dio.interceptors.add(_AuthInterceptor(ref));    // no-op until auth lands
  dio.interceptors.add(_LoggingInterceptor());
  return dio;
});
```

Two of these interceptors come from the spec directly:

- **Request-correlation interceptor**: attaches a fresh UUID `X-Request-ID`
  on every outbound request. The backend (phase 02) echoes this back; in
  the browser console, the same ID appears in both client logs and
  server logs. Debugging across the stack collapses from minutes to
  seconds.
- **Auth interceptor**: a placeholder slot that injects an auth token
  uniformly when authentication is added later. Keeping it in the chain
  now means feature code never has to touch headers when auth lands.

### 4. State layer with Riverpod & `AsyncValue`

The spec is explicit: use `AsyncValue` for the upload flow, no
ad-hoc `bool isLoading` flags. The pattern for any async-fetching
provider:

```dart
@riverpod
Future<List<ContributionPin>> nearbyContributions(
  NearbyContributionsRef ref,
  ({double lat, double lon, double radiusM}) query,
) async {
  final api = ref.watch(apiClientProvider);
  final res = await api.get('/api/v1/contributions/nearby', queryParameters: {
    'latitude': query.lat, 'longitude': query.lon, 'radius_m': query.radiusM,
  });
  return (res.data['items'] as List).map(ContributionPin.fromJson).toList();
}
```

In widgets:

```dart
ref.watch(nearbyContributionsProvider(query)).when(
  data: (pins) => MapWithPins(pins),
  loading: () => const _MapSkeleton(),
  error: (e, _) => _MapErrorBanner(error: e, onRetry: () => ref.invalidate(...)),
);
```

This pattern repeats in phases 09 and 10. Any boolean `isLoading` field
that creeps in is a bug.

### 5. Models

`lib/models/` holds the API shapes mirroring the backend's Pydantic
schemas, generated via `freezed` + `json_serializable`:

- `ContributionPin` (mirrors phase 02's `ContributionPin`)
- `ContributionResponse`
- `NearbyResponse`
- `FeatureDetection`
- `VisibilityStatus` enum: `public`, `caveat`, `hidden`

Run `dart run build_runner build` and commit the generated `.g.dart` and
`.freezed.dart` files alongside source.

### 6. Theme & accessibility baseline

`lib/theme/app_theme.dart`:

- Use `ColorScheme.fromSeed(seedColor: ..., brightness: ...)` for both
  light and dark themes. Do not hand-pick palette colours — the M3
  scheme generator already targets WCAG AA contrast ratios.
- Set `textTheme` from `Typography.material2021` and apply
  `MediaQuery.textScalerOf(context)` everywhere so user font-size
  preferences propagate. **Do not** clamp text scaling to a maximum;
  that breaks the system-text-size contract that vision-impaired users
  rely on.
- `MaterialApp.theme` exposes a `highContrastTheme` and
  `highContrastDarkTheme`. Provide both — the OS toggle for
  high-contrast mode should just work.

### 7. WCAG 2.1 AA checklist for components

Every shared widget under `lib/widgets/` must:

- Have a `Semantics(label: ..., hint: ...)` wrapper if it is interactive
  but not a stock `Button`/`TextField`.
- Use a hit target of at least 48x48 logical pixels (Material guideline,
  meets WCAG 2.5.5).
- Reach 4.5:1 contrast against its background in both themes (verified
  via the `accessibility_tools` overlay in debug builds).
- Be keyboard-navigable. Tab order should make sense; nothing reachable
  only by mouse.

The `accessibility_tools` package, mounted around the root widget in
debug mode only, surfaces violations in real time during development.

### 8. Connectivity check

Add a tiny `serverHealthProvider` that pings `/healthz` once at startup.
On failure, show a small banner ("Cannot reach NaviAble server — please
check your connection") rather than letting individual features fail in
isolation. This is the kind of universal feedback that screen-reader
users especially benefit from.

## Acceptance criteria

- [ ] `flutter run -d chrome` boots the app to a placeholder home
      screen with no console errors.
- [ ] `accessibility_tools` overlay is empty (no violations) on the
      home screen.
- [ ] Tabbing through the home screen reaches every interactive element
      in a sensible order.
- [ ] Setting the OS to "Larger Text" (or zooming the browser to 200%)
      grows fonts without clipping.
- [ ] Setting the OS to "High Contrast" / "Increased Contrast" switches
      to the high-contrast theme.
- [ ] A request issued through `apiClientProvider` has an `X-Request-ID`
      header, and the same ID appears in the backend's structured logs.
- [ ] Test: pulling the WiFi cable surfaces the global
      "cannot reach server" banner rather than a low-level Dio error
      bubbling up to the UI.

## Pitfalls / notes

- **Flutter Web ≠ Flutter Mobile.** `image_picker` on web returns
  `XFile` with a virtual path; uploading to Dio means converting via
  `MultipartFile.fromBytes(await xfile.readAsBytes(), filename: ...)`.
  Phase 09 walks through this.
- **`flutter_map` vs Google Maps:** `flutter_map` was chosen to avoid
  Google Maps API keys and the licensing surface on a student project.
  Phase 10 uses it. If a future investor demands Google tiles, swap
  the renderer in one file.
- **Don't ship `accessibility_tools` to release.** It runs only in
  debug. Verify with `flutter build web --release` that it is absent
  from the bundle.
- **Generated code is committed.** This is contentious in some teams,
  but it makes onboarding on Flutter Web much less painful than relying
  on every machine to build_runner cleanly.
