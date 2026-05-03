import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

/// Singleton provider for the NaviAble API client.
///
/// Usage:
/// ```dart
/// final client = ref.watch(apiClientProvider);
/// final places = await client.nearbyPlaces(latitude: 37.7749, longitude: -122.4194);
/// ```
final apiClientProvider = Provider<NaviAbleApiClient>((ref) => NaviAbleApiClient());
