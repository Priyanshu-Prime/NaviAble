import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';

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
  late MapController _mapController;
  LatLng? _currentCenter;
  Timer? _debounce;
  NearbyQuery? _activeQuery;
  bool _onlyVerified = false;
  bool _onlyReviewed = false;
  bool _showSearchBar = true;
  String? _selectedGid;
  double _currentZoom = 12;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
  }

  @override
  void dispose() {
    _mapController.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onMapMoved() {
    if (_mapController.camera.center == null) return;
    _currentCenter = _mapController.camera.center;
    _currentZoom = _mapController.camera.zoom;
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      final center = _mapController.camera.center;
      final zoom = _mapController.camera.zoom;
      final q = NearbyQuery(
        lat: center.latitude,
        lon: center.longitude,
        radiusM: _radiusFromZoom(zoom),
      );
      setState(() => _activeQuery = q);
    });
  }

  int _radiusFromZoom(double zoom) {
    final base = 40000 / math.pow(2, zoom - 11);
    return base.clamp(100, 10000).toInt();
  }

  Color _markerColorFor(PlaceSummary p) {
    if (!p.hasData) return Colors.blue;
    if (p.aggregateTrust >= 0.70) return Colors.green;
    if (p.aggregateTrust >= 0.40) return Colors.orange;
    return Colors.red;
  }

  @override
  Widget build(BuildContext context) {
    final locAsync = ref.watch(currentLocationProvider);
    final placesAsync = _activeQuery == null
        ? const AsyncValue<List<PlaceSummary>>.data([])
        : _onlyReviewed
            ? ref.watch(reviewedNearbyProvider(_activeQuery!))
            : ref.watch(nearbyPlacesProvider(_activeQuery!));

    return Scaffold(
      extendBodyBehindAppBar: true,
      body: locAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _ErrorOverlay(message: 'Location error: $e'),
        data: (loc) {
          final placesRaw = placesAsync.maybeWhen(
            data: (l) => l,
            orElse: () => const <PlaceSummary>[],
          );
          final filtered = _onlyVerified
              ? placesRaw.where((p) => p.hasData && p.aggregateTrust >= 0.70).toList()
              : placesRaw;

          final markers = filtered
              .map((p) => Marker(
                    point: LatLng(p.latitude, p.longitude),
                    width: 40,
                    height: 40,
                    child: GestureDetector(
                      onTap: () => setState(() => _selectedGid = p.googlePlaceId),
                      child: Icon(
                        Icons.location_on,
                        color: _markerColorFor(p),
                        size: 40,
                      ),
                    ),
                  ))
              .toList();

          final selected = filtered
              .where((p) => p.googlePlaceId == _selectedGid)
              .cast<PlaceSummary?>()
              .firstWhere((_) => true, orElse: () => null);

          return Stack(
            children: [
              FlutterMap(
                mapController: _mapController,
                options: MapOptions(
                  initialCenter: LatLng(loc.latitude, loc.longitude),
                  initialZoom: 12,
                ),
                children: [
                  TileLayer(
                    urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    userAgentPackageName: 'ai.naviable',
                  ),
                  MarkerLayer(markers: markers),
                ],
              ),

              // Search bar (collapsible)
              if (_showSearchBar)
                SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
                    child: Stack(
                      children: [
                        PlaceSearchBar(
                          onPick: (gid) => context.push('/place/$gid'),
                        ),
                        Positioned(
                          right: 8,
                          top: 8,
                          child: CircleAvatar(
                            radius: 16,
                            backgroundColor: Colors.grey.shade800,
                            child: IconButton(
                              icon: const Icon(Icons.close, size: 18, color: Colors.white),
                              onPressed: () => setState(() => _showSearchBar = false),
                              padding: EdgeInsets.zero,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              else
                // Search toggle button
                SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
                    child: FloatingActionButton.small(
                      heroTag: 'search_toggle',
                      backgroundColor: NaviAbleColors.primary,
                      onPressed: () => setState(() => _showSearchBar = true),
                      child: const Icon(Icons.search),
                    ),
                  ),
                ),

              // Filter chips
              Positioned(
                top: 80,
                left: 12,
                child: SafeArea(
                  child: Row(
                    children: [
                      FilterChip(
                        label: Text(_onlyVerified ? 'Verified only' : 'All places'),
                        avatar: Icon(_onlyVerified ? Icons.verified : Icons.public, size: 18),
                        selected: _onlyVerified,
                        onSelected: (v) => setState(() => _onlyVerified = v),
                      ),
                      const SizedBox(width: 8),
                      FilterChip(
                        label: Text(_onlyReviewed ? 'Reviewed (${_activeQuery?.radiusM ?? 0}m)' : 'All'),
                        avatar: Icon(_onlyReviewed ? Icons.rate_review : Icons.map, size: 18),
                        selected: _onlyReviewed,
                        onSelected: (v) => setState(() => _onlyReviewed = v),
                      ),
                    ],
                  ),
                ),
              ),

              // Loading indicator
              if (placesAsync.isLoading && filtered.isEmpty)
                const Positioned(
                  top: 16,
                  right: 16,
                  child: SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),

              // Recenter FAB
              Positioned(
                right: 12,
                bottom: 96,
                child: FloatingActionButton.small(
                  heroTag: 'recenter',
                  onPressed: () async {
                    final l = await ref.read(currentLocationProvider.future);
                    _mapController.move(LatLng(l.latitude, l.longitude), 14);
                  },
                  child: const Icon(Icons.my_location),
                ),
              ),

              // Add review FAB
              Positioned(
                right: 12,
                bottom: 24,
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
                  label: const Text('Add review', style: TextStyle(color: Colors.white)),
                ),
              ),

              // Selected pin sheet
              if (selected != null)
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 0,
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
