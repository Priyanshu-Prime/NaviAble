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
import '../providers/place_detail_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/place_search_bar.dart';

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
  bool _onlyReviewed = false;
  bool _showSearchBar = true;
  double _currentZoom = 12;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
    _mapController.mapEventStream.listen((event) {
      _onMapMoved();
    });
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

  void _centerOnPlace(String gid, LatLng position) {
    _mapController.move(position, 14);
    setState(() {
      _activeQuery = NearbyQuery(
        lat: position.latitude,
        lon: position.longitude,
        radiusM: _radiusFromZoom(14),
      );
    });
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
          // Initialize query if not yet set
          if (_activeQuery == null && _currentCenter == null) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              setState(() {
                _currentCenter = LatLng(loc.latitude, loc.longitude);
                _activeQuery = NearbyQuery(
                  lat: loc.latitude,
                  lon: loc.longitude,
                  radiusM: _radiusFromZoom(_currentZoom),
                );
              });
            });
          }

          final placesRaw = placesAsync.maybeWhen(
            data: (l) => l,
            orElse: () => const <PlaceSummary>[],
          );

          final markers = placesRaw
              .map((p) => Marker(
                    point: LatLng(p.latitude, p.longitude),
                    width: 40,
                    height: 40,
                    child: GestureDetector(
                      onTap: () => context.push('/place/${p.googlePlaceId}'),
                      child: Icon(
                        Icons.location_on,
                        color: _markerColorFor(p),
                        size: 40,
                      ),
                    ),
                  ))
              .toList();

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
                  if (_activeQuery != null)
                    CircleLayer(
                      circles: [
                        CircleMarker(
                          point: LatLng(_activeQuery!.lat, _activeQuery!.lon),
                          radius: _activeQuery!.radiusM.toDouble(),
                          useRadiusInMeter: true,
                          color: Colors.blue.withOpacity(0.08),
                          borderColor: Colors.blue.withOpacity(0.5),
                          borderStrokeWidth: 2,
                        ),
                      ],
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
                          onPick: (gid, position) async {
                            FocusScope.of(context).unfocus();
                            if (position != null) {
                              _centerOnPlace(gid, position);
                            } else {
                              try {
                                final detail = await ref.read(placeDetailProvider(gid).future);
                                if (mounted) {
                                  _centerOnPlace(gid, LatLng(detail.latitude, detail.longitude));
                                }
                              } catch (_) {
                                if (mounted) context.push('/place/$gid');
                              }
                            }
                          },
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
                  child: FilterChip(
                    label: Text(_onlyReviewed ? 'Reviewed (${_activeQuery?.radiusM ?? 0}m)' : 'All'),
                    avatar: Icon(_onlyReviewed ? Icons.rate_review : Icons.map, size: 18),
                    selected: _onlyReviewed,
                    onSelected: (v) => setState(() => _onlyReviewed = v),
                  ),
                ),
              ),

              // Loading indicator
              if (placesAsync.isLoading && placesRaw.isEmpty)
                const Positioned(
                  top: 16,
                  right: 16,
                  child: SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),

              // Zoom buttons
              Positioned(
                right: 12,
                top: 80,
                child: Column(
                  children: [
                    FloatingActionButton.small(
                      heroTag: 'zoom_in',
                      onPressed: () {
                        _mapController.move(
                          _mapController.camera.center,
                          _mapController.camera.zoom + 1,
                        );
                      },
                      child: const Icon(Icons.add),
                    ),
                    const SizedBox(height: 8),
                    FloatingActionButton.small(
                      heroTag: 'zoom_out',
                      onPressed: () {
                        _mapController.move(
                          _mapController.camera.center,
                          _mapController.camera.zoom - 1,
                        );
                      },
                      child: const Icon(Icons.remove),
                    ),
                  ],
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
                  onPressed: () => context.push('/contribute'),
                  icon: const Icon(Icons.add_a_photo, color: Colors.white),
                  label: const Text('Add review', style: TextStyle(color: Colors.white)),
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
