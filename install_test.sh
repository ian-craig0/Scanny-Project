#!/bin/bash
# Installer for GUI App on Raspberry Pi with MySQL, Database Import, and Required Python Libraries
# This script installs system packages, Python libraries, MySQL server,
# imports a local database, copies your application files,
# sets up a cron job, and configures display settings.

# ensure user has sudo access --------------------------------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script with sudo access. (run the command in the tutorial doc)"
  exit 1
fi



#check for internet connection --------------------------------------------------------------------------------
echo "Checking internet connectivity..."
if ! ping -c 1 google.com > /dev/null 2>&1; then
  echo "No internet connection detected. Please connect to the internet and try again."
  exit 1
fi
echo "Internet connection confirmed. Proceeding with installation..."



# update system packages --------------------------------------------------------------------------------
echo "Updating system packages..."
apt-get update
apt-get upgrade -y
echo "System packages updated successfully!"



#installing system packages --------------------------------------------------------------------------------
echo "Installing/Updating system packages..."
apt-get install -y python3 python3-pip python3-tk mariadb-server
echo "System packages installed/updated successfully!"

#installing python libraries --------------------------------------------------------------------------------
echo "Installing python libraries..."
pip3 install customtkinter mysql-connector-python Pillow PiicoDev-RFID mysqlclient
echo "Successfully installed python libraries!"

#start and import empty mysql database --------------------------------------------------------------------------------



#DOWNLOADING/UPDATING SCRIPT FROM GITHUB --------------------------------------------------------------------------------
# GitHub repository and target directory
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
  echo "Updating existing scanny directory..."
  rsync -a --delete "$REPO_DIR/scanny/" "$TARGET_DIR/"
else
  echo "Downloading new scanny directory..."
  cp -r "$REPO_DIR/scanny" "$TARGET_DIR"
fi

# Fix permissions (since script runs with sudo)
chown -R pi:pi "$TARGET_DIR"
echo "Scanny contents downloaded/updated successfuly!"



#setup cron job for python script --------------------------------------------------------------------------------

#invert display and touch inputs --------------------------------------------------------------------------------
# Function to rotate display
rotate_display() {
    CONFIG_FILE="/boot/firmware/config.txt"
    SECTION_HEADER="[all]"
    ROTATE_SETTING="display_rotate=2"

    # Backup original config
    sudo cp "$CONFIG_FILE" "${CONFIG_FILE}.bak.$(date +%s)"

    # Check if section exists
    if ! grep -q "^$SECTION_HEADER" "$CONFIG_FILE"; then
        echo "Adding display rotation configuration..."
        echo -e "\n$SECTION_HEADER" | sudo tee -a "$CONFIG_FILE" >/dev/null
        echo "$ROTATE_SETTING" | sudo tee -a "$CONFIG_FILE" >/dev/null
    elif ! grep -q "^$ROTATE_SETTING" "$CONFIG_FILE"; then
        echo "Updating display rotation configuration..."
        sudo sed -i "/^$SECTION_HEADER/a $ROTATE_SETTING" "$CONFIG_FILE"
    fi
}

# Function to rotate touch input
rotate_touch() {
    XORG_CONF="/usr/share/X11/xorg.conf.d/40-libinput.conf"
    IDENTIFIER='Identifier "libinput tablet catchall"'
    TRANSFORM_OPTION='Option "TransformationMatrix" "-1 0 1 0 -1 1 0 0 1"'

    # Backup original config
    sudo cp "$XORG_CONF" "${XORG_CONF}.bak.$(date +%s)"

    # Check if transformation already exists
    if ! grep -q "$TRANSFORM_OPTION" "$XORG_CONF"; then
        echo "Adding touch rotation configuration..."
        sudo sed -i "/$IDENTIFIER/,/EndSection/ {
            /EndSection/i \	$TRANSFORM_OPTION
        }" "$XORG_CONF"
    fi
}
rotate_display
rotate_touch
echo "Display and touch rotation configurations applied successfully!"
echo "A reboot may be required for changes to take effect."
