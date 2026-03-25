/**
 * NaviAble API Client
 *
 * Centralises all communication with the FastAPI backend.
 * The Vite dev server proxies /api/* and /health to http://localhost:8000.
 *
 * In production (built assets served by the same origin as the API),
 * the same paths work without any proxy configuration.
 */

const API_BASE = '';  // relative path — proxied in dev, same-origin in prod

/**
 * Check whether the backend is reachable and return its health status.
 *
 * @returns {Promise<{status: string, version: string, demo_mode: boolean, services: object}>}
 */
export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

/**
 * Submit a verification request to POST /api/v1/verify.
 *
 * @param {object} params
 * @param {File}   params.image        - JPEG or PNG image file object
 * @param {string} params.textReview   - User's written accessibility review
 * @param {string} params.locationId   - UUID string for the location
 * @returns {Promise<VerificationResponse>}
 *
 * @typedef {object} VerificationResponse
 * @property {string} status
 * @property {VerificationData} data
 *
 * @typedef {object} VerificationData
 * @property {NLPAnalysis}    nlp_analysis
 * @property {VisionAnalysis} vision_analysis
 * @property {number}         naviable_trust_score
 *
 * @typedef {object} NLPAnalysis
 * @property {boolean} is_genuine
 * @property {number}  confidence
 * @property {string}  label
 *
 * @typedef {object} VisionAnalysis
 * @property {number}  objects_detected
 * @property {Array}   features
 */
export async function verifyAccessibility({ image, textReview, locationId }) {
  const formData = new FormData();
  formData.append('image', image);
  formData.append('text_review', textReview);
  formData.append('location_id', locationId);

  const res = await fetch(`${API_BASE}/api/v1/verify`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}
