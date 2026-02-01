import re
import os
from typing import List, Dict

# SQL injection patterns for JavaScript/Node.js
SQL_INJECTION_PATTERNS = {
    "string_concatenation": {
        "pattern": r"(SELECT|INSERT|UPDATE|DELETE).*\+.*['\"]",
        "description": "SQL query using string concatenation",
        "severity": "HIGH"
    },
    "template_literal": {
        "pattern": r"`(SELECT|INSERT|UPDATE|DELETE).*\$\{.*\}`",
        "description": "SQL query using template literals with variables",
        "severity": "HIGH"
    },
    "direct_interpolation": {
        "pattern": r"['\"]SELECT.*['\"].*\+.*req\.(body|query|params)",
        "description": "Direct user input interpolation in SQL query",
        "severity": "CRITICAL"
    },
    "mysql_query": {
        "pattern": r"connection\.query\s*\(\s*['\"].*\+",
        "description": "MySQL query with string concatenation",
        "severity": "HIGH"
    },
    "postgres_query": {
        "pattern": r"client\.query\s*\(\s*['\"].*\+",
        "description": "PostgreSQL query with string concatenation", 
        "severity": "HIGH"
    }
}

# Safe patterns to exclude (parameterized queries)
SAFE_PATTERNS = [
    r"\$\d+",  # PostgreSQL parameterized queries ($1, $2, etc.)
    r"\?",     # MySQL/SQLite parameterized queries
    r":\w+",   # Named parameters
]

def scan_sql_injection(repo_path: str) -> List[Dict]:
    """Scan repository for SQL injection vulnerabilities"""
    findings = []
    
    # File extensions to scan
    extensions = ['.js', '.ts', '.jsx', '.tsx']
    
    for root, dirs, files in os.walk(repo_path):
        # Skip node_modules and other directories
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', 'dist', 'build']]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                        for line_num, line in enumerate(lines, 1):
                            # Skip comments and empty lines
                            stripped_line = line.strip()
                            if not stripped_line or stripped_line.startswith('//') or stripped_line.startswith('*'):
                                continue
                            
                            # Check for SQL injection patterns
                            for pattern_name, config in SQL_INJECTION_PATTERNS.items():
                                if re.search(config["pattern"], line, re.IGNORECASE):
                                    # Check if it's already using safe parameterized queries
                                    is_safe = any(re.search(safe_pattern, line) for safe_pattern in SAFE_PATTERNS)
                                    
                                    if not is_safe:
                                        findings.append({
                                            "type": "sql_injection",
                                            "subtype": pattern_name,
                                            "severity": config["severity"],
                                            "file_path": relative_path,
                                            "line_number": line_num,
                                            "message": config["description"],
                                            "line_content": line.strip(),
                                            "fixable": True,
                                            "confidence_score": 85
                                        })
                                        
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
                    continue
    
    return findings

def generate_sql_injection_fix(finding: Dict) -> Dict:
    """Generate fix suggestion for SQL injection vulnerabilities"""
    subtype = finding.get("subtype", "")
    line_content = finding.get("line_content", "")
    
    # Detect database library being used
    db_library = "unknown"
    if "mysql" in line_content.lower() or "connection.query" in line_content:
        db_library = "mysql"
    elif "pg" in line_content.lower() or "client.query" in line_content:
        db_library = "postgresql"
    elif "sqlite" in line_content.lower():
        db_library = "sqlite"
    
    fixes = {
        "mysql": {
            "description": "Use parameterized queries with MySQL",
            "example": "connection.query('SELECT * FROM users WHERE id = ?', [userId])",
            "confidence": 90
        },
        "postgresql": {
            "description": "Use parameterized queries with PostgreSQL",
            "example": "client.query('SELECT * FROM users WHERE id = $1', [userId])",
            "confidence": 90
        },
        "sqlite": {
            "description": "Use parameterized queries with SQLite",
            "example": "db.get('SELECT * FROM users WHERE id = ?', [userId])",
            "confidence": 90
        },
        "unknown": {
            "description": "Use parameterized queries instead of string concatenation",
            "example": "Use prepared statements or parameterized queries",
            "confidence": 70
        }
    }
    
    fix_config = fixes.get(db_library, fixes["unknown"])
    
    return {
        "confidence": fix_config["confidence"],
        "fix_type": "parameterized_query",
        "description": fix_config["description"],
        "example": fix_config["example"],
        "changes": [
            {
                "file": finding["file_path"],
                "action": "replace_line",
                "line_number": finding["line_number"],
                "description": "Replace string concatenation with parameterized query",
                "suggestion": fix_config["example"]
            }
        ],
        "additional_info": {
            "cwe": "CWE-89: SQL Injection",
            "owasp": "A03:2021 – Injection",
            "references": [
                "https://owasp.org/www-community/attacks/SQL_Injection",
                "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
            ]
        }
    }

def detect_orm_usage(repo_path: str) -> Dict:
    """Detect if the project uses an ORM that provides built-in protection"""
    package_json_path = os.path.join(repo_path, "package.json")
    
    orm_libraries = {
        "sequelize": "Sequelize ORM",
        "typeorm": "TypeORM", 
        "prisma": "Prisma ORM",
        "mongoose": "Mongoose ODM",
        "knex": "Knex.js Query Builder"
    }
    
    detected_orms = []
    
    if os.path.exists(package_json_path):
        try:
            import json
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
                
            dependencies = {
                **package_data.get("dependencies", {}),
                **package_data.get("devDependencies", {})
            }
            
            for orm_name, orm_display in orm_libraries.items():
                if orm_name in dependencies:
                    detected_orms.append({
                        "name": orm_name,
                        "display_name": orm_display,
                        "version": dependencies[orm_name]
                    })
                    
        except Exception as e:
            print(f"Error reading package.json: {e}")
    
    return {"orms": detected_orms}