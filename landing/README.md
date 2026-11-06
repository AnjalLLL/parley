# Landing page

Static site with no build step. Deploy this folder on its own.

- **Production** (e.g. `voiceai.ghimireanjal.com.np`): upload the folder as-is to Vercel, Netlify, Cloudflare Pages or GitHub Pages, and set the root/publish directory to `landing`. There is no backend there, so the demo card points visitors to the self-host steps.
- **Local**: `docker compose up` serves it at http://localhost:3000, and the live call works against the local backend.
- **Public backend later**: set `window.VOICE_AI_BACKEND = "wss://api.your-domain"` in `config.js`.
