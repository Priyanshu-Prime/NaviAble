import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/place_models.dart';
import '../providers/places_provider.dart';

class PlaceSearchBar extends ConsumerStatefulWidget {
  final ValueChanged<String> onPick;

  const PlaceSearchBar({super.key, required this.onPick});

  @override
  ConsumerState<PlaceSearchBar> createState() => _PlaceSearchBarState();
}

class _PlaceSearchBarState extends ConsumerState<PlaceSearchBar> {
  final _ctrl = TextEditingController();
  Timer? _debounce;
  String _lastQuery = '';

  @override
  void dispose() {
    _debounce?.cancel();
    _ctrl.dispose();
    super.dispose();
  }

  void _onQueryChanged(String query) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      setState(() {
        _lastQuery = query;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final searchAsync = ref.watch(searchProvider(_lastQuery));

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        TextField(
          controller: _ctrl,
          decoration: InputDecoration(
            hintText: 'Search for a place...',
            prefixIcon: const Icon(Icons.search),
            border: const OutlineInputBorder(),
          ),
          onChanged: _onQueryChanged,
        ),
        const SizedBox(height: 8),
        Flexible(
          child: searchAsync.when(
            data: (results) {
              if (_lastQuery.isEmpty) {
                return const SizedBox.shrink();
              }
              if (results.isEmpty) {
                return Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(
                    'No places found',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                );
              }
              return ListView.builder(
                shrinkWrap: true,
                itemCount: results.length,
                itemBuilder: (_, i) {
                  final place = results[i];
                  return ListTile(
                    leading: const Icon(Icons.location_on, size: 20),
                    title: Text(place.mainText),
                    subtitle: place.secondaryText != null
                        ? Text(place.secondaryText!, maxLines: 1)
                        : null,
                    onTap: () => widget.onPick(place.googlePlaceId),
                  );
                },
              );
            },
            loading: () => Padding(
              padding: const EdgeInsets.all(16),
              child: SizedBox(
                height: 24,
                width: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation(
                    Theme.of(context).primaryColor,
                  ),
                ),
              ),
            ),
            error: (e, st) => Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                'Error: $e',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.red.shade600),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
