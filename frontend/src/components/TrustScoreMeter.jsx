/**
 * TrustScoreMeter — SVG circular gauge displaying the NaviAble Trust Score.
 *
 * Props
 * -----
 * score : number  — value in [0, 1]
 *
 * The gauge uses the SVG stroke-dashoffset technique to animate a coloured
 * arc proportional to the score.  Colour transitions from red (low) through
 * amber (medium) to teal (high) to give an immediate visual signal.
 */
export default function TrustScoreMeter({ score }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - Math.min(Math.max(score, 0), 1));

  // Colour: red < 0.4, amber 0.4–0.69, teal >= 0.7
  const color =
    score >= 0.7 ? '#2ec4b6' :
    score >= 0.4 ? '#ff9f1c' :
                   '#ef233c';

  const percent = Math.round(score * 100);

  // Accessibility verdict text
  const verdict =
    score >= 0.7 ? 'Strong evidence of accessibility' :
    score >= 0.4 ? 'Partial accessibility evidence' :
                   'Insufficient evidence';

  return (
    <div className="trust-meter" aria-label={`NaviAble Trust Score: ${percent}%. ${verdict}.`}>
      <svg
        viewBox="0 0 120 120"
        width="180"
        height="180"
        aria-hidden="true"
        role="img"
      >
        {/* Background track */}
        <circle
          cx="60" cy="60" r={radius}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="12"
        />
        {/* Score arc */}
        <circle
          cx="60" cy="60" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          transform="rotate(-90 60 60)"
          style={{ transition: 'stroke-dashoffset 0.9s ease, stroke 0.5s ease' }}
        />
        {/* Score number */}
        <text
          x="60" y="55"
          textAnchor="middle"
          fontSize="26"
          fontWeight="700"
          fill={color}
          style={{ transition: 'fill 0.5s ease' }}
        >
          {percent}
        </text>
        <text x="60" y="71" textAnchor="middle" fontSize="10" fill="var(--color-text-muted)">
          / 100
        </text>
        <text x="60" y="85" textAnchor="middle" fontSize="9" fill="var(--color-text-muted)">
          TRUST SCORE
        </text>
      </svg>

      <p className="trust-verdict" style={{ color }}>
        {verdict}
      </p>

      <p className="trust-formula">
        60 % vision · 40 % NLP
      </p>
    </div>
  );
}
