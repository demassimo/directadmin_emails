#!/bin/sh
# Uninstall script for SpamScoreTracker
SCRIPT_DIR=$(dirname "$0")
PLUGIN_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

# Remove stored logs
rm -rf "$PLUGIN_DIR/logs"

exit 0
