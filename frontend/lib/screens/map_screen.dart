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
