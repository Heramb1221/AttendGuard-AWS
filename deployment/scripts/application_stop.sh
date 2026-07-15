#!/bin/bash
# Runs BEFORE the new revision replaces the old one (ApplicationStop hook).
# Stops the currently running gunicorn service, if any. Uses `|| true` so
# that a first-ever deployment (where the service doesn't exist yet) does
# not fail the whole deployment.
set -uo pipefail

echo "[application_stop] Stopping attendguard service (if running)..."
systemctl stop attendguard || true
echo "[application_stop] Done."
