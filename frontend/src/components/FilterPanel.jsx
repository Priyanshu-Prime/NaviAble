import axios from "axios";
import { useEffect, useState } from "react";

const featureFilters = [
  { key: "wheelchairAccess", label: "Wheelchair Access", icon: "♿" },
  { key: "ramp", label: "Ramp", icon: "🔼" },
  { key: "elevator", label: "Elevator", icon: "🛗" },
  { key: "accessibleRestroom", label: "Accessible Restroom", icon: "🚻" },
  { key: "brailleSignage", label: "Braille Signage", icon: "⠿" },
  { key: "hearingLoop", label: "Hearing Loop", icon: "🔊" },
  { key: "parkingSpot", label: "Accessible Parking", icon: "🅿️" },
  { key: "automaticDoors", label: "Automatic Doors", icon: "🚪" },
];

export default function FilterPanel({ filters, onChange }) {
  const [categories, setCategories] = useState(["All"]);
  const BASE_URL = process.env.REACT_APP_API_URL;

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const res = await axios.get(`${BASE_URL}/categories`);
        setCategories(["All", ...res.data]);
      } catch (err) {
        console.error("Failed to fetch categories", err);
      }
    };

    fetchCategories();
  }, [BASE_URL]);

  const toggle = (key) => {
    onChange({
      ...filters,
      [key]: !filters[key],
    });
  };

  const resetFilters = () => {
    onChange({
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
    });
  };

  return (
    <aside className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
      <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h18v2l-7 7v6l-4 2v-8L3 6V4z" />
        </svg>
        Filters
      </h2>

      {/* Category */}
      <div className="mb-5">
        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 block">
          Category
        </label>
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => onChange({ ...filters, category: cat })}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                filters.category === cat
                  ? "bg-indigo-600 text-white border-indigo-600"
                  : "bg-white text-gray-600 border-gray-200 hover:border-indigo-300"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Min Rating */}
      <div className="mb-5">
        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 block">
          Minimum Rating: {filters.minRating}★
        </label>
        <input
          type="range"
          min={1}
          max={5}
          step={0.5}
          value={filters.minRating}
          onChange={(e) =>
            onChange({ ...filters, minRating: parseFloat(e.target.value) })
          }
          className="w-full accent-indigo-600"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>1★</span>
          <span>5★</span>
        </div>
      </div>

      {/* Features */}
      <div>
        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 block">
          Accessibility Features
        </label>

        <div className="space-y-2">
          {featureFilters.map(({ key, label, icon }) => (
            <label key={key} className="flex items-center gap-3 cursor-pointer group">
              <div
                className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                  filters[key]
                    ? "bg-indigo-600 border-indigo-600"
                    : "border-gray-300 group-hover:border-indigo-400"
                }`}
                onClick={() => toggle(key)}
              >
                {filters[key] && (
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24">
                    <path stroke="currentColor" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>

              <input
                type="checkbox"
                checked={!!filters[key]}
                onChange={() => toggle(key)}
                className="sr-only"
              />

              <span className="text-sm text-gray-600 group-hover:text-gray-800">
                <span className="mr-1">{icon}</span> {label}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Reset */}
      <button
        onClick={resetFilters}
        className="mt-5 w-full text-sm text-indigo-600 hover:text-indigo-800 font-medium py-2 border border-indigo-200 rounded-xl hover:bg-indigo-50"
      >
        Reset Filters
      </button>
    </aside>
  );
}