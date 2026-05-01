import StarRating from "./StarRating";

export default function ReviewCard({ review }) {
  if (!review) return null;

  const formattedDate = review.date
    ? new Date(review.date).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "";

  return (
    <div className="bg-white rounded-xl border border-gray-100 p-5 hover:border-gray-200 transition-colors">
      
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <img
            src={review.userAvatar}
            alt={review.userName}
            className="w-9 h-9 rounded-full object-cover border border-gray-100"
          />
          <div>
            <p className="font-semibold text-gray-900 text-sm">
              {review.userName}
            </p>
            <p className="text-xs text-gray-400">{formattedDate}</p>
          </div>
        </div>

        <StarRating rating={review.rating} size="sm" />
      </div>

      {/* Review Text */}
      <p className="text-sm text-gray-600 mt-3 leading-relaxed">
        {review.text}
      </p>

      {/* Images */}
      {review.images && review.images.length > 0 && (
        <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
          {review.images.map((img, i) => (
            <img
              key={i}
              src={img}
              alt={`Review ${i + 1}`}
              className="h-20 w-28 object-cover rounded-lg flex-shrink-0 border border-gray-100"
            />
          ))}
        </div>
      )}

      {/* Features */}
      {review.features && review.features.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {review.features.map((f) => (
            <span
              key={f}
              className="text-xs bg-green-50 text-green-700 px-2.5 py-0.5 rounded-full border border-green-100"
            >
              ✓ {f.replace(/([A-Z])/g, " $1").trim()}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-4 mt-4 pt-3 border-t border-gray-50">
        <button className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-indigo-600 transition-colors">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
            <path
              stroke="currentColor"
              strokeWidth={2}
              d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
            />
          </svg>
          Helpful ({review.helpful || 0})
        </button>

        <button className="text-xs text-gray-400 hover:text-gray-600 transition-colors">
          Report
        </button>
      </div>
    </div>
  );
}