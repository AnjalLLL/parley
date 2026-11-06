# Self-hosting

## Single server

```bash
curl -O https://raw.githubusercontent.com/AnjalLLL/voxwire/main/deploy/docker-compose.yml
cat > .env <<ENV
GEMINI_API_KEY=…
PION_PUBLIC_IP=203.0.113.10
VOXWIRE_API_KEYS=$(openssl rand -hex 24)
VOXWIRE_SECRET=$(openssl rand -hex 32)
VOXWIRE_CORS_ORIGINS=https://app.example.com
ENV
docker compose up -d
```

Open UDP ports **5000–5100** on your firewall for media.

## Profiles

| Profile | Adds | You need |
|---|---|---|
| `https` | Caddy with automatic Let's Encrypt for the API and WSS | `DOMAIN` set, and ports 80/443 open. Download `deploy/Caddyfile` |
| `turn` | coturn with time-limited credentials | `TURN_SECRET`, `TURN_ENABLED=true`, `TURN_URL=turn:<domain>:3478`, and `deploy/turnserver.conf` |
| `monitoring` | Prometheus scraping `/metrics`, and Grafana on :3001 | `deploy/prometheus.yml` |

```bash
DOMAIN=voice.example.com docker compose --profile https --profile turn up -d
```

TURN is what makes calls work behind strict corporate networks and some mobile carriers.

## Sizing

Run `scripts/loadtest.py` against your server to measure session setup. The concurrent call limit is `MAX_CONCURRENT_CALLS`. Each call holds one connection to the AI provider, so provider rate limits usually hit before CPU does.

## Checklist

- [ ] `VOXWIRE_API_KEYS` and `VOXWIRE_SECRET` set
- [ ] HTTPS (the `https` profile, or your own proxy)
- [ ] `VOXWIRE_CORS_ORIGINS` limited to your domains
- [ ] `PION_PUBLIC_IP` set to the public IP, and UDP 5000–5100 open
- [ ] TURN for users behind strict NAT
