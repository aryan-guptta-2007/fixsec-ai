#!/usr/bin/env node
/**
 * Environment Verification Script for FixSec AI
 * Run this before deployment to catch environment issues
 */

const fs = require('fs');
const path = require('path');

console.log('🔍 FixSec AI Environment Verification\n');

// Check frontend environment
console.log('📱 Frontend Environment:');
const frontendEnvLocal = path.join(__dirname, 'frontend', '.env.local');
const frontendEnvProd = path.join(__dirname, 'frontend', '.env.production');

if (fs.existsSync(frontendEnvLocal)) {
  const envContent = fs.readFileSync(frontendEnvLocal, 'utf8');
  const apiUrl = envContent.match(/NEXT_PUBLIC_API_URL=(.+)/)?.[1];
  
  if (apiUrl) {
    console.log(`✅ API URL configured: ${apiUrl}`);
    
    if (apiUrl.includes('localhost') || apiUrl.includes('127.0.0.1')) {
      console.log('⚠️  Using localhost - OK for development');
    } else {
      console.log('✅ Using production URL');
    }
  } else {
    console.log('❌ NEXT_PUBLIC_API_URL not found in .env.local');
  }
} else {
  console.log('⚠️  frontend/.env.local not found');
}

if (fs.existsSync(frontendEnvProd)) {
  console.log('✅ frontend/.env.production template exists');
} else {
  console.log('❌ frontend/.env.production template missing');
}

// Check backend environment
console.log('\n🔧 Backend Environment:');
const backendEnvProd = path.join(__dirname, '.env.production');

if (fs.existsSync(backendEnvProd)) {
  console.log('✅ .env.production template exists');
  
  const envContent = fs.readFileSync(backendEnvProd, 'utf8');
  const requiredVars = [
    'DATABASE_URL',
    'GITHUB_CLIENT_ID',
    'GITHUB_CLIENT_SECRET',
    'FRONTEND_URL',
    'SECRET_KEY'
  ];
  
  console.log('\n📋 Required variables in template:');
  requiredVars.forEach(varName => {
    if (envContent.includes(varName)) {
      console.log(`✅ ${varName}`);
    } else {
      console.log(`❌ ${varName} missing`);
    }
  });
} else {
  console.log('❌ .env.production template missing');
}

// Check deployment files
console.log('\n🚀 Deployment Files:');
const deployFiles = [
  'deploy.sh',
  'docker-compose.prod.yml',
  'DEPLOYMENT.md',
  'DEPLOYMENT-CHECKLIST.md'
];

deployFiles.forEach(file => {
  if (fs.existsSync(path.join(__dirname, file))) {
    console.log(`✅ ${file}`);
  } else {
    console.log(`❌ ${file} missing`);
  }
});

console.log('\n🎯 Next Steps:');
console.log('1. Copy .env.production to .env.prod and fill in your values');
console.log('2. Update frontend/.env.production with your backend URL');
console.log('3. Create GitHub OAuth app for production');
console.log('4. Deploy using ./deploy.sh or cloud platform');
console.log('5. Test all functionality after deployment');

console.log('\n✅ Environment verification complete!');