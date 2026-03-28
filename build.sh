#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# LidLight build script
# Run this once on your Mac:  bash build.sh
#
# What it does:
#   1. Creates an isolated venv (no impact on system Python)
#   2. Installs rumps + PyObjC + py2app into that venv
#   3. Runs the tests
#   4. Builds LidLight.app in ./dist/
# ─────────────────────────────────────────────────────────────────────────────
set -e

VENV_DIR=".venv"

echo "── Creating virtual environment ──"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "── Installing dependencies ──"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "── Running tests ──"
python tests/test_policy.py

echo "── Building LidLight.app ──"
python setup.py py2app 2>&1 | tail -5

echo ""
echo "✓ Done.  App is at:  dist/LidLight.app"
echo "  To run directly (without building):  python run.py"
