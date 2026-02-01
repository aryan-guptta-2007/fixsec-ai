#!/usr/bin/env node

/**
 * FixSec AI Manual Test Flow Guide
 * Interactive testing guide for critical user journeys
 */

const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

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

function ask(question) {
    return new Promise((resolve) => {
        rl.question(question, resolve);
    });
}

class ManualTestGuide {
    constructor() {
        this.testResults = [];
        this.currentTest = 0;
        this.totalTests = 4;
    }

    async runAllTests() {
        log('cyan', '🧪 FixSec AI Manual Testing Guide');
        log('cyan', '==================================');
        log('yellow', 'This guide will walk you through testing all critical user flows.');
        log('yellow', 'Follow each step carefully and report the results.\n');

        await this.testAuthenticationFlow();
        await this.testScanningFlow();
        await this.testAutoFixFlow();
        await this.testBillingFlow();

        this.generateFinalReport();
        rl.close();
    }

    async testAuthenticationFlow() {
        this.currentTest++;
        log('blue', `\n📋 TEST ${this.currentTest}/${this.totalTests}: Authentication & Repository List`);
        log('blue', '================================================');

        const steps = [
            {
                step: 1,
                instruction: 'Navigate to http://localhost:3000',
                expected: 'Landing page loads with "Login with GitHub" button'
            },
            {
                step: 2,
                instruction: 'Click "Login with GitHub"',
                expected: 'Redirects to GitHub OAuth page'
            },
            {
                step: 3,
                instruction: 'Complete GitHub OAuth (authorize the app)',
                expected: 'Redirects back to dashboard with token in URL'
            },
            {
                step: 4,
                instruction: 'Verify dashboard loads',
                expected: 'Shows "FixSec AI Dashboard" header and repository list'
            },
            {
                step: 5,
                instruction: 'Check repository list',
                expected: 'Shows your GitHub repositories with Scan and Schedule buttons'
            }
        ];

        let testPassed = true;
        for (const { step, instruction, expected } of steps) {
            log('yellow', `\nStep ${step}: ${instruction}`);
            log('cyan', `Expected: ${expected}`);
            
            const result = await ask('Did this step work correctly? (y/n): ');
            if (result.toLowerCase() !== 'y') {
                testPassed = false;
                const issue = await ask('What went wrong? ');
                log('red', `❌ Issue: ${issue}`);
            } else {
                log('green', '✅ Step passed');
            }
        }

        this.recordTestResult('Authentication & Repository List', testPassed);
    }

    async testScanningFlow() {
        this.currentTest++;
        log('blue', `\n📋 TEST ${this.currentTest}/${this.totalTests}: Security Scanning`);
        log('blue', '=====================================');

        log('yellow', '\nPrerequisite: Create a test repository with vulnerabilities');
        log('cyan', 'Create a repo with these files:');
        log('cyan', '1. package.json with old dependencies (lodash@4.17.15, axios@0.18.0)');
        log('cyan', '2. config.js with hardcoded secrets (sk_live_, JWT_SECRET)');
        log('cyan', '3. db.js with SQL injection vulnerability');

        const repoReady = await ask('\nHave you created the test repository? (y/n): ');
        if (repoReady.toLowerCase() !== 'y') {
            log('red', '❌ Test repository required. Please create it first.');
            this.recordTestResult('Security Scanning', false);
            return;
        }

        const steps = [
            {
                step: 1,
                instruction: 'Click "Scan" button on your test repository',
                expected: 'Scan starts immediately, shows loading state'
            },
            {
                step: 2,
                instruction: 'Wait for scan completion (should take < 60 seconds)',
                expected: 'Redirects to scan results page'
            },
            {
                step: 3,
                instruction: 'Check vulnerability count',
                expected: 'Shows count > 0 (should detect secrets and dependencies)'
            },
            {
                step: 4,
                instruction: 'Review vulnerability table',
                expected: 'Shows different types: secrets, dependencies, with severity levels'
            },
            {
                step: 5,
                instruction: 'Check security score',
                expected: 'Shows score 0-100 and grade (A+ to F)'
            },
            {
                step: 6,
                instruction: 'Verify file paths and line numbers',
                expected: 'Accurate file locations and line references'
            }
        ];

        let testPassed = true;
        for (const { step, instruction, expected } of steps) {
            log('yellow', `\nStep ${step}: ${instruction}`);
            log('cyan', `Expected: ${expected}`);
            
            const result = await ask('Did this step work correctly? (y/n): ');
            if (result.toLowerCase() !== 'y') {
                testPassed = false;
                const issue = await ask('What went wrong? ');
                log('red', `❌ Issue: ${issue}`);
            } else {
                log('green', '✅ Step passed');
            }
        }

        // Additional checks
        const vulnCount = await ask('\nHow many vulnerabilities were detected? ');
        const securityScore = await ask('What was the security score? ');
        
        log('cyan', `Detected vulnerabilities: ${vulnCount}`);
        log('cyan', `Security score: ${securityScore}`);

        this.recordTestResult('Security Scanning', testPassed);
    }

    async testAutoFixFlow() {
        this.currentTest++;
        log('blue', `\n📋 TEST ${this.currentTest}/${this.totalTests}: Auto-Fix PR Creation`);
        log('blue', '==========================================');

        const steps = [
            {
                step: 1,
                instruction: 'From scan results, click "Analyze & Create Fix Plan"',
                expected: 'Fix plan modal opens showing what can be fixed'
            },
            {
                step: 2,
                instruction: 'Review fix plan details',
                expected: 'Shows dependency fixes available, secrets require manual review'
            },
            {
                step: 3,
                instruction: 'Click "Create PR Now"',
                expected: 'PR creation starts with loading indicator'
            },
            {
                step: 4,
                instruction: 'Wait for PR creation completion',
                expected: 'Success modal shows with PR URL'
            },
            {
                step: 5,
                instruction: 'Click PR URL to open in GitHub',
                expected: 'PR exists in GitHub with dependency updates'
            },
            {
                step: 6,
                instruction: 'Review PR content in GitHub',
                expected: 'PR contains package.json updates and clear description'
            },
            {
                step: 7,
                instruction: 'Merge the PR in GitHub',
                expected: 'PR merges successfully'
            },
            {
                step: 8,
                instruction: 'Return to FixSec AI and scan the same repo again',
                expected: 'New scan shows fewer vulnerabilities (dependencies fixed)'
            }
        ];

        let testPassed = true;
        for (const { step, instruction, expected } of steps) {
            log('yellow', `\nStep ${step}: ${instruction}`);
            log('cyan', `Expected: ${expected}`);
            
            const result = await ask('Did this step work correctly? (y/n): ');
            if (result.toLowerCase() !== 'y') {
                testPassed = false;
                const issue = await ask('What went wrong? ');
                log('red', `❌ Issue: ${issue}`);
            } else {
                log('green', '✅ Step passed');
            }
        }

        const beforeCount = await ask('\nHow many vulnerabilities before PR merge? ');
        const afterCount = await ask('How many vulnerabilities after PR merge? ');
        
        log('cyan', `Vulnerabilities before: ${beforeCount}`);
        log('cyan', `Vulnerabilities after: ${afterCount}`);

        if (parseInt(afterCount) < parseInt(beforeCount)) {
            log('green', '✅ Vulnerability count decreased - auto-fix working!');
        } else {
            log('red', '❌ Vulnerability count did not decrease');
            testPassed = false;
        }

        this.recordTestResult('Auto-Fix PR Creation', testPassed);
    }

    async testBillingFlow() {
        this.currentTest++;
        log('blue', `\n📋 TEST ${this.currentTest}/${this.totalTests}: Billing System`);
        log('blue', '================================');

        log('yellow', '\nNote: This test uses Stripe test mode. Use test card: 4242 4242 4242 4242');

        const steps = [
            {
                step: 1,
                instruction: 'Click "💳 Billing" in dashboard header',
                expected: 'Billing page loads showing current plan and usage'
            },
            {
                step: 2,
                instruction: 'Review current usage stats',
                expected: 'Shows repository count, scans today, scans this month'
            },
            {
                step: 3,
                instruction: 'Click "Upgrade to Professional" button',
                expected: 'Redirects to Stripe checkout page'
            },
            {
                step: 4,
                instruction: 'Fill in Stripe checkout with test card (4242 4242 4242 4242)',
                expected: 'Checkout form accepts test card details'
            },
            {
                step: 5,
                instruction: 'Complete payment',
                expected: 'Redirects to success page'
            },
            {
                step: 6,
                instruction: 'Return to dashboard and try unlimited scans',
                expected: 'Can now scan multiple times without limit'
            },
            {
                step: 7,
                instruction: 'Test auto-fix feature (should now be available)',
                expected: 'Auto-fix works without upgrade prompts'
            },
            {
                step: 8,
                instruction: 'Go back to billing page',
                expected: 'Shows Pro plan as current subscription'
            }
        ];

        let testPassed = true;
        for (const { step, instruction, expected } of steps) {
            log('yellow', `\nStep ${step}: ${instruction}`);
            log('cyan', `Expected: ${expected}`);
            
            const result = await ask('Did this step work correctly? (y/n): ');
            if (result.toLowerCase() !== 'y') {
                testPassed = false;
                const issue = await ask('What went wrong? ');
                log('red', `❌ Issue: ${issue}`);
            } else {
                log('green', '✅ Step passed');
            }
        }

        // Test plan limits
        log('yellow', '\nTesting plan limits...');
        const limitTest = await ask('Try scanning as a free user - do you get upgrade prompts? (y/n): ');
        if (limitTest.toLowerCase() !== 'y') {
            log('red', '❌ Plan limits not working correctly');
            testPassed = false;
        } else {
            log('green', '✅ Plan limits working correctly');
        }

        this.recordTestResult('Billing System', testPassed);
    }

    recordTestResult(testName, passed) {
        this.testResults.push({
            name: testName,
            passed,
            timestamp: new Date().toISOString()
        });

        if (passed) {
            log('green', `\n🎉 ${testName} - ALL STEPS PASSED!`);
        } else {
            log('red', `\n❌ ${testName} - SOME STEPS FAILED!`);
        }
    }

    generateFinalReport() {
        log('cyan', '\n📊 Final Test Results');
        log('cyan', '=====================');

        const passed = this.testResults.filter(t => t.passed).length;
        const total = this.testResults.length;
        const passRate = ((passed / total) * 100).toFixed(1);

        log('blue', `Total Test Suites: ${total}`);
        log('green', `Passed: ${passed}`);
        log('red', `Failed: ${total - passed}`);
        log('yellow', `Pass Rate: ${passRate}%`);

        log('\n📋 Test Results Summary:');
        this.testResults.forEach(test => {
            const status = test.passed ? '✅' : '❌';
            log(test.passed ? 'green' : 'red', `${status} ${test.name}`);
        });

        // Deployment readiness
        if (passed === total) {
            log('green', '\n🎉 ALL MANUAL TESTS PASSED!');
            log('green', '🚀 YOUR FIXSEC AI IS READY FOR DEPLOYMENT!');
            log('yellow', '\nNext steps:');
            log('yellow', '1. Run automated tests: node test-runner.js');
            log('yellow', '2. Complete deployment checklist');
            log('yellow', '3. Deploy to production');
            log('yellow', '4. Start your marketing campaign!');
        } else {
            log('red', '\n🚨 SOME TESTS FAILED - FIX ISSUES BEFORE DEPLOYMENT');
            log('yellow', '\nFailed tests need to be fixed:');
            this.testResults.filter(t => !t.passed).forEach(test => {
                log('red', `- ${test.name}`);
            });
        }

        // Save results
        const fs = require('fs');
        const report = {
            timestamp: new Date().toISOString(),
            totalTests: total,
            passedTests: passed,
            failedTests: total - passed,
            passRate: passRate,
            results: this.testResults,
            deploymentReady: passed === total
        };

        fs.writeFileSync('manual-test-results.json', JSON.stringify(report, null, 2));
        log('blue', '\n📄 Results saved to: manual-test-results.json');
    }
}

// Run manual tests if called directly
if (require.main === module) {
    const guide = new ManualTestGuide();
    guide.runAllTests().catch(error => {
        console.error('Manual test guide failed:', error);
        process.exit(1);
    });
}

module.exports = ManualTestGuide;