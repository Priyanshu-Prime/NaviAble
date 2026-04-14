import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="bg-white border-t border-gray-100 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
                <svg
                  className="w-3.5 h-3.5 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                  />
                </svg>
              </div>
              <span className="font-bold text-gray-900">
                Navi<span className="text-indigo-600">Able</span>
              </span>
            </div>

            <p className="text-sm text-gray-400 leading-relaxed max-w-xs">
              Crowdsourced accessibility discovery platform helping everyone
              navigate the world with confidence.
            </p>
          </div>

          {/* Platform Links */}
          <div>
            <h3 className="text-gray-900 font-semibold mb-3 text-sm">
              Platform
            </h3>
            <ul className="space-y-2">
              {[
                { to: "/explore", label: "Explore Places" },
                { to: "/add-review", label: "Add Review" },
                { to: "/profile", label: "My Profile" },
              ].map((l) => (
                <li key={l.to}>
                  <Link
                    to={l.to}
                    className="text-sm text-gray-400 hover:text-indigo-600 transition-colors"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Support Links */}
          <div>
            <h3 className="text-gray-900 font-semibold mb-3 text-sm">
              Support
            </h3>
            <ul className="space-y-2">
              {[
                { label: "About Us", to: "/about" },
                { label: "Accessibility Guide", to: "/accessibility-guide" },
                { label: "Contact", to: "/contact" },
                { label: "Privacy Policy", to: "/privacy-policy" },
              ].map((l) => (
                <li key={l.label}>
                  <Link
                    to={l.to}
                    className="text-sm text-gray-400 hover:text-indigo-600 transition-colors"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom */}
        <div className="border-t border-gray-100 mt-8 pt-6 flex flex-col sm:flex-row justify-between items-center gap-2">
          <p className="text-xs text-gray-400">
            © 2024 NaviAble. All rights reserved.
          </p>
          <p className="text-xs text-gray-400">
            Built for accessibility, by the community.
          </p>
        </div>
      </div>
    </footer>
  );
}