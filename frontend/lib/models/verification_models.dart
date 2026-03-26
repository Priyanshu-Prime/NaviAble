/// Data models for the NaviAble Verification API response.
///
/// These classes mirror the JSON contract defined in
/// `.agent/architecture/API_CONTRACTS.md`.  Every field uses the same names
/// as the JSON keys so that `fromJson` factories are simple and readable.
library models;

/// A single accessibility feature detected by the YOLO vision model.
///
/// Bounding box ([bbox]) uses pixel coordinates from the original image:
/// `[x1, y1, x2, y2]` where `(x1, y1)` is the top-left corner.
class DetectedFeature {
  /// Human-readable class label (e.g. `'ramp'`, `'handrail'`).
  final String className;

  /// Detection confidence in the range [0.0, 1.0].
  final double confidence;

  /// Bounding box as `[x1, y1, x2, y2]` pixel coordinates.
  final List<int> bbox;

  const DetectedFeature({
    required this.className,
    required this.confidence,
    required this.bbox,
  });

  factory DetectedFeature.fromJson(Map<String, dynamic> json) {
    return DetectedFeature(
      className: json['class'] as String,
      confidence: (json['confidence'] as num).toDouble(),
      bbox: (json['bbox'] as List).map((v) => (v as num).toInt()).toList(),
    );
  }
}

/// Aggregated output from the YOLOv11 vision inference pipeline.
class VisionAnalysis {
  /// Total number of accessibility features detected above the 50% threshold.
  final int objectsDetected;

  /// Individual detection results with class label, confidence, and bounding box.
  final List<DetectedFeature> features;

  const VisionAnalysis({
    required this.objectsDetected,
    required this.features,
  });

  factory VisionAnalysis.fromJson(Map<String, dynamic> json) {
    return VisionAnalysis(
      objectsDetected: json['objects_detected'] as int,
      features: (json['features'] as List)
          .map((f) => DetectedFeature.fromJson(f as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// Output from the RoBERTa NLP Integrity Engine.
///
/// The model was fine-tuned on a 402-row balanced dataset built via LLM
/// Knowledge Distillation to distinguish genuine physical descriptions
/// from generic accessibility-washed praise.
class NlpAnalysis {
  /// `true` when the review contains genuine physical accessibility details
  /// and the model confidence exceeds the 75% threshold.
  final bool isGenuine;

  /// Model probability that the review is genuine (Class-1 confidence).
  final double confidence;

  /// Human-readable label: `'Genuine Physical Detail'` or
  /// `'Generic / Non-specific praise'`.
  final String label;

  const NlpAnalysis({
    required this.isGenuine,
    required this.confidence,
    required this.label,
  });

  factory NlpAnalysis.fromJson(Map<String, dynamic> json) {
    return NlpAnalysis(
      isGenuine: json['is_genuine'] as bool,
      confidence: (json['confidence'] as num).toDouble(),
      label: json['label'] as String,
    );
  }
}

/// Combined Dual-AI verification result for a single review submission.
class VerificationData {
  /// NLP classifier output.
  final NlpAnalysis nlpAnalysis;

  /// YOLO vision detector output.
  final VisionAnalysis visionAnalysis;

  /// Composite trust score: `0.60 × vision_confidence + 0.40 × nlp_confidence`.
  /// Capped at `0.50` when no visual features are detected (as per system design).
  final double naviableTrustScore;

  const VerificationData({
    required this.nlpAnalysis,
    required this.visionAnalysis,
    required this.naviableTrustScore,
  });

  factory VerificationData.fromJson(Map<String, dynamic> json) {
    return VerificationData(
      nlpAnalysis: NlpAnalysis.fromJson(
          json['nlp_analysis'] as Map<String, dynamic>),
      visionAnalysis: VisionAnalysis.fromJson(
          json['vision_analysis'] as Map<String, dynamic>),
      naviableTrustScore:
          (json['naviable_trust_score'] as num).toDouble(),
    );
  }
}

/// Top-level API response envelope for `POST /api/v1/verify`.
class VerificationResponse {
  /// `'success'` on a valid inference run.
  final String status;

  /// The verification results.
  final VerificationData data;

  const VerificationResponse({
    required this.status,
    required this.data,
  });

  factory VerificationResponse.fromJson(Map<String, dynamic> json) {
    return VerificationResponse(
      status: json['status'] as String,
      data: VerificationData.fromJson(json['data'] as Map<String, dynamic>),
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
