# Landing page

Static site with no build step. Deploy this folder on its own.

- **Production** (e.g. `voxwire.ghimireanjal.com.np`): upload the folder as-is to Vercel, Netlify, Cloudflare Pages or GitHub Pages, and set the root/publish directory to `web`. There is no backend there, so the demo card points visitors to the self-host steps.
- **Local**: `docker compose up` serves it at http://localhost:3000, and the live call works against the local backend.
- **Dashboard**: `dashboard.html` shows calls, usage, transcripts and recordings for any Voxwire server (enter its URL and an API key).
- **Public backend later**: set `window.VOICE_AI_BACKEND = "wss://api.your-domain"` in `config.js`.
