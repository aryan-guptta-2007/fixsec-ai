@echo off
REM FixSec AI Production Deployment Script for Windows
REM This script automates the deployment process for Railway + Vercel

echo 🚀 FixSec AI Production Deployment
echo ==================================

REM Check if required files exist
echo 📋 Checking deployment files...

if not exist "railway.json" (
    echo ❌ Missing required file: railway.json
    exit /b 1
)

if not exist "nixpacks.toml" (
    echo ❌ Missing required file: nixpacks.toml
    exit /b 1
)

if not exist "vercel.json" (
    echo ❌ Missing required file: vercel.json
    exit /b 1
)

if not exist "backend\requirements-prod.txt" (
    echo ❌ Missing required file: backend\requirements-prod.txt
    exit /b 1
)

if not exist "frontend\package.json" (
    echo ❌ Missing required file: frontend\package.json
    exit /b 1
)

if not exist ".env.production" (
    echo ❌ Missing required file: .env.production
    echo Please copy .env.production template and fill in your values
    exit /b 1
)

echo ✅ All deployment files present

REM Check if CLI tools are installed
echo 📦 Checking CLI tools...

where railway >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing Railway CLI...
    npm install -g @railway/cli
)

where vercel >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing Vercel CLI...
    npm install -g vercel
)

echo ✅ CLI tools ready

REM Git check
echo 📝 Checking Git status...
git status --porcelain > temp_git_status.txt
for /f %%i in ("temp_git_status.txt") do set size=%%~zi
del temp_git_status.txt

if %size% gtr 0 (
    echo ⚠️ You have uncommitted changes. Committing them now...
    git add .
    git commit -m "Production deployment - %date% %time%"
)

echo ✅ Git status clean

REM Deploy instructions
echo 🚂 Railway Deployment Instructions:
echo 1. Go to https://railway.app
echo 2. Connect your GitHub repository
echo 3. Add PostgreSQL database service
echo 4. Set environment variables from .env.production
echo 5. Deploy will happen automatically
echo.
pause

echo ▲ Vercel Deployment Instructions:
echo 1. Go to https://vercel.com
echo 2. Import your GitHub repository
echo 3. Set root directory to 'frontend'
echo 4. Add environment variables:
echo    - NEXT_PUBLIC_API_URL=https://your-backend.railway.app
echo    - NEXT_PUBLIC_ENVIRONMENT=production
echo 5. Deploy will happen automatically
echo.
pause

echo.
echo 🎉 Deployment Setup Complete!
echo ==================================
echo.
echo Next Steps:
echo 1. Complete Railway and Vercel deployments
echo 2. Configure your custom domain DNS
echo 3. Set up monitoring and alerts
echo 4. Test the complete user flow
echo 5. Launch your marketing campaign!
echo.
echo 💰 Your FixSec AI SaaS is ready to go live!
pause