# Security Policy

## Supported versions

Security fixes go into the latest minor release only.

## Reporting a vulnerability

Please do **not** open a public issue. Instead, use [GitHub private vulnerability reporting](https://github.com/AnjalLLL/voxwire/security/advisories/new), or email **anjalghimire890@gmail.com**.

Include the affected version, steps to reproduce, and the impact. You should hear back within 3 business days. Once a fix is released, we'll credit you, unless you'd rather stay anonymous.

## Deployment notes

- The server has no built-in authentication yet. Put it behind your own auth or a reverse proxy before exposing it to the internet.
- Keep `GEMINI_API_KEY` and any TURN credentials in `.env` or a secret store. Never commit them.
