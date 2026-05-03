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
