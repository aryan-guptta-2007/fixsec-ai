# FixSec AI

Scan a GitHub repository for security problems, then open a pull request that fixes what can be fixed safely.

## What it does

Connect GitHub, pick a repository, and FixSec AI reports:

| Issue | Detection | Fix |
| --- | --- | --- |
| Hardcoded secrets | API keys, tokens, passwords, private keys | Python, JS/TS, Ruby and PHP: replaced with an environment lookup, documented in `.env.example`. Config files and key blocks go to manual review. |
| Vulnerable npm dependencies | `npm audit`, including nested `package.json` files | Non-breaking updates with `npm audit fix`. Major upgrades go to manual review. |
| SQL injection | Queries built by concatenation, template literals, f-strings and format strings | Always manual review, with a parameterized example. Rewriting a query safely needs knowledge of the driver. |

Each scan gets a 0-100 security score and history. Team plans can run scans on a schedule and send results by email, Slack, Discord or webhook.

Secret values are never written to the repository, the database or the API. Moving a secret out of the code does not remove it from git history, so each PR tells the owner to rotate it.

## Running locally

Requires Python 3.11+, Node.js 20+ and git.

Create a [GitHub OAuth App](https://github.com/settings/developers) with the callback URL `http://localhost:8000/auth/github/callback`.

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # then fill in GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET and SECRET_KEY
python db/init_db.py
uvicorn main:app --reload --port 8000

# Frontend, in a second terminal
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000.

Or run everything with Docker: `docker compose up --build`.

## Tests

```bash
cd backend && pytest
cd frontend && npm run lint && npm run build
```

Backend tests use real git against a local bare repository. GitHub's API and Stripe are faked.

## Architecture

- **Frontend**: Next.js and Tailwind
- **Backend**: FastAPI, SQLAlchemy and Alembic
- **Database**: PostgreSQL in production, SQLite locally
- **Auth**: GitHub OAuth. The backend issues its own session token and stores the GitHub token encrypted.
- **Billing**: Stripe Checkout and webhooks

Repositories are untrusted input. Each operation uses a throwaway clone, npm never runs install scripts, and the GitHub token is passed to git through the environment so it never reaches disk.

## Plans

Limits are enforced from `backend/core/billing.py`.

| Plan | Price | Repositories | Scans | Auto-fix PRs | Scheduled scans and alerts |
| --- | --- | --- | --- | --- | --- |
| Free | $0 | 1 | 1 per day | No | No |
| Starter | $25/mo | 5 | Unlimited | No | No |
| Professional | $49/mo | Unlimited | Unlimited | Yes | No |
| Team | $99/mo | Unlimited | Unlimited | Yes | Yes |

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md).
