# NaviAble — Web Frontend

React web application for demonstrating the **NaviAble Dual-AI Accessibility Verification Platform**.

---

## What It Does

The frontend provides an interactive demo interface that lets users:

1. **Upload a photo** of a location (drag-and-drop or file picker).
2. **Write a review** describing observed accessibility features.
3. **Submit to the backend** which runs YOLOv11 (vision) + RoBERTa (NLP) concurrently.
4. **See the results** — including a circular Trust Score gauge, NLP classification card, YOLO detection card, and the uploaded image with bounding boxes overlaid on every detected feature.

---

## Quick Start

### Prerequisites
- Node.js ≥ 18 (check with `node --version`)
- npm ≥ 9 (check with `npm --version`)
- The NaviAble backend running on `http://localhost:8000`

### 1. Install dependencies

```bash
cd frontend/
npm install
```

### 2. Start the backend (in a separate terminal)

```bash
cd backend/
NAVIABLE_DEMO_MODE=true uvicorn app.main:app --reload --port 8000
```

On Windows PowerShell:
```powershell
cd backend/
$env:NAVIABLE_DEMO_MODE="true"
uvicorn app.main:app --reload --port 8000
```

### 3. Start the frontend dev server

```bash
npm run dev
```

Open **http://localhost:5173** in your browser.

The Vite dev server automatically proxies all `/api/*` and `/health` requests to the backend at `http://localhost:8000`, so no CORS configuration is needed during development.

---

## Project Structure

```
frontend/
├── index.html                   # HTML entry point
├── package.json                 # Dependencies: React 18 + Vite
├── vite.config.js               # Dev server config + API proxy
└── src/
    ├── main.jsx                 # React root render
    ├── App.jsx                  # Root component + state machine
    ├── App.css                  # All styles (CSS variables + BEM-inspired)
    ├── api/
    │   └── client.js            # fetchHealth() + verifyAccessibility()
    └── components/
        ├── SubmitForm.jsx       # Image upload + text review form
        ├── Results.jsx          # Full results panel
        ├── TrustScoreMeter.jsx  # SVG circular gauge for trust score
        └── DetectionViewer.jsx  # Image + scaled YOLO bounding boxes
```

---

## Component Guide

### `App.jsx`

Root component managing a four-state machine:

| State     | Description                                  |
|-----------|----------------------------------------------|
| `idle`    | Form + "How It Works" panel shown            |
| `loading` | Request in flight; form disabled with spinner |
| `result`  | Verification complete; `Results` panel shown  |
| `error`   | Request failed; error card shown              |

Also performs a `/health` check on mount to detect whether the backend is reachable and whether demo mode is active.

---

### `SubmitForm.jsx`

- Drag-and-drop zone + hidden file input (click to browse).
- Validates file type (`image/jpeg`, `image/png`) and size (≤ 10 MB) client-side.
- Generates a random UUID (`crypto.randomUUID()`) for `location_id`.
- Full keyboard accessibility (tab focus, Enter to open file picker).
- ARIA attributes: `aria-busy`, `aria-invalid`, `aria-describedby`, `role="alert"`.

---

### `TrustScoreMeter.jsx`

SVG circular gauge using the `stroke-dashoffset` technique:

```
score = 0.0 → empty arc  (red)
score = 0.5 → half arc   (amber)
score = 1.0 → full arc   (teal)
```

Includes smooth CSS `transition` on `stroke-dashoffset` so the needle animates in when results arrive.

---

### `DetectionViewer.jsx`

Displays the uploaded image with absolutely-positioned `<div>` bounding boxes scaled from the YOLO coordinate space to the displayed image size:

```
scale.x = img.clientWidth  / img.naturalWidth
scale.y = img.clientHeight / img.naturalHeight

left   = bbox[0] × scale.x
top    = bbox[1] × scale.y
width  = (bbox[2] - bbox[0]) × scale.x
height = (bbox[3] - bbox[1]) × scale.y
```

Each feature class gets a distinct colour. A sortable table below the image lists all detections with confidence bars.

---

### `Results.jsx`

Combines `TrustScoreMeter` + NLP card + Vision card + `DetectionViewer` into the full results view.  Colour-codes cards by inference outcome:
- **Green border** — genuine review
- **Amber border** — generic review
- **Blue border** — vision analysis

---

## API Integration

All backend calls are in `src/api/client.js`:

```js
// GET /health
fetchHealth() → { status, version, demo_mode, services }

// POST /api/v1/verify (multipart/form-data)
verifyAccessibility({ image, textReview, locationId }) → VerificationResponse
```

---

## Building for Production

```bash
npm run build
```

Output is in `dist/`.  The built files can be served by any static file host or co-located with the FastAPI backend using `StaticFiles`.

To serve via FastAPI:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="dist", html=True), name="frontend")
```

---

## Accessibility Notes

This project is about accessibility, so the frontend practises what it preaches:

- All interactive elements are keyboard-reachable.
- `aria-label`, `aria-live`, `aria-busy`, `aria-invalid` attributes are used throughout.
- Colour contrasts meet WCAG AA requirements.
- Screen-reader-only text is provided where icon-only UI elements exist.
- Focus indicators are visible (`:focus-visible` ring).
