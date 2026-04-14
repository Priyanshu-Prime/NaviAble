import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import axios from "axios";

import StarRating from "../components/StarRating";
import AccessibilityBadge from "../components/AccessibilityBadge";
import ReviewCard from "../components/ReviewCard";
import MapPlaceholder from "../components/MapPlaceholder";

/* ---------------- Axios ---------------- */
const API_URL = process.env.REACT_APP_API_URL;

const api = axios.create({
  baseURL: API_URL,
});

/* ---------------- Feature Keys ---------------- */
const featureKeys = [
  { key: "wheelchairAccess", label: "Wheelchair Access", icon: "♿" },
  { key: "ramp", label: "Ramp", icon: "🔼" },
  { key: "elevator", label: "Elevator", icon: "🛗" },
  { key: "accessibleRestroom", label: "Accessible Restroom", icon: "🚻" },
  { key: "brailleSignage", label: "Braille Signage", icon: "⠿" },
  { key: "hearingLoop", label: "Hearing Loop", icon: "🔊" },
  { key: "parkingSpot", label: "Accessible Parking", icon: "🅿️" },
  { key: "automaticDoors", label: "Automatic Doors", icon: "🚪" },
];

export default function LocationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [location, setLocation] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeImage, setActiveImage] = useState(0);

  /* ---------------- Fetch Data ---------------- */
  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);

        const [locRes, reviewRes] = await Promise.all([
          api.get(`/locations/${id}`),
          api.get(`/locations/${id}/reviews`),
        ]);

        setLocation(locRes.data);
        setReviews(reviewRes.data);
      } catch (err) {
        console.error("Error fetching location:", err);
      } finally {
        setLoading(false);
      }
    }

    if (id) fetchData();
  }, [id]);

  /* ---------------- Loading ---------------- */
  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <p className="text-gray-400">Loading...</p>
      </div>
    );
  }

  /* ---------------- Not Found ---------------- */
  if (!location) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <div className="text-5xl mb-4">📍</div>
        <h2 className="text-xl font-bold text-gray-800 mb-2">
          Location not found
        </h2>
        <p className="text-gray-400 mb-6 text-sm">
          This place doesn't exist or has been removed.
        </p>
        <Link
          to="/explore"
          className="bg-indigo-600 text-white px-5 py-2.5 rounded-lg"
        >
          Back to Explore
        </Link>
      </div>
    );
  }

  /* ---------------- Images ---------------- */
  const images = [
    location.image,
    ...(reviews.flatMap((r) => r.images || [])),
  ].filter(Boolean);

  /* ---------------- Accessibility Score ---------------- */
  const accessibleCount = Object.values(location.features || {}).filter(Boolean).length;
  const totalFeatures = Object.values(location.features || {}).length;

  /* ---------------- Rating Breakdown ---------------- */
  const ratingBreakdown = [5, 4, 3, 2, 1].map((star) => ({
    star,
    count: reviews.filter((r) => Math.round(r.rating) === star).length,
  }));

  return (
    <div className="bg-white min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-400 mb-6">
          <Link to="/" className="hover:text-indigo-600">Home</Link>
          <span>/</span>
          <Link to="/explore" className="hover:text-indigo-600">Explore</Link>
          <span>/</span>
          <span className="text-gray-700 font-medium">{location.name}</span>
        </nav>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          {/* LEFT */}
          <div className="lg:col-span-2 space-y-5">

            {/* Image */}
            <div className="rounded-xl overflow-hidden border">
              <div className="relative h-72">
                <img
                  src={images[activeImage]}
                  alt={location.name}
                  className="w-full h-full object-cover"
                />
              </div>

              {images.length > 1 && (
                <div className="flex gap-2 p-3 overflow-x-auto">
                  {images.map((img, i) => (
                    <button key={i} onClick={() => setActiveImage(i)}>
                      <img src={img} className="w-14 h-14 rounded" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Info */}
            <div className="border rounded-xl p-6">
              <div className="flex justify-between">
                <div>
                  <h1 className="text-xl font-bold">{location.name}</h1>
                  <p className="text-gray-400 text-sm">{location.address}</p>
                </div>

                <div className="text-right">
                  <StarRating rating={location.rating} />
                  <p className="text-xs text-gray-400">
                    {reviews.length} reviews
                  </p>
                </div>
              </div>

              <p className="mt-4 text-sm text-gray-500">
                {location.description}
              </p>
            </div>

            {/* Features */}
            <div className="border rounded-xl p-6">
              <h2 className="font-bold mb-4">Accessibility Features</h2>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {featureKeys.map((f) => {
                  const available = location.features?.[f.key];

                  return (
                    <div key={f.key} className="p-3 border rounded text-center">
                      <div>{f.icon}</div>
                      <p className="text-xs">{f.label}</p>
                      <p className="text-xs">
                        {available ? "Yes" : "No"}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Reviews */}
            <div className="border rounded-xl p-6">
              <div className="flex justify-between mb-4">
                <h2 className="font-bold">
                  Reviews ({reviews.length})
                </h2>

                <Link
                  to={`/add-review?locationId=${location.id}`}
                  className="text-sm bg-indigo-600 text-white px-3 py-1 rounded"
                >
                  Write Review
                </Link>
              </div>

              {reviews.length === 0 ? (
                <p className="text-sm text-gray-400">No reviews yet.</p>
              ) : (
                <div className="space-y-4">
                  {reviews.map((r) => (
                    <ReviewCard key={r.id} review={r} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* RIGHT */}
          <div className="space-y-4">

            <div className="border rounded-xl p-4">
              <h3 className="font-semibold mb-2">Location</h3>
              <div className="h-48">
                <MapPlaceholder />
              </div>
              <p className="text-xs text-gray-400 mt-2">
                {location.address}
              </p>
            </div>

            <Link
              to={`/add-review?locationId=${location.id}`}
              className="block bg-indigo-600 text-white text-center py-2 rounded-lg"
            >
              Write a Review
            </Link>

            <button
              onClick={() => navigate(-1)}
              className="block w-full text-sm text-gray-400"
            >
              ← Go Back
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}