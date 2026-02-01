# FixSec AI Setup Guide

## Quick Start (Development)

### 1. GitHub OAuth Setup
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. Fill in:
   - **Application name**: FixSec AI
   - **Homepage URL**: `http://localhost:3000`
   - **Authorization callback URL**: `http://localhost:8000/auth/github/callback`
4. Save your `CLIENT_ID` and `CLIENT_SECRET`

### 2. Backend Setup
```bash
cd backend
cp .env.example .env
# Edit .env with your GitHub OAuth credentials
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Database Setup (Optional - uses SQLite by default)
For PostgreSQL:
```bash
docker run --name fixsec-postgres -e POSTGRES_DB=fixsec -e POSTGRES_USER=fixsec -e POSTGRES_PASSWORD=fixsec123 -p 5432:5432 -d postgres:15
```

## Docker Setup (Production)

### 1. Environment Variables
Create `.env` file in root directory:
```bash
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

### 2. Run with Docker Compose
```bash
docker-compose up -d
```

## Testing the Application

1. **Open**: http://localhost:3000
2. **Click**: "Continue with GitHub"
3. **Authorize**: FixSec AI to access your repositories
4. **Connect**: a JavaScript/TypeScript repository
5. **Start**: a security scan
6. **Create**: a fix pull request

## What Gets Scanned

### 🔑 Hardcoded Secrets
- Stripe API keys (`sk_live_`, `sk_test_`)
- AWS Access Keys (`AKIA...`)
- JWT secrets
- GitHub tokens (`ghp_...`)
- Private keys

### 💉 SQL Injection
- String concatenation in queries
- Template literal vulnerabilities
- Direct user input interpolation
- Unsafe MySQL/PostgreSQL queries

### 📦 Dependencies
- Vulnerable npm packages
- Outdated libraries
- Security patches available

## Monetization Ready

- **Free Tier**: 1 repo, detection only
- **Pro ($49/mo)**: 5 repos, auto-fix PRs
- **Team ($199/mo)**: 20 repos, scheduled scans

## Next Steps

1. **Add Stripe**: For subscription payments
2. **Add Tests**: Unit and integration tests
3. **Deploy**: To production (Vercel + Railway/Heroku)
4. **Marketing**: Launch on Product Hunt

## Support

- Check logs: `docker-compose logs`
- Database issues: Ensure PostgreSQL is running
- GitHub OAuth: Verify callback URL matches exactly