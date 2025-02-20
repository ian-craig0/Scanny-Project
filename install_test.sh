#!/bin/bash
# Installer for GUI App on Raspberry Pi with MySQL, Database Import, and Required Python Libraries

# Ensure user has sudo access
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script with sudo access."
  exit 1
fi

# Check for internet connection
echo "Checking internet connectivity..."
if ! ping -c 1 google.com > /dev/null 2>&1; then
  echo "No internet connection detected. Please connect to the internet and try again."
  exit 1
fi
echo "Internet connection confirmed. Proceeding with installation..."

# Update system packages
echo "Updating system packages..."
apt-get update
apt-get upgrade -y
echo "System packages updated successfully!"

# Install system packages
echo "Installing/Updating system packages..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-tk \
    python3-pil \
    libmariadb-dev \
    mariadb-server
echo "System packages installed/updated successfully!"

# Create virtual environment
VENV_DIR="/home/pi/scanny-venv"
echo "Creating Python virtual environment..."
sudo -u pi python3 -m venv "$VENV_DIR"

# Install Python libraries in virtual environment
echo "Installing Python libraries..."
sudo -u pi "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u pi "$VENV_DIR/bin/pip" install \
    customtkinter \
    mysql-connector-python \
    Pillow \
    mysqlclient \
    piicodev

# Verify installations
echo "Verifying dependencies..."
if sudo -u pi "$VENV_DIR/bin/python" -c "import tkinter, customtkinter, PIL, PiicoDev_RFID, mysql.connector, MySQLdb"; then
    echo "All dependencies installed and verified successfully"
else
    echo "Error: Some dependencies failed to install" >&2
    exit 1
fi

# Download/update project from GitHub
REPO_URL="https://github.com/ian-craig0/Scanny-Project.git"
REPO_DIR="Scanny-Project"
TARGET_DIR="/home/pi/Desktop/scanny"

echo "Updating project files..."
if [ -d "$REPO_DIR" ]; then
    git -C "$REPO_DIR" pull
else
    git clone "$REPO_URL" "$REPO_DIR"
fi

# Sync files to target directory
rsync -a --delete "$REPO_DIR/scanny/" "$TARGET_DIR/"
chown -R pi:pi "$TARGET_DIR"
echo "Project files updated successfully!"

# Setup cron job using virtual environment python
#echo "Setting up cron job..."
#CRON_CMD="@reboot $VENV_DIR/bin/python $TARGET_DIR/main.py"
#(sudo -u pi crontab -l 2>/dev/null | grep -vF "$CRON_CMD"; echo "$CRON_CMD") | sudo -u pi crontab -
#echo "Cron job configured!"

# Display rotation configuration
rotate_display() {
    CONFIG_FILE="/boot/firmware/config.txt"
    SECTION_HEADER="[all]"
    ROTATE_SETTING="display_rotate=2"

    cp "$CONFIG_FILE" "${CONFIG_FILE}.bak.$(date +%s)"
    if ! grep -q "^$SECTION_HEADER" "$CONFIG_FILE"; then
        echo -e "\n$SECTION_HEADER" | tee -a "$CONFIG_FILE" >/dev/null
        echo "$ROTATE_SETTING" | tee -a "$CONFIG_FILE" >/dev/null
    elif ! grep -q "^$ROTATE_SETTING" "$CONFIG_FILE"; then
        sed -i "/^$SECTION_HEADER/a $ROTATE_SETTING" "$CONFIG_FILE"
    fi
}

rotate_touch() {
    XORG_CONF="/usr/share/X11/xorg.conf.d/40-libinput.conf"
    IDENTIFIER='Identifier "libinput tablet catchall"'
    TRANSFORM_OPTION='Option "TransformationMatrix" "-1 0 1 0 -1 1 0 0 1"'

    cp "$XORG_CONF" "${XORG_CONF}.bak.$(date +%s)"
    if ! grep -q "$TRANSFORM_OPTION" "$XORG_CONF"; then
        sed -i "/$IDENTIFIER/,/EndSection/ { /EndSection/i \	$TRANSFORM_OPTION }" "$XORG_CONF"
    fi
}

# Apply display configurations
rotate_display
rotate_touch
echo "Display configuration applied! Reboot required for changes to take effect."

echo "Installation complete! Please reboot your system."
