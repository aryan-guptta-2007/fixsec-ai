# 🔧 FixSec AI Environment Setup Guide

## 🚨 Critical: Fix #1 SaaS Deployment Issue

**The #1 reason SaaS apps break after deployment is hardcoded URLs.**

FixSec AI is now properly configured to avoid this issue!

## ✅ Current Configuration

### Frontend Environment Variables
- ✅ **Development**: Uses `http://localhost:8000` from `.env.local`
- ✅ **Production**: Uses `NEXT_PUBLIC_API_URL` environment variable
- ✅ **No hardcoded URLs**: All API calls use `process.env.NEXT_PUBLIC_API_URL`

### Backend Environment Variables
- ✅ **All URLs configurable**: `FRONTEND_URL`, `CORS_ORIGINS`, `DATABASE_URL`
- ✅ **Production ready**: Complete `.env.production` template
- ✅ **Security**: All secrets in environment variables

## 🚀 Quick Setup

### 1. Development Setup
```bash
# Frontend is already configured
# backend/.env.local already has: NEXT_PUBLIC_API_URL=http://localhost:8000

# Backend uses environment variables from config.py
# No changes needed for development
```

### 2. Production Setup

#### Option A: Vercel + Railway (Recommended)

**Frontend (Vercel):**
1. Connect GitHub repo to Vercel
2. Set environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   ```
3. Deploy

**Backend (Railway):**
1. Connect GitHub repo to Railway
2. Add PostgreSQL database
3. Set environment variables:
   ```
   DATABASE_URL=postgresql://postgres:password@host:port/db
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   FRONTEND_URL=https://your-frontend.vercel.app
   CORS_ORIGINS=https://your-frontend.vercel.app
   SECRET_KEY=your_32_char_secret_key
   ```
4. Deploy

#### Option B: Docker Deployment
```bash
# 1. Copy environment template
cp .env.production .env.prod

# 2. Edit with your values
nano .env.prod

# 3. Update frontend production URL
# Edit frontend/.env.production:
# NEXT_PUBLIC_API_URL=https://your-backend-domain.com

# 4. Deploy
./deploy.sh
```

## 🔍 Verification

Run the verification script:
```bash
node verify-env.js
```

This checks:
- ✅ Frontend environment configuration
- ✅ Backend environment template
- ✅ Required variables present
- ✅ Deployment files ready

## 🌐 URL Configuration Examples

### Development
```bash
# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Backend
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Production
```bash
# Frontend
NEXT_PUBLIC_API_URL=https://api.fixsec.ai

# Backend
FRONTEND_URL=https://fixsec.ai
CORS_ORIGINS=https://fixsec.ai,https://www.fixsec.ai
```

## 🚨 Common Issues & Solutions

### Issue: CORS Error
```
Access to fetch at 'https://api.domain.com' from origin 'https://domain.com' has been blocked by CORS policy
```
**Solution:** Add your frontend domain to `CORS_ORIGINS` in backend environment

### Issue: Network Error
```
TypeError: Failed to fetch
```
**Solution:** Check `NEXT_PUBLIC_API_URL` points to correct backend URL

### Issue: OAuth Redirect Error
```
The redirect_uri MUST match the registered callback URL
```
**Solution:** Update GitHub OAuth app callback URL to match production domain

## ✅ Production Checklist

- [ ] Frontend `NEXT_PUBLIC_API_URL` points to production backend
- [ ] Backend `FRONTEND_URL` points to production frontend  
- [ ] Backend `CORS_ORIGINS` includes all frontend domains
- [ ] GitHub OAuth app configured for production domain
- [ ] Database connection string updated
- [ ] All secrets rotated for production
- [ ] SSL certificates configured
- [ ] Health checks passing

## 🎯 Ready for Revenue!

With proper environment configuration, your FixSec AI will:
- ✅ Deploy without URL issues
- ✅ Work across development and production
- ✅ Scale to multiple environments
- ✅ Handle domain changes easily

**Your SaaS is now deployment-ready! 🚀💰**