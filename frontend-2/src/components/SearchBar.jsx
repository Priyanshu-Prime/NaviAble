import { useState, useRef } from "react";

export default function SearchBar({
  onSearch,
  placeholder = "Search locations...",
  large = false,
  value,
}) {
  const [query, setQuery] = useState(value || "");
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);

  const SpeechRecognitionAPI =
    typeof window !== "undefined"
      ? window.SpeechRecognition || window.webkitSpeechRecognition
      : null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(query.trim());
  };

  const handleChange = (e) => {
    setQuery(e.target.value);
  };

  const handleVoice = () => {
    if (!SpeechRecognitionAPI) return;

    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setQuery(transcript);
      onSearch(transcript);
    };

    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  const inputHeight = large ? "h-13" : "h-11";

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div
        className={`flex items-center bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100 transition-all ${inputHeight}`}
      >
        {/* Search Icon */}
        <div className="pl-4 text-gray-400 flex-shrink-0">
          <svg
            className={large ? "w-5 h-5" : "w-4 h-4"}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        {/* Input */}
        <input
          type="search"
          value={query}
          onChange={handleChange}
          placeholder={placeholder}
          className={`flex-1 px-3 bg-transparent outline-none text-gray-800 placeholder-gray-400 ${
            large ? "text-base" : "text-sm"
          }`}
        />

        {/* Voice Button */}
        {SpeechRecognitionAPI && (
          <button
            type="button"
            onClick={handleVoice}
            className={`px-3 transition-colors ${
              listening
                ? "text-red-500 animate-pulse"
                : "text-gray-400 hover:text-indigo-500"
            }`}
          >
            🎤
          </button>
        )}

        {/* Submit */}
        <button
          type="submit"
          className={`bg-indigo-600 text-white font-medium hover:bg-indigo-700 px-5 h-full ${
            large ? "text-sm" : "text-xs"
          }`}
        >
          Search
        </button>
      </div>

      {/* Listening Indicator */}
      {listening && (
        <p className="text-xs text-red-500 mt-1.5 ml-1">
          Listening...
        </p>
      )}
    </form>
  );
}