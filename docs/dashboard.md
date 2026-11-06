# Dashboard and usage

Open `web/dashboard.html` (served at http://localhost:3000/dashboard.html with `docker compose up`). Enter your server URL and an API key to see:

- calls and minutes over the last 30 days, the active calls, and a minutes-per-day chart
- recent calls with channel, provider, duration and end reason
- each call's transcript and recordings

The data comes from the call log, a SQLite file in `DATA_DIR`, through these endpoints:

| Endpoint | Returns |
|---|---|
| `GET /api/sessions?limit=50` | `{active: [...], recent: [...]}` |
| `GET /api/usage?days=30` | `{calls, minutes, per_day: [{day, calls, minutes}], active_calls}` |

Each API key only sees its own calls. In dev mode (no keys) you see everything.
