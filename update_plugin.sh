#!/bin/sh
# Convenience script to rebuild and install the plugin locally.

set -e

# Build the archive in the repository root
./build_plugin.sh

ARCHIVE="spam_score_tracker.tar.gz"
PLUGIN_DIR="/usr/local/directadmin/plugins/spam_score_tracker"

if [ -d "$PLUGIN_DIR" ]; then
    echo "Removing existing plugin" >&2
    if [ -x "$PLUGIN_DIR/scripts/uninstall.sh" ]; then
        "$PLUGIN_DIR/scripts/uninstall.sh"
    fi
    rm -rf "$PLUGIN_DIR"
fi

mkdir -p /usr/local/directadmin/plugins

echo "Extracting new version" >&2

tar -xzf "$ARCHIVE" -C /usr/local/directadmin/plugins

if [ -x "$PLUGIN_DIR/scripts/install.sh" ]; then
    "$PLUGIN_DIR/scripts/install.sh"
fi

echo "Plugin updated"
