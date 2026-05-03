/// Data models for the NaviAble Verification API response.
///
/// These classes mirror the JSON contract from the FastAPI backend.
/// Every field uses the same names as the JSON keys so that `fromJson` factories
/// are simple and readable.
library models;

/// A single accessibility feature detected by the YOLO vision model.
///
/// Bounding box uses normalized coordinates [0.0, 1.0]:
/// `[x1, y1, x2, y2]` where `(x1, y1)` is the top-left corner.
class DetectedFeature {
  /// Detection confidence in the range [0.0, 1.0].
  final double confidence;

  /// Normalized bounding box as `[x1, y1, x2, y2]` in range [0.0, 1.0].
  final List<double> bbox;

  const DetectedFeature({
    required this.confidence,
    required this.bbox,
  });

  factory DetectedFeature.fromJson(Map<String, dynamic> json) {
    return DetectedFeature(
      confidence: (json['confidence'] as num).toDouble(),
      bbox: (json['bbox'] as List)
          .map((v) => (v as num).toDouble())
          .toList(),
    );
  }
}

/// Top-level API response for `POST /api/v1/verify`.
///
/// This is the actual response from the backend after processing an image
/// and text review through the Dual-AI pipeline (vision + NLP).
class VerificationResponse {
  /// Unique identifier for this contribution.
  final String id;

  /// Composite trust score: 0.60 × vision_score + 0.40 × nlp_score.
  /// Range: [0.0, 1.0]
  final double trustScore;

  /// YOLO vision model confidence (0.0 to 1.0).
  /// How confident the vision model is in detecting accessibility features.
  final double visionScore;

  /// RoBERTa NLP model confidence (0.0 to 1.0).
  /// How confident the NLP model is in the review authenticity.
  final double nlpScore;

  /// Visibility status: PUBLIC, CAVEAT, or HIDDEN.
  /// Based on trust score thresholds.
  final String visibilityStatus;

  /// Map of feature type to list of detections.
  /// Example: {'ramp': [DetectedFeature(...), ...], 'stairs': [...]}
  final Map<String, List<DetectedFeature>> detectedFeatures;

  const VerificationResponse({
    required this.id,
    required this.trustScore,
    required this.visionScore,
    required this.nlpScore,
    required this.visibilityStatus,
    required this.detectedFeatures,
  });

  factory VerificationResponse.fromJson(Map<String, dynamic> json) {
    final detectedFeaturesJson =
        json['detected_features'] as Map<String, dynamic>? ?? {};

    final detectedFeatures = <String, List<DetectedFeature>>{};
    detectedFeaturesJson.forEach((key, value) {
      if (value is List) {
        detectedFeatures[key] = value
            .map((f) => DetectedFeature.fromJson(f as Map<String, dynamic>))
            .toList();
      }
    });

    return VerificationResponse(
      id: json['id'] as String,
      trustScore: (json['trust_score'] as num).toDouble(),
      visionScore: (json['vision_score'] as num).toDouble(),
      nlpScore: (json['nlp_score'] as num).toDouble(),
      visibilityStatus: json['visibility_status'] as String,
      detectedFeatures: detectedFeatures,
    );
  }
}

/// Backend health check response from `GET /health`.
class HealthResponse {
  final String status;
  final String version;
  final bool demoMode;
  final Map<String, String> services;

  const HealthResponse({
    required this.status,
    required this.version,
    required this.demoMode,
    required this.services,
  });

  factory HealthResponse.fromJson(Map<String, dynamic> json) {
    final svcMap = (json['services'] as Map<String, dynamic>)
        .map((k, v) => MapEntry(k, v.toString()));
    return HealthResponse(
      status: json['status'] as String,
      version: json['version'] as String,
      demoMode: json['demo_mode'] as bool,
      services: svcMap,
    );
  }
}
