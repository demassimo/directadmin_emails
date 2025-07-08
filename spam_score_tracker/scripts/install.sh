#!/bin/sh
# Install script for SpamScoreTracker
SCRIPT_DIR=$(dirname "$0")
PLUGIN_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

# Ensure log directory exists
mkdir -p "$PLUGIN_DIR/logs"
chmod 775 "$PLUGIN_DIR/logs"

# Ensure admin page is executable
chmod 755 "$PLUGIN_DIR/admin/index.html"

# Set ownership so DirectAdmin can write
chown -R diradmin:diradmin "$PLUGIN_DIR"

# Allow diradmin to read system log files (adm group usually has access)
if id diradmin >/dev/null 2>&1; then
    usermod -a -G adm diradmin 2>/dev/null || true
fi

# Install Python 3 if missing and ensure mysql-connector-python is available
if ! command -v python3 >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update && apt-get install -y python3 python3-pip
    elif command -v yum >/dev/null 2>&1; then
        yum install -y python3 python3-pip
    fi
fi

if command -v python3 >/dev/null 2>&1; then
    python3 - <<'EOF'
import pkgutil, sys, subprocess
if not pkgutil.find_loader('mysql.connector'):
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'mysql-connector-python'])
EOF
fi

# Create MySQL database, user, and table if they don't exist
mysql -u root <<'EOF'
CREATE DATABASE IF NOT EXISTS mail_logs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'mail_logs'@'localhost' IDENTIFIED BY 'l59X8bHfO07FIBWY08Z98';
GRANT ALL PRIVILEGES ON mail_logs.* TO 'mail_logs'@'localhost';
FLUSH PRIVILEGES;
USE mail_logs;
CREATE TABLE IF NOT EXISTS spam_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ts DATETIME NOT NULL,
    score FLOAT NOT NULL,
    message_id VARCHAR(255) NOT NULL,
    sender VARCHAR(255) DEFAULT NULL,
    recipients TEXT,
    subject TEXT,
    KEY(message_id),
    KEY(ts)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE spam_scores CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE spam_scores ADD COLUMN IF NOT EXISTS sender VARCHAR(255);
ALTER TABLE spam_scores ADD COLUMN IF NOT EXISTS recipients TEXT;
ALTER TABLE spam_scores ADD COLUMN IF NOT EXISTS subject TEXT;
EOF

# Install systemd service to continually backfill
SERVICE_FILE=/etc/systemd/system/spam_score_tracker.service
cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Spam Score Tracker
After=network.target mysql.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 $PLUGIN_DIR/scripts/spam_score_tool.py follow
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload
    systemctl enable --now spam_score_tracker.service || true
fi

exit 0
