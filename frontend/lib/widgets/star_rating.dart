import 'package:flutter/material.dart';

class StarRating extends StatelessWidget {
  final int? value;
  final ValueChanged<int> onChanged;
  const StarRating({super.key, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Rating',
      value: value == null ? 'unset' : '$value of 5 stars',
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(5, (i) {
          final filled = (value ?? 0) > i;
          return Semantics(
            inMutuallyExclusiveGroup: true,
            selected: value == i + 1,
            button: true,
            label: '${i + 1} of 5 stars',
            child: IconButton(
              icon: Icon(filled ? Icons.star : Icons.star_border, size: 32),
              color: filled ? Colors.amber.shade700 : Colors.grey.shade400,
              onPressed: () => onChanged(i + 1),
            ),
          );
        }),
      ),
    );
  }
}
