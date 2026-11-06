# Security Policy

## Supported versions

Security fixes go into the latest minor release only.

## Reporting a vulnerability

Please do **not** open a public issue. Instead, use [GitHub private vulnerability reporting](https://github.com/AnjalLLL/voxwire/security/advisories/new), or email **anjalghimire890@gmail.com**.

Include the affected version, steps to reproduce, and the impact. You should hear back within 3 business days. Once a fix is released, we'll credit you, unless you'd rather stay anonymous.

## Deployment notes

- Always set `VOXWIRE_API_KEYS` and `VOXWIRE_SECRET` before exposing the server. Without keys it runs in open dev mode.
- Set `VOXWIRE_CORS_ORIGINS` to your own domains, and serve the server over HTTPS/WSS (for example behind Caddy).
- Keep `GEMINI_API_KEY` and any TURN credentials in `.env` or a secret store. Never commit them.
