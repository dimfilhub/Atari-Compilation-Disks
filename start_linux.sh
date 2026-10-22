#!/usr/bin/env bash
# Linux launcher. Double-click it in your file manager and choose "Run"
# (or run it from a terminal). Setup is skipped for anything already done.
cd "$(dirname "$0")" || exit 1

fail() {
    echo
    echo "$1"
    read -r -p "Press Enter to close..." _
    exit 1
}

# 1. Python
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(sys.version_info[0] < 3)'; then
    PY=python
else
    fail "Python 3 was not found. Install it with your package manager, e.g.:
  sudo apt install python3 python3-venv python3-tk
  sudo dnf install python3 python3-tkinter"
fi

# 2. Virtual environment
if [ ! -x .venv/bin/python ]; then
    echo "Creating virtual environment..."
    "$PY" -m venv .venv || fail "Could not create the virtual environment.
On Debian/Ubuntu install it with: sudo apt install python3-venv"
fi

# 3. Requirements (only when requirements.txt changed since last install)
STAMP=.venv/requirements.installed
if ! cmp -s requirements.txt "$STAMP"; then
    echo "Installing requirements..."
    .venv/bin/python -m pip install -r requirements.txt || fail "Installing requirements failed."
    cp requirements.txt "$STAMP"
fi

# The GUI needs tkinter, which is a separate package on many distros
.venv/bin/python -c 'import tkinter' 2>/dev/null || fail "Python's tkinter module is missing. Install it, e.g.:
  sudo apt install python3-tk
  sudo dnf install python3-tkinter"

# 4. Start the app
exec .venv/bin/python comp_disks_player.py
