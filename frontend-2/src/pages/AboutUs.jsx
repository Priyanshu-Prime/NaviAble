import { Link } from "react-router-dom";

export default function AboutUs() {
  return (
    <div className="bg-white min-h-screen">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-400 mb-8">
          <Link to="/" className="hover:text-indigo-600 transition-colors">
            Home
          </Link>
          <span>/</span>
          <span className="text-gray-700 font-medium">About Us</span>
        </nav>

        {/* Header */}
        <div className="mb-10">
          <span className="inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 text-xs font-medium px-3 py-1.5 rounded-full mb-4 border border-indigo-100">
            Our Story
          </span>

          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            About NaviAble
          </h1>

          <p className="text-gray-500 leading-relaxed text-base">
            NaviAble is a crowdsourced accessibility discovery platform built to help
            everyone — regardless of ability — navigate the world with confidence.
            We believe that accessibility information should be freely available,
            community-driven, and easy to find.
          </p>
        </div>

        <div className="space-y-10">
          
          {/* Mission */}
          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-3">
              Our Mission
            </h2>
            <p className="text-gray-500 leading-relaxed">
              Our mission is to empower people with disabilities, caregivers,
              and accessibility advocates by providing a reliable, up-to-date
              database of accessibility features at locations worldwide.
              We do this by harnessing the power of community contributions.
            </p>
          </section>

          {/* How it works */}
          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-3">
              How It Works
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mt-4">
              {[
                {
                  step: "1",
                  title: "Discover",
                  desc: "Search for accessible locations near you using our map and filters.",
                },
                {
                  step: "2",
                  title: "Review",
                  desc: "Share your accessibility experience at any location.",
                },
                {
                  step: "3",
                  title: "Help Others",
                  desc: "Your reviews help others plan with confidence.",
                },
              ].map((item) => (
                <div
                  key={item.step}
                  className="bg-gray-50 rounded-xl p-5 border border-gray-100"
                >
                  <div className="w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center font-bold text-sm mb-3">
                    {item.step}
                  </div>

                  <h3 className="font-semibold text-gray-900 mb-1">
                    {item.title}
                  </h3>

                  <p className="text-sm text-gray-400">
                    {item.desc}
                  </p>
                </div>
              ))}
            </div>
          </section>

          {/* Values */}
          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-3">
              Our Values
            </h2>

            <ul className="space-y-3">
              {[
                {
                  title: "Inclusivity",
                  desc: "We design for everyone, ensuring our platform is accessible.",
                },
                {
                  title: "Community First",
                  desc: "Every feature is guided by real user needs.",
                },
                {
                  title: "Transparency",
                  desc: "Our data is community-sourced and open.",
                },
                {
                  title: "Continuous Improvement",
                  desc: "We improve based on feedback.",
                },
              ].map((v) => (
                <li
                  key={v.title}
                  className="flex gap-3 p-4 bg-white border border-gray-100 rounded-xl"
                >
                  <span className="text-indigo-500 mt-0.5">✦</span>
                  <div>
                    <span className="font-semibold text-gray-900 text-sm">
                      {v.title}:{" "}
                    </span>
                    <span className="text-sm text-gray-500">
                      {v.desc}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          {/* CTA */}
          <section className="bg-indigo-50 rounded-xl p-6 border border-indigo-100">
            <h2 className="text-lg font-bold text-indigo-900 mb-2">
              Join the Community
            </h2>

            <p className="text-sm text-indigo-700 mb-4">
              Help us build the most comprehensive accessibility map in the world.
            </p>

            <div className="flex gap-3">
              <Link
                to="/add-review"
                className="bg-indigo-600 text-white text-sm font-semibold px-5 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors"
              >
                Add a Review
              </Link>

              <Link
                to="/explore"
                className="bg-white text-indigo-600 text-sm font-semibold px-5 py-2.5 rounded-lg border border-indigo-200 hover:bg-indigo-50 transition-colors"
              >
                Explore Places
              </Link>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}