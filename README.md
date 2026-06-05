# Spotter — ELD Trip Planner & HOS Logs

Full-stack app that plans interstate property-carrying trips under **70-hour / 8-day** FMCSA rules, shows the route on a free map, and generates **driver daily log** grids (FMCSA graph format).

## Stack

- **Backend:** Django 5 + Django REST Framework
- **Frontend:** React 18 + Vite + Tailwind + Leaflet (OpenStreetMap tiles)
- **Routing / geocoding:** OSRM + Nominatim (no API keys)

## HOS assumptions (per spec)

- Property-carrying interstate driver, **70 hr / 8 day**
- No adverse driving, short-haul, or split-sleeper exceptions
- **14-hour** window, **11-hour** driving, **30-minute** break after 8 hr driving
- **10-hour** off-duty (sleeper) between driving windows
- **1 hour** on-duty at pickup and dropoff
- Fuel stop (**30 min** on-duty) at least every **1,000 miles**

## Quick start

Copy environment config once (repo root, shared by backend and frontend):

```bash
cp .env.example .env
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
python manage.py runserver
```

API: `POST http://127.0.0.1:8000/api/plan/`

```json
{
  "current_location": "Richmond, VA",
  "pickup_location": "Baltimore, MD",
  "dropoff_location": "Newark, NJ",
  "cycle_used_hours": 0
}
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` to Django using `BACKEND_URL` from `.env`.

## Deploy on Vercel

The repo is set up for a **single Vercel project**: the React app is served as static files and `/api/*` routes to the Django API via a Python serverless function.

```
spotter/
  api/index.py          # Django WSGI handler for Vercel
  vercel.json           # build + /api rewrites
  package.json          # frontend build orchestration
  requirements.txt      # Python deps for the API function
  backend/              # Django app (unchanged layout)
  frontend/             # Vite React app
```

1. Push the repo to GitHub and import it in [Vercel](https://vercel.com/new).
2. Leave **Root Directory** empty (repo root). Vercel reads `vercel.json` automatically.
3. Add environment variables in the Vercel project settings:

| Variable | Value |
|----------|--------|
| `SECRET_KEY` | Strong random Django secret |
| `DEBUG` | `False` |
| `GEOCODING_USER_AGENT` | Your app name + contact (Nominatim policy) |

You do **not** need `BACKEND_URL` or `FRONTEND_URL` on Vercel — the build uses same-origin `/api` calls and Django allows `.vercel.app` hosts automatically.

Trip planning calls external geocoding APIs and may take 10–30 seconds; `vercel.json` sets `maxDuration: 60` for the API function (requires a Vercel plan that supports longer function timeouts).

```bash
# Optional: deploy from CLI
npm i -g vercel
vercel
```

Local development is unchanged: run Django in `backend/` and Vite in `frontend/` as described below.

## Hosting on a custom domain

Edit the repo-root `.env` (both apps read the same file):

| Variable | Purpose |
|----------|---------|
| `BACKEND_URL` | Public API URL, e.g. `https://api.yourdomain.com` |
| `FRONTEND_URL` | Public app URL, e.g. `https://yourdomain.com` (used for CORS) |

Django derives `ALLOWED_HOSTS` from `BACKEND_URL` and `CORS_ALLOWED_ORIGINS` from `FRONTEND_URL`. Override with comma-separated `ALLOWED_HOSTS` or `CORS_ALLOWED_ORIGINS` if you use extra hostnames (e.g. `www`).

1. Deploy Django behind HTTPS at `BACKEND_URL`; set `DEBUG=False` and a strong `SECRET_KEY`.
2. Build the frontend with the same `.env`, then serve `frontend/dist` at `FRONTEND_URL`:

```bash
npm run build
```

The built app calls `BACKEND_URL` directly. In local dev, requests stay on `/api` and Vite proxies to `BACKEND_URL`.

## Project layout

```
spotter/
  api/index.py            # Vercel serverless Django entry
  vercel.json
  backend/
    trips/hos_engine.py   # HOS simulation & log segments
    trips/geocoding.py    # Nominatim + OSRM
    trips/views.py        # REST endpoint
  frontend/
    src/components/LogGrid.tsx   # SVG paper-style log grid
    src/components/RouteMap.tsx
```

## Notes

- Nominatim requires a polite **User-Agent** and rate limits (~1 req/s); first plan may take a few seconds.
- Log grids use home-terminal style 24-hour rows (Off Duty, Sleeper, Driving, On Duty) with solid status lines and 70/8 recap.
- For production hosting, set `SECRET_KEY`, `DEBUG=False`, and use a production WSGI server + HTTPS.
