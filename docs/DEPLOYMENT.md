# Deployment

The simplest production setup for the pilot is a single small VPS (2 vCPU / 2–4 GB RAM) running Docker Compose behind a TLS reverse proxy.

## 1. Server

```bash
# Ubuntu 24.04
curl -fsSL https://get.docker.com | sh
git clone <your repo> /opt/shoppilot && cd /opt/shoppilot
cp .env.example .env
```

Edit `.env`:

```dotenv
ENVIRONMENT=production
SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
COOKIE_SECURE=true
FRONTEND_URL=https://app.example.com
CORS_ORIGINS=https://app.example.com
POSTGRES_PASSWORD=<strong password>
META_...=<real values>
```

With `ENVIRONMENT=production`, the API refuses to start if the default `SECRET_KEY` is used or if `COOKIE_SECURE` is false.

## 2. Reverse proxy with HTTPS (Caddy example)

Only the proxy should be reachable from the internet. Bind the app ports to localhost by setting `ports: ["127.0.0.1:8000:8000"]` and `["127.0.0.1:3000:3000"]` in a `docker-compose.override.yml`.

```caddyfile
app.example.com {
    reverse_proxy 127.0.0.1:3000
}

api.example.com {
    # Meta webhooks hit the backend directly
    reverse_proxy /webhooks/* 127.0.0.1:8000
    respond 404
}
```

Point the Meta webhook callback to `https://api.example.com/webhooks/whatsapp/`. Browser traffic only goes through `app.example.com`, and Next.js proxies `/api` to the backend internally.

## 3. Start

```bash
docker compose up -d --build
docker compose exec backend python -m app.cli create-superuser --email admin@example.com --name Admin --password '<strong>'
docker compose ps
```

Migrations run automatically on backend start (`RUN_MIGRATIONS=true`).

## 4. Operations

| Task | Command |
|---|---|
| Logs | `docker compose logs -f backend` |
| Upgrade | `git pull && docker compose up -d --build` |
| Activate a paid plan after verifying the bKash/Nagad payment | `docker compose exec backend python -m app.cli activate-subscription --business-id 3 --plan starter --months 1 --reference BKASH-8N7X...` |
| Purge old webhook events (cron, daily) | `docker compose exec -T backend python -m app.cli purge-webhook-events` |
| DB backup (cron, daily) | `docker compose exec -T db pg_dump -U shoppilot shoppilot \| gzip > /backups/shoppilot-$(date +%F).sql.gz` |
| Media backup | back up the `shoppilot_media` volume |
| Restore | `gunzip -c backup.sql.gz \| docker compose exec -T db psql -U shoppilot shoppilot` |

Example crontab:

```cron
15 3 * * * cd /opt/shoppilot && docker compose exec -T db pg_dump -U shoppilot shoppilot | gzip > /backups/shoppilot-$(date +\%F).sql.gz
30 3 * * * cd /opt/shoppilot && docker compose exec -T backend python -m app.cli purge-webhook-events
```

## 5. Scaling notes

- Run several `uvicorn` workers by overriding the backend command with `--workers 2`. The in-memory rate limiter is then per worker, so switch it to Redis before relying on strict limits.
- Move product images to S3-compatible storage by implementing the `FileStorage` port.
- Add Celery and Redis only once background jobs are really needed, for example scheduled reminders or media downloads.
