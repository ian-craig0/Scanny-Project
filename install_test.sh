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
    mariadb-server \
    python3-dev \
    libjpeg-dev \
    libopenjp2-7 \
    libtiff5 \
    i2c-tools \
    libatlas-base-dev  # Required for numpy dependencies
echo "System packages installed/updated successfully!"

# Create fresh virtual environment - FORCE CLEAN INSTALL
VENV_PATH="/home/pi/scanny-venv"
echo "Creating fresh Python virtual environment..."
sudo rm -rf "$VENV_PATH"
sudo -u pi python3 -m venv "$VENV_PATH"

# Install Python packages in venv - CORRECTED PACKAGES
echo "Installing Python libraries in virtual environment..."
sudo -u pi "$VENV_PATH/bin/pip" install --upgrade pip setuptools wheel
sudo -u pi "$VENV_PATH/bin/pip" install \
    customtkinter==5.2.2 \
    mysql-connector-python==8.2.0 \
    Pillow==10.3.0 \
    mysqlclient==2.2.1 \
    "git+https://github.com/CoreElectronics/CE-PiicoDev-Python-Library.git" \
    "git+https://github.com/CoreElectronics/CE-PiicoDev-RFID-Python.git"

# Enable I2C properly
echo "Enabling hardware interfaces..."
sudo raspi-config nonint do_i2c 0
sudo usermod -aG i2c pi

# Verify installations with better diagnostics
echo "Verifying dependencies..."
verify_command() {
    sudo -u pi "$VENV_PATH/bin/python" -c "import $1"
    return $?
}

modules=("tkinter" "customtkinter" "PIL" "PiicoDev_RFID" "mysql.connector" "MySQLdb")

for module in "${modules[@]}"; do
    if ! verify_command "$module"; then
        echo "CRITICAL ERROR: Failed to import $module"
        echo "Attempting to reinstall..."
        case $module in
            "customtkinter") sudo -u pi "$VENV_PATH/bin/pip" install --force-reinstall customtkinter==5.2.2 ;;
            "PiicoDev_RFID") sudo -u pi "$VENV_PATH/bin/pip" install --force-reinstall "git+https://github.com/CoreElectronics/CE-PiicoDev-RFID-Python.git" ;;
            *) sudo -u pi "$VENV_PATH/bin/pip" install --force-reinstall "$module" ;;
        esac
    fi
done

# Final verification
if sudo -u pi "$VENV_PATH/bin/python" -c "import sys; from PiicoDev_RFID import PiicoDev_RFID; import customtkinter; print('All critical imports successful')"; then
    echo "All dependencies verified successfully"
else
    echo "FATAL ERROR: Core dependencies missing"
    echo "Installed packages:"
    sudo -u pi "$VENV_PATH/bin/pip" list
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
