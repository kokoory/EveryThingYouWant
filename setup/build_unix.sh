#!/usr/bin/env bash
set -e

echo "===================================================="
echo "  Requirements Graph Manager - Portable Build"
echo "===================================================="
echo

cd "$(dirname "$0")/.."

if [ ! -d venv ]; then
    echo "[ERROR] Run ./setup/install_unix.sh first."
    exit 1
fi

source venv/bin/activate

# Install PyInstaller
echo "[1/3] Installing PyInstaller..."
pip install pyinstaller

# Clean
echo
echo "[2/3] Cleaning previous build..."
rm -rf dist/RequirementsGraphManager build/

# Build
echo
echo "[3/3] Building portable executable..."
pyinstaller build_portable.spec --noconfirm

# Create launcher script
cat > dist/RequirementsGraphManager/start.sh << 'SCRIPT'
#!/usr/bin/env bash
cd "$(dirname "$0")"
./RequirementsGraphManager
SCRIPT
chmod +x dist/RequirementsGraphManager/start.sh
chmod +x dist/RequirementsGraphManager/RequirementsGraphManager

echo
echo "===================================================="
echo "  Build complete!"
echo "===================================================="
echo
echo "  Output folder: dist/RequirementsGraphManager/"
echo "  Run:           ./dist/RequirementsGraphManager/start.sh"
echo
echo "  Copy the entire folder to any machine (same OS)"
echo "  and run start.sh without installing Python!"
echo
