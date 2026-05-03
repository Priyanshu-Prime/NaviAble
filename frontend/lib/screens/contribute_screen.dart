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
          if (response.placeId != null) ...[
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.map_outlined),
              label: const Text('Back to map'),
            ),
          ],
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
