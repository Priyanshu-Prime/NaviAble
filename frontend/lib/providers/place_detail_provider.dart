import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/providers.dart';
import '../models/place_models.dart';

final placeDetailProvider =
    FutureProvider.family<PlaceDetail, String>((ref, googlePlaceId) async {
  final api = ref.watch(apiClientProvider);
  return api.placeDetail(googlePlaceId);
});
