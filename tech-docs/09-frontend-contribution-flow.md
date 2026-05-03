# Phase 09 — Frontend Contribution Flow

## Goal

Build the screen the user lands on when they choose to add a new
accessibility data point. They take or pick a photo, write a short
review, give a star rating, and confirm their location. The form posts
to `/api/v1/verify` and shows them what came back: their Trust Score,
which features the vision model saw, and whether the contribution was
published, flagged with a caveat, or held for review.

This is the user's only direct moment with the AI verification layer —
keep the result feedback honest and informative.

## Prerequisites

- Phase 06 merged: `/api/v1/verify` accepts the multipart payload and
  returns a complete `ContributionResponse`.
- Phase 08 merged: Riverpod, Dio, and the model classes exist.

## Spec essentials

| Field          | Source                                              |
|----------------|-----------------------------------------------------|
| Photo upload   | `image_picker` (`pickImage(source: camera/gallery)`)|
| Text note      | `TextField`, max 2000 chars to match backend cap    |
| Rating         | 1–5 stars                                           |
| Location       | `geolocator.getCurrentPosition()` — never silent fallbacks |
| State display  | Riverpod `AsyncValue` (loading / data / error)      |

## Current state

`frontend/lib/screens/` may have placeholders. This phase adds
`ContributeScreen` as the canonical implementation and removes any
older drafts.

## Deliverables

### 1. Form state

A single `ContributionFormState` model (Freezed) holds the in-progress
form:

```dart
@freezed
class ContributionFormState with _$ContributionFormState {
  const factory ContributionFormState({
    Uint8List? imageBytes,
    String? imageFilename,
    @Default('') String review,
    int? rating,
    LocationFix? location,
  }) = _ContributionFormState;

  bool get isReady =>
    imageBytes != null && review.trim().isNotEmpty &&
    rating != null && location != null;
}
```

A `StateNotifierProvider<ContributionFormNotifier, ContributionFormState>`
exposes setters for each field. Keep validation rules aligned with phase
02's Pydantic schema — a review that's empty after `trim()` should be
unsubmittable on the client, mirroring the server's `min_length=1`.

### 2. Submission flow with `AsyncValue`

```dart
@riverpod
class ContributionSubmission extends _$ContributionSubmission {
  @override
  AsyncValue<ContributionResponse?> build() => const AsyncData(null);

  Future<void> submit(ContributionFormState form) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final api = ref.read(apiClientProvider);
      final body = FormData.fromMap({
        'image': MultipartFile.fromBytes(form.imageBytes!,
            filename: form.imageFilename),
        'review': form.review.trim(),
        'latitude': form.location!.latitude,
        'longitude': form.location!.longitude,
        'rating': form.rating!,
      });
      final res = await api.post('/api/v1/verify', data: body);
      return ContributionResponse.fromJson(res.data);
    });
  }
}
```

The screen reads this provider and renders three different UIs based on
its `AsyncValue` state. No `bool isSubmitting`, ever — that is the
specific anti-pattern the spec forbids.

### 3. The screen

`lib/screens/contribute_screen.dart`:

- Top: photo picker. Shows the picked image in a 1:1 frame, with a
  "Retake" button. Empty state shows two options: "Take photo" (camera)
  and "Choose from device" (gallery).
- Middle: review text field. `maxLength: 2000`, counter visible, a
  helper text "What did you notice about accessibility here?"
- Below: 1–5 star rating widget. Custom widget that exposes proper
  semantics (`Semantics(label: 'Rating: 4 of 5 stars', value: '4')`).
  Do not use a generic `Slider` — wheelchair users on a screen reader
  should hear the rating, not a percentage.
- Location row: "Use current location" button that calls
  `geolocator.getCurrentPosition()`. On success, show the resolved
  address (reverse-geocoded) so the user can confirm it. **Never** fall
  back silently to a default lat/lon — if location is denied or fails,
  the form is not submittable.
- Submit button: disabled until `form.isReady`. When the user presses
  it, the `AsyncValue` flips to loading.

### 4. Loading state UX

A multi-second wait is normal here — the backend runs YOLOv11 +
RoBERTa concurrently, plus image upload. Show a non-blocking progress
indicator with explanatory text:

> "Verifying your photo and review… this usually takes a few seconds."

For screen reader users, announce this with `SemanticsService.announce`.
A spinner alone is invisible to assistive tech.

### 5. Result feedback

When the submission completes, replace the form with a result card that
tells the truth about what happened:

| Status     | Card content                                                   |
|------------|----------------------------------------------------------------|
| `PUBLIC`   | "Your contribution is live. Trust Score: 0.82." Plus a list of detected features ("ramp – 0.87 confidence"). |
| `CAVEAT`   | "Your contribution is published with a caveat. Trust Score: 0.55. A moderator will review it shortly." |
| `HIDDEN`   | "Your contribution is saved but not published. Trust Score: 0.21. The platform couldn't verify enough detail. Try retaking the photo or adding more context to your review." |

Surface `vision_score` and `nlp_score` separately on the card. The
honest framing — "we saw the ramp clearly but the text didn't tell us
much" — gives users actionable feedback for next time. Do not collapse
the result into a single number on screen.

A "Submit another" button resets the form via
`ref.invalidate(contributionFormNotifierProvider)`.

### 6. Error states

| Error                              | UI                                          |
|------------------------------------|---------------------------------------------|
| Network failure / timeout          | "Couldn't reach NaviAble — try again." Retry button. |
| `503` from backend                 | "The verification service is busy. Please try again in a moment." |
| `413` (image too big)              | Inline on the photo field: "Image too large (max 10 MB)." |
| `415` (bad image type)             | Inline: "Please upload a JPEG, PNG, or WebP image." |
| `422` validation error             | Should not happen — the form blocks invalid submissions. If it does, log and show "Something went wrong." |

The 422 case is interesting: if the client and server validation drift
apart, the user sees a generic message. The fix is to align the
validators, not to add a more permissive client.

### 7. Geolocation handling

`geolocator` requires permission. The flow:

1. User taps "Use current location."
2. App requests permission (`Geolocator.requestPermission()`).
3. On `denied` / `deniedForever`, show a clear message with how to
   re-enable in browser settings. Do not auto-retry the prompt.
4. On `whileInUse` / `always`, fetch the position with
   `desiredAccuracy: LocationAccuracy.high`. Set a 10 s timeout — the
   browser sometimes takes forever, and a stuck spinner is the worst UX.
5. Show the resolved coordinates and an editable text field for venue
   name (optional, not sent to backend in MVP — captured for future use).

## Acceptance criteria

- [ ] A user can pick a photo, write a review, set a rating, grant
      location, and submit. The result card shows the real Trust Score
      and per-model breakdown returned by the backend.
- [ ] The submit button is greyed out until all four fields are valid;
      pressing it (e.g. via keyboard) when greyed does nothing.
- [ ] During the upload + verification window, the UI shows a clear
      loading state. Screen readers announce it.
- [ ] On a 503, the user sees a retry option, not a stack trace.
- [ ] Submitting the same photo twice within one session does not
      re-prompt the camera (the cached `imageBytes` is used until the
      user explicitly chooses "Retake").
- [ ] Location-permission-denied surfaces an instructive message; the
      form is not submittable without a real location.
- [ ] No `bool isLoading` / `bool hasError` flags appear in any
      reviewed code — `AsyncValue` everywhere.
- [ ] WCAG audit of the screen via `accessibility_tools` is clean.

## Pitfalls / notes

- **`image_picker` on Flutter Web returns `XFile`, not a `File`.** Read
  bytes with `await xfile.readAsBytes()` and use
  `MultipartFile.fromBytes`. The mobile-first examples online with
  `MultipartFile.fromFile(File(...))` will not compile against `web`.
- **Star rating accessibility is easy to get wrong.** Stock Flutter
  widgets render five stars but expose them as one tappable container
  with no semantic value. Build it with five `IconButton`s, each
  semantically a `Radio` with `value: i`.
- **Don't show the request ID to the user** — it's developer ergonomics,
  not user information. Surface it in DevTools / logs only.
- **Honest feedback over flattering UI.** A `HIDDEN` result is not a
  failure — it is the system protecting other users from a contribution
  the AI couldn't verify. Frame the card as "couldn't verify yet," not
  "your contribution was rejected."
