import { Link } from "react-router-dom";

const features = [
  {
    icon: "♿",
    title: "Wheelchair Access",
    desc: "Indicates step-free access throughout the location.",
    tips: [
      "Wide doorways (min 32 inches)",
      "Level or ramped entrances",
      "Accessible routes between floors",
    ],
  },
  {
    icon: "🔼",
    title: "Ramps",
    desc: "Ramps provide an alternative to steps for mobility access.",
    tips: [
      "Gentle slope (1:12 or less)",
      "Handrails on both sides",
      "Non-slip surfaces",
    ],
  },
  {
    icon: "🛗",
    title: "Elevator",
    desc: "Elevators enable access to multiple floors.",
    tips: [
      "Reachable buttons",
      "Audio announcements",
      "Adequate cabin size",
    ],
  },
  {
    icon: "🚻",
    title: "Accessible Restroom",
    desc: "Restrooms designed for wheelchair and mobility users.",
    tips: [
      "Grab bars near toilet",
      "60-inch turning radius",
      "Lowered sinks",
    ],
  },
  {
    icon: "⠿",
    title: "Braille Signage",
    desc: "Braille helps visually impaired users navigate.",
    tips: [
      "Reachable height",
      "Tactile maps",
      "High-contrast text",
    ],
  },
  {
    icon: "🔊",
    title: "Hearing Loop",
    desc: "Audio system for hearing aids with T-setting.",
    tips: [
      "Look for loop symbol",
      "Ask staff if active",
      "Works with modern hearing aids",
    ],
  },
  {
    icon: "🅿️",
    title: "Accessible Parking",
    desc: "Dedicated parking spaces near entrances.",
    tips: [
      "Minimum 8ft width",
      "Close to entrance",
      "Level ground",
    ],
  },
  {
    icon: "🚪",
    title: "Automatic Doors",
    desc: "Doors that open automatically.",
    tips: [
      "Wide sensor range",
      "Enough open time",
      "Manual override available",
    ],
  },
];

export default function AccessibilityGuide() {
  return (
    <div className="bg-white min-h-screen">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-400 mb-8">
          <Link to="/" className="hover:text-indigo-600 transition-colors">
            Home
          </Link>
          <span>/</span>
          <span className="text-gray-700 font-medium">
            Accessibility Guide
          </span>
        </nav>

        {/* Header */}
        <div className="mb-10">
          <span className="inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 text-xs font-medium px-3 py-1.5 rounded-full mb-4 border border-indigo-100">
            Reference Guide
          </span>

          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Accessibility Guide
          </h1>

          <p className="text-gray-500 leading-relaxed">
            Learn what each accessibility feature means and what to check when visiting a location.
          </p>
        </div>

        {/* Features */}
        <div className="space-y-5">
          {features.map((f) => (
            <div
              key={f.title}
              className="bg-white border border-gray-100 rounded-xl p-6 hover:border-indigo-200 transition-colors"
            >
              <div className="flex items-start gap-4">
                <div className="text-3xl">{f.icon}</div>

                <div className="flex-1">
                  <h2 className="text-base font-bold text-gray-900 mb-1">
                    {f.title}
                  </h2>

                  <p className="text-sm text-gray-500 mb-3">
                    {f.desc}
                  </p>

                  <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                    <p className="text-xs font-semibold text-gray-600 mb-2">
                      What to look for:
                    </p>

                    <ul className="space-y-1">
                      {f.tips.map((tip) => (
                        <li
                          key={tip}
                          className="text-xs text-gray-500 flex gap-2"
                        >
                          <span className="text-indigo-400">•</span>
                          {tip}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="mt-10 bg-indigo-50 rounded-xl p-6 border border-indigo-100">
          <h2 className="text-lg font-bold text-indigo-900 mb-2">
            Ready to contribute?
          </h2>

          <p className="text-sm text-indigo-700 mb-4">
            Use this guide when writing your next review.
          </p>

          <Link
            to="/add-review"
            className="inline-block bg-indigo-600 text-white text-sm font-semibold px-5 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Write a Review
          </Link>
        </div>

      </div>
    </div>
  );
}