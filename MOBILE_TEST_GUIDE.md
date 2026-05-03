# NaviAble Mobile Testing Guide

## Quick Start: Run the Full Stack

```bash
# From project root
./run.sh
```

You'll be prompted to choose a device. The script will:
1. ✅ Start PostgreSQL database (Docker)
2. ✅ Start FastAPI backend on `http://127.0.0.1:8000`
3. ✅ Wait for backend health check
4. ✅ Launch frontend on your chosen device

**Data will persist** between runs thanks to Docker volumes. You can stop and restart without losing data.

---

## Device Options

### 1. **Chrome (Web) - Fastest**
```bash
./run.sh
# Choose option 1
```
- Best for quick testing
- Full browser DevTools support
- Can inspect network requests and database state
- **Access:** http://127.0.0.1:5173
- Maps API key must have "Maps JavaScript API" enabled

### 2. **macOS Desktop App - Mobile-like**
```bash
./run.sh
# Choose option 2
```
- Most similar to actual mobile experience
- Window size approximates mobile screen
- Good for testing responsive UI and touch interactions
- Backend reachable via `localhost:8000`

### 3. **Android Emulator**
```bash
./run.sh
# Choose option 3
```
- Backend reachable via `10.0.2.2:8000` (run.sh sets this automatically)
- Mock GPS via Extended Controls → Location → "Set location"
- Requires Maps SDK key for Android (restricted to package `ai.naviable`)

### 4. **iOS Simulator**
```bash
./run.sh
# Choose option 4
```
- Backend reachable via `localhost:8000`
- Mock GPS via Xcode → Debug → Simulate Location
- Requires Maps SDK key for iOS (restricted to bundle id `ai.naviable`)

### 5. **Physical Device (Wi-Fi)**
```bash
./run.sh
# Choose option 5
```
- Backend must be reachable on your Mac's LAN IP — open the firewall
- iOS device may complain about a self-signed cert; we use plain HTTP in dev so this is fine
- Automatically detects your local IP and sets API_BASE_URL accordingly

### Explicit Device Selection
```bash
# Use Chrome
FLUTTER_DEVICE=chrome ./run.sh

# Use macOS
FLUTTER_DEVICE=macos ./run.sh

# Use Android (custom device ID)
FLUTTER_DEVICE=emulator-5554 ./run.sh

# Use custom API URL
API_BASE_URL=http://192.168.1.42:8000 ./run.sh
```

---

## Complete Testing Workflow

### Step 1: Start the Project
```bash
./run.sh
```

Wait for output:
```
✅ Backend is ready
Using device: macos  (or chrome)
```

### Step 2: Test Core Features

#### **A. Contribution Submission**
1. Open the app on your device
2. Navigate to "Create Contribution"
3. Fill in:
   - Rating (1-5 stars)
   - Review text (min 1 char, max 2000)
   - Location (map tap or manual input)
   - Image (optional)
4. Click "Submit"
5. Verify: Success message appears

#### **B. Nearby Contributions**
1. Navigate to "Map View" or "Nearby"
2. App should show contributions within 1km (or your radius)
3. Tap a pin to see details
4. Verify: Data persists from previous submissions

#### **C. Trust Score Calculation**
1. Submit a contribution with high-quality image + detailed review
2. Check the response for `trust_score` field
3. Later submissions should show different scores based on image/text quality

---

## Verification Checklist

### Backend Health
```bash
# In another terminal, check backend is running
curl http://127.0.0.1:8000/health
# Expected: {"status": "ok"}
```

### Database Health
```bash
# List tables (requires psql installed)
psql -h localhost -p 5434 -U naviable -d naviable -c "\dt"

# Or via Docker
docker exec naviable-postgis psql -U naviable -d naviable -c "\dt"
```

### View Submitted Data
```bash
# Check contributions table
docker exec naviable-postgis psql -U naviable -d naviable -c \
  "SELECT id, latitude, longitude, rating, trust_score, created_at FROM contributions LIMIT 5;"
```

---

## Environment Variables for Testing

```bash
# Run in demo mode (if implemented)
NAVIABLE_DEMO_MODE=true ./run.sh

# Custom backend URL
API_BASE_URL=http://192.168.1.100:8000 ./run.sh

# Skip database (use existing one)
SKIP_DOCKER=true ./run.sh

# Backend only (no frontend)
./run.sh -b

# Docker only (no backend/frontend)
./run.sh -d
```

---

## Stopping Everything

```bash
# Graceful shutdown
./stop.sh

# Force kill (emergency)
./stop.sh -a

# Stop only Docker (keep backend running)
./stop.sh -d
```

**Data persists** - running `./run.sh` again will load the same database.

---

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs postgis
curl http://127.0.0.1:8000/health
```

### Frontend won't connect to backend
- Verify backend is running: `curl http://127.0.0.1:8000/health`
- Check `API_BASE_URL` env var
- On mobile: use actual IP instead of `127.0.0.1`
  ```bash
  API_BASE_URL=http://192.168.1.X:8000 ./run.sh
  ```

### Database connection errors
```bash
# Restart Docker
docker-compose -f docker-compose.yml restart postgis

# Or full reset (WARNING: deletes data)
docker-compose -f docker-compose.yml down -v
./run.sh
```

### Port already in use
```bash
# Change ports
BACKEND_PORT=8001 FLUTTER_WEB_PORT=5174 ./run.sh
```

---

## Network Testing on Real Mobile Device

To test on a physical phone connected to your Mac:

```bash
# Get your Mac's IP address
ifconfig | grep "inet " | grep -v 127.0.0.1

# Example: 192.168.1.42
# Then run:
API_BASE_URL=http://192.168.1.42:8000 ./run.sh
```

On Flutter, this should automatically detect available devices and show them in the device list.

---

## Data Persistence Example

```bash
# Session 1: Submit some data
./run.sh
# Submit 3 contributions, close with Ctrl+C

# Session 2: Data is still there
./run.sh
# Use "Nearby" to see the 3 contributions from Session 1

# Session 3: Fresh start (delete data)
./stop.sh
docker volume rm naviable_naviable_pgdata
./run.sh
# Database is empty, ready for new testing
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `./run.sh` | Start everything (interactive device selection) |
| `./run.sh -b` | Backend only |
| `./run.sh -d` | Docker only |
| `FLUTTER_DEVICE=chrome ./run.sh` | Web browser |
| `FLUTTER_DEVICE=macos ./run.sh` | Desktop app |
| `./stop.sh` | Graceful stop |
| `./stop.sh -a` | Force kill all |
| `curl http://127.0.0.1:8000/health` | Check backend |
