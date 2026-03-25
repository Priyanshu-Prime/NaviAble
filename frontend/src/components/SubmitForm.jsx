import { useState, useCallback } from 'react';

/**
 * SubmitForm — Image upload + text review form.
 *
 * Props
 * -----
 * onSubmit(formValues) : async function called when the user clicks "Verify"
 * isLoading : boolean — disables the form while a request is in flight
 */
export default function SubmitForm({ onSubmit, isLoading }) {
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [textReview, setTextReview] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});

  // ── Image handling ──────────────────────────────────────────────────
  const handleFile = useCallback((file) => {
    if (!file) return;
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      setFieldErrors((e) => ({ ...e, image: 'Only JPEG and PNG images are supported.' }));
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setFieldErrors((e) => ({ ...e, image: 'Image must be smaller than 10 MB.' }));
      return;
    }
    setFieldErrors((e) => ({ ...e, image: null }));
    setImage(file);
    setImagePreview(URL.createObjectURL(file));
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragOver(false);
      handleFile(e.dataTransfer.files[0]);
    },
    [handleFile],
  );

  // ── Submission ──────────────────────────────────────────────────────
  const handleSubmit = (e) => {
    e.preventDefault();
    const errors = {};
    if (!image) errors.image = 'Please upload an image.';
    if (!textReview.trim()) errors.textReview = 'Please enter a review.';
    if (Object.keys(errors).length) {
      setFieldErrors(errors);
      return;
    }
    // Generate a random UUID for the location in demo context
    const locationId = crypto.randomUUID();
    onSubmit({ image, textReview, locationId });
  };

  return (
    <form className="submit-form" onSubmit={handleSubmit} noValidate>
      <h2 className="form-title">Submit a Review</h2>
      <p className="form-subtitle">
        Upload a photo of the location and describe the accessibility features
        you observed. The AI will verify the evidence.
      </p>

      {/* ── Image Upload ─────────────────────────────── */}
      <div className="field-group">
        <label className="field-label" htmlFor="image-upload">
          Location Photo <span className="required">*</span>
        </label>

        <div
          className={`dropzone ${dragOver ? 'dropzone--active' : ''} ${imagePreview ? 'dropzone--has-image' : ''}`}
          role="button"
          tabIndex={0}
          aria-label="Upload image. Drag and drop a JPEG or PNG, or click to browse."
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById('image-upload').click()}
          onKeyDown={(e) => e.key === 'Enter' && document.getElementById('image-upload').click()}
        >
          {imagePreview ? (
            <img src={imagePreview} alt="Selected location" className="dropzone__preview" />
          ) : (
            <div className="dropzone__placeholder">
              <span className="dropzone__icon" aria-hidden="true">📸</span>
              <p>Drag &amp; drop an image here, or <strong>click to browse</strong></p>
              <p className="dropzone__hint">JPEG or PNG · max 10 MB</p>
            </div>
          )}
        </div>

        <input
          id="image-upload"
          type="file"
          accept="image/jpeg,image/png"
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          onChange={(e) => handleFile(e.target.files[0])}
        />

        {fieldErrors.image && (
          <p className="field-error" role="alert">{fieldErrors.image}</p>
        )}

        {image && (
          <p className="file-info">
            {image.name} &middot; {(image.size / 1024).toFixed(0)} KB
            <button
              type="button"
              className="link-btn"
              aria-label="Remove selected image"
              onClick={(e) => { e.stopPropagation(); setImage(null); setImagePreview(null); }}
            >
              Remove
            </button>
          </p>
        )}
      </div>

      {/* ── Text Review ──────────────────────────────── */}
      <div className="field-group">
        <label className="field-label" htmlFor="text-review">
          Accessibility Review <span className="required">*</span>
        </label>
        <textarea
          id="text-review"
          className={`textarea ${fieldErrors.textReview ? 'textarea--error' : ''}`}
          rows={5}
          placeholder="Describe what you saw: ramps, handrails, doorway widths, lift access, tactile paving…"
          value={textReview}
          onChange={(e) => {
            setTextReview(e.target.value);
            setFieldErrors((err) => ({ ...err, textReview: null }));
          }}
          aria-describedby={fieldErrors.textReview ? 'review-error' : undefined}
          aria-invalid={!!fieldErrors.textReview}
        />
        {fieldErrors.textReview && (
          <p id="review-error" className="field-error" role="alert">{fieldErrors.textReview}</p>
        )}
        <p className="char-count" aria-live="polite">
          {textReview.length} character{textReview.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* ── Submit ───────────────────────────────────── */}
      <button
        type="submit"
        className="btn btn--primary btn--full"
        disabled={isLoading}
        aria-busy={isLoading}
      >
        {isLoading ? (
          <>
            <span className="spinner" aria-hidden="true" />
            Analysing…
          </>
        ) : (
          '⚡ Verify Accessibility'
        )}
      </button>

      <p className="form-footer">
        Your submission is analysed by both a <strong>YOLOv11 vision model</strong> and a
        &nbsp;<strong>RoBERTa NLP classifier</strong> running concurrently.
      </p>
    </form>
  );
}
