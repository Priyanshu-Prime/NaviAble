import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

import StarRating from "../components/StarRating";
import ReviewCard from "../components/ReviewCard";

/* ---------------- Axios ---------------- */
const API_URL = process.env.REACT_APP_API_URL;

const api = axios.create({
  baseURL: API_URL,
});

export default function Profile() {
  const [user, setUser] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [locationsMap, setLocationsMap] = useState({});
  const [loading, setLoading] = useState(true);

  /* ---------------- Fetch Data ---------------- */
  useEffect(() => {
    async function fetchProfile() {
      try {
        setLoading(true);

        // adjust endpoints based on your backend
        const [userRes, reviewsRes] = await Promise.all([
          api.get("/user/me"),
          api.get("/user/me/reviews"),
        ]);

        setUser(userRes.data);
        setReviews(reviewsRes.data);

        // fetch related locations
        const locationIds = [...new Set(reviewsRes.data.map(r => r.locationId))];

        const locationPromises = locationIds.map(id =>
          api.get(`/locations/${id}`)
        );

        const locationResponses = await Promise.all(locationPromises);

        const map = {};
        locationResponses.forEach(res => {
          map[res.data.id] = res.data;
        });

        setLocationsMap(map);

      } catch (err) {
        console.error("Error fetching profile:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchProfile();
  }, []);

  /* ---------------- Loading ---------------- */
  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-20 text-center">
        <p className="text-gray-400">Loading profile...</p>
      </div>
    );
  }

  if (!user) return null;

  /* ---------------- Stats ---------------- */
  const stats = [
    { label: "Reviews Written", value: reviews.length, icon: "✍️" },
    { label: "Contribution Points", value: user.contributionPoints || 0, icon: "⭐" },
    { label: "Places Visited", value: reviews.length, icon: "📍" },
    {
      label: "Helpful Votes",
      value: reviews.reduce((s, r) => s + (r.helpful || 0), 0),
      icon: "👍",
    },
  ];

  const averageRating =
    reviews.length > 0
      ? reviews.reduce((s, r) => s + r.rating, 0) / reviews.length
      : 0;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

      {/* Header */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-700 rounded-2xl p-6 text-white mb-6">
        <div className="flex gap-5 items-center">

          <img
            src={user.avatar}
            alt={user.name}
            className="w-20 h-20 rounded-xl object-cover"
          />

          <div className="flex-1">
            <h1 className="text-2xl font-bold">{user.name}</h1>
            <p className="text-sm text-indigo-200">{user.email}</p>

            <p className="text-xs text-indigo-300 mt-1">
              Member since{" "}
              {new Date(user.joinDate).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
              })}
            </p>

            <div className="flex gap-2 mt-3 flex-wrap">
              {(user.badges || []).map((b) => (
                <span key={b} className="text-xs bg-white/20 px-2 py-1 rounded">
                  {b}
                </span>
              ))}
            </div>
          </div>

          <Link
            to="/add-review"
            className="bg-white text-indigo-600 px-4 py-2 rounded"
          >
            + Add Review
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {stats.map((s) => (
          <div key={s.label} className="bg-white border p-4 rounded text-center">
            <div>{s.icon}</div>
            <p className="font-bold">{s.value}</p>
            <p className="text-xs text-gray-400">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">

        {/* Reviews */}
        <div className="lg:col-span-2">
          <h2 className="font-bold mb-3">
            My Reviews ({reviews.length})
          </h2>

          {reviews.length === 0 ? (
            <p className="text-gray-400 text-sm">
              No reviews yet.
            </p>
          ) : (
            <div className="space-y-4">
              {reviews.map((r) => {
                const loc = locationsMap[r.locationId];

                return (
                  <div key={r.id}>
                    {loc && (
                      <Link
                        to={`/location/${loc.id}`}
                        className="text-sm text-indigo-600"
                      >
                        📍 {loc.name}
                      </Link>
                    )}
                    <ReviewCard review={r} />
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">

          {/* Avg Rating */}
          {reviews.length > 0 && (
            <div className="bg-white border p-4 rounded">
              <h3 className="text-sm mb-2">Average Rating</h3>

              <div className="flex items-center gap-2">
                <span className="text-xl font-bold">
                  {averageRating.toFixed(1)}
                </span>
                <StarRating rating={averageRating} />
              </div>
            </div>
          )}

          {/* Quick Links */}
          <div className="bg-white border p-4 rounded">
            <Link to="/add-review" className="block text-sm mb-2">
              ✍️ Write Review
            </Link>
            <Link to="/explore" className="block text-sm">
              🔍 Explore
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}