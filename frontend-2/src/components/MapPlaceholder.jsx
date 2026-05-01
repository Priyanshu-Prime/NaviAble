export default function MapPlaceholder() {
  return (
    <div className="relative w-full h-full min-h-[300px] bg-gray-50 rounded-xl overflow-hidden border border-gray-200">
      
      {/* Grid */}
      <svg
        className="absolute inset-0 w-full h-full"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="map-grid" width="48" height="48" patternUnits="userSpaceOnUse">
            <path d="M 48 0 L 0 0 0 48" fill="none" stroke="#e5e7eb" strokeWidth="1" />
          </pattern>
        </defs>

        <rect width="100%" height="100%" fill="url(#map-grid)" />

        {/* Roads */}
        <line x1="0" y1="50%" x2="100%" y2="50%" stroke="#d1d5db" strokeWidth="10" />
        <line x1="32%" y1="0" x2="32%" y2="100%" stroke="#d1d5db" strokeWidth="7" />
        <line x1="68%" y1="0" x2="68%" y2="100%" stroke="#d1d5db" strokeWidth="7" />

        {/* Blocks */}
        <rect x="5%" y="5%" width="22%" height="18%" rx="4" fill="#f3f4f6" />
      </svg>

      {/* Pins */}
      {[
        { x: "32%", y: "44%", label: "Library", primary: true },
        { x: "55%", y: "58%", label: "Cafe", primary: false },
      ].map((pin) => (
        <div
          key={pin.label}
          className="absolute transform -translate-x-1/2 -translate-y-full"
          style={{ left: pin.x, top: pin.y }}
        >
          <div className="relative group">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center shadow-md border-2 border-white ${
                pin.primary ? "bg-indigo-600" : "bg-white"
              }`}
            >
              <span>{pin.primary ? "📍" : "📌"}</span>
            </div>

            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100">
              {pin.label}
            </div>
          </div>
        </div>
      ))}

      {/* Badge */}
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2">
        <div className="bg-white border border-gray-200 rounded-lg px-3 py-1.5 shadow-sm">
          <p className="text-xs text-gray-500 font-medium">
            Map view — coming soon
          </p>
        </div>
      </div>
    </div>
  );
}