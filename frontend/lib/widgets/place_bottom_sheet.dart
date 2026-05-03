import 'package:flutter/material.dart';

import '../models/place_models.dart';
import '../theme/app_theme.dart';

class PlaceBottomSheet extends StatelessWidget {
  final PlaceSummary place;
  final VoidCallback onClose;
  final VoidCallback onOpen;
  const PlaceBottomSheet({
    super.key,
    required this.place,
    required this.onClose,
    required this.onOpen,
  });

  Color get _color {
    if (!place.hasData) return Colors.grey.shade600;
    if (place.aggregateTrust >= 0.70) return NaviAbleColors.accent;
    if (place.aggregateTrust >= 0.40) return NaviAbleColors.warning;
    return NaviAbleColors.danger;
  }

  String get _trustLabel {
    if (!place.hasData) return 'No accessibility data yet';
    return 'Trust ${(place.aggregateTrust * 100).round()}%  '
           '· ${place.publicCount} verified review'
           '${place.publicCount == 1 ? "" : "s"}';
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      elevation: 8,
      color: Theme.of(context).colorScheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 36, height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade400,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  CircleAvatar(
                    backgroundColor: _color,
                    radius: 14,
                    child: Icon(
                      place.hasData ? Icons.accessible : Icons.help_outline,
                      color: Colors.white, size: 16,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      place.name,
                      style: Theme.of(context).textTheme.titleMedium,
                      maxLines: 2, overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  IconButton(icon: const Icon(Icons.close), onPressed: onClose),
                ],
              ),
              if (place.formattedAddress != null) ...[
                const SizedBox(height: 4),
                Text(place.formattedAddress!,
                    style: Theme.of(context).textTheme.bodySmall),
              ],
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: _color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(_trustLabel,
                    style: TextStyle(color: _color, fontWeight: FontWeight.w600)),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: onOpen,
                      icon: const Icon(Icons.read_more),
                      label: const Text('View details'),
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
}
