import { useRef, useState, useEffect } from 'react';

/**
 * DetectionViewer — Displays the uploaded image with YOLO bounding boxes.
 *
 * Bounding box coordinates from the API are in the original image's pixel
 * space.  This component scales them to match the *displayed* image size
 * by comparing naturalWidth/naturalHeight with the rendered clientWidth/Height.
 *
 * Props
 * -----
 * imageUrl    : string  — object URL for the uploaded image
 * features    : Array   — list of detection objects {class, confidence, bbox}
 */

// Consistent colour per class label
const CLASS_COLORS = {
  ramp: '#4cc9f0',
  handrail: '#f72585',
  flat_entrance: '#7209b7',
  accessible_doorway: '#4361ee',
  tactile_paving: '#3a0ca3',
  elevator: '#4895ef',
  accessible_parking: '#560bad',
};

function colorFor(cls) {
  return CLASS_COLORS[cls] ?? '#2ec4b6';
}

export default function DetectionViewer({ imageUrl, features }) {
  const imgRef = useRef(null);
  const [scale, setScale] = useState({ x: 1, y: 1 });

  const updateScale = () => {
    const img = imgRef.current;
    if (!img || !img.naturalWidth) return;
    setScale({
      x: img.clientWidth  / img.naturalWidth,
      y: img.clientHeight / img.naturalHeight,
    });
  };

  useEffect(() => {
    window.addEventListener('resize', updateScale);
    return () => window.removeEventListener('resize', updateScale);
  }, []);

  return (
    <div className="detection-viewer">
      <h3 className="section-label">Vision Analysis</h3>

      {features.length === 0 ? (
        <p className="no-detections">No accessibility features detected above threshold.</p>
      ) : (
        <p className="detections-summary">
          Detected <strong>{features.length}</strong> accessibility feature{features.length !== 1 ? 's' : ''}
        </p>
      )}

      <div
        className="image-container"
        role="img"
        aria-label={`Uploaded location photo with ${features.length} detected accessibility features`}
      >
        <img
          ref={imgRef}
          src={imageUrl}
          alt="Uploaded location"
          className="detection-image"
          onLoad={updateScale}
        />

        {features.map((feat, idx) => {
          const [x1, y1, x2, y2] = feat.bbox;
          const color = colorFor(feat.class);
          return (
            <div
              key={idx}
              className="bbox"
              style={{
                left:   x1 * scale.x,
                top:    y1 * scale.y,
                width:  (x2 - x1) * scale.x,
                height: (y2 - y1) * scale.y,
                borderColor: color,
              }}
              aria-label={`${feat.class} detected with ${Math.round(feat.confidence * 100)}% confidence`}
            >
              <span className="bbox__label" style={{ backgroundColor: color }}>
                {feat.class.replace(/_/g, ' ')} {Math.round(feat.confidence * 100)}%
              </span>
            </div>
          );
        })}
      </div>

      {/* Feature list table */}
      {features.length > 0 && (
        <table className="feature-table" aria-label="Detected accessibility features">
          <thead>
            <tr>
              <th scope="col">Feature</th>
              <th scope="col">Confidence</th>
              <th scope="col">Bounding Box</th>
            </tr>
          </thead>
          <tbody>
            {features.map((feat, idx) => (
              <tr key={idx}>
                <td>
                  <span
                    className="feature-dot"
                    style={{ backgroundColor: colorFor(feat.class) }}
                    aria-hidden="true"
                  />
                  {feat.class.replace(/_/g, ' ')}
                </td>
                <td>
                  <div className="conf-bar-wrap" role="meter" aria-valuenow={Math.round(feat.confidence * 100)} aria-valuemin={0} aria-valuemax={100}>
                    <div
                      className="conf-bar"
                      style={{
                        width: `${feat.confidence * 100}%`,
                        backgroundColor: colorFor(feat.class),
                      }}
                    />
                    <span>{Math.round(feat.confidence * 100)}%</span>
                  </div>
                </td>
                <td className="bbox-coords">
                  [{feat.bbox.join(', ')}]
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
