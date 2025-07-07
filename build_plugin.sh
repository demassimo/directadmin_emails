#!/bin/sh
# Create an archive of the plugin for easy upload.
# The resulting spam_score_tracker.tar.gz is written to the repository root so
# it is never included inside the archive itself.

set -e

PLUGIN_DIR="spam_score_tracker"
OUTPUT="spam_score_tracker.tar.gz"

# Ensure we start from the script directory
cd "$(dirname "$0")"

# Remove any existing archive to avoid nesting
rm -f "$OUTPUT"

# Create the archive from the plugin directory
tar -czf "$OUTPUT" -C "$PLUGIN_DIR" .
