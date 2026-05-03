# Phase 06 — Flutter: contribute flow (camera → EXIF → place autocomplete → submit → trust card)

**Status:** not started
**Depends on:** phase 04 (api client, models), phase 05 (map provides place pre-fill)
**Affects:** `frontend/lib/screens/contribute_screen.dart`, `frontend/lib/providers/contribute_provider.dart`, `frontend/lib/widgets/`

## Goal

Build the screen the user lands on after tapping "Add review". The flow:

1. Pick a photo (camera or gallery).
2. Try to extract EXIF GPS client-side. If found, show "📍 Detected from
   photo: <reverse-geocoded place>". If absent, show three buttons:
   "Use my current location", "Pick a place", "Type an address".
3. Write a review (multi-line, 1–2000 chars).
4. Pick a 1–5 star rating with proper a11y semantics.
5. Submit → multi-second loading → trust score result card with vision +
   NLP breakdown and detected features.

The screen is reusable: phase 05 navigates here with `extra: { gid, name }`
to pre-select a place.

---

## Deliverables

### 1. State + provider

Create `frontend/lib/providers/contribute_provider.dart`:

```dart
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
```

### 2. Star rating widget (a11y-correct)

Create `frontend/lib/widgets/star_rating.dart`:

```dart
import 'package:flutter/material.dart';

class StarRating extends StatelessWidget {
  final int? value;
  final ValueChanged<int> onChanged;
  const StarRating({super.key, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Rating',
      value: value == null ? 'unset' : '$value of 5 stars',
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(5, (i) {
          final filled = (value ?? 0) > i;
          return Semantics(
            inMutuallyExclusiveGroup: true,
            selected: value == i + 1,
            button: true,
            label: '${i + 1} of 5 stars',
            child: IconButton(
              icon: Icon(filled ? Icons.star : Icons.star_border, size: 32),
              color: filled ? Colors.amber.shade700 : Colors.grey.shade400,
              onPressed: () => onChanged(i + 1),
            ),
          );
        }),
      ),
    );
  }
}
```

### 3. Image picker + EXIF reader helper

Create `frontend/lib/services/image_pick.dart`:

```dart
import 'dart:typed_data';

import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:image_picker/image_picker.dart';
import 'package:native_exif/native_exif.dart';

class PickedPhoto {
  final Uint8List bytes;
  final String filename;
  final double? latitude;
  final double? longitude;
  const PickedPhoto({
    required this.bytes,
    required this.filename,
    this.latitude,
    this.longitude,
  });
}

class ImagePickService {
  final _picker = ImagePicker();

  Future<PickedPhoto?> pick({required ImageSource source}) async {
    final XFile? x = await _picker.pickImage(
      source: source,
      imageQuality: 90,
      maxWidth: 1920,
    );
    if (x == null) return null;

    double? lat, lon;
    try {
      final exif = await Exif.fromPath(x.path);
      final attrs = await exif.getLatLong();
      lat = attrs?.latitude;
      lon = attrs?.longitude;
      await exif.close();
    } catch (_) {/* not all platforms expose EXIF */}

    final bytes = await x.readAsBytes();
    final compressed = await FlutterImageCompress.compressWithList(
      bytes, quality: 85, minWidth: 1280, minHeight: 1280, format: CompressFormat.jpeg,
    );

    return PickedPhoto(
      bytes: compressed,
      filename: x.name,
      latitude: lat,
      longitude: lon,
    );
  }
}
```

### 4. The contribute screen

Replace `frontend/lib/screens/contribute_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../models/verification_models.dart';
import '../providers/contribute_provider.dart';
import '../services/image_pick.dart';
import '../theme/app_theme.dart';
import '../widgets/star_rating.dart';
import '../widgets/place_search_bar.dart';

class ContributeScreen extends ConsumerStatefulWidget {
  final String? presetGooglePlaceId;
  final String? presetPlaceName;

  const ContributeScreen({
    super.key,
    this.presetGooglePlaceId,
    this.presetPlaceName,
  });

  @override
  ConsumerState<ContributeScreen> createState() => _ContributeScreenState();
}

class _ContributeScreenState extends ConsumerState<ContributeScreen> {
  final _imageSvc = ImagePickService();
  final _addressCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    if (widget.presetGooglePlaceId != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(contributeProvider.notifier).pickPlace(
              widget.presetGooglePlaceId!,
              widget.presetPlaceName ?? 'Selected place',
            );
      });
    }
  }

  Future<void> _pick(ImageSource source) async {
    final picked = await _imageSvc.pick(source: source);
    if (picked == null) return;
    ref.read(contributeProvider.notifier).setImage(picked.bytes, picked.filename);
    if (picked.latitude != null && picked.longitude != null) {
      ref.read(contributeProvider.notifier)
          .setExifGps(picked.latitude!, picked.longitude!);
    } else {
      ref.read(contributeProvider.notifier).clearExifGps();
    }
  }

  Future<void> _useDeviceLocation() async {
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      perm = await Geolocator.requestPermission();
    }
    if (perm == LocationPermission.deniedForever || perm == LocationPermission.denied) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Location permission denied')),
        );
      }
      return;
    }
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 10),
      );
      ref.read(contributeProvider.notifier).setDeviceGps(pos.latitude, pos.longitude);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not get location: $e')),
        );
      }
    }
  }

  @override
  void dispose() {
    _addressCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final form = ref.watch(contributeProvider);
    final submission = ref.watch(submissionProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Add accessibility review'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.pop(),
        ),
      ),
      body: submission.when(
        data: (resp) {
          if (resp == null) return _buildForm(form);
          return _ResultCard(response: resp);
        },
        loading: () => const _SubmittingPanel(),
        error: (e, _) => _ErrorPanel(
          message: '$e',
          onRetry: () => ref.read(submissionProvider.notifier).submit(),
        ),
      ),
    );
  }

  Widget _buildForm(ContributeForm form) {
    final canSubmit = form.isReady;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _photoBlock(form),
          const SizedBox(height: 16),
          _locationBlock(form),
          const SizedBox(height: 16),
          _reviewBlock(form),
          const SizedBox(height: 16),
          _ratingBlock(form),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: canSubmit
                ? () => ref.read(submissionProvider.notifier).submit()
                : null,
            icon: const Icon(Icons.check_circle),
            label: const Text('Submit for AI verification'),
            style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(52),
              backgroundColor: NaviAbleColors.primary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _photoBlock(ContributeForm form) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('1. Photo', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            if (form.imageBytes != null)
              AspectRatio(
                aspectRatio: 1,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.memory(form.imageBytes!, fit: BoxFit.cover),
                ),
              )
            else
              Container(
                height: 180,
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.grey.shade300, style: BorderStyle.solid),
                ),
                child: const Center(child: Icon(Icons.image_outlined, size: 48, color: Colors.grey)),
              ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _pick(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('Camera'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _pick(ImageSource.gallery),
                    icon: const Icon(Icons.photo_library),
                    label: const Text('Gallery'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _locationBlock(ContributeForm form) {
    final src = form.source;
    String label;
    Color color;
    switch (src) {
      case LocationSource.place:
        label = 'Place: ${form.googlePlaceName ?? 'selected'}';
        color = NaviAbleColors.accent;
        break;
      case LocationSource.device:
        label = 'Device GPS: '
            '${form.deviceLatitude!.toStringAsFixed(5)}, '
            '${form.deviceLongitude!.toStringAsFixed(5)}';
        color = NaviAbleColors.accent;
        break;
      case LocationSource.exif:
        label = 'From photo EXIF: '
            '${form.exifLatitude!.toStringAsFixed(5)}, '
            '${form.exifLongitude!.toStringAsFixed(5)}';
        color = NaviAbleColors.primary;
        break;
      case LocationSource.address:
        label = 'Address: ${form.typedAddress}';
        color = NaviAbleColors.warning;
        break;
      case null:
        label = 'No location yet — pick one below';
        color = NaviAbleColors.danger;
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('2. Location', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(Icons.location_on, color: color),
                  const SizedBox(width: 8),
                  Expanded(child: Text(label, style: TextStyle(color: color))),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ActionChip(
                  avatar: const Icon(Icons.my_location, size: 16),
                  label: const Text('Use my GPS'),
                  onPressed: _useDeviceLocation,
                ),
                ActionChip(
                  avatar: const Icon(Icons.search, size: 16),
                  label: const Text('Pick a place'),
                  onPressed: () => _showPlacePicker(),
                ),
                ActionChip(
                  avatar: const Icon(Icons.edit_location_alt, size: 16),
                  label: const Text('Type address'),
                  onPressed: () => _showAddressInput(),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showPlacePicker() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
          top: 12, left: 12, right: 12,
        ),
        child: PlaceSearchBar(
          onPick: (gid) {
            Navigator.pop(context);
            // We don't yet know the name from the autocomplete row alone in this widget;
            // fetch detail or store the description as a fallback.
            ref.read(contributeProvider.notifier).pickPlace(gid, 'Selected place');
          },
        ),
      ),
    );
  }

  void _showAddressInput() {
    _addressCtrl.text = ref.read(contributeProvider).typedAddress ?? '';
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Type the address'),
        content: TextField(
          controller: _addressCtrl,
          maxLines: 2,
          decoration: const InputDecoration(hintText: 'e.g. 1 MG Road, Bangalore'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(
            onPressed: () {
              ref.read(contributeProvider.notifier).setAddress(_addressCtrl.text.trim());
              Navigator.pop(context);
            },
            child: const Text('Use this address'),
          ),
        ],
      ),
    );
  }

  Widget _reviewBlock(ContributeForm form) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('3. Your review',
                style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            TextField(
              maxLength: 2000,
              maxLines: 5,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText:
                    'Describe the accessibility: ramp slope, doorway width, '
                    'restroom layout, lifts, signage…',
              ),
              onChanged: (s) =>
                  ref.read(contributeProvider.notifier).setReview(s),
            ),
          ],
        ),
      ),
    );
  }

  Widget _ratingBlock(ContributeForm form) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            const Align(
              alignment: Alignment.centerLeft,
              child: Text('4. Your rating',
                  style: TextStyle(fontWeight: FontWeight.w700)),
            ),
            const SizedBox(height: 4),
            StarRating(
              value: form.rating,
              onChanged: (r) =>
                  ref.read(contributeProvider.notifier).setRating(r),
            ),
          ],
        ),
      ),
    );
  }
}

class _SubmittingPanel extends StatelessWidget {
  const _SubmittingPanel();
  @override
  Widget build(BuildContext context) => const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 24),
              Text(
                'Verifying your photo and review…\nthis usually takes a few seconds.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
}

class _ResultCard extends ConsumerWidget {
  final VerificationResponse response;
  const _ResultCard({required this.response});

  Color _colorFor() {
    switch (response.visibilityStatus) {
      case 'PUBLIC':
        return NaviAbleColors.accent;
      case 'CAVEAT':
        return NaviAbleColors.warning;
      default:
        return NaviAbleColors.danger;
    }
  }

  String _headlineFor() {
    switch (response.visibilityStatus) {
      case 'PUBLIC':
        return 'Published. Thanks!';
      case 'CAVEAT':
        return 'Published with a caveat';
      default:
        return 'Saved but not published';
    }
  }

  String _explanationFor() {
    switch (response.visibilityStatus) {
      case 'PUBLIC':
        return 'Your contribution is live on the map.';
      case 'CAVEAT':
        return 'A moderator will review it shortly. Other users see a caution badge in the meantime.';
      default:
        return 'The AI couldn\'t verify enough detail. Try retaking the photo with the accessibility feature in clear view, and adding more concrete description to your review.';
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pct = (response.trustScore * 100).round();
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Card(
            color: _colorFor().withOpacity(0.08),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  Icon(Icons.verified, color: _colorFor(), size: 56),
                  const SizedBox(height: 12),
                  Text(_headlineFor(),
                      style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text(_explanationFor(),
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 16),
                  Text('Trust Score: $pct%',
                      style: Theme.of(context)
                          .textTheme
                          .titleLarge
                          ?.copyWith(color: _colorFor())),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _scoreLine('Vision (YOLOv11)', response.visionScore),
                  _scoreLine('Text (RoBERTa)', response.nlpScore),
                  if (response.detectedFeatures.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    const Text('Detected features',
                        style: TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: response.detectedFeatures.entries
                          .expand((e) => e.value.map((d) => Chip(
                                avatar: const Icon(Icons.check, size: 16),
                                label: Text(
                                    '${e.key} ${(d.confidence * 100).round()}%'),
                              )))
                          .toList(),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () {
                    ref.read(submissionProvider.notifier).reset();
                  },
                  child: const Text('Submit another'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Done'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _scoreLine(String label, double v) {
    final pct = (v * 100).round();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(label)),
              Text('$pct%'),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: v,
              minHeight: 6,
              backgroundColor: Colors.grey.shade200,
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorPanel extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorPanel({required this.message, required this.onRetry});
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: Colors.red, size: 48),
              const SizedBox(height: 16),
              const Text('Submission failed',
                  style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Try again'),
              ),
            ],
          ),
        ),
      );
}
```

---

## Acceptance criteria

- [ ] Picking a photo from the gallery (with EXIF GPS) auto-fills the
      "From photo EXIF" badge and unlocks submit.
- [ ] Picking a photo without EXIF (e.g. fresh camera shot in some apps)
      shows "No location yet" and forces the user to choose one of three
      explicit fallbacks.
- [ ] Tapping "Use my GPS" requests permission once and fills in the
      device GPS badge.
- [ ] Tapping "Pick a place" opens a place autocomplete sheet; selecting
      a row populates the place badge.
- [ ] Tapping "Type address" stores the typed address.
- [ ] When all four sections are valid, the submit button is enabled.
      It's disabled otherwise and unresponsive to keyboard activation.
- [ ] On submit, the loading panel appears for 2–6s, then the result card.
      `PUBLIC` is green, `CAVEAT` amber, `HIDDEN` red.
- [ ] On a 503 from the backend, the error panel shows with a retry that
      replays the same submission.
- [ ] "Submit another" resets the form back to empty.

## Smoke commands

```bash
# Backend running, one verify already to seed a place
GOOGLE_PLACES_API_KEY=YOUR_KEY ./run.sh -b

# In the running app:
# 1) Tap FAB "Add review" without selecting a pin first
# 2) Pick photo from gallery (geo-tagged): EXIF badge appears
# 3) Type review > 10 chars; pick 4 stars
# 4) Submit. Trust card appears with VPN scores.
# 5) Repeat with non-EXIF photo + "Use my GPS"
# 6) Repeat with "Pick a place" workflow

# Verify DB:
docker exec naviable-postgis psql -U naviable -d naviable -c \
  "SELECT c.trust_score, c.visibility_status, p.name FROM contributions c JOIN places p ON c.place_id = p.id ORDER BY c.created_at DESC LIMIT 5;"
```

## Pitfalls

- `native_exif` on iOS requires the photo URL to be a real file path, not
  a `ph://` (PHAsset) reference. `image_picker` already returns a real path
  on both platforms — but if you swap to `photo_manager` later, you must
  call `requestOriginal()` first.
- The `image_picker` returns full-resolution images. The model was trained
  on 1280×1280; pre-compressing client-side with `flutter_image_compress`
  saves 70–90% bandwidth and makes the YOLO inference faster.
- Geolocator's `timeLimit` is essential. Without it, on a phone with no
  GPS lock, the call hangs forever — the spinner is the worst UX.
- The "Pick a place" sheet currently sets `name = "Selected place"`. To
  show the real place name in the badge, fetch detail when the user picks
  an autocomplete row (one extra API call). For MVP, the `place_name`
  comes back from `/verify` anyway and is shown in the result card.
- Don't pass huge images through `MultipartFile.fromBytes` if you're seeing
  OOM. Switch to `MultipartFile.fromFile` from a temp file path and let
  Dio stream it.
