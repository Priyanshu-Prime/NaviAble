import { Link } from "react-router-dom";
import StarRating from "./StarRating";
import AccessibilityBadge from "./AccessibilityBadge";

export default function LocationCard({ location, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden animate-pulse">
        <div className="h-44 bg-gray-100" />
        <div className="p-4 space-y-3">
          <div className="h-4 bg-gray-100 rounded w-3/4" />
          <div className="h-3 bg-gray-100 rounded w-1/2" />
          <div className="flex gap-2">
            <div className="h-5 bg-gray-100 rounded-full w-16" />
            <div className="h-5 bg-gray-100 rounded-full w-16" />
          </div>
        </div>
      </div>
    );
  }

  const activeFeatures = Object.entries(location?.features || {})
    .filter(([, v]) => v)
    .map(([k]) => k)
    .slice(0, 3);

  const totalFeatures = Object.values(location?.features || {}).filter(Boolean).length;

  return (
    <Link
      to={`/location/${location.id}`}
      className="group bg-white rounded-xl border border-gray-100 overflow-hidden hover:border-indigo-200 hover:shadow-md transition-all duration-200 block"
    >
      <div className="relative h-44 overflow-hidden bg-gray-100">
        <img
          src={location.image}
          alt={location.name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />

        <div className="absolute top-3 left-3">
          <span className="bg-white text-xs font-medium text-gray-600 px-2.5 py-1 rounded-full shadow-sm border border-gray-100">
            {location.category}
          </span>
        </div>

        <div className="absolute top-3 right-3 bg-white rounded-full px-2 py-0.5 flex items-center gap-1 shadow-sm border border-gray-100">
          <svg className="w-3 h-3 text-amber-400 fill-amber-400" viewBox="0 0 24 24">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
          <span className="text-xs font-semibold text-gray-800">
            {location.rating}
          </span>
        </div>
      </div>

      <div className="p-4">
        <h3 className="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors text-sm line-clamp-1">
          {location.name}
        </h3>

        <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1 line-clamp-1">
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          </svg>
          {location.address}
        </p>

        <div className="flex items-center gap-2 mt-2">
          <StarRating rating={location.rating} size="sm" />
          <span className="text-xs text-gray-400">
            ({location.reviewCount})
          </span>
        </div>

        <div className="flex flex-wrap gap-1.5 mt-3">
          {activeFeatures.map((f) => (
            <AccessibilityBadge key={f} feature={f} size="sm" />
          ))}

          {totalFeatures > 3 && (
            <span className="text-xs text-indigo-600 font-medium px-2 py-0.5 bg-indigo-50 rounded-full">
              +{totalFeatures - 3}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}