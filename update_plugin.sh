#!/bin/bash

set -e

# Work in the directory where this script is located
cd "$(dirname "$0")"

# Variables
REPO_URL="https://github.com/demassimo/directadmin_emails.git"
TMP_DIR="./tmp"
PLUGIN_NAME="spam_score_tracker"
PLUGIN_DIR="/usr/local/directadmin/plugins/$PLUGIN_NAME"

# Step 1: Clean up and clone the latest code
echo "Fetching latest plugin source from GitHub..."
rm -rf "$TMP_DIR"
git clone "$REPO_URL" "$TMP_DIR"

# Step 2: Remove old plugin if it exists
if [ -d "$PLUGIN_DIR" ]; then
    echo "Removing existing plugin..."
    if [ -x "$PLUGIN_DIR/scripts/uninstall.sh" ]; then
        "$PLUGIN_DIR/scripts/uninstall.sh"
    fi
    rm -rf "$PLUGIN_DIR"
fi

# Step 3: Copy the plugin folder into DirectAdmin plugins
echo "Copying new plugin files..."
cp -r "$TMP_DIR/$PLUGIN_NAME" "$PLUGIN_DIR"

# Step 4: Run install script if available
if [ -x "$PLUGIN_DIR/scripts/install.sh" ]; then
    "$PLUGIN_DIR/scripts/install.sh"
fi

echo "Plugin updated successfully."
