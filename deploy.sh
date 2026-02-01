#!/bin/bash

# FixSec AI Production Deployment Script
# This script automates the deployment process for Railway + Vercel

set -e  # Exit on any error

echo "🚀 FixSec AI Production Deployment"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if required files exist
echo -e "${BLUE}📋 Checking deployment files...${NC}"

required_files=(
    "railway.json"
    "nixpacks.toml" 
    "vercel.json"
    "backend/requirements-prod.txt"
    "frontend/package.json"
    ".env.production"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Missing required file: $file${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ All deployment files present${NC}"

# Check environment variables
echo -e "${BLUE}🔧 Checking environment configuration...${NC}"

if [ ! -f ".env.production" ]; then
    echo -e "${RED}❌ .env.production file not found${NC}"
    echo "Please copy .env.production template and fill in your values"
    exit 1
fi

# Source the production environment
source .env.production

required_vars=(
    "GITHUB_CLIENT_ID"
    "GITHUB_CLIENT_SECRET"
    "SECRET_KEY"
    "FRONTEND_URL"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${YELLOW}⚠️  Warning: $var is not set in .env.production${NC}"
    fi
done

echo -e "${GREEN}✅ Environment configuration checked${NC}"

# Install Railway CLI if not present
if ! command -v railway &> /dev/null; then
    echo -e "${BLUE}📦 Installing Railway CLI...${NC}"
    npm install -g @railway/cli
fi

# Install Vercel CLI if not present  
if ! command -v vercel &> /dev/null; then
    echo -e "${BLUE}📦 Installing Vercel CLI...${NC}"
    npm install -g vercel
fi

echo -e "${GREEN}✅ CLI tools ready${NC}"

# Git check
echo -e "${BLUE}📝 Checking Git status...${NC}"

if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  You have uncommitted changes. Committing them now...${NC}"
    git add .
    git commit -m "Production deployment - $(date)"
fi

echo -e "${GREEN}✅ Git status clean${NC}"

# Deploy Backend to Railway
echo -e "${BLUE}🚂 Deploying backend to Railway...${NC}"

if [ ! -f "railway.json" ]; then
    echo -e "${RED}❌ railway.json not found${NC}"
    exit 1
fi

echo "Please follow these steps for Railway deployment:"
echo "1. Go to https://railway.app"
echo "2. Connect your GitHub repository"
echo "3. Add PostgreSQL database service"
echo "4. Set environment variables from .env.production"
echo "5. Deploy will happen automatically"

read -p "Press Enter when Railway deployment is complete..."

# Deploy Frontend to Vercel
echo -e "${BLUE}▲ Deploying frontend to Vercel...${NC}"

if [ ! -f "vercel.json" ]; then
    echo -e "${RED}❌ vercel.json not found${NC}"
    exit 1
fi

echo "Please follow these steps for Vercel deployment:"
echo "1. Go to https://vercel.com"
echo "2. Import your GitHub repository"
echo "3. Set root directory to 'frontend'"
echo "4. Add environment variables:"
echo "   - NEXT_PUBLIC_API_URL=https://your-backend.railway.app"
echo "   - NEXT_PUBLIC_ENVIRONMENT=production"
echo "5. Deploy will happen automatically"

read -p "Press Enter when Vercel deployment is complete..."

# Health checks
echo -e "${BLUE}🏥 Running health checks...${NC}"

if [ -n "$BACKEND_URL" ]; then
    echo "Testing backend health endpoint..."
    if curl -f "$BACKEND_URL/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend health check passed${NC}"
    else
        echo -e "${RED}❌ Backend health check failed${NC}"
    fi
fi

if [ -n "$FRONTEND_URL" ]; then
    echo "Testing frontend..."
    if curl -f "$FRONTEND_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend health check passed${NC}"
    else
        echo -e "${RED}❌ Frontend health check failed${NC}"
    fi
fi

# Success message
echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo "=================================="
echo -e "Frontend: ${BLUE}$FRONTEND_URL${NC}"
echo -e "Backend:  ${BLUE}$BACKEND_URL${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure your custom domain DNS"
echo "2. Set up monitoring and alerts"
echo "3. Test the complete user flow"
echo "4. Launch your marketing campaign!"
echo ""
echo -e "${GREEN}💰 Your FixSec AI SaaS is now live and ready to make money!${NC}"