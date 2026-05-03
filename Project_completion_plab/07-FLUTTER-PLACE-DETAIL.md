# Phase 07 — Flutter: Place Detail screen (aggregate score, review feed, photo carousel)

**Status:** not started
**Depends on:** phase 04 (api client + routing), phase 05 (search/map navigates here)
**Affects:** `frontend/lib/screens/place_detail_screen.dart`, `frontend/lib/providers/`, `frontend/lib/widgets/`

## Goal

When the user taps a marker's "View details" button or picks a search
suggestion, they land on a full place page showing:

- Hero section with the place name, address, and a big trust badge.
- Aggregated metrics: trust score (recency-weighted), # of public reviews,
  # of total contributions, last-update time.
- Photo carousel of the most-recent reviewer-submitted photos (PUBLIC
  + CAVEAT only — HIDDEN never appears).
- Review feed with rating, review text, per-review trust score, and a
  "caveat" badge for `CAVEAT` rows.
- "Add your review" CTA at the bottom that pushes `/contribute` with
  the place pre-selected.

This is the place where a wheelchair user *decides* if they're going to
visit. The honest framing matters — show the score, show the underlying
reviews, don't paper over caveats.

---

## Deliverables

### 1. Provider

Create `frontend/lib/providers/place_detail_provider.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/providers.dart';
import '../models/place_models.dart';

final placeDetailProvider =
    FutureProvider.family<PlaceDetail, String>((ref, googlePlaceId) async {
  final api = ref.watch(apiClientProvider);
  return api.placeDetail(googlePlaceId);
});
```

### 2. The screen

Replace `frontend/lib/screens/place_detail_screen.dart`:

```dart
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../models/place_models.dart';
import '../providers/place_detail_provider.dart';
import '../theme/app_theme.dart';

class PlaceDetailScreen extends ConsumerWidget {
  final String googlePlaceId;
  const PlaceDetailScreen({super.key, required this.googlePlaceId});

  Color _trustColor(double t, bool hasData) {
    if (!hasData) return Colors.grey.shade600;
    if (t >= 0.70) return NaviAbleColors.accent;
    if (t >= 0.40) return NaviAbleColors.warning;
    return NaviAbleColors.danger;
  }

  String _trustLabel(double t, bool hasData) {
    if (!hasData) return 'No accessibility data yet';
    if (t >= 0.70) return 'Verified accessible';
    if (t >= 0.40) return 'Reported with caveat';
    return 'Reported as not accessible';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(placeDetailProvider(googlePlaceId));

    return Scaffold(
      body: detail.when(
        loading: () => const _Loader(),
        error: (e, _) => _Err(message: '$e', onRetry: () => ref.invalidate(placeDetailProvider(googlePlaceId))),
        data: (p) {
          final color = _trustColor(p.aggregateTrust, p.hasData);
          return CustomScrollView(
            slivers: [
              SliverAppBar.large(
                pinned: true,
                expandedHeight: 200,
                title: Text(p.name, maxLines: 1, overflow: TextOverflow.ellipsis),
                flexibleSpace: FlexibleSpaceBar(
                  background: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter, end: Alignment.bottomCenter,
                        colors: [color.withOpacity(0.4), color.withOpacity(0.05)],
                      ),
                    ),
                  ),
                ),
              ),
              SliverToBoxAdapter(child: _heroBlock(context, p, color)),
              SliverToBoxAdapter(child: _photoCarousel(p)),
              SliverToBoxAdapter(child: _reviewSectionHeader(p)),
              SliverList.separated(
                itemCount: p.contributions.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (_, i) => _ReviewTile(pin: p.contributions[i]),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: 96)),
            ],
          );
        },
      ),
      floatingActionButton: detail.maybeWhen(
        data: (p) => FloatingActionButton.extended(
          backgroundColor: NaviAbleColors.primary,
          onPressed: () => context.push('/contribute', extra: {
            'gid': p.googlePlaceId,
            'name': p.name,
          }),
          icon: const Icon(Icons.add_a_photo, color: Colors.white),
          label: const Text('Add your review',
              style: TextStyle(color: Colors.white)),
        ),
        orElse: () => null,
      ),
    );
  }

  Widget _heroBlock(BuildContext ctx, PlaceDetail p, Color color) {
    final pct = (p.aggregateTrust * 100).round();
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (p.formattedAddress != null)
            Row(
              children: [
                const Icon(Icons.place_outlined, size: 18),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(p.formattedAddress!,
                      style: Theme.of(ctx).textTheme.bodyMedium),
                ),
              ],
            ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: color.withOpacity(0.08),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: color.withOpacity(0.4)),
            ),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 28,
                  backgroundColor: color,
                  child: Icon(
                      p.hasData ? Icons.accessible : Icons.help_outline,
                      color: Colors.white, size: 28),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _trustLabel(p.aggregateTrust, p.hasData),
                        style: TextStyle(
                            color: color, fontWeight: FontWeight.w700, fontSize: 16),
                      ),
                      const SizedBox(height: 4),
                      Text(p.hasData
                          ? 'Trust $pct%  ·  ${p.publicCount} verified review'
                              '${p.publicCount == 1 ? "" : "s"}'
                          : 'Be the first to verify accessibility here.'),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _photoCarousel(PlaceDetail p) {
    final urls = p.contributions
        .where((c) => c.imageUrl != null)
        .map((c) => c.imageUrl!)
        .toList();
    if (urls.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(0, 4, 0, 8),
      child: SizedBox(
        height: 140,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          itemCount: urls.length,
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemBuilder: (_, i) => ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: CachedNetworkImage(
              imageUrl: urls[i],
              width: 160, height: 140, fit: BoxFit.cover,
              placeholder: (_, __) => Container(color: Colors.grey.shade200),
              errorWidget: (_, __, ___) => Container(
                color: Colors.grey.shade300,
                child: const Icon(Icons.broken_image),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _reviewSectionHeader(PlaceDetail p) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Row(
        children: [
          const Icon(Icons.rate_review_outlined),
          const SizedBox(width: 8),
          Text('Reviews (${p.contributions.length})',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
        ],
      ),
    );
  }
}

class _ReviewTile extends StatelessWidget {
  final ContributionPin pin;
  const _ReviewTile({required this.pin});

  @override
  Widget build(BuildContext context) {
    final isCaveat = pin.visibilityStatus == 'CAVEAT';
    final pct = (pin.trustScore * 100).round();
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      leading: pin.imageUrl != null
          ? ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: CachedNetworkImage(
                imageUrl: pin.imageUrl!,
                width: 56, height: 56, fit: BoxFit.cover,
                placeholder: (_, __) => Container(width: 56, height: 56, color: Colors.grey.shade200),
                errorWidget: (_, __, ___) => Container(
                  width: 56, height: 56,
                  color: Colors.grey.shade300,
                  child: const Icon(Icons.image_not_supported),
                ),
              ),
            )
          : const CircleAvatar(child: Icon(Icons.person_outline)),
      title: Row(
        children: [
          Row(
            children: List.generate(5, (i) => Icon(
              i < pin.rating ? Icons.star : Icons.star_border,
              size: 16, color: Colors.amber.shade700,
            )),
          ),
          const SizedBox(width: 8),
          Text('Trust $pct%',
              style: TextStyle(
                color: pct >= 70 ? NaviAbleColors.accent : NaviAbleColors.warning,
                fontWeight: FontWeight.w600,
              )),
          if (isCaveat) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: NaviAbleColors.warning.withOpacity(0.15),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text('caveat',
                  style: TextStyle(
                    fontSize: 11,
                    color: NaviAbleColors.warning,
                    fontWeight: FontWeight.w700,
                  )),
            ),
          ],
        ],
      ),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Text(pin.textNote, maxLines: 4, overflow: TextOverflow.ellipsis),
      ),
    );
  }
}

class _Loader extends StatelessWidget {
  const _Loader();
  @override
  Widget build(BuildContext context) =>
      const Center(child: CircularProgressIndicator());
}

class _Err extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _Err({required this.message, required this.onRetry});
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, color: Colors.red, size: 56),
            const SizedBox(height: 16),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
}
```

### 3. Tap-target from the contribute success card

When a user submits a review with a known `placeId`, the result card on
phase 06 should optionally let them "View this place" — that's a one-line
addition: in `_ResultCard.build` of `contribute_screen.dart`, between the
"Submit another" and "Done" buttons, add:

```dart
if (response.placeId != null) ...[
  const SizedBox(height: 8),
  TextButton.icon(
    onPressed: () {
      // We have place_id (UUID) but route uses google_place_id; navigate to map detail link
      // through the response if you also expose google_place_id on VerificationResponse — see below.
      // For MVP, simply pop back; the map will reflect the new contribution after refresh.
      Navigator.of(context).pop();
    },
    icon: const Icon(Icons.map_outlined),
    label: const Text('Back to map'),
  ),
],
```

(Optional enhancement: extend `VerificationResponse` to also include
`google_place_id` and link directly to `/place/<gid>`. Backend change is
adding two characters to the response object.)

### 4. Empty / new-place behaviour

Tapping a search suggestion for a place we've never seen — `placeDetailProvider`
calls `/places/{gid}`, which **upserts** the place server-side and returns
`contributions: []`. The screen renders the hero with "No accessibility data
yet · Be the first to verify accessibility here." and the FAB takes them
into the contribute flow with the place pre-selected.

The carousel and review tile sections are simply skipped when the lists
are empty — no special "empty state" widgets are needed because the FAB
itself is the call-to-action.

---

## Acceptance criteria

- [ ] Navigating to `/place/<known_gid>` shows the hero, photo carousel,
      and review tiles. Trust band colour matches `aggregateTrust`.
- [ ] Navigating to `/place/<unknown_gid>` shows the hero with "Be the
      first" copy and zero reviews; the FAB is still functional.
- [ ] Tapping the FAB pushes `/contribute` with the place pre-selected
      (verify by inspecting the badge on phase 06 screen).
- [ ] `CAVEAT` rows display the orange "caveat" pill; `PUBLIC` rows do not.
- [ ] Image URLs that 404 fall back to the broken-image placeholder
      without crashing the list.
- [ ] Pulling network plug shows the error state with a working retry.

## Smoke commands

```bash
# In the running mobile app:
# 1) Map → tap a marker → bottom sheet → "View details" — detail screen
# 2) Map → search → tap an unknown place — detail with "Be the first" copy
# 3) On detail with reviews → photo carousel scrolls horizontally
# 4) Tap FAB → contribute screen with the place pre-filled
# 5) Submit a review → return to detail → expect to see a new tile after refresh

# Force a refresh by re-entering the route:
# (Riverpod's family is keyed; the simplest way is to pop and re-push.)
```

## Pitfalls

- The detail provider is **family-keyed** by `googlePlaceId`. Don't
  invalidate `placeDetailProvider` (the family) — invalidate the specific
  family entry: `ref.invalidate(placeDetailProvider(googlePlaceId))`.
- The carousel binds image URLs from the backend's `image_url` field. In
  dev, those are served at `http://localhost:8000/static/<file>` — Android
  Emulator must use `http://10.0.2.2:8000/static/<file>` instead. Make
  sure `PUBLIC_BASE_URL` in the backend `.env` matches what the device can
  reach.
- `cached_network_image` keeps a disk cache. After running a few demo
  cycles, that grows fast — clear with
  `await CachedNetworkImage.evictFromCache(url)` if needed.
- `SliverAppBar.large` requires `expandedHeight`; without it the title
  collapses immediately on iOS and looks broken.
- The review tile shows the **per-contribution** trust score, not the
  place-aggregate. Don't confuse the two on screen — they're labelled
  separately on purpose.
