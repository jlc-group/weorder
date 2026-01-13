#!/bin/bash

# WeOrder Daily Sync Script
# This script triggers a full sync of orders for all platforms (last 30 days lookback)

# Navigate to project directory
cd "$(dirname "$0")"

# Activate Virtual Environment
source ./venv_fix/bin/activate

# Run the sync job
echo "Starting Daily Order Sync at $(date)..."
# Trigger Sync via API (Wait for backend to start if needed)
echo "Triggering sync via API..."
curl -X POST http://localhost:9202/api/sync/trigger

echo "Sync completed at $(date)."
