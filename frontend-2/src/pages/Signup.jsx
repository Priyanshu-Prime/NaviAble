import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Signup({ onLogin }) {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirm: "",
  });

  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [agreed, setAgreed] = useState(false);

  const validate = () => {
    const e = {};

    if (form.name.trim().length < 2) {
      e.name = "Name must be at least 2 characters.";
    }

    if (!form.email.includes("@")) {
      e.email = "Enter a valid email address.";
    }

    if (form.password.length < 6) {
      e.password = "Password must be at least 6 characters.";
    }

    if (form.password !== form.confirm) {
      e.confirm = "Passwords do not match.";
    }

    if (!agreed) {
      e.agreed = "You must agree to the terms.";
    }

    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!validate()) return;

    setLoading(true);

    setTimeout(() => {
      setLoading(false);
      onLogin();
      navigate("/profile");
    }, 800);
  };

  return (
    <div className="bg-white min-h-[80vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <span className="text-white text-xl">👤</span>
          </div>
          <h1 className="text-xl font-bold text-gray-900">
            Create your account
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Join the NaviAble community
          </p>
        </div>

        {/* Form */}
        <div className="bg-white rounded-xl border border-gray-100 p-7 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">
                Full Name
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) =>
                  setForm({ ...form, name: e.target.value })
                }
                placeholder="John Doe"
                className={`w-full px-3 py-2.5 rounded-lg border text-sm ${
                  errors.name ? "border-red-400" : "border-gray-200"
                }`}
              />
              {errors.name && (
                <p className="text-red-500 text-xs mt-1">
                  {errors.name}
                </p>
              )}
            </div>

            {/* Email */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">
                Email
              </label>
              <input
                type="email"
                value={form.email}
                onChange={(e) =>
                  setForm({ ...form, email: e.target.value })
                }
                placeholder="you@example.com"
                className={`w-full px-3 py-2.5 rounded-lg border text-sm ${
                  errors.email ? "border-red-400" : "border-gray-200"
                }`}
              />
              {errors.email && (
                <p className="text-red-500 text-xs mt-1">
                  {errors.email}
                </p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={form.password}
                onChange={(e) =>
                  setForm({ ...form, password: e.target.value })
                }
                placeholder="Min. 6 characters"
                className={`w-full px-3 py-2.5 rounded-lg border text-sm ${
                  errors.password ? "border-red-400" : "border-gray-200"
                }`}
              />
              {errors.password && (
                <p className="text-red-500 text-xs mt-1">
                  {errors.password}
                </p>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">
                Confirm Password
              </label>
              <input
                type="password"
                value={form.confirm}
                onChange={(e) =>
                  setForm({ ...form, confirm: e.target.value })
                }
                placeholder="Repeat your password"
                className={`w-full px-3 py-2.5 rounded-lg border text-sm ${
                  errors.confirm ? "border-red-400" : "border-gray-200"
                }`}
              />
              {errors.confirm && (
                <p className="text-red-500 text-xs mt-1">
                  {errors.confirm}
                </p>
              )}
            </div>

            {/* Terms */}
            <label className="flex items-center gap-2 text-xs text-gray-500">
              <input
                type="checkbox"
                checked={agreed}
                onChange={() => setAgreed(!agreed)}
              />
              I agree to the{" "}
              <span className="text-indigo-600">Terms</span> and{" "}
              <span className="text-indigo-600">Privacy Policy</span>
            </label>

            {errors.agreed && (
              <p className="text-red-500 text-xs">{errors.agreed}</p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 text-white py-2.5 rounded-lg"
            >
              {loading ? "Creating account..." : "Create Account"}
            </button>
          </form>

          {/* Footer */}
          <p className="text-sm text-gray-400 text-center mt-4">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-indigo-600 font-medium"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}