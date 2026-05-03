import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/providers.dart';
import '../models/verification_models.dart';

enum LocationSource { exif, device, place, address }

class ContributeForm {
  final Uint8List? imageBytes;
  final String imageFilename;
  final double? exifLatitude;
  final double? exifLongitude;
  final double? deviceLatitude;
  final double? deviceLongitude;
  final String? googlePlaceId;
  final String? googlePlaceName;
  final String? typedAddress;
  final String review;
  final int? rating;

  const ContributeForm({
    this.imageBytes,
    this.imageFilename = 'photo.jpg',
    this.exifLatitude,
    this.exifLongitude,
    this.deviceLatitude,
    this.deviceLongitude,
    this.googlePlaceId,
    this.googlePlaceName,
    this.typedAddress,
    this.review = '',
    this.rating,
  });

  /// Which location signal is in effect (priority: place > device > exif > address).
  LocationSource? get source {
    if (googlePlaceId != null) return LocationSource.place;
    if (deviceLatitude != null && deviceLongitude != null) return LocationSource.device;
    if (exifLatitude != null && exifLongitude != null) return LocationSource.exif;
    if (typedAddress != null && typedAddress!.trim().isNotEmpty) return LocationSource.address;
    return null;
  }

  bool get isReady =>
      imageBytes != null &&
      review.trim().isNotEmpty &&
      rating != null &&
      source != null;

  ContributeForm copyWith({
    Uint8List? imageBytes,
    String? imageFilename,
    double? exifLatitude,
    double? exifLongitude,
    double? deviceLatitude,
    double? deviceLongitude,
    String? googlePlaceId,
    String? googlePlaceName,
    String? typedAddress,
    String? review,
    int? rating,
    bool clearPlace = false,
    bool clearDevice = false,
    bool clearExif = false,
    bool clearAddress = false,
  }) {
    return ContributeForm(
      imageBytes: imageBytes ?? this.imageBytes,
      imageFilename: imageFilename ?? this.imageFilename,
      exifLatitude: clearExif ? null : (exifLatitude ?? this.exifLatitude),
      exifLongitude: clearExif ? null : (exifLongitude ?? this.exifLongitude),
      deviceLatitude: clearDevice ? null : (deviceLatitude ?? this.deviceLatitude),
      deviceLongitude: clearDevice ? null : (deviceLongitude ?? this.deviceLongitude),
      googlePlaceId: clearPlace ? null : (googlePlaceId ?? this.googlePlaceId),
      googlePlaceName: clearPlace ? null : (googlePlaceName ?? this.googlePlaceName),
      typedAddress: clearAddress ? null : (typedAddress ?? this.typedAddress),
      review: review ?? this.review,
      rating: rating ?? this.rating,
    );
  }
}

class ContributeNotifier extends Notifier<ContributeForm> {
  @override
  ContributeForm build() => const ContributeForm();

  void setImage(Uint8List bytes, String name) =>
      state = state.copyWith(imageBytes: bytes, imageFilename: name);
  void setExifGps(double lat, double lon) =>
      state = state.copyWith(exifLatitude: lat, exifLongitude: lon);
  void clearExifGps() => state = state.copyWith(clearExif: true);
  void setDeviceGps(double lat, double lon) =>
      state = state.copyWith(deviceLatitude: lat, deviceLongitude: lon);
  void clearDeviceGps() => state = state.copyWith(clearDevice: true);
  void pickPlace(String gid, String name) =>
      state = state.copyWith(googlePlaceId: gid, googlePlaceName: name);
  void clearPlace() => state = state.copyWith(clearPlace: true);
  void setAddress(String s) => state = state.copyWith(typedAddress: s);
  void clearAddress() => state = state.copyWith(clearAddress: true);
  void setReview(String s) => state = state.copyWith(review: s);
  void setRating(int r) => state = state.copyWith(rating: r);
  void resetForm() => state = const ContributeForm();
}

final contributeProvider =
    NotifierProvider<ContributeNotifier, ContributeForm>(ContributeNotifier.new);

final submissionProvider =
    StateNotifierProvider<SubmissionNotifier, AsyncValue<VerificationResponse?>>(
  (ref) => SubmissionNotifier(ref),
);

class SubmissionNotifier extends StateNotifier<AsyncValue<VerificationResponse?>> {
  final Ref _ref;
  SubmissionNotifier(this._ref) : super(const AsyncData(null));

  Future<void> submit() async {
    final form = _ref.read(contributeProvider);
    if (!form.isReady) return;
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final api = _ref.read(apiClientProvider);
      // Priority: place > device > exif > address
      double? lat, lon;
      String? addr;
      String? gid;
      switch (form.source!) {
        case LocationSource.place:
          gid = form.googlePlaceId;
          break;
        case LocationSource.device:
          lat = form.deviceLatitude;
          lon = form.deviceLongitude;
          break;
        case LocationSource.exif:
          lat = form.exifLatitude;
          lon = form.exifLongitude;
          break;
        case LocationSource.address:
          addr = form.typedAddress;
          break;
      }
      return api.verify(
        imageBytes: form.imageBytes!,
        imageFilename: form.imageFilename,
        review: form.review.trim(),
        rating: form.rating!,
        googlePlaceId: gid,
        latitude: lat,
        longitude: lon,
        address: addr,
      );
    });
  }

  void reset() {
    _ref.read(contributeProvider.notifier).resetForm();
    state = const AsyncData(null);
  }
}
