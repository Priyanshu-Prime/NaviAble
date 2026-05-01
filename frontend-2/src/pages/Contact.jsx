import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const API_URL = process.env.REACT_APP_API_URL;

export default function Contact() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    subject: "",
    message: "",
  });

  const [errors, setErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const validate = () => {
    const e = {};

    if (!form.name.trim()) e.name = "Name is required.";
    if (!form.email.includes("@")) e.email = "Enter a valid email address.";
    if (!form.subject.trim()) e.subject = "Subject is required.";
    if (form.message.trim().length < 10)
      e.message = "Message must be at least 10 characters.";

    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    try {
      setLoading(true);

      await axios.post(`${API_URL}/contact`, form);

      setSubmitted(true);
    } catch (err) {
      console.error("Error sending message:", err);
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="bg-white min-h-[80vh] flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
            <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>

          <h2 className="text-xl font-bold text-gray-900 mb-2">
            Message Sent!
          </h2>

          <p className="text-gray-400 text-sm mb-6">
            Thanks for reaching out. We'll get back to you within 1–2 business days.
          </p>

          <Link
            to="/"
            className="bg-indigo-600 text-white px-5 py-2.5 rounded-lg hover:bg-indigo-700 text-sm"
          >
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white min-h-screen">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-14">

        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-400 mb-8">
          <Link to="/" className="hover:text-indigo-600">Home</Link>
          <span>/</span>
          <span className="text-gray-700 font-medium">Contact</span>
        </nav>

        {/* Header */}
        <div className="mb-10">
          <span className="inline-flex items-center bg-indigo-50 text-indigo-700 text-xs px-3 py-1.5 rounded-full mb-4 border">
            Get in Touch
          </span>

          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Contact Us
          </h1>

          <p className="text-gray-500">
            Have a question or suggestion? We'd love to hear from you.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">

          {/* Info */}
          <div className="space-y-4">
            {[
              { icon: "✉️", title: "Email", value: "hello@naviable.app" },
              { icon: "🐦", title: "Twitter", value: "@NaviAble" },
              { icon: "💬", title: "Response Time", value: "1–2 days" },
            ].map((item) => (
              <div key={item.title} className="bg-gray-50 p-4 rounded-xl border">
                <div className="text-xl">{item.icon}</div>
                <p className="text-xs text-gray-500">{item.title}</p>
                <p className="text-sm text-gray-800">{item.value}</p>
              </div>
            ))}
          </div>

          {/* Form */}
          <div className="md:col-span-2">
            <form onSubmit={handleSubmit} className="space-y-4">

              {/* Name */}
              <input
                type="text"
                placeholder="Name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full border px-3 py-2 rounded-lg"
              />
              {errors.name && <p className="text-red-500 text-xs">{errors.name}</p>}

              {/* Email */}
              <input
                type="email"
                placeholder="Email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full border px-3 py-2 rounded-lg"
              />
              {errors.email && <p className="text-red-500 text-xs">{errors.email}</p>}

              {/* Subject */}
              <input
                type="text"
                placeholder="Subject"
                value={form.subject}
                onChange={(e) => setForm({ ...form, subject: e.target.value })}
                className="w-full border px-3 py-2 rounded-lg"
              />
              {errors.subject && <p className="text-red-500 text-xs">{errors.subject}</p>}

              {/* Message */}
              <textarea
                rows={5}
                placeholder="Message"
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                className="w-full border px-3 py-2 rounded-lg"
              />
              {errors.message && <p className="text-red-500 text-xs">{errors.message}</p>}

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 text-white py-2.5 rounded-lg"
              >
                {loading ? "Sending..." : "Send Message"}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}