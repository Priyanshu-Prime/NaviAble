import { useState, useEffect } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import StarRating from "../components/StarRating";
import UploadForm from "../components/UploadForm";

const API_URL = process.env.REACT_APP_API_URL;

const featureOptions = [
  { key: "wheelchairAccess", label: "Wheelchair Access", icon: "♿" },
  { key: "ramp", label: "Ramp", icon: "🔼" },
  { key: "elevator", label: "Elevator", icon: "🛗" },
  { key: "accessibleRestroom", label: "Accessible Restroom", icon: "🚻" },
  { key: "brailleSignage", label: "Braille Signage", icon: "⠿" },
  { key: "hearingLoop", label: "Hearing Loop", icon: "🔊" },
  { key: "parkingSpot", label: "Accessible Parking", icon: "🅿️" },
  { key: "automaticDoors", label: "Automatic Doors", icon: "🚪" },
];

export default function AddReview() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const preselectedId = searchParams.get("locationId") || "";

  const [locations, setLocations] = useState([]);
  const [locationId, setLocationId] = useState(preselectedId);
  const [rating, setRating] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [selectedFeatures, setSelectedFeatures] = useState([]);
  const [visitDate, setVisitDate] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [errors, setErrors] = useState({});
  const [images, setImages] = useState([]);

  // ✅ Fetch locations from backend
  useEffect(() => {
    const fetchLocations = async () => {
      try {
        const res = await axios.get(`${API_URL}/locations`);
        setLocations(res.data);
      } catch (err) {
        console.error("Error fetching locations:", err);
      }
    };

    fetchLocations();
  }, []);

  const selectedLocation = locations.find((l) => l.id === locationId);

  const toggleFeature = (key) => {
    setSelectedFeatures((prev) =>
      prev.includes(key) ? prev.filter((f) => f !== key) : [...prev, key]
    );
  };

  const validate = () => {
    const e = {};

    if (!locationId) e.location = "Please select a location.";
    if (rating === 0) e.rating = "Please select a rating.";
    if (reviewText.trim().length < 20)
      e.reviewText = "Review must be at least 20 characters.";

    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    try {
      await axios.post(`${API_URL}/reviews`, {
        locationId,
        rating,
        text: reviewText,
        features: selectedFeatures,
        visitDate,
        images,
      });

      setSubmitted(true);
    } catch (err) {
      console.error("Error submitting review:", err);
    }
  };

  if (submitted) {
    return (
      <div className="bg-white min-h-screen flex items-center justify-center px-4 py-20">
        <div className="max-w-md w-full text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
            <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>

          <h2 className="text-xl font-bold text-gray-900 mb-2">Review Submitted!</h2>

          <p className="text-gray-400 text-sm mb-1">
            Thank you for contributing to <span className="font-semibold text-indigo-600">NaviAble</span>.
          </p>

          <p className="text-sm text-gray-400 mb-8">
            Your review for <strong className="text-gray-700">{selectedLocation?.name}</strong> has been added.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to={`/location/${locationId}`}
              className="bg-indigo-600 text-white px-5 py-2.5 rounded-lg hover:bg-indigo-700 text-sm"
            >
              View Location
            </Link>

            <button
              onClick={() => {
                setSubmitted(false);
                setRating(0);
                setReviewText("");
                setSelectedFeatures([]);
                setVisitDate("");
                setLocationId("");
                setImages([]);
              }}
              className="border border-gray-200 text-gray-600 px-5 py-2.5 rounded-lg hover:bg-gray-50 text-sm"
            >
              Add Another
            </button>

            <Link
              to="/explore"
              className="border border-gray-200 text-gray-600 px-5 py-2.5 rounded-lg hover:bg-gray-50 text-sm"
            >
              Explore Places
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white min-h-screen">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">

        {/* Header */}
        <div className="mb-7">
          <nav className="flex items-center gap-2 text-sm text-gray-400 mb-3">
            <Link to="/">Home</Link>
            <span>/</span>
            <span className="text-gray-700 font-medium">Add Review</span>
          </nav>

          <h1 className="text-2xl font-bold text-gray-900">Write a Review</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">

          {/* Location */}
          <div className="bg-white border p-5 rounded-xl">
            <select
              value={locationId}
              onChange={(e) => setLocationId(e.target.value)}
              className="w-full border px-3 py-2 rounded-lg"
            >
              <option value="">Select location</option>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name}
                </option>
              ))}
            </select>
            {errors.location && <p className="text-red-500 text-xs">{errors.location}</p>}
          </div>

          {/* Rating */}
          <StarRating rating={rating} size="lg" interactive onRate={setRating} />
          {errors.rating && <p className="text-red-500 text-xs">{errors.rating}</p>}

          {/* Review */}
          <textarea
            value={reviewText}
            onChange={(e) => setReviewText(e.target.value)}
            className="w-full border p-3 rounded-lg"
            placeholder="Write review..."
          />
          {errors.reviewText && <p className="text-red-500 text-xs">{errors.reviewText}</p>}

          {/* Features */}
          <div className="grid grid-cols-2 gap-2">
            {featureOptions.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => toggleFeature(f.key)}
                className={`p-2 border rounded ${
                  selectedFeatures.includes(f.key)
                    ? "bg-indigo-600 text-white"
                    : "bg-white"
                }`}
              >
                {f.icon} {f.label}
              </button>
            ))}
          </div>

          {/* Upload */}
          <UploadForm onImagesChange={setImages} />

          {/* Submit */}
          <button className="w-full bg-indigo-600 text-white py-3 rounded-lg">
            Submit Review
          </button>
        </form>
      </div>
    </div>
  );
}