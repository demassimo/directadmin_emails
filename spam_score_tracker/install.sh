#!/bin/sh
# Install script for SpamScoreTracker
PLUGIN_DIR=$(dirname "$0")

# Ensure log directory exists
mkdir -p "$PLUGIN_DIR/logs"

# Ensure admin page is executable
chmod 755 "$PLUGIN_DIR/admin/index.html"

# Set ownership so DirectAdmin can write
chown -R diradmin:diradmin "$PLUGIN_DIR"

exit 0
