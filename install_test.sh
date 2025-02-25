#!/bin/bash
# Installer for GUI App on Raspberry Pi with MySQL, Database Import, and Required Python Libraries
# This script installs system packages, Python libraries, MySQL server,
# imports a local database, copies your application files,
# sets up a systemd service, and configures display settings.

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
VENV_PATH="/home/pi/scanny-venv"
REQUIREMENTS=(
    customtkinter
    mysql-connector-python
    Pillow
    mysqlclient
    piicodev
)

if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    sudo -u pi python3 -m venv "$VENV_PATH"
fi

# Install/update packages
echo "Checking dependencies..."
sudo -u pi "$VENV_PATH/bin/pip" install --upgrade pip
sudo -u pi "$VENV_PATH/bin/pip" install --quiet "${REQUIREMENTS[@]}"

echo "Verifying installation..."
sudo -u pi "$VENV_PATH/bin/python" -c "
try:
    import customtkinter, mysql.connector, PIL, PiicoDev_RFID
    print('All dependencies verified successfully')
except ImportError as e:
    print(f'Error: {e}')
    exit(1)
"


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


#setup systemd service for python script --------------------------------------------------------------------------------
echo "Creating systemd service file to enable kiosk mode..."
sudo tee /etc/systemd/system/kiosk.service > /dev/null << 'EOF'
[Unit]
Description=Kiosk Python Script in Virtual Environment
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/Desktop/scanny
ExecStart=/home/pi/scanny-venv/bin/python /home/pi/Desktop/scanny/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "Kiosk mode service successfully created!"

#enabling service
sudo systemctl daemon-reload
sudo systemctl enable kiosk.service
sudo systemctl start kiosk.service
echo "Kiosk mode successfully enabled!"



#setup and import empty mysql database --------------------------------------------------------------------------------
echo "Starting MySQL Database Setup"
echo "Create new MySQL user or login to previous one:"
read -p "Enter MySQL username: " new_user </dev/tty
read -p "Enter MySQL password: " new_pass </dev/tty
echo ""

# Escape password for sed
escaped_pass=$(sed "s/'/'\\\\''/g" <<< "$new_pass")

# MySQL with error checking
if ! sudo mysql -u root <<EOF ; then
CREATE USER IF NOT EXISTS '$new_user'@'localhost' IDENTIFIED BY '$new_pass';
GRANT USAGE ON *.* TO '$new_user'@'localhost';
GRANT ALL PRIVILEGES ON \`${new_user}_%\`.* TO '$new_user'@'localhost';
FLUSH PRIVILEGES;
EOF
  echo "MySQL user creation failed!" >&2
  exit 1
fi
echo "Successfully logged in/created MySQL user!"

# Update credentials in python code
sudo sed -i -E \
  -e "s/(user\s*=\s*['\"])[^'\"]*(['\"])/\1$new_user\2/g" \
  -e "s/(passwd\s*=\s*['\"])[^'\"]*(['\"])/\1$escaped_pass\2/g" \
  "/home/pi/Desktop/scanny/main.py"



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
