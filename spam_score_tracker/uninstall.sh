#!/bin/sh
# Uninstall script for SpamScoreTracker
PLUGIN_DIR=$(dirname "$0")

# Remove stored logs
rm -rf "$PLUGIN_DIR/logs"

exit 0
