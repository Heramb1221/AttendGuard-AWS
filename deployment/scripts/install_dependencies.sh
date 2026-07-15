#!/bin/bash
# Runs BEFORE the new revision is installed (BeforeInstall hook).
# Installs system + Python dependencies needed to run the Flask app.
set -euo pipefail

echo "[install_dependencies] Updating apt package index..."
apt-get update -y

echo "[install_dependencies] Installing system packages..."
apt-get install -y python3-pip python3-venv nginx libpq-dev python3-dev

echo "[install_dependencies] Ensuring target directory exists..."
mkdir -p /home/ubuntu/attendguard
chown ubuntu:ubuntu /home/ubuntu/attendguard

echo "[install_dependencies] Done."
