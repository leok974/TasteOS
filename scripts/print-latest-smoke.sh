#!/usr/bin/env bash
set -euo pipefail
ls -t LOGS/smoke.*.log 2>/dev/null | head -n1 || echo ""
