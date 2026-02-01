import re
import os
from typing import List, Dict

# Common secret patterns
SECRET_PATTERNS = {
    "stripe_secret": {
        "pattern": r"sk_live_[0-9a-zA-Z]{24}",
        "description": "Stripe Live Secret Key",
        "severity": "CRITICAL"
    },
    "stripe_test": {
        "pattern": r"sk_test_[0-9a-zA-Z]{24}",
        "description": "Stripe Test Secret Key", 
        "severity": "HIGH"
    },
    "aws_access_key": {
        "pattern": r"AKIA[0-9A-Z]{16}",
        "description": "AWS Access Key ID",
        "severity": "CRITICAL"
    },
    "jwt_secret": {
        "pattern": r"JWT_SECRET\s*[=:]\s*['\"][^'\"]{10,}['\"]",
        "description": "JWT Secret Key",
        "severity": "HIGH"
    },
    "api_key": {
        "pattern": r"API_KEY\s*[=:]\s*['\"][^'\"]{10,}['\"]",
        "description": "Generic API Key",
        "severity": "MEDIUM"
    },
    "private_key": {
        "pattern": r"-----BEGIN PRIVATE KEY-----",
        "description": "Private Key",
        "severity": "CRITICAL"
    },
    "github_token": {
        "pattern": r"ghp_[0-9a-zA-Z]{36}",
        "description": "GitHub Personal Access Token",
        "severity": "HIGH"
    }
}

def scan_secrets(repo_path: str) -> List[Dict]:
    """Scan repository for hardcoded secrets"""
    findings = []
    
    # File extensions to scan
    extensions = ['.js', '.ts', '.jsx', '.tsx', '.json', '.env', '.config.js']
    
    for root, dirs, files in os.walk(repo_path):
        # Skip node_modules and other common directories
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', 'dist', 'build']]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            for secret_type, config in SECRET_PATTERNS.items():
                                if re.search(config["pattern"], line, re.IGNORECASE):
                                    findings.append({
                                        "type": "secrets",
                                        "subtype": secret_type,
                                        "severity": config["severity"],
                                        "file_path": relative_path,
                                        "line_number": line_num,
                                        "message": f"{config['description']} found in code",
                                        "line_content": line.strip(),
                                        "fixable": True,
                                        "confidence_score": 95
                                    })
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
                    continue
    
    return findings

def generate_secret_fix(finding: Dict) -> Dict:
    """Generate fix suggestion for hardcoded secrets"""
    secret_type = finding.get("subtype", "unknown")
    
    fixes = {
        "stripe_secret": {
            "action": "move_to_env",
            "env_var": "STRIPE_SECRET_KEY",
            "replacement": "process.env.STRIPE_SECRET_KEY",
            "instructions": "Move Stripe secret key to .env file and use environment variable"
        },
        "stripe_test": {
            "action": "move_to_env", 
            "env_var": "STRIPE_TEST_KEY",
            "replacement": "process.env.STRIPE_TEST_KEY",
            "instructions": "Move Stripe test key to .env file and use environment variable"
        },
        "jwt_secret": {
            "action": "move_to_env",
            "env_var": "JWT_SECRET",
            "replacement": "process.env.JWT_SECRET",
            "instructions": "Move JWT secret to .env file and use environment variable"
        },
        "api_key": {
            "action": "move_to_env",
            "env_var": "API_KEY", 
            "replacement": "process.env.API_KEY",
            "instructions": "Move API key to .env file and use environment variable"
        }
    }
    
    fix_config = fixes.get(secret_type, {
        "action": "move_to_env",
        "env_var": "SECRET_VALUE",
        "replacement": "process.env.SECRET_VALUE", 
        "instructions": "Move secret to .env file and use environment variable"
    })
    
    return {
        "confidence": 95,
        "fix_type": "environment_variable",
        "description": fix_config["instructions"],
        "changes": [
            {
                "file": ".env",
                "action": "add_line",
                "content": f"{fix_config['env_var']}=your_secret_here"
            },
            {
                "file": finding["file_path"],
                "action": "replace_line",
                "line_number": finding["line_number"],
                "new_content": fix_config["replacement"]
            }
        ]
    }