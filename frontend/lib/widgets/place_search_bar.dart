import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';

import '../models/place_models.dart';
import '../providers/places_provider.dart';

typedef OnPickPlace = void Function(String googlePlaceId, LatLng? position);

class PlaceSearchBar extends ConsumerStatefulWidget {
  final OnPickPlace onPick;
  const PlaceSearchBar({super.key, required this.onPick});

  @override
  ConsumerState<PlaceSearchBar> createState() => _PlaceSearchBarState();
}

class _PlaceSearchBarState extends ConsumerState<PlaceSearchBar> {
  final _controller = TextEditingController();
  String _query = '';
  Timer? _debounce;

  void _onChanged(String s) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350),
        () => setState(() => _query = s));
  }

  @override
  void dispose() {
    _controller.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  Widget _buildReviewedResultsList(
    BuildContext context,
    List<PlaceSummary> places,
  ) {
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: places.length,
      itemBuilder: (_, i) {
        final p = places[i];
        return ListTile(
          leading: const Icon(Icons.rate_review_outlined),
          title: Text(p.name, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: p.formattedAddress == null
              ? null
              : Text(p.formattedAddress!,
                  maxLines: 1, overflow: TextOverflow.ellipsis),
          trailing: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: Colors.blue.withOpacity(0.2),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              '${p.publicCount} review${p.publicCount == 1 ? "" : "s"}',
              style: const TextStyle(fontSize: 12),
            ),
          ),
          onTap: () {
            FocusScope.of(context).unfocus();
            context.push('/place/${p.googlePlaceId}');
          },
        );
      },
    );
  }

  Widget _buildGoogleResultsList(
    BuildContext context,
    List<PlaceAutocomplete> places,
  ) {
    return ConstrainedBox(
      constraints: const BoxConstraints(maxHeight: 240),
      child: Container(
        color: Theme.of(context).colorScheme.surface,
        child: ListView.builder(
          shrinkWrap: true,
          itemCount: places.length,
          itemBuilder: (_, i) {
            final p = places[i];
            return ListTile(
              leading: const Icon(Icons.place_outlined),
              title: Text(p.mainText, maxLines: 1, overflow: TextOverflow.ellipsis),
              subtitle: p.secondaryText == null
                  ? null
                  : Text(p.secondaryText!,
                      maxLines: 1, overflow: TextOverflow.ellipsis),
              onTap: () {
                FocusScope.of(context).unfocus();
                widget.onPick(p.googlePlaceId, null);
              },
            );
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final reviewedAll = ref.watch(reviewedAllProvider(_query));
    final googleResults = _query.length < 2
        ? const AsyncValue<List<PlaceAutocomplete>>.data([])
        : ref.watch(searchProvider(_query));

    return Material(
      elevation: 4,
      borderRadius: BorderRadius.circular(12),
      color: Theme.of(context).colorScheme.surface,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _controller,
            onChanged: _onChanged,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _query.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _controller.clear();
                        setState(() => _query = '');
                      }),
              hintText: 'Search a place by name or address',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
              filled: true,
              fillColor: Theme.of(context).colorScheme.surface,
            ),
          ),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 400),
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  reviewedAll.maybeWhen(
                    data: (places) {
                      if (places.isEmpty) return const SizedBox.shrink();
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (_query.length >= 2)
                            Padding(
                              padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                              child: Text(
                                'Reviewed places',
                                style: Theme.of(context)
                                    .textTheme
                                    .labelSmall
                                    ?.copyWith(color: Colors.grey),
                              ),
                            ),
                          _buildReviewedResultsList(context, places),
                        ],
                      );
                    },
                    orElse: () => const SizedBox.shrink(),
                  ),
                  if (_query.length >= 2)
                    googleResults.maybeWhen(
                      data: (gList) {
                        if (gList.isEmpty) return const SizedBox.shrink();
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Padding(
                              padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                              child: Text(
                                'Google Places',
                                style: Theme.of(context)
                                    .textTheme
                                    .labelSmall
                                    ?.copyWith(color: Colors.grey),
                              ),
                            ),
                            _buildGoogleResultsList(context, gList),
                          ],
                        );
                      },
                      orElse: () => const SizedBox.shrink(),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
