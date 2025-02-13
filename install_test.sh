#!/bin/bash
# Installer for GUI App on Raspberry Pi with MySQL, Database Import, and Required Python Libraries
# This script installs system packages, Python libraries, MySQL server,
# imports a local database, copies your application files,
# sets up a cron job, and configures display settings.

# 1. Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root. Use: sudo ./install.sh"
  exit 1
fi

# 2. Check for Internet connectivity
echo "Checking internet connectivity..."
if ! ping -c 1 google.com > /dev/null 2>&1; then
  echo "No internet connection detected. Please connect to the internet and try again."
  exit 1
fi

echo "Internet connection confirmed. Proceeding with installation..."

echo "Updating system packages..."
apt-get update
