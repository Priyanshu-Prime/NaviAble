# Phase 10 — Frontend Map & Discovery View

## Goal

Render contributions as map pins, differentiated by confidence band, and
let the user query "what's accessible near here?" The view fetches from
`/api/v1/contributions/nearby` (phase 07), updates as the user pans, and
opens a detail card when a pin is tapped.

This is the read side of the platform — what most users see most of the
time. The contribution flow (phase 09) is a smaller fraction of traffic
but produces the data this view consumes.

## Prerequisites

- Phase 07 merged: `/api/v1/contributions/nearby` is live.
- Phase 08 merged: `flutter_map`, `latlong2`, and `geolocator` are
  installed and the Riverpod / Dio scaffolding works.

## Spec essentials

| Requirement                                         | Source                |
|-----------------------------------------------------|-----------------------|
| Visually differentiate `PUBLIC` vs `CAVEAT`         | Project spec §5.3     |
| Spatial queries via the backend, not in client      | Phase 07              |
| WCAG 2.1 AA throughout                              | Project spec §5.2     |
| Display pin metadata (rating, text, image)          | Phase 02 `ContributionPin` |

## Current state

`frontend/lib/screens/` may have a placeholder map screen. This phase
finalises it.

## Deliverables

### 1. Map screen layout

`lib/screens/map_screen.dart`:

- Full-screen `FlutterMap` with an OpenStreetMap tile layer.
  Initial camera centred on the user's location if granted, else on a
  sensible city default (e.g. Tiruchirappalli for the demo).
- A floating "My location" button (bottom right) that recenters on the
  current position.
- A floating "Add accessibility data" FAB (bottom centre) that
  navigates to the contribution screen (phase 09).
- A subtle confidence-legend overlay (top right) so users know what
  the two pin styles mean.

### 2. Spatial query strategy

When the map's centre or zoom changes, debounce 400 ms, then issue a
new `nearbyContributions(query)` call with:

- `latitude`, `longitude` = current map centre.
- `radius_m` = derived from the visible map bounds (use the diagonal
  half-distance, capped at the backend's 10 km max).

```dart
ref.listen(mapCentreProvider, (_, centre) {
  _debouncer.run(() => ref.invalidate(
    nearbyContributionsProvider((lat: centre.lat, lon: centre.lon, radiusM: _radiusFromBounds()))
  ));
});
```

Do not call the API on every pan frame — that's a recipe for both
client jank and backend overload.

### 3. Pin styling

Two pin styles, drawn as Flutter widgets:

| Status  | Marker                                           |
|---------|--------------------------------------------------|
| `PUBLIC`| Solid filled marker, primary brand colour, accessibility icon |
| `CAVEAT`| Outlined marker with a hatched fill, neutral colour, warning icon |

Both meet WCAG contrast against typical map tiles. Test both light and
dark map themes — and against satellite tiles if you ever add them.

`HIDDEN` pins do not appear here at all because the backend never
returns them. Asserting this in a UI test is overkill; the backend test
in phase 11 covers it.

### 4. Pin tap → detail sheet

Tapping a pin opens a `DraggableScrollableSheet` from the bottom:

- Photo (the `image_url` from the pin).
- Trust Score, plus the explicit `vision_score` and `nlp_score`.
- Star rating.
- Review text.
- For `CAVEAT` pins, a header banner: "This contribution is awaiting
  moderator review. The information may not be fully verified."

The detail sheet is keyboard-dismissible (Escape) and screen-reader
friendly (`Semantics(scopesRoute: true)`).

### 5. Empty / loading / error states

Use the standard `AsyncValue.when` pattern from phase 08.

- **Loading**: shimmer over the map area, no pin scatter (don't show
  stale pins from a prior query — that's confusing).
- **Empty data**: a small "no contributions in this area yet — be the
  first" banner with a CTA to the contribution flow.
- **Error**: a banner with retry. Do not blank the map; the tiles
  themselves are useful even when our data is unavailable.

### 6. Geolocation refresh

The user's location is a separate stream from the map centre.
A `userLocationProvider` (StreamProvider over
`Geolocator.getPositionStream`) updates the "you are here" pin
without triggering a fresh nearby query. Only deliberate map moves
trigger the query — otherwise GPS jitter would re-fetch constantly.

### 7. Accessibility specifics for the map

This is the hardest screen for accessibility because maps are
inherently visual. Mitigations:

- Provide a list-view alternative (toggle in the AppBar). The list view
  shows the same pins as cards, sorted by distance, fully
  screen-reader-navigable. For a wheelchair user on a screen reader,
  the list view is what they use — the map is for sighted browsing.
- Every interactive marker exposes
  `Semantics(label: 'Contribution at ${rating} stars, ${text_note}, ${distance_m}m away')`.
- Ensure focus visible styling is preserved on keyboard navigation.

### 8. Performance

- Marker clustering: when the visible region holds > 50 pins, cluster
  via the `flutter_map_marker_cluster` plugin. Otherwise pan/zoom
  becomes janky.
- Image thumbnails: the `image_url` from the backend is the original
  photo. Render in the detail sheet only — not in the marker. Showing
  the full image as a marker tries to download a 4 MB JPEG per pin.
- Tile cache: `flutter_map`'s default `NetworkTileProvider` is fine for
  MVP. If the demo runs on a flaky network, swap to a cached provider.

## Acceptance criteria

- [ ] The map loads, fetches `nearby` for the initial viewport, and
      renders pins with correct styling per `visibility_status`.
- [ ] Panning the map debounces to one network request per 400 ms (max),
      verifiable in the network tab.
- [ ] Tapping a pin opens the detail sheet with photo, scores, rating,
      and review text. Closing returns focus to the map.
- [ ] The list-view toggle shows the same data as cards, sorted by
      distance, and is fully keyboard-navigable.
- [ ] An empty viewport shows the "be the first" banner.
- [ ] On a network error, retry from the banner refetches successfully.
- [ ] No `HIDDEN` pin ever appears (this should be impossible by
      backend contract; the test asserts it anyway with a fixture).
- [ ] WCAG audit clean. Both light and dark themes pass contrast.
- [ ] Performance: with 200 pins in the viewport, panning maintains
      ≥ 30 fps on a mid-range laptop.

## Pitfalls / notes

- **OSM tile usage policy.** Heavy traffic against the public OSM
  tile servers is rate-limited and frowned upon. For demos this is
  fine. For any real deployment, self-host a tile server or pay a
  provider (Mapbox, Stadia).
- **Mobile gestures vs. desktop.** Flutter Web on desktop should have
  scroll-to-zoom; on touch, pinch-to-zoom. `flutter_map` handles both
  but requires `interactiveFlags: InteractiveFlag.all`.
- **Don't pre-fetch the whole world.** The 10 km cap is there for a
  reason. If the user zooms way out, drop pins entirely and show a
  "zoom in to see contributions" banner — far better than a 10 000-pin
  blob.
- **Coordinate ordering is a perennial bug.** PostGIS uses
  `(longitude, latitude)`. `latlong2.LatLng` uses
  `(latitude, longitude)`. The conversions live in one helper, used
  everywhere; do not inline them.
