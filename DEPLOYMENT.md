# Deployment

The backend needs `git` and Node.js at runtime, because it clones repositories and runs `npm audit`. The recommended setup is Railway for the backend and Postgres, and Vercel for the frontend. `docker-compose.prod.yml` runs the whole stack on your own server.

## 1. Create a GitHub OAuth App

At [GitHub Developer Settings](https://github.com/settings/developers), create an OAuth App. You will set the callback URL in step 3, once you know the backend's address.

## 2. Create Stripe products (optional)

Billing can wait, since the free plan works without it. To enable it, create three monthly prices in Stripe (Starter $25, Professional $49, Team $99), and turn on the [customer portal](https://dashboard.stripe.com/settings/billing/portal) with plan switching.

## 3. Deploy the backend on Railway

1. Create a project from this repository and add a PostgreSQL service. Railway sets `DATABASE_URL`.
2. Set the variables from `backend/.env.production.template`. These are required:
   - `ENVIRONMENT=production`
   - `SECRET_KEY`, at least 32 random characters. The server refuses to start without it.
   - `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`
   - `BACKEND_URL` and `FRONTEND_URL`
3. Deploy. `nixpacks.toml` installs Python, Node.js and git, runs migrations, and starts the server.
4. Confirm that `<BACKEND_URL>/health` responds.
5. In your GitHub OAuth App, set the callback URL to `<BACKEND_URL>/auth/github/callback`.

## 4. Deploy the frontend on Vercel

1. Import this repository.
2. Set `NEXT_PUBLIC_API_URL` to your `BACKEND_URL`. It is built into the browser bundle, so redeploy after changing it.
3. Deploy, and make sure `FRONTEND_URL` on the backend matches the final address.

## 5. Connect Stripe webhooks

In Stripe, add the endpoint `<BACKEND_URL>/billing/webhook` with these events:

- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_failed`

Then set `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` and the three `STRIPE_*_PRICE_ID` variables on the backend.

## Self-hosting with Docker

```bash
cp backend/.env.production.template .env.production   # fill it in
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Put a TLS-terminating proxy in front of ports 3000 and 8000.

## Operations

- **Migrations** run on every start through `db/init_db.py`.
- **Scheduled scans** run in a background thread in each server process. Schedules are claimed atomically, so several workers are safe. Set `SCHEDULER_ENABLED=false` to turn the thread off.
- **`SECRET_KEY`** signs sessions and encrypts stored GitHub tokens. Changing it signs everyone out, and scheduled scans fail for each user until they sign in again.
- **Email** needs `SENDGRID_API_KEY`. Without it, email channels report an error instead of silently doing nothing.
