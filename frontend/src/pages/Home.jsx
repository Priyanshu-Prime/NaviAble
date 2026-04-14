import { useMemo, useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";

import SearchBar from "../components/SearchBar";
import MapPlaceholder from "../components/MapPlaceholder";
import LocationCard from "../components/LocationCard";

/* ---------------- Axios ---------------- */
const API_URL = process.env.REACT_APP_API_URL;

const api = axios.create({
  baseURL: API_URL,
});

export default function Home() {
  const navigate = useNavigate();

  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(false);

  /* ---------------- Fetch Featured ---------------- */
  useEffect(() => {
    async function fetchFeatured() {
      try {
        setLoading(true);

        // assuming backend supports limit or featured flag
        const res = await api.get("/locations", {
          params: { limit: 4, sortBy: "rating" },
        });

        setLocations(res.data);
      } catch (err) {
        console.error("Error fetching featured locations:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchFeatured();
  }, []);

  /* ---------------- Handlers ---------------- */
  const handleSearch = (q) => {
    const trimmed = q.trim();
    navigate(trimmed ? `/explore?q=${encodeURIComponent(trimmed)}` : "/explore");
  };

  const handleTagClick = (tag) => {
    navigate(`/explore?q=${encodeURIComponent(tag)}`);
  };

  /* ---------------- Memo ---------------- */
  const featured = useMemo(() => locations.slice(0, 4), [locations]);

  /* ---------------- UI ---------------- */
  return (
    <div className="flex flex-col bg-white">

      {/* Hero */}
      <section className="border-b border-gray-100">
        <div className="max-w-3xl mx-auto px-4 py-24 text-center">

          <span className="inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 text-xs px-3 py-1.5 rounded-full mb-6 border border-indigo-100">
            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full" />
            Crowdsourced by the community
          </span>

          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-5">
            Navigate the World <span className="text-indigo-600">Accessibly</span>
          </h1>

          <p className="text-lg text-gray-500 mb-8 max-w-xl mx-auto">
            Discover and share accessibility information for locations near you.
          </p>

          <div className="max-w-xl mx-auto">
            <SearchBar
              onSearch={handleSearch}
              placeholder="Search a place, city, or category..."
              large
            />
          </div>

          {/* Quick Tags */}
          <div className="flex flex-wrap gap-2 mt-5 justify-center">
            {["Wheelchair Access", "Ramps", "Elevators", "Braille", "Hearing Loop"].map((tag) => (
              <button
                key={tag}
                onClick={() => handleTagClick(tag)}
                className="text-xs bg-gray-50 hover:bg-indigo-50 hover:text-indigo-600 border border-gray-200 hover:border-indigo-200 rounded-full px-3 py-1.5 text-gray-600 transition-colors"
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Map + Featured */}
      <section className="max-w-7xl mx-auto px-4 py-16">
        <div className="grid lg:grid-cols-2 gap-10">

          {/* Map */}
          <div>
            <h2 className="text-xl font-bold mb-1">Explore Nearby</h2>
            <p className="text-sm text-gray-400 mb-5">
              Accessible locations in your area
            </p>

            <div
              className="h-80 lg:h-96 cursor-pointer"
              onClick={() => navigate("/explore")}
            >
              <MapPlaceholder />
            </div>
          </div>

          {/* Featured */}
          <div>
            <div className="flex justify-between mb-5">
              <div>
                <h2 className="text-xl font-bold">Featured Places</h2>
                <p className="text-sm text-gray-400">Highly rated locations</p>
              </div>

              <Link
                to="/explore"
                className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
              >
                View all →
              </Link>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              {loading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <LocationCard key={i} loading />
                ))
              ) : (
                featured.map((loc) => (
                  <LocationCard key={loc.id} location={loc} />
                ))
              )}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-indigo-600 py-14 text-center">
        <h2 className="text-2xl font-bold text-white mb-3">
          Help Build the Map
        </h2>
        <p className="text-indigo-200 mb-6 text-sm">
          Share your accessibility experiences and help others.
        </p>

        <div className="flex justify-center gap-3">
          <Link
            to="/add-review"
            className="bg-white text-indigo-600 px-6 py-2.5 rounded-lg font-semibold"
          >
            Add Review
          </Link>

          <Link
            to="/explore"
            className="bg-indigo-700 text-white px-6 py-2.5 rounded-lg border border-indigo-500"
          >
            Explore
          </Link>
        </div>
      </section>
    </div>
  );
}