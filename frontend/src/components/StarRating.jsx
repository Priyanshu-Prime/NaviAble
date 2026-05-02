export default function StarRating({
  rating,
  size = "md",
  interactive = false,
  onRate,
}) {
  const sizes = {
    sm: "w-3.5 h-3.5",
    md: "w-5 h-5",
    lg: "w-7 h-7",
  };

  return (
    <div
      className="flex items-center gap-0.5"
      aria-label={`Rating: ${rating} out of 5 stars`}
    >
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = star <= Math.floor(rating);
        const half =
          !filled && star === Math.ceil(rating) && rating % 1 !== 0;

        return (
          <button
            key={star}
            type="button"
            onClick={() => interactive && onRate && onRate(star)}
            className={
              interactive
                ? "cursor-pointer hover:scale-110 transition-transform"
                : "cursor-default"
            }
          >
            <svg
              className={`${sizes[size]} ${
                filled
                  ? "text-amber-400 fill-amber-400"
                  : half
                  ? "text-amber-400"
                  : "text-gray-200 fill-gray-200"
              }`}
              viewBox="0 0 24 24"
            >
              {half ? (
                <>
                  <defs>
                    <linearGradient id={`half-${star}`}>
                      <stop offset="50%" stopColor="#fbbf24" />
                      <stop offset="50%" stopColor="#e5e7eb" />
                    </linearGradient>
                  </defs>
                  <path
                    fill={`url(#half-${star})`}
                    d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
                  />
                </>
              ) : (
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              )}
            </svg>
          </button>
        );
      })}
    </div>
  );
}