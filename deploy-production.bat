@echo off
REM 🚀 FixSec AI Production Deployment Script (Windows)
REM Makes deployment to Railway + Vercel super easy

echo 🚀 FixSec AI Production Deployment
echo ==================================

REM Check if required tools are installed
where railway >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Railway CLI not installed. Run: npm install -g @railway/cli
    exit /b 1
)

where vercel >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Vercel CLI not installed. Run: npm install -g vercel
    exit /b 1
)

echo ✅ All required tools are installed

REM Deploy Backend to Railway
echo.
echo 📦 Deploying Backend to Railway...
echo =================================

cd backend
echo 🚀 Deploying backend...
railway up

echo ✅ Backend deployment initiated

REM Deploy Frontend to Vercel
echo.
echo 🌐 Deploying Frontend to Vercel...
echo ==================================

cd ..\frontend

echo 🚀 Deploying frontend...
vercel --prod

echo.
echo 🎉 DEPLOYMENT COMPLETE!
echo ======================
echo.
echo 🔧 Next Steps:
echo 1. Update GitHub OAuth app with new URLs
echo 2. Setup Stripe products and get price IDs
echo 3. Configure environment variables in Railway
echo 4. Test the production deployment
echo.
echo 💰 Ready to start earning money! 🚀

pause