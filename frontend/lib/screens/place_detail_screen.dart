import 'package:flutter/material.dart';

class PlaceDetailScreen extends StatelessWidget {
  final String googlePlaceId;

  const PlaceDetailScreen({super.key, required this.googlePlaceId});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Text('Place: $googlePlaceId — phase 07'),
      ),
    );
  }
}
