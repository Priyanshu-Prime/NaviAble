import 'package:flutter_riverpod/flutter_riverpod.dart';

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

final searchProvider = FutureProvider.family<List<PlaceAutocomplete>, String>(
  (ref, query) async {
    if (query.trim().length < 2) return [];
    final api = ref.watch(apiClientProvider);
    return api.searchPlaces(query: query);
  },
);
