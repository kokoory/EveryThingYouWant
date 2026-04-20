#!/usr/bin/env bash
set -e

echo "===================================================="
echo "  Requirements Graph Manager - Unix Setup"
echo "  (Python 3.12)"
echo "===================================================="
echo

# Check Python 3.12
PYTHON_BIN=""
for cmd in python3.12 python3 python; do
    if command -v "$cmd" &> /dev/null; then
        VERSION=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        if [[ "$VERSION" == "3.12" ]]; then
            PYTHON_BIN="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[WARNING] Python 3.12 not found. Trying default python3..."
    if ! command -v python3 &> /dev/null; then
        echo "[ERROR] Python 3 is not installed."
        echo "Install Python 3.12: https://www.python.org/downloads/"
        exit 1
    fi
    PYTHON_BIN="python3"
fi

echo "Using: $PYTHON_BIN ($("$PYTHON_BIN" --version))"

# Move to project root
cd "$(dirname "$0")/.."

# Create virtual environment
if [ ! -d venv ]; then
    echo
    echo "[1/3] Creating virtual environment..."
    "$PYTHON_BIN" -m venv venv
else
    echo "[1/3] Virtual environment already exists. Skipping."
fi

# Activate
echo
echo "[2/3] Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate

# Detect platform for offline wheels
PLATFORM=""
case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) PLATFORM="linux" ;;
    Darwin-arm64) PLATFORM="macos_arm64" ;;
    Darwin-x86_64) PLATFORM="macos_intel" ;;
esac

# Install
echo
echo "[3/3] Installing dependencies..."

if [ -n "$PLATFORM" ] && [ -d "setup/wheels/$PLATFORM" ]; then
    echo "Using offline wheel cache: setup/wheels/$PLATFORM"
    if ! python -m pip install --no-index --find-links="setup/wheels/$PLATFORM" -r setup/requirements.txt; then
        echo "[WARNING] Offline install failed, trying online..."
        python -m pip install --upgrade pip
        python -m pip install -r setup/requirements.txt
    fi
else
    python -m pip install --upgrade pip
    python -m pip install -r setup/requirements.txt
fi

echo
echo "===================================================="
echo "  Installation complete!"
echo "===================================================="
echo
echo "To start the server, run:  ./setup/run_unix.sh"
echo "Then open browser at:      http://localhost:8000"
echo
