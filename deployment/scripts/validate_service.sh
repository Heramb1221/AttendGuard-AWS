#!/bin/bash
# Runs LAST (ValidateService hook). Confirms the app is actually responding
# before CodeDeploy marks the deployment as successful.
set -uo pipefail

echo "[validate_service] Waiting for application to become ready..."
for i in {1..10}; do
    if curl -sf http://127.0.0.1/auth/login > /dev/null; then
        echo "[validate_service] Application responded successfully."
        exit 0
    fi
    echo "[validate_service] Not ready yet, retrying ($i/10)..."
    sleep 3
done

echo "[validate_service] ERROR: Application did not respond after 30 seconds."
exit 1
