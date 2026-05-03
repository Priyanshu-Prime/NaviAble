class PlaceSummary {
  final String? id;
  final String googlePlaceId;
  final String name;
  final String? formattedAddress;
  final double latitude;
  final double longitude;
  final List<String> googleTypes;
  final double aggregateTrust;
  final int publicCount;
  final int contributionCount;
  final bool hasData;

  PlaceSummary({
    required this.id,
    required this.googlePlaceId,
    required this.name,
    required this.formattedAddress,
    required this.latitude,
    required this.longitude,
    required this.googleTypes,
    required this.aggregateTrust,
    required this.publicCount,
    required this.contributionCount,
    required this.hasData,
  });

  factory PlaceSummary.fromJson(Map<String, dynamic> j) => PlaceSummary(
        id: j['id']?.toString(),
        googlePlaceId: j['google_place_id'] as String,
        name: j['name'] as String,
        formattedAddress: j['formatted_address'] as String?,
        latitude: (j['latitude'] as num).toDouble(),
        longitude: (j['longitude'] as num).toDouble(),
        googleTypes: (j['google_types'] as List? ?? []).cast<String>(),
        aggregateTrust: (j['aggregate_trust'] as num).toDouble(),
        publicCount: j['public_count'] as int,
        contributionCount: j['contribution_count'] as int,
        hasData: j['has_data'] as bool,
      );
}

class PlaceAutocomplete {
  final String googlePlaceId;
  final String description;
  final String mainText;
  final String? secondaryText;

  PlaceAutocomplete({
    required this.googlePlaceId,
    required this.description,
    required this.mainText,
    required this.secondaryText,
  });

  factory PlaceAutocomplete.fromJson(Map<String, dynamic> j) => PlaceAutocomplete(
        googlePlaceId: j['google_place_id'] as String,
        description: j['description'] as String,
        mainText: j['main_text'] as String,
        secondaryText: j['secondary_text'] as String?,
      );
}

class ContributionPin {
  final String id;
  final String? placeId;
  final double latitude;
  final double longitude;
  final double trustScore;
  final String visibilityStatus;
  final int rating;
  final String textNote;
  final String? imageUrl;

  ContributionPin({
    required this.id,
    this.placeId,
    required this.latitude,
    required this.longitude,
    required this.trustScore,
    required this.visibilityStatus,
    required this.rating,
    required this.textNote,
    required this.imageUrl,
  });

  factory ContributionPin.fromJson(Map<String, dynamic> j) => ContributionPin(
        id: j['id'] as String,
        placeId: j['place_id']?.toString(),
        latitude: (j['latitude'] as num).toDouble(),
        longitude: (j['longitude'] as num).toDouble(),
        trustScore: (j['trust_score'] as num).toDouble(),
        visibilityStatus: j['visibility_status'] as String,
        rating: j['rating'] as int,
        textNote: j['text_note'] as String,
        imageUrl: j['image_url'] as String?,
      );
}

class PlaceDetail extends PlaceSummary {
  final List<ContributionPin> contributions;

  PlaceDetail({
    required super.id,
    required super.googlePlaceId,
    required super.name,
    required super.formattedAddress,
    required super.latitude,
    required super.longitude,
    required super.googleTypes,
    required super.aggregateTrust,
    required super.publicCount,
    required super.contributionCount,
    required super.hasData,
    required this.contributions,
  });

  factory PlaceDetail.fromJson(Map<String, dynamic> j) {
    final base = PlaceSummary.fromJson(j);
    return PlaceDetail(
      id: base.id,
      googlePlaceId: base.googlePlaceId,
      name: base.name,
      formattedAddress: base.formattedAddress,
      latitude: base.latitude,
      longitude: base.longitude,
      googleTypes: base.googleTypes,
      aggregateTrust: base.aggregateTrust,
      publicCount: base.publicCount,
      contributionCount: base.contributionCount,
      hasData: base.hasData,
      contributions: (j['contributions'] as List? ?? [])
          .map((c) => ContributionPin.fromJson(c as Map<String, dynamic>))
          .toList(),
    );
  }
}
