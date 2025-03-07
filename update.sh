#!/bin/bash
sudo systemctl stop kiosk.service

REPO_URL="https://github.com/ian-craig0/Scanny-Project.git"
REPO_DIR="Scanny-Project"  # Local clone directory
TARGET_DIR="/home/pi/Desktop/scanny"  # Case-sensitive path!

# Clone or update the repository
if [ -d "$REPO_DIR" ]; then
  git -C "$REPO_DIR" pull
else
  git clone "$REPO_URL" "$REPO_DIR"
fi

# Update or create the target directory
if [ -d "$TARGET_DIR" ]; then
  rsync -a --delete "$REPO_DIR/scanny/" "$TARGET_DIR/"
else
  cp -r "$REPO_DIR/scanny" "$TARGET_DIR"
fi

# Fix permissions (since script runs with sudo)
chown -R pi:pi "$TARGET_DIR"
chown -R pi:pi /home/pi/Scanny-Project
sudo systemctl start kiosk.service
