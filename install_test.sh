#!/bin/bash
# Installer for GUI App on Raspberry Pi with MySQL, Database Import, and Required Python Libraries

# Ensure user has sudo access
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script with sudo access. (run the command in the tutorial doc)"
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

# Install system dependencies
echo "Installing/Updating system packages..."
apt-get install -y \
    python3-tk \
    python3-pil \
    python3-pil.imagetk \
    libmariadb-dev \
    python3-venv \
    python3-pip \
    mariadb-server
echo "System packages installed/updated successfully!"

# Create virtual environment as pi user
VENV_PATH="/home/pi/scanny-venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating Python virtual environment..."
    sudo -u pi python3 -m venv "$VENV_PATH"
fi

# Install Python packages in venv
echo "Installing Python libraries in virtual environment..."
sudo -u pi "$VENV_PATH/bin/pip" install --upgrade pip
sudo -u pi "$VENV_PATH/bin/pip" install \
    customtkinter \
    mysql-connector-python \
    Pillow \
    piicodev \
    mysqlclient

# Verify installations
echo "Verifying dependencies..."
if sudo -u pi "$VENV_PATH/bin/python" -c "import tkinter, customtkinter, PIL, piicodev, mysql.connector, MySQLdb"; then
    echo "All dependencies verified successfully"
else
    echo "Error: Some dependencies failed to install" >&2
    exit 1
fi

# DOWNLOADING/UPDATING SCRIPT FROM GITHUB
REPO_URL="https://github.com/ian-craig0/Scanny-Project.git"
REPO_DIR="Scanny-Project"
TARGET_DIR="/home/pi/Desktop/scanny"

# Clone or update repository
if [ -d "$REPO_DIR" ]; then
    git -C "$REPO_DIR" pull
else
    git clone "$REPO_URL" "$REPO_DIR"
fi

# Sync files
echo "Updating application files..."
rsync -a --delete "$REPO_DIR/scanny/" "$TARGET_DIR/"
chown -R pi:pi "$TARGET_DIR"
echo "Scanny contents updated successfully!"

# Setup cron job (example - modify as needed)
#echo "Setting up cron job..."
#CRON_CMD="@reboot /home/pi/scanny-venv/bin/python /home/pi/Desktop/scanny/main.py"
#(crontab -u pi -l 2>/dev/null | grep -vF "$CRON_CMD"; echo "$CRON_CMD") | crontab -u pi -
#echo "Cron job configured!"

# Rotate display and touch inputs
rotate_display() {
    CONFIG_FILE="/boot/firmware/config.txt"
    SECTION_HEADER="[all]"
    ROTATE_SETTING="display_rotate=2"

    sudo cp "$CONFIG_FILE" "${CONFIG_FILE}.bak.$(date +%s)"
    if ! grep -q "^$SECTION_HEADER" "$CONFIG_FILE"; then
        echo -e "\n$SECTION_HEADER" | sudo tee -a "$CONFIG_FILE" >/dev/null
        echo "$ROTATE_SETTING" | sudo tee -a "$CONFIG_FILE" >/dev/null
    elif ! grep -q "^$ROTATE_SETTING" "$CONFIG_FILE"; then
        sudo sed -i "/^$SECTION_HEADER/a $ROTATE_SETTING" "$CONFIG_FILE"
    fi
}

rotate_touch() {
    XORG_CONF="/usr/share/X11/xorg.conf.d/40-libinput.conf"
    IDENTIFIER='Identifier "libinput tablet catchall"'
    TRANSFORM_OPTION='Option "TransformationMatrix" "-1 0 1 0 -1 1 0 0 1"'

    sudo cp "$XORG_CONF" "${XORG_CONF}.bak.$(date +%s)"
    if ! grep -q "$TRANSFORM_OPTION" "$XORG_CONF"; then
        sudo sed -i "/$IDENTIFIER/,/EndSection/ { /EndSection/i \	$TRANSFORM_OPTION }" "$XORG_CONF"
    fi
}

rotate_display
rotate_touch
echo "Display configuration updated! A reboot is required for changes to take effect."

echo "Installation complete! Please reboot your system."
