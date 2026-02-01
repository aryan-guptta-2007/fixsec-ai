#!/usr/bin/env node

/**
 * FixSec AI Deployment Verification Script
 * Tests all critical endpoints after deployment
 */

const https = require('https');
const http = require('http');

// Configuration - UPDATE THESE AFTER DEPLOYMENT
const BACKEND_URL = process.env.BACKEND_URL || 'https://fixsec-ai-production.up.railway.app';
const FRONTEND_URL = process.env.FRONTEND_URL || 'https://fixsec-ai.vercel.app';

console.log('🧪 FixSec AI Deployment Verification');
console.log('====================================');
console.log(`Backend: ${BACKEND_URL}`);
console.log(`Frontend: ${FRONTEND_URL}`);
console.log('');

// Test function
async function testEndpoint(url, description) {
  return new Promise((resolve) => {
    const client = url.startsWith('https') ? https : http;
    
    const req = client.get(url, (res) => {
      const success = res.statusCode >= 200 && res.statusCode < 300;
      console.log(`${success ? '✅' : '❌'} ${description}: ${res.statusCode}`);
      
      if (url.includes('/health')) {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            console.log(`   Status: ${json.status}, Environment: ${json.environment}`);
          } catch (e) {
            console.log(`   Response: ${data.substring(0, 100)}`);
          }
        });
      }
      
      resolve(success);
    });
    
    req.on('error', (err) => {
      console.log(`❌ ${description}: ERROR - ${err.message}`);
      resolve(false);
    });
    
    req.setTimeout(10000, () => {
      console.log(`❌ ${description}: TIMEOUT`);
      req.destroy();
      resolve(false);
    });
  });
}

// Run tests
async function runTests() {
  console.log('🔍 Testing Backend Endpoints...');
  console.log('------------------------------');
  
  const backendTests = [
    [`${BACKEND_URL}/health`, 'Health check (CRITICAL)'],
    [`${BACKEND_URL}/`, 'Root endpoint'],
    [`${BACKEND_URL}/docs`, 'API documentation'],
  ];
  
  let backendPassed = 0;
  for (const [url, desc] of backendTests) {
    const success = await testEndpoint(url, desc);
    if (success) backendPassed++;
    await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1s between tests
  }
  
  console.log('');
  console.log('🔍 Testing Frontend...');
  console.log('----------------------');
  
  const frontendTests = [
    [`${FRONTEND_URL}/`, 'Frontend homepage'],
    [`${FRONTEND_URL}/login`, 'Login page'],
    [`${FRONTEND_URL}/dashboard`, 'Dashboard page'],
  ];
  
  let frontendPassed = 0;
  for (const [url, desc] of frontendTests) {
    const success = await testEndpoint(url, desc);
    if (success) frontendPassed++;
    await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1s between tests
  }
  
  console.log('');
  console.log('📊 DEPLOYMENT VERIFICATION RESULTS');
  console.log('==================================');
  console.log(`Backend: ${backendPassed}/${backendTests.length} tests passed`);
  console.log(`Frontend: ${frontendPassed}/${frontendTests.length} tests passed`);
  
  const allPassed = backendPassed === backendTests.length && frontendPassed === frontendTests.length;
  
  if (allPassed) {
    console.log('');
    console.log('🎉 DEPLOYMENT SUCCESSFUL!');
    console.log('✅ All systems operational');
    console.log('✅ Ready for production traffic');
    console.log('💰 Ready to start earning money!');
    console.log('');
    console.log('🚀 Next Steps:');
    console.log('1. Test GitHub OAuth login manually');
    console.log('2. Test repository scanning');
    console.log('3. Test PR creation');
    console.log('4. Launch publicly!');
  } else {
    console.log('');
    console.log('⚠️  DEPLOYMENT ISSUES DETECTED');
    console.log('❌ Some endpoints are not responding');
    console.log('🔧 Check Railway and Vercel logs');
    console.log('');
    console.log('🔍 Troubleshooting:');
    console.log('- Verify environment variables are set');
    console.log('- Check Railway start command');
    console.log('- Ensure root directory is correct');
    console.log('- Test backend health endpoint directly');
  }
  
  console.log('');
  console.log('🔗 Quick Links:');
  console.log(`   Backend Health: ${BACKEND_URL}/health`);
  console.log(`   Frontend App: ${FRONTEND_URL}`);
  console.log(`   API Docs: ${BACKEND_URL}/docs`);
  console.log('');
  console.log('💡 Manual Testing Checklist:');
  console.log('   1. Visit frontend and click "Login with GitHub"');
  console.log('   2. Authorize app and check dashboard loads');
  console.log('   3. Select repo and click "🔍 Scan"');
  console.log('   4. Click "🚀 Analyze & Create Smart Fix Plan"');
  console.log('   5. Create PR and verify it appears on GitHub');
}

runTests().catch(console.error);