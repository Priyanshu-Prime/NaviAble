import { Link } from "react-router-dom";

const sections = [
  {
    title: "Information We Collect",
    content: `We collect information you provide directly to us, such as when you create an account, submit a review, or contact us. This includes:
    
• Account information: name, email address, and password.
• Review content: text, ratings, photos, and accessibility feature selections you submit.
• Usage data: pages visited, search queries, and interactions with the platform.
• Device information: browser type, operating system, and IP address.`,
  },
  {
    title: "How We Use Your Information",
    content: `We use the information we collect to:

• Provide, maintain, and improve our services.
• Display your reviews and contributions on the platform.
• Send you service-related communications.
• Respond to your comments and questions.
• Monitor and improve user experience.
• Prevent fraud or abuse.`,
  },
  {
    title: "Sharing of Information",
    content: `We do not sell your personal information. We may share your information in the following circumstances:

• Public contributions: Reviews are visible publicly.
• Service providers: Trusted vendors (hosting, analytics).
• Legal requirements: If required by law.`,
  },
  {
    title: "Data Retention",
    content: `We retain your data as long as your account is active. You can request deletion anytime. Some public reviews may remain anonymized.`,
  },
  {
    title: "Cookies",
    content: `We use cookies to maintain sessions and improve experience. Disabling cookies may affect functionality.`,
  },
  {
    title: "Security",
    content: `We use HTTPS and industry-standard protections. However, no system is 100% secure.`,
  },
  {
    title: "Your Rights",
    content: `You may have rights to access, update, delete, or restrict your data depending on your location.

Contact: privacy@naviable.app`,
  },
  {
    title: "Children's Privacy",
    content: `We do not knowingly collect data from children under 13.`,
  },
  {
    title: "Changes to This Policy",
    content: `We may update this policy. Continued use means acceptance of updates.`,
  },
  {
    title: "Contact Us",
    content: `Email: privacy@naviable.app
NaviAble, Inc.
San Francisco, CA`,
  },
];

// helper to create clean IDs
const getId = (title) =>
  title.toLowerCase().replace(/[^a-z0-9]+/g, "-");

export default function PrivacyPolicy() {
  return (
    <div className="bg-white min-h-screen scroll-smooth">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-14">

        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-400 mb-8">
          <Link to="/" className="hover:text-indigo-600">Home</Link>
          <span>/</span>
          <span className="text-gray-700 font-medium">Privacy Policy</span>
        </nav>

        {/* Header */}
        <div className="mb-10">
          <span className="inline-block bg-indigo-50 text-indigo-700 text-xs px-3 py-1 rounded-full mb-4">
            Legal
          </span>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Privacy Policy
          </h1>
          <p className="text-sm text-gray-400">Effective: Jan 1, 2024</p>
          <p className="text-gray-500 mt-4">
            We value your privacy. This page explains how your data is collected
            and used.
          </p>
        </div>

        {/* Table of Contents */}
        <div className="bg-gray-50 rounded-xl p-5 border mb-8 sticky top-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Table of Contents
          </h2>
          <ol className="space-y-2">
            {sections.map((s, i) => (
              <li key={i}>
                <a
                  href={`#${getId(s.title)}`}
                  className="text-sm text-indigo-600 hover:underline"
                >
                  {i + 1}. {s.title}
                </a>
              </li>
            ))}
          </ol>
        </div>

        {/* Sections */}
        <div className="space-y-10">
          {sections.map((s, i) => (
            <section key={i} id={getId(s.title)}>
              <h2 className="text-lg font-bold text-gray-900 mb-3">
                {i + 1}. {s.title}
              </h2>
              <p className="text-sm text-gray-500 whitespace-pre-line leading-relaxed">
                {s.content}
              </p>
            </section>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-12 border-t pt-8 flex flex-col sm:flex-row gap-3">
          <Link
            to="/contact"
            className="bg-indigo-600 text-white px-5 py-2.5 rounded-lg text-sm text-center"
          >
            Contact Us
          </Link>
          <Link
            to="/"
            className="border px-5 py-2.5 rounded-lg text-sm text-center"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}