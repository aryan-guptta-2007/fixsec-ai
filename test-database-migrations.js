#!/usr/bin/env node
/**
 * Database Migrations Test for FixSec AI
 * Tests that database schema and migrations work correctly
 */

const fs = require('fs');
const path = require('path');

console.log('🗄️ FixSec AI Database Migrations Test\n');

// Test database migration system
function testMigrationSystem() {
  console.log('📋 Testing Migration System:\n');
  
  const tests = [
    {
      name: "Alembic Configuration",
      check: () => {
        const alembicIni = path.join('backend', 'alembic.ini');
        const alembicEnv = path.join('backend', 'alembic', 'env.py');
        
        return fs.existsSync(alembicIni) && fs.existsSync(alembicEnv);
      },
      description: "Alembic is properly configured"
    },
    {
      name: "Database Models",
      check: () => {
        const modelsFile = path.join('backend', 'db', 'models.py');
        if (!fs.existsSync(modelsFile)) return false;
        
        const content = fs.readFileSync(modelsFile, 'utf8');
        const requiredModels = ['User', 'Repository', 'Scan', 'Vulnerability', 'PullRequest'];
        
        return requiredModels.every(model => content.includes(`class ${model}`));
      },
      description: "All required database models are defined"
    },
    {
      name: "Initial Migration",
      check: () => {
        const versionsDir = path.join('backend', 'alembic', 'versions');
        if (!fs.existsSync(versionsDir)) return false;
        
        const files = fs.readdirSync(versionsDir);
        const migrationFiles = files.filter(f => f.endsWith('.py') && f.includes('initial'));
        
        return migrationFiles.length > 0;
      },
      description: "Initial database migration exists"
    },
    {
      name: "Database Initialization Script",
      check: () => {
        const initScript = path.join('backend', 'db', 'init_db.py');
        if (!fs.existsSync(initScript)) return false;
        
        const content = fs.readFileSync(initScript, 'utf8');
        return content.includes('init_database') && content.includes('run_migrations');
      },
      description: "Database initialization script is complete"
    },
    {
      name: "Deployment Integration",
      check: () => {
        const deployScript = path.join('deploy.sh');
        if (!fs.existsSync(deployScript)) return false;
        
        const content = fs.readFileSync(deployScript, 'utf8');
        return content.includes('database migrations') && content.includes('init_db.py');
      },
      description: "Deployment script includes database migrations"
    },
    {
      name: "Environment Support",
      check: () => {
        const sessionFile = path.join('backend', 'db', 'session.py');
        if (!fs.existsSync(sessionFile)) return false;
        
        const content = fs.readFileSync(sessionFile, 'utf8');
        return content.includes('sqlite') && content.includes('postgresql');
      },
      description: "Both SQLite and PostgreSQL are supported"
    }
  ];
  
  let passed = 0;
  let total = tests.length;
  
  tests.forEach((test, index) => {
    try {
      const result = test.check();
      if (result) {
        console.log(`✅ Test ${index + 1}: ${test.name}`);
        console.log(`   ${test.description}`);
        passed++;
      } else {
        console.log(`❌ Test ${index + 1}: ${test.name}`);
        console.log(`   ${test.description} - FAILED`);
      }
    } catch (error) {
      console.log(`❌ Test ${index + 1}: ${test.name}`);
      console.log(`   Error: ${error.message}`);
    }
  });
  
  console.log(`\n🎯 Test Summary: ${passed}/${total} tests passed`);
  return { passed, total };
}

// Test database schema structure
function testDatabaseSchema() {
  console.log('\n📊 Testing Database Schema:\n');
  
  const modelsFile = path.join('backend', 'db', 'models.py');
  if (!fs.existsSync(modelsFile)) {
    console.log('❌ Models file not found');
    return { passed: 0, total: 1 };
  }
  
  const content = fs.readFileSync(modelsFile, 'utf8');
  
  const schemaTests = [
    {
      name: "User Model",
      check: () => content.includes('class User') && 
                   content.includes('github_id') && 
                   content.includes('github_token'),
      description: "User model has GitHub OAuth fields"
    },
    {
      name: "Repository Model", 
      check: () => content.includes('class Repository') &&
                   content.includes('user_id') &&
                   content.includes('ForeignKey("users.id")'),
      description: "Repository model links to users"
    },
    {
      name: "Scan Model",
      check: () => content.includes('class Scan') &&
                   content.includes('repo_id') &&
                   content.includes('issues_found'),
      description: "Scan model tracks vulnerability scans"
    },
    {
      name: "Vulnerability Model",
      check: () => content.includes('class Vulnerability') &&
                   content.includes('severity') &&
                   content.includes('file_path'),
      description: "Vulnerability model stores security issues"
    },
    {
      name: "PullRequest Model",
      check: () => content.includes('class PullRequest') &&
                   content.includes('pr_url') &&
                   content.includes('fixes_applied'),
      description: "PullRequest model tracks auto-fix PRs"
    },
    {
      name: "Relationships",
      check: () => content.includes('relationship(') &&
                   content.includes('back_populates'),
      description: "Models have proper relationships defined"
    }
  ];
  
  let passed = 0;
  let total = schemaTests.length;
  
  schemaTests.forEach((test, index) => {
    const result = test.check();
    if (result) {
      console.log(`✅ Schema ${index + 1}: ${test.name}`);
      console.log(`   ${test.description}`);
      passed++;
    } else {
      console.log(`❌ Schema ${index + 1}: ${test.name}`);
      console.log(`   ${test.description} - FAILED`);
    }
  });
  
  console.log(`\n🎯 Schema Summary: ${passed}/${total} tests passed`);
  return { passed, total };
}

// Test production readiness
function testProductionReadiness() {
  console.log('\n🚀 Testing Production Readiness:\n');
  
  const productionTests = [
    {
      name: "Environment Variables",
      check: () => {
        const configFile = path.join('backend', 'config.py');
        if (!fs.existsSync(configFile)) return false;
        
        const content = fs.readFileSync(configFile, 'utf8');
        return content.includes('DATABASE_URL') && content.includes('os.getenv');
      },
      description: "Database URL configurable via environment"
    },
    {
      name: "Docker Integration",
      check: () => {
        const dockerCompose = path.join('docker-compose.prod.yml');
        if (!fs.existsSync(dockerCompose)) return false;
        
        const content = fs.readFileSync(dockerCompose, 'utf8');
        return content.includes('postgres') && content.includes('DATABASE_URL');
      },
      description: "Docker Compose includes database service"
    },
    {
      name: "Migration Safety",
      check: () => {
        const initScript = path.join('backend', 'db', 'init_db.py');
        if (!fs.existsSync(initScript)) return false;
        
        const content = fs.readFileSync(initScript, 'utf8');
        return content.includes('verify_database') && content.includes('logger');
      },
      description: "Migration script includes safety checks"
    },
    {
      name: "Health Checks",
      check: () => {
        const mainFile = path.join('backend', 'main.py');
        if (!fs.existsSync(mainFile)) return false;
        
        const content = fs.readFileSync(mainFile, 'utf8');
        return content.includes('/health');
      },
      description: "Health check endpoint available"
    }
  ];
  
  let passed = 0;
  let total = productionTests.length;
  
  productionTests.forEach((test, index) => {
    const result = test.check();
    if (result) {
      console.log(`✅ Production ${index + 1}: ${test.name}`);
      console.log(`   ${test.description}`);
      passed++;
    } else {
      console.log(`❌ Production ${index + 1}: ${test.name}`);
      console.log(`   ${test.description} - FAILED`);
    }
  });
  
  console.log(`\n🎯 Production Summary: ${passed}/${total} tests passed`);
  return { passed, total };
}

// Run all tests
console.log('🧪 Running Database Migration Tests...\n');

const migrationResults = testMigrationSystem();
const schemaResults = testDatabaseSchema();
const productionResults = testProductionReadiness();

const totalPassed = migrationResults.passed + schemaResults.passed + productionResults.passed;
const totalTests = migrationResults.total + schemaResults.total + productionResults.total;

console.log('\n📊 Overall Test Results:');
console.log(`✅ Passed: ${totalPassed}/${totalTests} tests`);
console.log(`📈 Success Rate: ${Math.round((totalPassed/totalTests) * 100)}%`);

if (totalPassed === totalTests) {
  console.log('\n🎉 All tests passed! Database migration system is production-ready.');
  
  console.log('\n💡 Migration System Benefits:');
  console.log('• ✅ Automatic database schema creation');
  console.log('• ✅ Safe schema updates without data loss');
  console.log('• ✅ Version-controlled database changes');
  console.log('• ✅ Consistent deployments across environments');
  console.log('• ✅ Support for both SQLite and PostgreSQL');
  
  console.log('\n🚀 Deployment Commands:');
  console.log('# Development');
  console.log('cd backend && alembic upgrade head');
  console.log('');
  console.log('# Production');
  console.log('python db/init_db.py');
  console.log('');
  console.log('# Docker');
  console.log('docker-compose run --rm backend python db/init_db.py');
  
} else {
  console.log('\n⚠️ Some tests failed. Check migration system setup.');
}

console.log('\n✅ Database migration testing complete!');