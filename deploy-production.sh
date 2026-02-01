#!/bin/bash

# 🚀 FixSec AI Production Deployment Script
# Makes deployment to Railway + Vercel super easy

echo "🚀 FixSec AI Production Deployment"
echo "=================================="

# Check if required tools are installed
command -v railway >/dev/null 2>&1 || { echo "❌ Railway CLI not installed. Run: npm install -g @railway/cli"; exit 1; }
command -v vercel >/dev/null 2>&1 || { echo "❌ Vercel CLI not installed. Run: npm install -g vercel"; exit 1; }

echo "✅ All required tools are installed"

# Deploy Backend to Railway
echo ""
echo "📦 Deploying Backend to Railway..."
echo "================================="

# Check if railway is logged in
if ! railway whoami >/dev/null 2>&1; then
    echo "🔐 Please login to Railway first:"
    railway login
fi

# Deploy backend
cd backend
echo "🚀 Deploying backend..."
railway up

# Get the backend URL
BACKEND_URL=$(railway status --json | jq -r '.deployments[0].url')
echo "✅ Backend deployed to: $BACKEND_URL"

# Deploy Frontend to Vercel
echo ""
echo "🌐 Deploying Frontend to Vercel..."
echo "=================================="

cd ../frontend

# Check if vercel is logged in
if ! vercel whoami >/dev/null 2>&1; then
    echo "🔐 Please login to Vercel first:"
    vercel login
fi

# Set environment variables
echo "🔧 Setting environment variables..."
vercel env add NEXT_PUBLIC_API_URL production
vercel env add NEXT_PUBLIC_APP_URL production

# Deploy frontend
echo "🚀 Deploying frontend..."
vercel --prod

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================"
echo ""
echo "✅ Backend: $BACKEND_URL"
echo "✅ Frontend: Check Vercel dashboard for URL"
echo ""
echo "🔧 Next Steps:"
echo "1. Update GitHub OAuth app with new URLs"
echo "2. Setup Stripe products and get price IDs"
echo "3. Configure environment variables in Railway"
echo "4. Test the production deployment"
echo ""
echo "💰 Ready to start earning money! 🚀"