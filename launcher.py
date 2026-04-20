"""Portable launcher for Requirements Graph Manager.

This is the entry point for the PyInstaller-built executable.
It starts the FastAPI server and opens the browser automatically.
"""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def get_base_path():
    """Get the base path for bundled resources."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def get_data_path():
    """Get writable data path next to the executable."""
    if getattr(sys, 'frozen', False):
        return Path(os.path.dirname(sys.executable)) / "data"
    return Path(__file__).parent / "data"


def open_browser(port):
    """Open browser after a short delay."""
    time.sleep(2)
    webbrowser.open(f"http://localhost:{port}")


def main():
    port = 8000
    host = "127.0.0.1"

    # Set data directory environment variable
    data_path = get_data_path()
    data_path.mkdir(parents=True, exist_ok=True)
    os.environ["RGM_DATA_DIR"] = str(data_path)

    # Set base path for frontend files
    base_path = get_base_path()
    os.environ["RGM_BASE_DIR"] = str(base_path)

    print("=" * 52)
    print("  Requirements Graph Manager")
    print("=" * 52)
    print(f"  Server:  http://localhost:{port}")
    print(f"  Data:    {data_path}")
    print(f"  Base:    {base_path}")
    print("=" * 52)
    print()
    print("  Browser will open automatically...")
    print("  Press Ctrl+C to stop the server.")
    print()

    # Open browser in background thread
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # Start server
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
