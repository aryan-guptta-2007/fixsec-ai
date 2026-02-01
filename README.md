# FixSec AI

**Tagline**: Scan code → find vulnerabilities → auto-create fix PR

## What This Product Does
A developer connects GitHub repo → tool scans code → finds security issues → generates:
- ✅ Explanation (what's wrong)
- ✅ Patch code (fixed code) 
- ✅ Pull Request automatically
- ✅ Adds tests (optional)
- ✅ Shows risk score + severity

## MVP Focus
Scan a repo and auto-create a PR for 3 vulnerability types:
1. **Hardcoded Secrets** - API keys, tokens, passwords
2. **SQL Injection** - Basic string concatenation patterns
3. **Insecure Dependencies** - Outdated vulnerable packages

## Quick Start

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

## Architecture
- **Frontend**: Next.js + Tailwind
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Auth**: GitHub OAuth
- **Deployment**: Docker

## Monetization
- **Free**: 1 repo, detection only
- **Pro ($49/mo)**: 5 repos, auto PR fixes
- **Team ($199/mo)**: 20 repos, scheduled scans