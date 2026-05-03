import 'package:flutter/material.dart';

class ContributeScreen extends StatelessWidget {
  final String? presetGooglePlaceId;
  final String? presetPlaceName;

  const ContributeScreen({
    super.key,
    this.presetGooglePlaceId,
    this.presetPlaceName,
  });

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Text('Contribute — phase 06'),
      ),
    );
  }
}
