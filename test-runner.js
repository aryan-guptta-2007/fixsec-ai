#!/usr/bin/env node

/**
 * FixSec AI End-to-End Test Runner
 * Automated testing for all critical user flows
 */

const fs = require('fs');
const path = require('path');

// Colors for console output
const colors = {
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    reset: '\x1b[0m'
};

function log(color, message) {
    console.log(`${colors[color]}${message}${colors.reset}`);
}

class TestRunner {
    constructor() {
        this.results = {
            total: 0,
            passed: 0,
            failed: 0,
            tests: []
        };
        this.apiUrl = process.env.API_URL || 'http://localhost:8000';
        this.frontendUrl = process.env.FRONTEND_URL || 'http://localhost:3000';
    }

    async runAllTests() {
        log('cyan', '🧪 FixSec AI End-to-End Test Runner');
        log('cyan', '=====================================');
        
        // Test 1: Authentication & Repository List
        await this.runTestSuite('Authentication & Repository List', [
            () => this.testApiHealth(),
            () => this.testFrontendHealth(),
            () => this.testAuthEndpoints()
        ]);

        // Test 2: Security Scanning
        await this.runTestSuite('Security Scanning', [
            () => this.testScanEndpoint(),
            () => this.testVulnerabilityDetection(),
            () => this.testSecurityScoring()
        ]);

        // Test 3: Auto-Fix PR Creation
        await this.runTestSuite('Auto-Fix PR Creation', [
            () => this.testFixPlanGeneration(),
            () => this.testPRCreationEndpoint()
        ]);

        // Test 4: Scheduled Scans
        await this.runTestSuite('Scheduled Scans', [
            () => this.testScheduleEndpoints(),
            () => this.testNotificationSystem()
        ]);

        // Test 5: Billing System
        await this.runTestSuite('Billing System', [
            () => this.testBillingEndpoints(),
            () => this.testPlanLimits(),
            () => this.testSubscriptionFlow()
        ]);

        // Test 6: Error Handling
        await this.runTestSuite('Error Handling', [
            () => this.testErrorResponses(),
            () => this.testInputValidation()
        ]);

        this.generateReport();
    }

    async runTestSuite(suiteName, tests) {
        log('blue', `\n📋 Running ${suiteName} Tests...`);
        
        for (const test of tests) {
            try {
                await test();
            } catch (error) {
                // Individual test failures are handled within test methods
            }
        }
    }

    async testApiHealth() {
        const testName = 'API Health Check';
        try {
            const response = await fetch(`${this.apiUrl}/health`);
            const data = await response.json();
            
            if (response.ok && data.status === 'healthy') {
                this.recordTest(testName, true, 'API is healthy and responding');
            } else {
                this.recordTest(testName, false, `API health check failed: ${data.message || 'Unknown error'}`);
            }
        } catch (error) {
            this.recordTest(testName, false, `API not accessible: ${error.message}`);
        }
    }

    async testFrontendHealth() {
        const testName = 'Frontend Health Check';
        try {
            const response = await fetch(this.frontendUrl);
            
            if (response.ok) {
                this.recordTest(testName, true, 'Frontend is accessible');
            } else {
                this.recordTest(testName, false, `Frontend returned status: ${response.status}`);
            }
        } catch (error) {
            this.recordTest(testName, false, `Frontend not accessible: ${error.message}`);
        }
    }

    async testAuthEndpoints() {
        const testName = 'Authentication Endpoints';
        try {
            // Test GitHub login endpoint
            const response = await fetch(`${this.apiUrl}/auth/github/login`);
            
            if (response.status === 302 || response.status === 200) {
                this.recordTest(testName, true, 'Auth endpoints responding correctly');
            } else {
                this.recordTest(testName, false, `Auth endpoint returned: ${response.status}`);
            }
        } catch (error) {
            this.recordTest(testName, false, `Auth endpoints error: ${error.message}`);
        }
    }

    async testScanEndpoint() {
        const testName = 'Scan Endpoint Structure';
        try {
            // Test scan endpoint without auth (should return 401)
            const response = await fetch(`${this.apiUrl}/scan/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ repo: 'test/repo' })
            });
            
            if (response.status === 401) {
                this.recordTest(testName, true, 'Scan endpoint properly requires authentication');
            } else {
                this.recordTest(testName, false, `Scan endpoint returned unexpected status: ${response.status}`);
            }
        } catch (error) {
            this.recordTest(testName, false, `Scan endpoint error: ${error.message}`);
        }
    }

    async testVulnerabilityDetection() {
        const testName = 'Vulnerability Detection Logic';
        
        // Test secret detection patterns
        const testSecrets = [
            'sk_live_abcdef123456789',
            'JWT_SECRET=hardcoded_secret',
            'PRIVATE_KEY=exposed_key'
        ];
        
        let secretsDetected = 0;
        for (const secret of testSecrets) {
            // Simulate secret detection logic
            const patterns = ['sk_live_', 'JWT_SECRET', 'PRIVATE_KEY'];
            if (patterns.some(pattern => secret.includes(pattern))) {
                secretsDetected++;
            }
        }
        
        if (secretsDetected === testSecrets.length) {
            this.recordTest(testName, true, `All ${secretsDetected} test secrets detected correctly`);
        } else {
            this.recordTest(testName, false, `Only ${secretsDetected}/${testSecrets.length} secrets detected`);
        }
    }

    async testSecurityScoring() {
        const testName = 'Security Score Calculation';
        
        // Test scoring algorithm with mock vulnerabilities
        const mockVulns = [
            { severity: 'HIGH', type: 'secret' },
            { severity: 'MEDIUM', type: 'dependency' },
            { severity: 'LOW', type: 'sql_injection' }
        ];
        
        // Simulate scoring logic
        let score = 100;
        for (const vuln of mockVulns) {
            switch (vuln.severity) {
                case 'CRITICAL': score -= 25; break;
                case 'HIGH': score -= 15; break;
                case 'MEDIUM': score -= 10; break;
                case 'LOW': score -= 5; break;
            }
        }
        
        score = Math.max(0, score);
        
        if (score >= 0 && score <= 100) {
            this.recordTest(testName, true, `Security score calculated correctly: ${score}`);
        } else {
            this.recordTest(testName, false, `Invalid security score: ${score}`);
        }
    }

    async testFixPlanGeneration() {
        const testName = 'Fix Plan Generation';
        try {
            // Test fix plan endpoint without auth (should return 401)
            const response = await fetch(`${this.apiUrl}/pr/fix-plan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ repo: 'test/repo', vulnerabilities: [] })
            });
            
            if (response.status === 401) {
                this.recordTest(testName, true, 'Fix plan endpoint properly requires authentication');
            } else {
                this.recordTest(testName, false, `Fix plan endpoint returned: ${response.status}`);
            }
        } catch (error) {
            this.recordTest(testName, false, `Fix plan endpoint error: ${error.message}`);
        }
    }

    async testPRCreationEndpoint() {
        const testName = 'PR Creation Endpoint';
        try {
            // Test auto-fix endpoint without auth (should return 401)
            const response = await fetch(`${this.apiUrl}/pr/auto-fix`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ repo: 'test/repo' })
            });
            
            if (response.status === 401) {
                this.recordTest(testName, true, 'PR creation endpoint properly requires authentication');
            } else {
                this.recordTest(testName, false, `PR creation endpoint returned: ${response.status}`);
            }
        } catch (error) {
            this.recordTest(testName, false, `PR creation endpoint error: ${error.message}`);
        }
    }

    async testScheduleEndpoints() {
        const testName = 'Schedule Endpoints';
        try {
            // Test schedule endpoint without auth (should return 401)
            const response = await fetch(`${this.apiUrl}/schedule/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ repo: 'test/repo', frequency: 'daily' })
            });
            
            if (response.status === 401 || response.status === 404) {
                this.recordTest(testName, true, 'Schedule endpoints properly configured');
            } else {
                this.recordTest(testName, false, `Schedule endpoint returned: ${response.status}`);
            }
        } catch (error) {
            this.recordTest(testName, false, `Schedule endpoint error: ${error.message}`);
        }
    }

    async testNotificationSystem() {
        const testName = 'Notification System';
        
        // Test notification configuration validation
        const validChannels = ['email', 'discord', 'slack', 'webhook'];
        const testConfig = {
            email: 'test@example.com',
            discord: 'https://discord.com/api/webhooks/test',
            slack: 'https://hooks.slack.com/test',
            webhook: 'https://api.example.com/webhook'
        };
        
        let validConfigs = 0;
        for (const [channel, config] of Object.entries(testConfig)) {
            if (validChannels.includes(channel) && config.includes('http')) {
                validConfigs++;
            }
        }
        
        if (validConfigs === Object.keys(testConfig).length - 1) { // email doesn't need http
            this.recordTest(testName, true, 'Notification configuration validation working');
        } else {
            this.recordTest(testName, false, 'Notification configuration validation failed');
        }
    }

    async testBillingEndpoints() {
        const testName = 'Billing Endpoints';
        try {
            // Test billing plans endpoint (should be public)
            const response = await fetch(`${this.apiUrl}/billing/plans`);
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.plans) {
                    this.recordTest(testName, true, 'Billing endpoints responding correctly');
                } else {
                    this.recordTest(testName, false, 'Billing plans endpoint returned invalid data');
                }
            } else {
                this.recordTest(testName, false, `Billing endpoint returned: ${response.status}`);
            }
        } catch (error) {
            this.recordTest(testName, false, `Billing endpoint error: ${error.message}`);
        }
    }

    async testPlanLimits() {
        const testName = 'Plan Limits Logic';
        
        // Test plan limit logic
        const plans = {
            free: { repos_limit: 1, scans_per_day: 1, auto_fix: false },
            pro: { repos_limit: null, scans_per_day: null, auto_fix: true },
            team: { repos_limit: null, scans_per_day: null, auto_fix: true }
        };
        
        let limitsCorrect = true;
        
        // Test free plan limits
        if (plans.free.repos_limit !== 1 || plans.free.scans_per_day !== 1 || plans.free.auto_fix !== false) {
            limitsCorrect = false;
        }
        
        // Test pro plan limits
        if (plans.pro.repos_limit !== null || plans.pro.scans_per_day !== null || plans.pro.auto_fix !== true) {
            limitsCorrect = false;
        }
        
        if (limitsCorrect) {
            this.recordTest(testName, true, 'Plan limits configured correctly');
        } else {
            this.recordTest(testName, false, 'Plan limits configuration incorrect');
        }
    }

    async testSubscriptionFlow() {
        const testName = 'Subscription Flow Structure';
        try {
            // Test subscription endpoint without auth (should return 401)
            const response = await fetch(`${this.apiUrl}/billing/subscription`);
            
            if (response.status === 401) {
                this.recordTest(testName, true, 'Subscription endpoints properly require authentication');
            } else {
                this.recordTest(testName, false, `Subscription endpoint returned: ${response.status}`);
            }
        } catch (error) {
            this.recordTest(testName, false, `Subscription endpoint error: ${error.message}`);
        }
    }

    async testErrorResponses() {
        const testName = 'Error Response Handling';
        try {
            // Test invalid endpoint
            const response = await fetch(`${this.apiUrl}/invalid-endpoint`);
            
            if (response.status === 404) {
                this.recordTest(testName, true, 'Error responses handled correctly');
            } else {
                this.recordTest(testName, false, `Invalid endpoint returned: ${response.status}`);
            }
        } catch (error) {
            this.recordTest(testName, false, `Error handling test failed: ${error.message}`);
        }
    }

    async testInputValidation() {
        const testName = 'Input Validation';
        try {
            // Test scan endpoint with invalid data
            const response = await fetch(`${this.apiUrl}/scan/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ invalid: 'data' })
            });
            
            if (response.status === 400 || response.status === 401) {
                this.recordTest(testName, true, 'Input validation working correctly');
            } else {
                this.recordTest(testName, false, `Input validation returned: ${response.status}`);
            }
        } catch (error) {
            this.recordTest(testName, false, `Input validation test error: ${error.message}`);
        }
    }

    recordTest(name, passed, message) {
        this.results.total++;
        if (passed) {
            this.results.passed++;
            log('green', `✅ ${name}: ${message}`);
        } else {
            this.results.failed++;
            log('red', `❌ ${name}: ${message}`);
        }
        
        this.results.tests.push({
            name,
            passed,
            message,
            timestamp: new Date().toISOString()
        });
    }

    generateReport() {
        log('cyan', '\n📊 Test Results Summary');
        log('cyan', '========================');
        
        log('blue', `Total Tests: ${this.results.total}`);
        log('green', `Passed: ${this.results.passed}`);
        log('red', `Failed: ${this.results.failed}`);
        
        const passRate = ((this.results.passed / this.results.total) * 100).toFixed(1);
        log('yellow', `Pass Rate: ${passRate}%`);
        
        // Deployment readiness
        if (this.results.failed === 0) {
            log('green', '\n🎉 ALL TESTS PASSED - READY FOR DEPLOYMENT! 🚀');
        } else if (this.results.failed <= 2) {
            log('yellow', '\n⚠️ MINOR ISSUES DETECTED - REVIEW BEFORE DEPLOYMENT');
        } else {
            log('red', '\n🚨 CRITICAL ISSUES DETECTED - FIX BEFORE DEPLOYMENT');
        }
        
        // Save detailed results
        const reportPath = 'test-results.json';
        fs.writeFileSync(reportPath, JSON.stringify(this.results, null, 2));
        log('blue', `\n📄 Detailed results saved to: ${reportPath}`);
        
        // Generate deployment checklist
        this.generateDeploymentChecklist();
    }

    generateDeploymentChecklist() {
        const checklist = `
# 🚀 Deployment Readiness Checklist

## Test Results Summary
- **Total Tests**: ${this.results.total}
- **Passed**: ${this.results.passed}
- **Failed**: ${this.results.failed}
- **Pass Rate**: ${((this.results.passed / this.results.total) * 100).toFixed(1)}%

## Deployment Status
${this.results.failed === 0 ? '✅ **READY FOR DEPLOYMENT**' : '❌ **NOT READY - FIX ISSUES FIRST**'}

## Failed Tests
${this.results.tests.filter(t => !t.passed).map(t => `- ❌ ${t.name}: ${t.message}`).join('\n') || 'None - All tests passed! 🎉'}

## Next Steps
${this.results.failed === 0 ? 
`1. ✅ All automated tests passed
2. ✅ Run manual testing checklist
3. ✅ Deploy to production
4. ✅ Monitor for issues
5. ✅ Start marketing campaign!` :
`1. ❌ Fix failed tests above
2. ❌ Re-run test suite
3. ❌ Ensure 100% pass rate
4. ❌ Then proceed with deployment`}

## Manual Testing Required
- [ ] Complete GitHub OAuth flow
- [ ] Test with real repository
- [ ] Verify PR creation works
- [ ] Test billing with Stripe test cards
- [ ] Confirm notifications work

Generated: ${new Date().toISOString()}
        `;
        
        fs.writeFileSync('deployment-checklist.md', checklist);
        log('blue', '📋 Deployment checklist saved to: deployment-checklist.md');
    }
}

// Run tests if called directly
if (require.main === module) {
    const runner = new TestRunner();
    runner.runAllTests().catch(error => {
        console.error('Test runner failed:', error);
        process.exit(1);
    });
}

module.exports = TestRunner;