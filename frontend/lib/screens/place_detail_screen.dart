import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';

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
              SliverToBoxAdapter(child: _mapWidget(p)),
              SliverToBoxAdapter(child: _photoCarousel(p)),
              SliverToBoxAdapter(child: _reviewSectionHeader(p, context)),
              if (p.contributions.isEmpty)
                SliverToBoxAdapter(child: _emptyReviewsWidget(context))
              else
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
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
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
                          : p.contributions.isNotEmpty
                              ? '${p.contributions.length} community review'
                                  '${p.contributions.length == 1 ? "" : "s"}'
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
    // Get contributions with images sorted by trust score (highest first)
    final withImages = p.contributions
        .where((c) => c.imageUrl != null)
        .toList();

    if (withImages.isEmpty) return const SizedBox.shrink();

    // Sort by trust score descending to show best first
    withImages.sort((a, b) => b.trustScore.compareTo(a.trustScore));

    return Padding(
      padding: const EdgeInsets.fromLTRB(0, 4, 0, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Best image (highest trust score) featured at top
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: CachedNetworkImage(
                imageUrl: withImages[0].imageUrl!,
                width: double.infinity,
                height: 200,
                fit: BoxFit.cover,
                placeholder: (_, __) => Container(
                  height: 200,
                  color: Colors.grey.shade200,
                ),
                errorWidget: (_, __, ___) => Container(
                  height: 200,
                  color: Colors.grey.shade300,
                  child: const Icon(Icons.broken_image),
                ),
              ),
            ),
          ),
          if (withImages.length > 1) ...[
            const SizedBox(height: 12),
            // More images carousel
            SizedBox(
              height: 100,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                itemCount: withImages.length - 1,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (_, i) => ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: CachedNetworkImage(
                    imageUrl: withImages[i + 1].imageUrl!,
                    width: 120,
                    height: 100,
                    fit: BoxFit.cover,
                    placeholder: (_, __) => Container(color: Colors.grey.shade200),
                    errorWidget: (_, __, ___) => Container(
                      color: Colors.grey.shade300,
                      child: const Icon(Icons.image_not_supported, size: 20),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _mapWidget(PlaceDetail p) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: SizedBox(
          height: 250,
          child: FlutterMap(
            options: MapOptions(
              initialCenter: LatLng(p.latitude, p.longitude),
              initialZoom: 14,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'ai.naviable',
              ),
              MarkerLayer(
                markers: [
                  Marker(
                    point: LatLng(p.latitude, p.longitude),
                    width: 40,
                    height: 40,
                    child: Icon(
                      Icons.location_on,
                      color: NaviAbleColors.primary,
                      size: 40,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _reviewSectionHeader(PlaceDetail p, BuildContext ctx) {
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

  Widget _emptyReviewsWidget(BuildContext ctx) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      child: Column(
        children: [
          Icon(Icons.rate_review_outlined, size: 48, color: Colors.grey.shade400),
          const SizedBox(height: 12),
          Text(
            'No reviews yet',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: Colors.grey.shade700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Be the first to share your accessibility experience at this location',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey.shade600,
            ),
          ),
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
