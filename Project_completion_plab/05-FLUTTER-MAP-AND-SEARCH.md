# Phase 05 — Flutter: Google Map screen with nearby places, search, and trust-tinted markers

**Status:** not started
**Depends on:** phase 04 (mobile bootstrap, API client, routing)
**Affects:** `frontend/lib/screens/map_screen.dart`, `frontend/lib/widgets/`, `frontend/lib/providers/`

## Goal

Replace the phase-04 placeholder `MapScreen` with the real one. A user
opens the app and sees:

- A full-screen Google Map centred on their current GPS (with a fallback
  default if permission is denied).
- Markers for every Google Place around them, **tinted by accessibility
  trust**: green = high (≥0.70), amber = caveat (0.40–0.69), grey = no
  data yet, red = explicitly low (≥1 PUBLIC review with trust < 0.40 — rare).
- A floating search bar that autocompletes Google Places.
- An "All / Only verified" toggle filter.
- Tap a marker → bottom sheet with name, trust score, "View details" button.
- A FAB to "Add review here" that pre-fills the contribute form with the
  most-recent map centre's resolved place.

---

## Deliverables

### 1. Provider for current location

Create `frontend/lib/providers/location_provider.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

class LocationFix {
  final double latitude;
  final double longitude;
  const LocationFix(this.latitude, this.longitude);
}

const LocationFix _defaultLocation = LocationFix(12.9716, 77.5946); // Bangalore

final currentLocationProvider = FutureProvider<LocationFix>((ref) async {
  final enabled = await Geolocator.isLocationServiceEnabled();
  if (!enabled) return _defaultLocation;

  var perm = await Geolocator.checkPermission();
  if (perm == LocationPermission.denied) {
    perm = await Geolocator.requestPermission();
  }
  if (perm == LocationPermission.deniedForever || perm == LocationPermission.denied) {
    return _defaultLocation;
  }
  try {
    final pos = await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
      timeLimit: const Duration(seconds: 10),
    );
    return LocationFix(pos.latitude, pos.longitude);
  } catch (_) {
    return _defaultLocation;
  }
});
```

### 2. Provider for nearby places (debounced)

Create `frontend/lib/providers/places_provider.dart`:

```dart
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/providers.dart';
import '../models/place_models.dart';

class NearbyQuery {
  final double lat;
  final double lon;
  final int radiusM;
  final String? keyword;
  const NearbyQuery({
    required this.lat,
    required this.lon,
    required this.radiusM,
    this.keyword,
  });

  @override
  bool operator ==(Object o) =>
      o is NearbyQuery &&
      o.lat == lat &&
      o.lon == lon &&
      o.radiusM == radiusM &&
      o.keyword == keyword;

  @override
  int get hashCode => Object.hash(lat, lon, radiusM, keyword);
}

final nearbyPlacesProvider =
    FutureProvider.family<List<PlaceSummary>, NearbyQuery>((ref, q) async {
  final api = ref.watch(apiClientProvider);
  return api.nearbyPlaces(
    latitude: q.lat,
    longitude: q.lon,
    radiusM: q.radiusM,
    keyword: q.keyword,
  );
});

final searchProvider =
    FutureProvider.family<List<PlaceAutocomplete>, String>((ref, query) async {
  if (query.trim().length < 2) return [];
  final api = ref.watch(apiClientProvider);
  return api.searchPlaces(query);
});
```

### 3. The map screen

Replace `frontend/lib/screens/map_screen.dart` entirely:

```dart
import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../models/place_models.dart';
import '../providers/location_provider.dart';
import '../providers/places_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/place_search_bar.dart';
import '../widgets/place_bottom_sheet.dart';

class MapScreen extends ConsumerStatefulWidget {
  const MapScreen({super.key});

  @override
  ConsumerState<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends ConsumerState<MapScreen> {
  GoogleMapController? _map;
  CameraPosition? _camera;
  Timer? _debounce;
  NearbyQuery? _activeQuery;
  bool _onlyVerified = false;
  String? _selectedGid;

  void _onCameraIdle() {
    if (_camera == null) return;
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      final q = NearbyQuery(
        lat: _camera!.target.latitude,
        lon: _camera!.target.longitude,
        radiusM: _radiusFromZoom(_camera!.zoom),
      );
      setState(() => _activeQuery = q);
    });
  }

  int _radiusFromZoom(double zoom) {
    // Approximate "half the visible diagonal in metres". Capped at backend max.
    final base = 40000 / math.pow(2, zoom - 11);
    return base.clamp(100, 10000).toInt();
  }

  Color _markerColorFor(PlaceSummary p) {
    if (!p.hasData) return Colors.grey;
    if (p.aggregateTrust >= 0.70) return Colors.green.shade700;
    if (p.aggregateTrust >= 0.40) return Colors.amber.shade700;
    return Colors.red.shade700;
  }

  BitmapDescriptor _markerHueFor(PlaceSummary p) {
    if (!p.hasData) return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueAzure);
    if (p.aggregateTrust >= 0.70) return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueGreen);
    if (p.aggregateTrust >= 0.40) return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueOrange);
    return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueRed);
  }

  @override
  Widget build(BuildContext context) {
    final locAsync = ref.watch(currentLocationProvider);
    final placesAsync = _activeQuery == null
        ? const AsyncValue<List<PlaceSummary>>.data([])
        : ref.watch(nearbyPlacesProvider(_activeQuery!));

    return Scaffold(
      extendBodyBehindAppBar: true,
      body: locAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _ErrorOverlay(message: 'Location error: $e'),
        data: (loc) {
          final initialCamera = CameraPosition(
            target: LatLng(loc.latitude, loc.longitude),
            zoom: 15,
          );

          final placesRaw = placesAsync.maybeWhen(
            data: (l) => l,
            orElse: () => const <PlaceSummary>[],
          );
          final filtered = _onlyVerified
              ? placesRaw.where((p) => p.hasData && p.aggregateTrust >= 0.70).toList()
              : placesRaw;

          final markers = filtered
              .map((p) => Marker(
                    markerId: MarkerId(p.googlePlaceId),
                    position: LatLng(p.latitude, p.longitude),
                    icon: _markerHueFor(p),
                    onTap: () => setState(() => _selectedGid = p.googlePlaceId),
                  ))
              .toSet();

          final selected = filtered
              .where((p) => p.googlePlaceId == _selectedGid)
              .cast<PlaceSummary?>()
              .firstWhere((_) => true, orElse: () => null);

          return Stack(
            children: [
              GoogleMap(
                initialCameraPosition: initialCamera,
                myLocationEnabled: true,
                myLocationButtonEnabled: false,
                markers: markers,
                onMapCreated: (c) {
                  _map = c;
                  _camera = initialCamera;
                  _onCameraIdle();
                },
                onCameraMove: (cp) => _camera = cp,
                onCameraIdle: _onCameraIdle,
                onTap: (_) => setState(() => _selectedGid = null),
              ),

              // Search bar
              SafeArea(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
                  child: PlaceSearchBar(
                    onPick: (gid) => context.push('/place/$gid'),
                  ),
                ),
              ),

              // Filter chip
              Positioned(
                top: 80, left: 12,
                child: SafeArea(
                  child: FilterChip(
                    label: Text(_onlyVerified ? 'Verified only' : 'All places'),
                    avatar: Icon(_onlyVerified ? Icons.verified : Icons.public, size: 18),
                    selected: _onlyVerified,
                    onSelected: (v) => setState(() => _onlyVerified = v),
                  ),
                ),
              ),

              // Loading shimmer
              if (placesAsync.isLoading && filtered.isEmpty)
                const Positioned(
                  top: 16, right: 16,
                  child: SizedBox(
                    width: 24, height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),

              // Recenter FAB
              Positioned(
                right: 12, bottom: 96,
                child: FloatingActionButton.small(
                  heroTag: 'recenter',
                  onPressed: () async {
                    final l = await ref.read(currentLocationProvider.future);
                    _map?.animateCamera(CameraUpdate.newLatLngZoom(
                      LatLng(l.latitude, l.longitude), 16,
                    ));
                  },
                  child: const Icon(Icons.my_location),
                ),
              ),

              // Add review FAB
              Positioned(
                right: 12, bottom: 24,
                child: FloatingActionButton.extended(
                  heroTag: 'add',
                  backgroundColor: NaviAbleColors.primary,
                  onPressed: () {
                    if (selected != null) {
                      context.push('/contribute', extra: {
                        'gid': selected.googlePlaceId,
                        'name': selected.name,
                      });
                    } else {
                      context.push('/contribute');
                    }
                  },
                  icon: const Icon(Icons.add_a_photo, color: Colors.white),
                  label: const Text('Add review',
                      style: TextStyle(color: Colors.white)),
                ),
              ),

              // Selected pin sheet
              if (selected != null)
                Positioned(
                  left: 0, right: 0, bottom: 0,
                  child: PlaceBottomSheet(
                    place: selected,
                    onClose: () => setState(() => _selectedGid = null),
                    onOpen: () => context.push('/place/${selected.googlePlaceId}'),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _ErrorOverlay extends StatelessWidget {
  final String message;
  const _ErrorOverlay({required this.message});
  @override
  Widget build(BuildContext context) =>
      Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(message)));
}
```

### 4. Search bar widget

Create `frontend/lib/widgets/place_search_bar.dart`:

```dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/place_models.dart';
import '../providers/places_provider.dart';

typedef OnPickPlace = void Function(String googlePlaceId);

class PlaceSearchBar extends ConsumerStatefulWidget {
  final OnPickPlace onPick;
  const PlaceSearchBar({super.key, required this.onPick});

  @override
  ConsumerState<PlaceSearchBar> createState() => _PlaceSearchBarState();
}

class _PlaceSearchBarState extends ConsumerState<PlaceSearchBar> {
  final _controller = TextEditingController();
  String _query = '';
  Timer? _debounce;

  void _onChanged(String s) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350),
        () => setState(() => _query = s));
  }

  @override
  void dispose() {
    _controller.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final results = _query.length < 2
        ? const AsyncValue<List<PlaceAutocomplete>>.data([])
        : ref.watch(searchProvider(_query));

    return Material(
      elevation: 4,
      borderRadius: BorderRadius.circular(12),
      child: Column(
        children: [
          TextField(
            controller: _controller,
            onChanged: _onChanged,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _query.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _controller.clear();
                        setState(() => _query = '');
                      }),
              hintText: 'Search a place by name or address',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
              filled: true,
              fillColor: Colors.white,
            ),
          ),
          results.maybeWhen(
            data: (list) => list.isEmpty
                ? const SizedBox.shrink()
                : ConstrainedBox(
                    constraints: const BoxConstraints(maxHeight: 240),
                    child: ListView.builder(
                      shrinkWrap: true,
                      itemCount: list.length,
                      itemBuilder: (_, i) {
                        final p = list[i];
                        return ListTile(
                          leading: const Icon(Icons.place_outlined),
                          title: Text(p.mainText, maxLines: 1, overflow: TextOverflow.ellipsis),
                          subtitle: p.secondaryText == null
                              ? null
                              : Text(p.secondaryText!,
                                  maxLines: 1, overflow: TextOverflow.ellipsis),
                          onTap: () {
                            FocusScope.of(context).unfocus();
                            widget.onPick(p.googlePlaceId);
                          },
                        );
                      },
                    ),
                  ),
            orElse: () => const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }
}
```

### 5. Bottom sheet for tapped marker

Create `frontend/lib/widgets/place_bottom_sheet.dart`:

```dart
import 'package:flutter/material.dart';

import '../models/place_models.dart';
import '../theme/app_theme.dart';

class PlaceBottomSheet extends StatelessWidget {
  final PlaceSummary place;
  final VoidCallback onClose;
  final VoidCallback onOpen;
  const PlaceBottomSheet({
    super.key,
    required this.place,
    required this.onClose,
    required this.onOpen,
  });

  Color get _color {
    if (!place.hasData) return Colors.grey.shade600;
    if (place.aggregateTrust >= 0.70) return NaviAbleColors.accent;
    if (place.aggregateTrust >= 0.40) return NaviAbleColors.warning;
    return NaviAbleColors.danger;
  }

  String get _trustLabel {
    if (!place.hasData) return 'No accessibility data yet';
    return 'Trust ${(place.aggregateTrust * 100).round()}%  '
           '· ${place.publicCount} verified review'
           '${place.publicCount == 1 ? "" : "s"}';
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      elevation: 8,
      color: Theme.of(context).colorScheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 36, height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade400,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  CircleAvatar(
                    backgroundColor: _color,
                    radius: 14,
                    child: Icon(
                      place.hasData ? Icons.accessible : Icons.help_outline,
                      color: Colors.white, size: 16,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      place.name,
                      style: Theme.of(context).textTheme.titleMedium,
                      maxLines: 2, overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  IconButton(icon: const Icon(Icons.close), onPressed: onClose),
                ],
              ),
              if (place.formattedAddress != null) ...[
                const SizedBox(height: 4),
                Text(place.formattedAddress!,
                    style: Theme.of(context).textTheme.bodySmall),
              ],
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: _color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(_trustLabel,
                    style: TextStyle(color: _color, fontWeight: FontWeight.w600)),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: onOpen,
                      icon: const Icon(Icons.read_more),
                      label: const Text('View details'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

---

## Acceptance criteria

- [ ] Launching the app on a phone shows a Google Map centred on the user's
      GPS location (or Bangalore if denied), with markers tinted by trust.
- [ ] Panning the map debounces and triggers exactly one API call per
      400 ms idle period (verifiable from `Dio` logs / charles).
- [ ] Toggling "Verified only" hides grey + amber + red markers in real time.
- [ ] Typing into the search bar after 350 ms debounce shows autocomplete
      results from `/places/search`. Tapping one navigates to `/place/<gid>`.
- [ ] Tapping a marker raises the bottom sheet with name, address, trust
      label, and "View details". Tapping outside the sheet dismisses it.
- [ ] Tapping the FAB with a pin selected pre-fills the contribute form
      (verify by inspecting the `extra` map at `/contribute`).
- [ ] No `bool isLoading` state; everything routes through `AsyncValue`.

## Smoke commands

```bash
# Backend up with a real Google Places key
GOOGLE_PLACES_API_KEY=YOUR_KEY ./run.sh -b

# Run the mobile app
cd frontend
flutter run -d <android-emulator-id> --dart-define=API_BASE_URL=http://10.0.2.2:8000

# In the app:
# 1) Confirm map renders (if not, MAPS_API_KEY in local.properties is wrong)
# 2) Pan to Bangalore MG Road area; pins should appear within ~1s
# 3) Search "Phoenix Marketcity Bangalore" — should navigate to placeholder detail
# 4) Tap a pin → bottom sheet → "View details" → placeholder
```

## Pitfalls

- **A blank map** almost always means a bad Maps SDK key. Check
  `adb logcat | grep -i "Authorization failure"` on Android.
- **No markers but search works**: the Maps SDK key is fine, but the
  server-side Places key isn't. Hit `/api/v1/places/nearby?...` from curl
  to confirm.
- `Marker.icon` with `BitmapDescriptor.defaultMarkerWithHue` is *async-load
  free*, ideal for a first cut. To replace with custom Flutter-rendered
  pins later, use `BitmapDescriptor.fromBytes(await widgetToImage(...))`.
- **Camera-idle storms**: every momentary pause fires `onCameraIdle`. The
  400 ms debounce is what stops spam — do not remove it.
- **Permissions on iOS**: if the location prompt never appears, check
  `Info.plist` has both `NSLocationWhenInUseUsageDescription` *and*
  the always-and-when-in-use key.
- **Marker clustering** is omitted in MVP. With > 100 pins, swap to the
  `google_maps_cluster_manager` plugin; the API surface is the same.
