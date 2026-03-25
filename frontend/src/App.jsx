import { useState, useEffect, useCallback } from 'react';
import SubmitForm from './components/SubmitForm.jsx';
import Results from './components/Results.jsx';
import { verifyAccessibility, fetchHealth } from './api/client.js';

/**
 * App — Root component for the NaviAble web demo.
 *
 * State machine
 * -------------
 *  'idle'    → form shown; user fills in image + review
 *  'loading' → API request in flight; spinner shown
 *  'result'  → verification complete; Results panel shown
 *  'error'   → request failed; error message shown
 */
export default function App() {
  const [view, setView] = useState('idle');          // 'idle' | 'loading' | 'result' | 'error'
  const [result, setResult] = useState(null);        // VerificationResponse
  const [imageUrl, setImageUrl] = useState(null);    // object URL for DetectionViewer
  const [errorMsg, setErrorMsg] = useState('');
  const [healthStatus, setHealthStatus] = useState(null); // null | health object

  // ── Backend connectivity check on mount ────────────────────────────
  useEffect(() => {
    fetchHealth()
      .then(setHealthStatus)
      .catch(() => setHealthStatus({ status: 'unreachable' }));
  }, []);

  // ── Form submission ─────────────────────────────────────────────────
  const handleSubmit = useCallback(async ({ image, textReview, locationId }) => {
    setView('loading');
    setErrorMsg('');

    // Persist image URL for the results panel
    const url = URL.createObjectURL(image);
    setImageUrl(url);

    try {
      const data = await verifyAccessibility({ image, textReview, locationId });
      setResult(data);
      setView('result');
    } catch (err) {
      setErrorMsg(err.message || 'An unexpected error occurred.');
      setView('error');
    }
  }, []);

  const handleReset = useCallback(() => {
    setView('idle');
    setResult(null);
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    setImageUrl(null);
    setErrorMsg('');
  }, [imageUrl]);

  // ── Backend status banner ───────────────────────────────────────────
  const renderStatusBanner = () => {
    if (!healthStatus) return null;
    if (healthStatus.status === 'unreachable') {
      return (
        <div className="banner banner--error" role="alert">
          <strong>Backend Unreachable</strong> — Start the FastAPI server with{' '}
          <code>NAVIABLE_DEMO_MODE=true uvicorn app.main:app --reload --port 8000</code>
        </div>
      );
    }
    if (healthStatus.demo_mode) {
      return (
        <div className="banner banner--info" role="status">
          🔬 <strong>Demo Mode</strong> — Synthetic ML results are being returned.
          Load real model weights to disable this banner.
        </div>
      );
    }
    return (
      <div className="banner banner--success" role="status">
        ✅ Backend connected · YOLO: <strong>{healthStatus.services?.yolo}</strong> ·
        RoBERTa: <strong>{healthStatus.services?.roberta}</strong>
      </div>
    );
  };

  return (
    <div className="app">
      {/* ── Header ─────────────────────────────────── */}
      <header className="app-header" role="banner">
        <div className="header-inner">
          <div className="header-brand">
            <span className="header-icon" aria-hidden="true">♿</span>
            <div>
              <h1 className="header-title">NaviAble</h1>
              <p className="header-tagline">Dual-AI Accessibility Verification</p>
            </div>
          </div>
          <div className="header-meta">
            <span className="header-badge">YOLOv11 + RoBERTa</span>
            <span className="header-badge header-badge--dim">IIIT Trichy · Team 7</span>
          </div>
        </div>
      </header>

      {/* ── Status Banner ──────────────────────────── */}
      {renderStatusBanner()}

      {/* ── Main Content ───────────────────────────── */}
      <main className="app-main" role="main">
        {(view === 'idle' || view === 'loading' || view === 'error') && (
          <div className="layout">
            {/* Left: Form */}
            <div className="layout__form">
              <SubmitForm onSubmit={handleSubmit} isLoading={view === 'loading'} />

              {view === 'error' && (
                <div className="error-card" role="alert">
                  <strong>Verification failed</strong>
                  <p>{errorMsg}</p>
                  <button className="btn btn--outline btn--sm" onClick={handleReset}>
                    Try again
                  </button>
                </div>
              )}
            </div>

            {/* Right: How It Works explainer */}
            <aside className="layout__explainer" aria-label="How NaviAble works">
              <HowItWorks />
            </aside>
          </div>
        )}

        {view === 'result' && result && (
          <Results result={result} imageUrl={imageUrl} onReset={handleReset} />
        )}
      </main>

      {/* ── Footer ─────────────────────────────────── */}
      <footer className="app-footer" role="contentinfo">
        <p>
          NaviAble · IIIT Trichy Final Year Project 2024 · Team 7 ·
          Built with FastAPI + YOLOv11 + RoBERTa
        </p>
      </footer>
    </div>
  );
}

// ── Inline explainer component ──────────────────────────────────────────────

function HowItWorks() {
  const steps = [
    {
      icon: '📸',
      title: 'Upload a Photo',
      desc: 'Take or upload a JPEG/PNG photo of the entrance, ramp, doorway, or any accessibility feature.',
    },
    {
      icon: '✍️',
      title: 'Write a Review',
      desc: 'Describe what you observe. Be specific — mention ramps, handrails, doorway widths, and slopes.',
    },
    {
      icon: '👁️',
      title: 'Vision Analysis',
      desc: 'YOLOv11 scans the image for physical features: ramps, handrails, tactile paving, accessible doorways.',
    },
    {
      icon: '🔤',
      title: 'NLP Verification',
      desc: 'Fine-tuned RoBERTa classifies your review as genuine physical detail or generic praise.',
    },
    {
      icon: '🏆',
      title: 'Trust Score',
      desc: 'A composite score (60% vision + 40% NLP) measures the overall accessibility evidence.',
    },
  ];

  return (
    <div className="explainer">
      <h2 className="explainer__title">How It Works</h2>
      <ol className="explainer__steps" aria-label="NaviAble verification steps">
        {steps.map((s, i) => (
          <li key={i} className="explainer__step">
            <span className="step-icon" aria-hidden="true">{s.icon}</span>
            <div>
              <h3 className="step-title">{s.title}</h3>
              <p className="step-desc">{s.desc}</p>
            </div>
          </li>
        ))}
      </ol>

      <div className="model-stats">
        <h3 className="model-stats__title">Model Performance</h3>
        <div className="stat-grid">
          <div className="stat">
            <span className="stat__label">YOLO mAP@0.5</span>
            <span className="stat__value">47.29%</span>
          </div>
          <div className="stat">
            <span className="stat__label">RoBERTa Accuracy</span>
            <span className="stat__value">87.65%</span>
          </div>
          <div className="stat">
            <span className="stat__label">Training Epochs</span>
            <span className="stat__value">YOLO: 25 · NLP: 5</span>
          </div>
          <div className="stat">
            <span className="stat__label">NLP Dataset</span>
            <span className="stat__value">402 rows (balanced)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
