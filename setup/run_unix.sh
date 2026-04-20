#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

if [ ! -d venv ]; then
    echo "[ERROR] Virtual environment not found."
    echo "Please run ./setup/install_unix.sh first."
    exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "===================================================="
echo "  Requirements Graph Manager"
echo "  Server starting at http://localhost:8000"
echo "  Press Ctrl+C to stop"
echo "===================================================="
echo

python run.py
