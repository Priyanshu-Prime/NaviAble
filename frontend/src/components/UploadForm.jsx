import { useState, useRef } from "react";

export default function UploadForm({ onImagesChange, maxFiles = 5 }) {
  const [previews, setPreviews] = useState([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const handleFiles = (files) => {
    if (!files) return;

    const arr = Array.from(files).slice(0, maxFiles - previews.length);
    const newPreviews = arr.map((file) => URL.createObjectURL(file));

    setPreviews((prev) => [...prev, ...newPreviews]);

    if (onImagesChange) {
      onImagesChange(arr);
    }
  };

  const removeImage = (index) => {
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Photos{" "}
        <span className="text-gray-400 font-normal">
          (up to {maxFiles})
        </span>
      </label>

      {/* Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current && inputRef.current.click()}
        onKeyDown={(e) =>
          e.key === "Enter" && inputRef.current && inputRef.current.click()
        }
        role="button"
        tabIndex={0}
        aria-label="Upload images"
        className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-colors ${
          dragging
            ? "border-indigo-400 bg-indigo-50"
            : "border-gray-200 hover:border-indigo-300 hover:bg-gray-50"
        }`}
      >
        <div className="flex flex-col items-center gap-2">
          <div className="w-12 h-12 bg-indigo-50 rounded-xl flex items-center justify-center">
            <svg
              className="w-6 h-6 text-indigo-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700">
              Drop photos here or click to upload
            </p>
            <p className="text-xs text-gray-400 mt-0.5">
              PNG, JPG, WEBP up to 10MB each
            </p>
          </div>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {/* Previews */}
      {previews.length > 0 && (
        <div className="flex flex-wrap gap-3 mt-4">
          {previews.map((src, i) => (
            <div key={i} className="relative group">
              <img
                src={src}
                alt={`Preview ${i + 1}`}
                className="w-24 h-24 object-cover rounded-xl border border-gray-200"
              />

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  removeImage(i);
                }}
                className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}