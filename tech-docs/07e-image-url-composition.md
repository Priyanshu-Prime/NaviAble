# Phase 07e — Image URL Composition

## Goal

`ContributionPin.image_url` is a fully-qualified URL the frontend can
render directly. The endpoint composes it from settings; it never
returns an absolute filesystem path.

## Prerequisites

- Phase 07a merged: `_to_pin` helper exists and calls a URL composer.
- Phase 02a merged: `Settings` exposes a `public_base_url` and a
  `static_prefix` (add these in this phase if not already present).

## Deliverables

### Settings additions

```python
class Settings(BaseSettings):
    # ... existing fields
    public_base_url: str = "http://localhost:8000"   # dev default
    static_prefix: str = "/static"                   # phase 02b mount
```

`public_base_url` is environment-specific:

- Dev: `http://localhost:8000`
- Staging: `https://staging-api.naviable.example`
- Prod: `https://cdn.naviable.example` (CDN in front of object store)

### URL composer

```python
def _compose_image_url(image_path: str, settings: Settings) -> str | None:
    if not image_path:
        return None
    filename = Path(image_path).name
    return f"{settings.public_base_url.rstrip('/')}{settings.static_prefix}/{filename}"
```

Use `Path(...).name` to extract the filename — never join the raw
`image_path`, which is an absolute filesystem path on the server.

### `image_url` always nullable in the schema

`ContributionPin.image_url: str | None`. A `None` is valid: it means
the row exists but the image is absent (e.g. cleaned up, migration
artefact). Don't filter rows out for this — show the pin without a
photo.

## Acceptance criteria

- [ ] Every pin returned by `/contributions/nearby` has either a fully
      qualified `https://` (or `http://` in dev) `image_url`, or `null`.
- [ ] No `image_url` value contains `/Users/`, `/var/`, or `C:\` —
      i.e. no leaked filesystem paths.
- [ ] In dev, `image_url` resolves to a real image when fetched (the
      `/static` mount serves it).
- [ ] In prod (when configured), `image_url` points at the CDN, not the
      app server.

## Pitfalls / notes

- **`rstrip('/')` matters.** A `public_base_url` with a trailing slash
  composes `…//static/…` otherwise. Some load balancers normalise it,
  some don't.
- **Don't sign URLs here.** If/when private contributions ship,
  signed-URL generation is its own service module — keep this
  composition function dumb.
- **Don't bake the URL into the DB.** `image_path` stays as the storage
  identifier; the URL is composed at read time. That way a CDN switch
  is one settings change, not a backfill migration.
- **Thumbnails:** for map markers, requesting the original image is
  expensive. Phase 09/10 should request a thumbnail variant; for MVP,
  serve the original. Document the latency cost rather than
  pre-optimising.
