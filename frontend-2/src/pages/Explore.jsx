import { useState, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";

import SearchBar from "../components/SearchBar";
import FilterPanel from "../components/FilterPanel";
import LocationCard from "../components/LocationCard";

/* ---------------- Axios Instance ---------------- */
const API_URL = process.env.REACT_APP_API_URL;

const api = axios.create({
  baseURL: API_URL,
});

/* ---------------- Debounce Hook ---------------- */
function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

/* ---------------- Default Filters ---------------- */
const defaultFilters = {
  wheelchairAccess: false,
  ramp: false,
  elevator: false,
  accessibleRestroom: false,
  brailleSignage: false,
  hearingLoop: false,
  parkingSpot: false,
  automaticDoors: false,
  category: "All",
  minRating: 1,
};

export default function Explore() {
  const [searchParams] = useSearchParams();

  const [query, setQuery] = useState(searchParams.get("q") || "");
  const debouncedQuery = useDebounce(query, 300);

  const [filters, setFilters] = useState(defaultFilters);
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [sortBy, setSortBy] = useState("rating");

  /* ---------------- Fetch from Backend ---------------- */
  useEffect(() => {
    async function fetchLocations() {
      try {
        setLoading(true);

        const params = {
          q: debouncedQuery,
          category: filters.category !== "All" ? filters.category : "",
          minRating: filters.minRating,
          sortBy,
          ...filters, // send feature filters too
        };

        const res = await api.get("/locations", { params });

        setLocations(res.data);
      } catch (err) {
        console.error("Error fetching locations:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchLocations();
  }, [debouncedQuery, filters, sortBy]);

  /* ---------------- Optional Frontend Filtering (Safety Net) ---------------- */
  const filteredLocations = useMemo(() => {
    return locations
      .filter((loc) => {
        if (filters.category !== "All" && loc.category !== filters.category)
          return false;

        if (loc.rating < filters.minRating) return false;

        const featureKeys = [
          "wheelchairAccess",
          "ramp",
          "elevator",
          "accessibleRestroom",
          "brailleSignage",
          "hearingLoop",
          "parkingSpot",
          "automaticDoors",
        ];

        for (const key of featureKeys) {
          if (filters[key] && !loc.features?.[key]) return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === "rating") return b.rating - a.rating;
        if (sortBy === "reviews") return b.reviewCount - a.reviewCount;
        return a.name.localeCompare(b.name);
      });
  }, [locations, filters, sortBy]);

  /* ---------------- Active Filter Count ---------------- */
  const activeFilterCount = useMemo(() => {
    return Object.entries(filters).filter(([key, value]) => {
      if (key === "category") return value !== "All";
      if (key === "minRating") return value > 1;
      return value === true;
    }).length;
  }, [filters]);

  /* ---------------- Handlers ---------------- */
  const handleSearch = (q) => setQuery(q);

  const clearAllFilters = () => {
    setQuery("");
    setFilters(defaultFilters);
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="bg-white min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">
            Explore Places
          </h1>
          <p className="text-sm text-gray-400">
            Find accessible locations near you
          </p>
        </div>

        {/* Search + Controls */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="flex-1">
            <SearchBar
              onSearch={handleSearch}
              placeholder="Search by name, address, or category..."
              value={query}
            />
          </div>

          <div className="flex gap-2">
            {/* Filters Toggle */}
            <button
              onClick={() => setShowFilters((prev) => !prev)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                showFilters || activeFilterCount > 0
                  ? "bg-indigo-600 text-white border-indigo-600"
                  : "bg-white text-gray-600 border-gray-200 hover:border-indigo-300"
              }`}
            >
              Filters
              {activeFilterCount > 0 && (
                <span className="bg-white text-indigo-600 text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center">
                  {activeFilterCount}
                </span>
              )}
            </button>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 bg-white focus:outline-none focus:border-indigo-400"
            >
              <option value="rating">Top Rated</option>
              <option value="reviews">Most Reviewed</option>
              <option value="name">A–Z</option>
            </select>
          </div>
        </div>

        <div className="flex gap-6">

          {/* Filter Panel */}
          {showFilters && (
            <div className="w-64 flex-shrink-0">
              <FilterPanel filters={filters} onChange={setFilters} />
            </div>
          )}

          {/* Results */}
          <div className="flex-1">
            <p className="text-sm text-gray-400 mb-4">
              {loading
                ? "Searching…"
                : `${filteredLocations.length} place${
                    filteredLocations.length !== 1 ? "s" : ""
                  } found`}
            </p>

            {/* Loading */}
            {loading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <LocationCard key={i} loading />
                ))}
              </div>
            ) : filteredLocations.length === 0 ? (
              /* Empty State */
              <div className="text-center py-20">
                <div className="text-5xl mb-4">🔍</div>
                <h3 className="text-base font-semibold text-gray-800 mb-2">
                  No places found
                </h3>
                <p className="text-sm text-gray-400 mb-4">
                  Try adjusting your search or filters
                </p>
                <button
                  onClick={clearAllFilters}
                  className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  Clear all filters
                </button>
              </div>
            ) : (
              /* Results Grid */
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredLocations.map((loc) => (
                  <LocationCard key={loc.id} location={loc} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}