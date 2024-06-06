#!/bin/bash

#
# Clean up
#
echo "Cleaning older federation tests..."
DAYS_OLD=30
INTEGRATION_DIR="/home/devops/integration"
find "$INTEGRATION_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +$DAYS_OLD -exec rm -rf {} \;
