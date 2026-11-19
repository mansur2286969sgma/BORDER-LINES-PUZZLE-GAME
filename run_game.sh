#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if command -v python3 &>/dev/null; then
    python3 main.py "$@"
else
    python main.py "$@"
fi
