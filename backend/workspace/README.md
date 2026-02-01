# FixSec AI Workspace Directory

This directory contains temporary repository clones used for security scanning and PR operations.

## Purpose

- **Scanning**: Clone repositories for vulnerability analysis
- **PR Creation**: Prepare fix branches and create pull requests
- **Fix Planning**: Analyze potential fixes before applying

## Structure

```
workspace/
├── facebook_react_61418cf6/
│   └── repo/                    # Cloned repository code
├── microsoft_vscode_45437e6b/
│   └── repo/
└── user_project_a1b2c3d4/
    └── repo/
```

## Management

- **Automatic Cleanup**: Old workspaces are cleaned up based on age (default: 24 hours)
- **Manual Cleanup**: Use `POST /workspace/cleanup` API endpoint
- **Monitoring**: Use `GET /workspace/stats` for usage statistics

## Benefits

- ✅ **No Windows temp-lock issues** (WinError 32 eliminated)
- ✅ **Faster operations** with workspace reuse
- ✅ **Better debugging** with persistent workspaces
- ✅ **Production monitoring** with health checks

## Configuration

Set environment variables to customize behavior:

- `WORKSPACE_BASE_PATH`: Base directory path (default: backend/workspace)
- `WORKSPACE_MAX_AGE_HOURS`: Cleanup age threshold (default: 24)
- `WORKSPACE_SIZE_WARNING_MB`: Size warning threshold (default: 1000)

## Security

- Workspaces contain cloned repository code with authentication tokens
- Directory is excluded from version control (.gitignore)
- Automatic cleanup prevents sensitive data accumulation