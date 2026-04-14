import { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";

import Navbar from "./components/Navbar";
import Footer from "./components/Footer";

import Home from "./pages/Home";
import Explore from "./pages/Explore";
import LocationDetail from "./pages/LocationDetail";
import AddReview from "./pages/AddReview";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Profile from "./pages/Profile";
import AboutUs from "./pages/AboutUs";
import AccessibilityGuide from "./pages/AccessibilityGuide";
import Contact from "./pages/Contact";
import PrivacyPolicy from "./pages/PrivacyPolicy";

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const handleLogin = () => setIsLoggedIn(true);
  const handleLogout = () => setIsLoggedIn(false);

  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-gray-50">
        <Navbar isLoggedIn={isLoggedIn} onLogout={handleLogout} />

        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/explore" element={<Explore />} />
            <Route path="/location/:id" element={<LocationDetail />} />
            <Route path="/add-review" element={<AddReview />} />

            <Route path="/login" element={<Login onLogin={handleLogin} />} />
            <Route path="/signup" element={<Signup onLogin={handleLogin} />} />

            <Route path="/profile" element={<Profile />} />
            <Route path="/about" element={<AboutUs />} />
            <Route path="/accessibility-guide" element={<AccessibilityGuide />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/privacy-policy" element={<PrivacyPolicy />} />
          </Routes>
        </main>

        <Footer />
        <Toaster position="top-right" />
      </div>
    </BrowserRouter>
  );
}