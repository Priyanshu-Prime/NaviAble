import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/providers.dart';
import '../models/place_models.dart';

final searchProvider = FutureProvider.family<List<PlaceAutocomplete>, String>(
  (ref, query) async {
    if (query.trim().isEmpty) return [];
    final api = ref.watch(apiClientProvider);
    return api.searchPlaces(query: query);
  },
);
