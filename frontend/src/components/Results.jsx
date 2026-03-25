import TrustScoreMeter from './TrustScoreMeter.jsx';
import DetectionViewer from './DetectionViewer.jsx';

/**
 * Results — Displays the full dual-AI verification output.
 *
 * Props
 * -----
 * result      : VerificationResponse  — the parsed API response
 * imageUrl    : string                — object URL of the uploaded image
 * onReset     : function              — called when user clicks "Verify Another"
 */
export default function Results({ result, imageUrl, onReset }) {
  const { data } = result;
  const { nlp_analysis, vision_analysis, naviable_trust_score } = data;

  const overallVerdict =
    naviable_trust_score >= 0.7 ? { text: 'Verified Accessible', cls: 'verdict--success', icon: '✅' } :
    naviable_trust_score >= 0.4 ? { text: 'Partially Verified',  cls: 'verdict--warning', icon: '⚠️' } :
                                   { text: 'Insufficient Evidence', cls: 'verdict--danger', icon: '❌' };

  return (
    <section className="results" aria-label="Verification results">
      {/* ── Header ───────────────────────────────────── */}
      <div className="results__header">
        <h2 className="results__title">Verification Complete</h2>
        <span className={`verdict-badge ${overallVerdict.cls}`} role="status">
          {overallVerdict.icon} {overallVerdict.text}
        </span>
      </div>

      {/* ── Trust Score ──────────────────────────────── */}
      <div className="results__trust">
        <TrustScoreMeter score={naviable_trust_score} />
      </div>

      {/* ── Dual-AI breakdown ────────────────────────── */}
      <div className="results__grid">

        {/* NLP Card */}
        <div className={`ai-card ${nlp_analysis.is_genuine ? 'ai-card--genuine' : 'ai-card--generic'}`}>
          <h3 className="ai-card__title">
            <span aria-hidden="true">🔤</span> NLP Integrity Engine
          </h3>
          <p className="ai-card__subtitle">RoBERTa · Fine-tuned on 402 labelled reviews</p>

          <div className="ai-card__verdict">
            <span className={`badge ${nlp_analysis.is_genuine ? 'badge--success' : 'badge--neutral'}`}>
              {nlp_analysis.is_genuine ? '✅ Genuine' : '⚠️ Generic'}
            </span>
            <span className="ai-card__label">{nlp_analysis.label}</span>
          </div>

          <div className="confidence-row">
            <span className="confidence-label">Confidence</span>
            <div
              className="confidence-track"
              role="meter"
              aria-valuenow={Math.round(nlp_analysis.confidence * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`NLP confidence: ${Math.round(nlp_analysis.confidence * 100)}%`}
            >
              <div
                className="confidence-fill confidence-fill--nlp"
                style={{ width: `${nlp_analysis.confidence * 100}%` }}
              />
            </div>
            <span className="confidence-value">{Math.round(nlp_analysis.confidence * 100)}%</span>
          </div>

          <p className="ai-card__explanation">
            {nlp_analysis.is_genuine
              ? 'The review contains specific, verifiable accessibility details — not generic praise.'
              : 'The review lacks specific physical detail and may not reliably indicate accessibility.'}
          </p>
        </div>

        {/* Vision Card */}
        <div className="ai-card ai-card--vision">
          <h3 className="ai-card__title">
            <span aria-hidden="true">👁️</span> Vision Detection
          </h3>
          <p className="ai-card__subtitle">YOLOv11 · mAP@0.5: 47.29 % (Epoch 25)</p>

          <div className="ai-card__verdict">
            <span className={`badge ${vision_analysis.objects_detected > 0 ? 'badge--success' : 'badge--neutral'}`}>
              {vision_analysis.objects_detected > 0
                ? `✅ ${vision_analysis.objects_detected} feature${vision_analysis.objects_detected !== 1 ? 's' : ''} found`
                : '⚠️ No features detected'}
            </span>
          </div>

          {vision_analysis.features.length > 0 && (
            <ul className="feature-pills" aria-label="Detected features">
              {vision_analysis.features.map((f, i) => (
                <li key={i} className="feature-pill">
                  {f.class.replace(/_/g, '\u00a0')}
                  <span className="feature-pill__conf">{Math.round(f.confidence * 100)}%</span>
                </li>
              ))}
            </ul>
          )}

          <p className="ai-card__explanation">
            {vision_analysis.objects_detected > 0
              ? 'Physical accessibility infrastructure was detected in the uploaded image.'
              : 'No accessibility features were detected above the 50 % confidence threshold.'}
          </p>
        </div>
      </div>

      {/* ── Detection Viewer (image + bboxes) ────────── */}
      <DetectionViewer imageUrl={imageUrl} features={vision_analysis.features} />

      {/* ── Reset ────────────────────────────────────── */}
      <div className="results__footer">
        <button className="btn btn--outline" onClick={onReset}>
          ← Verify Another Location
        </button>
        <p className="results__disclaimer">
          NaviAble Trust Score formula: <code>0.60 × vision + 0.40 × NLP</code>.
          Scores ≥ 0.70 indicate strong evidence of physical accessibility.
        </p>
      </div>
    </section>
  );
}
