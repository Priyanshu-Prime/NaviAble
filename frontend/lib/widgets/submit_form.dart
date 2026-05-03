/// SubmitForm — the primary user input widget for NaviAble.
///
/// Allows the user to:
///   1. Type a text accessibility review.
///   2. Pick an image from their gallery / file system.
///   3. Submit both to the backend for Dual-AI verification.
///
/// The widget integrates with the [verifyProvider] (Riverpod) for state
/// management, keeping all business logic out of the UI layer.
///
/// Accessibility mandate compliance (`.agent/system/CONSTRAINTS_AND_RULES.md`):
/// - Every interactive element is wrapped in a [Semantics] node.
/// - All buttons meet the 48 dp minimum touch-target size.
/// - The image preview is described by a [Semantics.label].
library submit_form;

import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../providers/verify_provider.dart';
import '../theme/app_theme.dart';
import './star_rating.dart';

/// The primary submission form for NaviAble.
///
/// This is a [ConsumerStatefulWidget] so it can:
/// - Own the local form / text controller state.
/// - Watch the [verifyProvider] to show loading / error feedback.
class SubmitForm extends ConsumerStatefulWidget {
  const SubmitForm({super.key});

  @override
  ConsumerState<SubmitForm> createState() => _SubmitFormState();
}

class _SubmitFormState extends ConsumerState<SubmitForm> {
  final _formKey = GlobalKey<FormState>();
  final _reviewController = TextEditingController();

  /// Raw bytes of the user-selected image, stored in widget state because they
  /// are transient UI state that does not need to live in a Riverpod provider.
  Uint8List? _imageBytes;
  String _imageFilename = '';
  int? _rating;

  final _imagePicker = ImagePicker();

  @override
  void dispose() {
    _reviewController.dispose();
    super.dispose();
  }

  // ── Image Picking ─────────────────────────────────────────────────────────

  /// Opens the platform file picker and stores the selected image bytes.
  ///
  /// Uses [ImagePicker.pickImage] with [ImageSource.gallery] which maps to the
  /// browser's `<input type="file">` on Flutter Web.
  Future<void> _pickImage() async {
    try {
      final XFile? picked = await _imagePicker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 100, // raw quality; compression happens in the provider
      );
      if (picked == null) return; // user cancelled

      final bytes = await picked.readAsBytes();
      setState(() {
        _imageBytes = bytes;
        _imageFilename = picked.name;
      });
    } on Exception catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Could not load image: $e'),
            backgroundColor: NaviAbleColors.danger,
          ),
        );
      }
    }
  }

  // ── Form Submission ───────────────────────────────────────────────────────

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_imageBytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please select an image of the location.'),
          backgroundColor: NaviAbleColors.warning,
        ),
      );
      return;
    }
    if (_rating == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please select a rating (1-5 stars).'),
          backgroundColor: NaviAbleColors.warning,
        ),
      );
      return;
    }

    await ref.read(verifyProvider.notifier).submit(
          imageBytes: _imageBytes!.toList(),
          imageFilename: _imageFilename.isEmpty ? 'photo.jpg' : _imageFilename,
          review: _reviewController.text.trim(),
          rating: _rating!,
        );
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final verifyState = ref.watch(verifyProvider);
    final isLoading = verifyState is VerifyLoading;

    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // ── Section header ──────────────────────────────────────────────
          const Text(
            'Submit a Review for Verification',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: NaviAbleColors.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Upload a photo and write your accessibility review. '
            'Our Dual-AI engine will verify its authenticity.',
            style: TextStyle(fontSize: 13, color: NaviAbleColors.textMuted),
          ),
          const SizedBox(height: 20),

          // ── Image picker ────────────────────────────────────────────────
          Semantics(
            label: _imageBytes == null
                ? 'Select accessibility photo. No image selected.'
                : 'Accessibility photo selected: $_imageFilename. '
                    'Tap to change.',
            button: true,
            child: InkWell(
              onTap: isLoading ? null : _pickImage,
              borderRadius: BorderRadius.circular(12),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                height: 200,
                decoration: BoxDecoration(
                  border: Border.all(
                    color: _imageBytes != null
                        ? NaviAbleColors.primary
                        : NaviAbleColors.border,
                    width: _imageBytes != null ? 2 : 1.5,
                    style: _imageBytes == null
                        ? BorderStyle.solid
                        : BorderStyle.solid,
                  ),
                  borderRadius: BorderRadius.circular(12),
                  color: NaviAbleColors.background,
                ),
                child: _imageBytes == null
                    ? const _ImagePickerPlaceholder()
                    : ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: Stack(
                          fit: StackFit.expand,
                          children: [
                            Image.memory(_imageBytes!, fit: BoxFit.cover),
                            // Overlay tap-to-change hint
                            Positioned(
                              bottom: 0,
                              left: 0,
                              right: 0,
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                    vertical: 6, horizontal: 12),
                                color: Colors.black54,
                                child: const Text(
                                  'Tap to change image',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // ── Text review field ───────────────────────────────────────────
          Semantics(
            label: 'Accessibility review text field',
            child: TextFormField(
              controller: _reviewController,
              enabled: !isLoading,
              minLines: 4,
              maxLines: 6,
              maxLength: 500,
              textInputAction: TextInputAction.newline,
              decoration: const InputDecoration(
                labelText: 'Accessibility Review',
                hintText:
                    'Describe the accessibility features you observed '
                    '(e.g., "There is a wide ramp at the entrance with a '
                    'metal handrail on both sides").',
                alignLabelWithHint: true,
              ),
              validator: (value) {
                if (value == null || value.trim().length < 10) {
                  return 'Please write at least 10 characters.';
                }
                return null;
              },
            ),
          ),
          const SizedBox(height: 20),

          // ── Star rating ─────────────────────────────────────────────────
          Semantics(
            label: 'Rate the location accessibility',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'How would you rate the accessibility?',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: NaviAbleColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 12),
                StarRating(
                  value: _rating,
                  onChanged: (rating) => setState(() => _rating = rating),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // ── Submit button ───────────────────────────────────────────────
          Semantics(
            label: isLoading
                ? 'Verifying your review, please wait.'
                : 'Verify accessibility review button',
            button: true,
            child: ElevatedButton.icon(
              onPressed: isLoading ? null : _submit,
              // 48 dp height enforced via theme; icon adds affordance.
              icon: isLoading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.verified_outlined, size: 20),
              label: Text(
                isLoading ? 'Analysing with AI…' : 'Verify with NaviAble AI',
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),

          // ── Error banner ────────────────────────────────────────────────
          if (verifyState is VerifyError) ...[
            const SizedBox(height: 12),
            Semantics(
              label: 'Error: ${(verifyState as VerifyError).message}',
              liveRegion: true,
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFEBEE),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: NaviAbleColors.danger),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline,
                        color: NaviAbleColors.danger, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        (verifyState as VerifyError).message,
                        style: const TextStyle(
                          color: NaviAbleColors.danger,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Placeholder shown inside the image picker area when no image is selected.
class _ImagePickerPlaceholder extends StatelessWidget {
  const _ImagePickerPlaceholder();

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(
          Icons.add_photo_alternate_outlined,
          size: 48,
          color: NaviAbleColors.primary.withOpacity(0.6),
        ),
        const SizedBox(height: 12),
        const Text(
          'Click to select an image',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: NaviAbleColors.primary,
          ),
        ),
        const SizedBox(height: 4),
        const Text(
          'JPEG, PNG — photo of the accessible location',
          style: TextStyle(fontSize: 12, color: NaviAbleColors.textMuted),
        ),
      ],
    );
  }
}
