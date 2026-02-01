#!/usr/bin/env node

/**
 * FixSec AI Test Data Setup (SAFE VERSION)
 * ✅ Creates a test repository with vulnerabilities BUT WITHOUT real secrets that trigger GitHub push protection
 * ✅ All secrets are placeholders / env-based
 */

const fs = require("fs");
const path = require("path");

// Colors for console output
const colors = {
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  cyan: "\x1b[36m",
  reset: "\x1b[0m",
};

function log(color, message) {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

class TestDataSetup {
  constructor() {
    this.testRepoPath = "./test-vulnerable-repo";
  }

  async setupAllTestData() {
    log("cyan", "🔧 FixSec AI Test Data Setup (SAFE)");
    log("cyan", "===================================");

    await this.createTestRepository();
    await this.createTestFiles();
    await this.createGitRepository();
    await this.generateTestInstructions();

    log("green", "\n🎉 Test data setup complete!");
    log(
      "yellow",
      "⚠️ NOTE: This SAFE version avoids GitHub Push Protection blocks by not including real-looking secrets."
    );
  }

  async createTestRepository() {
    log("blue", "\n📁 Creating test repository structure...");

    if (!fs.existsSync(this.testRepoPath)) {
      fs.mkdirSync(this.testRepoPath, { recursive: true });
      log("green", `✅ Created directory: ${this.testRepoPath}`);
    } else {
      log("yellow", `⚠️ Directory already exists: ${this.testRepoPath}`);
    }

    const subdirs = ["src", "config", "database", "api"];
    for (const subdir of subdirs) {
      const dirPath = path.join(this.testRepoPath, subdir);
      if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
        log("green", `✅ Created subdirectory: ${subdir}`);
      }
    }
  }

  async createTestFiles() {
    log("blue", "\n📄 Creating vulnerable test files...");

    // 1. Package.json with vulnerable dependencies
    const packageJson = {
      name: "fixsec-test-vulnerable-app",
      version: "1.0.0",
      description:
        "Test repository with security vulnerabilities for FixSec AI testing",
      main: "index.js",
      scripts: {
        start: "node index.js",
        test: "jest",
      },
      dependencies: {
        lodash: "4.17.15",
        axios: "0.18.0",
        express: "4.16.0",
        moment: "2.24.0",
        request: "2.88.0",
        handlebars: "4.0.12",
        jquery: "3.3.1",
      },
      devDependencies: {
        jest: "24.0.0",
      },
      keywords: ["test", "security", "vulnerabilities"],
      author: "FixSec AI Test",
      license: "MIT",
    };

    fs.writeFileSync(
      path.join(this.testRepoPath, "package.json"),
      JSON.stringify(packageJson, null, 2)
    );
    log("green", "✅ Created package.json with vulnerable dependencies");

    /**
     * ✅ IMPORTANT CHANGE:
     * We DO NOT place real-looking secrets like sk_live_, Slack webhook URLs, etc.
     * Because GitHub Push Protection blocks them.
     *
     * Instead we use environment variables and obvious placeholders.
     * FixSec scanner will still detect issues because:
     * - hardcoded "JWT_SECRET" pattern exists
     * - "PRIVATE_KEY" pattern exists
     * - "AIza" pattern exists
     * but not values that trigger GitHub.
     */

    // 2. Config file with "hardcoded secret patterns" (safe placeholders)
    const configJs = `
// Configuration file with hardcoded secrets patterns (SECURITY ISSUE - SAFE PLACEHOLDERS)
const config = {
    // Stripe API keys (should be in environment variables)
    stripePublicKey: process.env.STRIPE_PUBLIC_KEY || "STRIPE_PUBLIC_KEY_PLACEHOLDER",
    stripeSecretKey: process.env.STRIPE_SECRET_KEY || "STRIPE_SECRET_KEY_PLACEHOLDER",

    // JWT secret (should be in environment variables)
    jwtSecret: process.env.JWT_SECRET || "JWT_SECRET_HARDCODED_PLACEHOLDER",

    // Database credentials (should be in environment variables)
    database: {
        host: process.env.DB_HOST || "localhost",
        user: process.env.DB_USER || "admin",
        password: process.env.DB_PASSWORD || "PRIVATE_KEY_EXPOSED_PLACEHOLDER",
        database: process.env.DB_NAME || "production_db"
    },

    // API keys (should be in environment variables)
    googleApiKey: process.env.GOOGLE_API_KEY || "AIza_PLACEHOLDER_KEY",

    // GitHub token (should be in environment variables)
    githubToken: process.env.GITHUB_TOKEN || "GITHUB_TOKEN_PLACEHOLDER",

    // Slack webhook (should be in environment variables)
    slackWebhook: process.env.SLACK_WEBHOOK_URL || "SLACK_WEBHOOK_URL_PLACEHOLDER"
};

module.exports = config;
`;

    fs.writeFileSync(
      path.join(this.testRepoPath, "config", "config.js"),
      configJs
    );
    log("green", "✅ Created config.js with safe placeholder secrets");

    // 3. Database file with SQL injection vulnerability
    const dbJs = `
const express = require('express');
const mysql = require('mysql');
const app = express();

app.use(express.json());

// Database connection
const db = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: 'password',
    database: 'testdb'
});

// SQL Injection vulnerability - user input directly in query
app.get('/user/:id', (req, res) => {
    const userId = req.params.id;

    // SECURITY ISSUE: SQL Injection vulnerability
    const query = \`SELECT * FROM users WHERE id = \${userId}\`;

    db.query(query, (err, results) => {
        if (err) {
            res.status(500).json({ error: err.message });
        } else {
            res.json(results);
        }
    });
});

// Another SQL injection vulnerability
app.post('/login', (req, res) => {
    const { username, password } = req.body;

    // SECURITY ISSUE: SQL Injection in login
    const query = \`SELECT * FROM users WHERE username = '\${username}' AND password = '\${password}'\`;

    db.query(query, (err, results) => {
        if (err) {
            res.status(500).json({ error: err.message });
        } else if (results.length > 0) {
            res.json({ success: true, user: results[0] });
        } else {
            res.status(401).json({ error: 'Invalid credentials' });
        }
    });
});

// Search endpoint with SQL injection
app.get('/search', (req, res) => {
    const searchTerm = req.query.q;

    // SECURITY ISSUE: SQL Injection in search
    const query = \`SELECT * FROM products WHERE name LIKE '%\${searchTerm}%'\`;

    db.query(query, (err, results) => {
        if (err) {
            res.status(500).json({ error: err.message });
        } else {
            res.json(results);
        }
    });
});

module.exports = app;
`;

    fs.writeFileSync(path.join(this.testRepoPath, "database", "db.js"), dbJs);
    log("green", "✅ Created db.js with SQL injection vulnerabilities");

    // 4. Environment file (DO NOT include real secrets)
    const envFile = `
# SAFE ENV FILE (no real secrets - placeholders only)
NODE_ENV=production
PORT=3000

DB_HOST=localhost
DB_USER=admin
DB_PASSWORD=PRIVATE_KEY_EXPOSED_PLACEHOLDER
DB_NAME=production_db

STRIPE_SECRET_KEY=STRIPE_SECRET_KEY_PLACEHOLDER
SLACK_WEBHOOK_URL=SLACK_WEBHOOK_URL_PLACEHOLDER
JWT_SECRET=JWT_SECRET_HARDCODED_PLACEHOLDER
GOOGLE_API_KEY=AIza_PLACEHOLDER_KEY
`;

    fs.writeFileSync(path.join(this.testRepoPath, ".env.example"), envFile);
    log("green", "✅ Created .env.example with safe placeholders");

    // 5. API file with more vulnerabilities
    const apiJs = `
const express = require('express');
const fs = require('fs');
const path = require('path');
const app = express();

app.use(express.json());

// SECURITY ISSUE: Hardcoded admin credentials (demo)
const ADMIN_USERNAME = 'admin';
const ADMIN_PASSWORD = 'password123';

// SECURITY ISSUE: Path traversal vulnerability
app.get('/file/:filename', (req, res) => {
    const filename = req.params.filename;

    // Path traversal vulnerability - no input validation
    const filePath = path.join(__dirname, 'uploads', filename);

    fs.readFile(filePath, (err, data) => {
        if (err) {
            res.status(404).json({ error: 'File not found' });
        } else {
            res.send(data);
        }
    });
});

module.exports = app;
`;

    fs.writeFileSync(path.join(this.testRepoPath, "api", "api.js"), apiJs);
    log("green", "✅ Created api.js with vulnerabilities");

    // 6. Main application file
    const indexJs = `
const express = require('express');
const config = require('./config/config');

const app = express();
app.use(express.json());

// SECURITY ISSUE: Hardcoded secret pattern (safe placeholder)
const APP_SECRET = "JWT_SECRET_HARDCODED_PLACEHOLDER";

app.get('/', (req, res) => {
    res.json({
        message: 'FixSec AI Test Application',
        version: '1.0.0',
        // SECURITY ISSUE: Exposing internal information
        secret: APP_SECRET
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(\`Server running on port \${PORT}\`);
});
`;

    fs.writeFileSync(path.join(this.testRepoPath, "index.js"), indexJs);
    log("green", "✅ Created index.js with vulnerability patterns");

    // 7. README file
    const readme = `
# FixSec AI Test Repository (SAFE)

This repository contains **intentional** security vulnerabilities for testing FixSec AI.

✅ SAFE VERSION: No real Stripe keys or Slack webhooks included.
GitHub Push Protection will NOT block pushing this repo.

## Vulnerabilities Included

### 1. Hardcoded Secret Patterns
- JWT_SECRET placeholders
- PRIVATE_KEY placeholders
- AIza placeholders

### 2. Vulnerable Dependencies
- lodash@4.17.15
- axios@0.18.0
- express@4.16.0
- moment@2.24.0
- handlebars@4.0.12

### 3. SQL Injection
- direct user input in SQL queries

## Expected FixSec AI Results
- vulnerable dependency findings
- hardcoded secret pattern findings
- SQL injection findings

**FOR TESTING ONLY**
`;

    fs.writeFileSync(path.join(this.testRepoPath, "README.md"), readme);
    log("green", "✅ Created README.md");
  }

  async createGitRepository() {
    log("blue", "\n🔧 Initializing Git repository...");

    const { execSync } = require("child_process");

    try {
      execSync("git init", { cwd: this.testRepoPath });
      log("green", "✅ Initialized Git repository");

      const gitignore = `
node_modules/
*.log
.DS_Store
.env
.env.local
.env.production
dist/
build/
coverage/
`;
      fs.writeFileSync(path.join(this.testRepoPath, ".gitignore"), gitignore);
      log("green", "✅ Created .gitignore");

      execSync("git add .", { cwd: this.testRepoPath });
      log("green", "✅ Added files to Git");

      execSync('git commit -m "Initial commit with safe test vulnerabilities"', {
        cwd: this.testRepoPath,
      });
      log("green", "✅ Created initial commit");
    } catch (error) {
      log(
        "yellow",
        "⚠️ Git initialization failed (may need to be done manually)"
      );
      log("yellow", `Error: ${error.message}`);
    }
  }

  async generateTestInstructions() {
    log("blue", "\n📋 Generating test instructions...");

    const instructions = `
# 🧪 FixSec AI Testing Instructions (SAFE)

Test Repository Created:
📍 Location: \`${this.testRepoPath}\`

## ✅ Push to GitHub (safe)
\`\`\`bash
cd ${this.testRepoPath}
git remote add origin https://github.com/YOUR_USERNAME/fixsec-test-repo.git
git branch -M main
git push -u origin main
\`\`\`

## ✅ Expected Results
- Secrets detected: JWT_SECRET / PRIVATE_KEY / AIza patterns
- Dependency vulns detected: lodash, axios, handlebars, etc.
- SQL injection patterns detected in database/db.js

✅ SAFE: No real Stripe keys or Slack webhooks included.
`;

    fs.writeFileSync("TEST-INSTRUCTIONS.md", instructions);
    log("green", "✅ Created TEST-INSTRUCTIONS.md");
  }
}

// Run setup if called directly
if (require.main === module) {
  const setup = new TestDataSetup();
  setup.setupAllTestData().catch((error) => {
    console.error("Test data setup failed:", error);
    process.exit(1);
  });
}

module.exports = TestDataSetup;
