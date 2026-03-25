# JSON API Contracts

You must strictly adhere to these schemas when building FastAPI routes and Flutter model classes.

## Endpoint: POST `/api/v1/verify`
**Multipart Form Data Request**:
- `text_review`: String
- `location_id`: UUID
- `image`: File (image/jpeg, image/png)

**JSON Response (200 OK)**:
```json
{
  "status": "success",
  "data": {
    "nlp_analysis": {
      "is_genuine": true,
      "confidence": 0.87,
      "label": "Genuine Physical Detail"
    },
    "vision_analysis": {
      "objects_detected": 2,
      "features": [
        {"class": "ramp", "confidence": 0.62, "bbox": [10, 20, 150, 200]},
        {"class": "handrail", "confidence": 0.55, "bbox": [15, 25, 140, 190]}
      ]
    },
    "naviable_trust_score": 0.72
  }
}
```