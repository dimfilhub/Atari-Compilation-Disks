#!/usr/bin/env bash
# macOS launcher: double-click in Finder. Setup is skipped for anything already done.
cd "$(dirname "$0")" || exit 1

fail() {
    echo
    echo "$1"
    read -r -p "Press Enter to close..." _
    exit 1
}

# 1. Python
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys' >/dev/null 2>&1; then
    PY=python3
else
    fail "Python 3 was not found. Install it from https://www.python.org/downloads/
(or run: brew install python-tk) and then double-click this file again."
fi

# 2. Virtual environment
if [ ! -x .venv/bin/python ]; then
    echo "Creating virtual environment..."
    "$PY" -m venv .venv || fail "Could not create the virtual environment."
fi

# 3. Requirements (only when requirements.txt changed since last install)
STAMP=.venv/requirements.installed
if ! cmp -s requirements.txt "$STAMP"; then
    echo "Installing requirements..."
    .venv/bin/python -m pip install -r requirements.txt || fail "Installing requirements failed."
    cp requirements.txt "$STAMP"
fi

.venv/bin/python -c 'import tkinter' 2>/dev/null || fail "Python's tkinter module is missing.
Install Python from https://www.python.org/downloads/ (it includes tkinter)
or run: brew install python-tk"

# 4. Start the app, then close the Terminal window once it exits
.venv/bin/python comp_disks_player.py
