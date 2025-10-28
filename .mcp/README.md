# TasteOS MCP Servers

This directory contains Model Context Protocol (MCP) servers for secure, controlled automation in the TasteOS development workflow.

## Servers

### 1. Shell Server (`shell-server.cjs`)
Executes only whitelisted commands for security.

**Allowed commands:**
- `pwsh -File apps/api/scripts/test_api.ps1` - API smoke tests (PowerShell)
- `bash apps/api/scripts/test_api.sh` - API smoke tests (Bash)
- `pwsh -File apps/api/scripts/login.ps1` - Get authentication token
- `pnpm dev:api/dev:web/dev:app` - Start development servers
- `pnpm typecheck/lint/test` - Run checks

### 2. Filesystem Logs Server (`fs-logs-server.cjs`)
Read-only access to the `LOGS/` directory.

**Tools:**
- `read_log_file` - Read a specific log file
- `list_log_files` - List all log files with metadata

## Setup

1. Install dependencies:
   ```bash
   cd .mcp
   npm install
   ```

2. Configure in VS Code settings (`.vscode/settings.json`):
   ```json
   {
     "mcp.servers": {
       "tasteos-shell": {
         "command": "node",
         "args": ["${workspaceFolder}/.mcp/shell-server.cjs"]
       },
       "tasteos-logs": {
         "command": "node",
         "args": ["${workspaceFolder}/.mcp/fs-logs-server.cjs"]
       }
     }
   }
   ```

## Usage Examples

### Run smoke tests
"Use tasteos-shell to run the API smoke tests"

### Check test results
"Use tasteos-logs to list all log files, then read the latest smoke test"

### Get authentication token
"Use tasteos-shell to run the login script"

## Security

- **Shell server**: Only executes pre-approved commands
- **FS server**: Only accesses LOGS/ directory (read-only)
- No arbitrary shell access
- No access to sensitive files or directories
