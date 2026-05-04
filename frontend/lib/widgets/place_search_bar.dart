import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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

  Widget _buildResultsList(
    BuildContext context,
    List<PlaceSummary> places, {
    required bool isDatabase,
  }) {
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
              leading: const Icon(Icons.location_on),
              title: Text(p.name, maxLines: 1, overflow: TextOverflow.ellipsis),
              subtitle: p.formattedAddress == null
                  ? null
                  : Text(p.formattedAddress!,
                      maxLines: 1, overflow: TextOverflow.ellipsis),
              trailing: p.publicCount > 0
                  ? Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.blue.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        '${p.publicCount} reviews',
                        style: const TextStyle(fontSize: 12),
                      ),
                    )
                  : null,
              onTap: () {
                FocusScope.of(context).unfocus();
                widget.onPick(p.googlePlaceId, LatLng(p.latitude, p.longitude));
              },
            );
          },
        ),
      ),
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
    final googleResults = _query.length < 2
        ? const AsyncValue<List<PlaceAutocomplete>>.data([])
        : ref.watch(searchProvider(_query));
    final dbResults = _query.length < 2
        ? const AsyncValue<List<PlaceSummary>>.data([])
        : ref.watch(databaseSearchProvider(_query));

    return Material(
      elevation: 4,
      borderRadius: BorderRadius.circular(12),
      color: Theme.of(context).colorScheme.surface,
      child: Column(
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
          dbResults.maybeWhen(
            data: (dbList) => dbList.isEmpty
                ? const SizedBox.shrink()
                : _buildResultsList(context, dbList, isDatabase: true),
            orElse: () => const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }
}
