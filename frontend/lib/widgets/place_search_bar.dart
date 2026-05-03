import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/place_models.dart';
import '../providers/places_provider.dart';

typedef OnPickPlace = void Function(String googlePlaceId);

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

  @override
  Widget build(BuildContext context) {
    final results = _query.length < 2
        ? const AsyncValue<List<PlaceAutocomplete>>.data([])
        : ref.watch(searchProvider(_query));

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
          results.maybeWhen(
            data: (list) => list.isEmpty
                ? const SizedBox.shrink()
                : ConstrainedBox(
                    constraints: const BoxConstraints(maxHeight: 240),
                    child: Container(
                      color: Theme.of(context).colorScheme.surface,
                      child: ListView.builder(
                        shrinkWrap: true,
                        itemCount: list.length,
                        itemBuilder: (_, i) {
                          final p = list[i];
                          return ListTile(
                            leading: const Icon(Icons.place_outlined),
                            title: Text(p.mainText, maxLines: 1, overflow: TextOverflow.ellipsis),
                            subtitle: p.secondaryText == null
                                ? null
                                : Text(p.secondaryText!,
                                    maxLines: 1, overflow: TextOverflow.ellipsis),
                            onTap: () {
                              FocusScope.of(context).unfocus();
                              widget.onPick(p.googlePlaceId);
                            },
                          );
                        },
                      ),
                    ),
                  ),
            orElse: () => const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }
}
