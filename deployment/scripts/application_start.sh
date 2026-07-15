#!/bin/bash
# Runs AFTER the new revision is installed (ApplicationStart hook).
# Sets up the Python virtual environment, installs the systemd unit and
# nginx config shipped in this revision, and starts the app.
set -euo pipefail

APP_DIR=/home/ubuntu/attendguard

echo "[application_start] Creating virtual environment..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[application_start] Installing systemd service..."
cp deployment/systemd/attendguard.service /etc/systemd/system/attendguard.service
systemctl daemon-reload

echo "[application_start] Installing nginx site config..."
cp deployment/nginx/attendguard.conf /etc/nginx/sites-available/attendguard
ln -sf /etc/nginx/sites-available/attendguard /etc/nginx/sites-enabled/attendguard
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo "[application_start] Starting services..."
systemctl enable attendguard
systemctl restart attendguard
systemctl restart nginx

echo "[application_start] Done."
