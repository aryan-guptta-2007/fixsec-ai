#!/usr/bin/env node

/**
 * Remove Demo Vulnerabilities Script
 * Ensures FixSec AI shows real results, not demo data
 */

const fs = require('fs');
const path = require('path');

console.log('🧹 Removing demo vulnerabilities and test data...');

// Remove any demo files that might create fake vulnerabilities
const demoFiles = [
  'demo-secrets.js',
  'test-vulnerabilities.js',
  'fake-api-keys.env',
  'demo-sql-injection.js',
  'test-hardcoded-secrets.js'
];

demoFiles.forEach(file => {
  if (fs.existsSync(file)) {
    fs.unlinkSync(file);
    console.log(`✅ Removed: ${file}`);
  }
});

// Clean up any test directories
const testDirs = [
  'demo-vulnerable-code',
  'test-security-issues'
];

testDirs.forEach(dir => {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
    console.log(`✅ Removed directory: ${dir}`);
  }
});

// Ensure .fixsecignore is properly configured
const fixsecIgnoreContent = `# FixSec AI Ignore Rules
# Production configuration - no demo vulnerabilities

# Ignore build and dependency directories
node_modules/
dist/
build/
.next/
*.min.js

# Ignore test files (they often contain fake secrets for testing)
test/**/*
tests/**/*
__tests__/**/*
*.test.js
*.test.ts
*.spec.js
*.spec.ts

# Ignore demo and example files
demo/**/*
examples/**/*
**/demo/**/*
**/examples/**/*

# Ignore specific demo patterns
*demo*
*example*
*test*api*key*
*fake*secret*

# Ignore documentation that might contain example keys
README.md
docs/**/*
*.md
`;

fs.writeFileSync('.fixsecignore', fixsecIgnoreContent);
console.log('✅ Updated .fixsecignore with production rules');

console.log('🎯 Demo cleanup complete! FixSec AI will now show real security results.');
console.log('💡 Run a fresh scan to see clean, production-ready results.');