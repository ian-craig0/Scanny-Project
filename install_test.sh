
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
echo ""



# update system packages --------------------------------------------------------------------------------
echo "Updating system packages..."
apt-get update
apt-get full-upgrade
echo "System packages updated successfully!"
echo ""



#installing system packages --------------------------------------------------------------------------------
echo "Installing/Updating system packages..."
apt-get install -y python3 python3-pip python3-tk mariadb-server python3-dev default-libmysqlclient-dev build-essential pkg-config
echo "System packages installed/updated successfully!"
echo ""

#enabling I2C so piicodev RFID functions
echo "Configuring I2C support..."
sudo raspi-config nonint do_i2c 0
echo "i2c-dev" | sudo tee -a /etc/modules
sudo adduser pi i2c
echo ""

#changing time zone
TIMEZONE="America/Chicago"
sudo timedatectl set-timezone "$TIMEZONE"
echo "Time zone changed succcessfuly to America/Chicago"
echo ""

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
echo ""

# Install Space Grotesk font only if not already installed ----------------------------------------------
FONT_DIR="/home/pi/.fonts"

# Create the .fonts directory if it doesn't exist
if [ ! -d "$FONT_DIR" ]; then
    echo "Creating .fonts directory in home folder"
    mkdir -p "$FONT_DIR"
fi

# Download the font if it's not already present
if [ ! -f "/home/pi/.fonts/Space_Grotesk.ttf" ]; then
    echo "Downloading Space Grotesk font..."
    wget -O "/home/pi/.fonts/Space_Grotesk.ttf" "https://github.com/floriankarsten/space-grotesk/raw/master/fonts/ttf/SpaceGrotesk%5Bwght%5D.ttf"
else
    echo "Font is already installed."
fi

# Update font cache so the font is available for Python
echo "Updating font cache..."
fc-cache -fv

echo "Font installation complete! You can now use 'Space Grotesk' in Python."
echo ""



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
echo ""

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
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority

[Install]
WantedBy=multi-user.target
EOF

echo "Kiosk mode service successfully created!"
echo ""

#setup and import empty mysql database --------------------------------------------------------------------------------
echo "Starting MySQL Database Setup"
echo "Create new MySQL user or login to previous one:"
read -p "Enter MySQL username: " new_user </dev/tty
read -p "Enter MySQL password: " new_pass </dev/tty
echo ""

# Escape password for sed
escaped_pass=$(sed "s/'/'\\\\''/g" <<< "$new_pass")

# MySQL with error checking
if ! sudo mysql -u root <<EOF
CREATE USER IF NOT EXISTS '$new_user'@'localhost' IDENTIFIED BY '$new_pass';
GRANT USAGE ON *.* TO '$new_user'@'localhost';
GRANT ALL PRIVILEGES ON *.* TO '$new_user'@'localhost';
FLUSH PRIVILEGES;
EOF
then
  echo "MySQL user creation failed!" >&2
  exit 1
fi
echo "Successfully logged in/created MySQL user!"

# Update credentials in python code
sudo sed -i -E \
  -e "s/(user\s*=\s*['\"])[^'\"]*(['\"])/\1$new_user\2/g" \
  -e "s/(passwd\s*=\s*['\"])[^'\"]*(['\"])/\1$escaped_pass\2/g" \
  "/home/pi/Desktop/scanny/main.py"
echo ""


#MySQL Database Importing
MYSQL_USER=$new_user
MYSQL_PASS=$new_pass
DATABASE="scanner"
SQL_URL="https://raw.githubusercontent.com/ian-craig0/Scanny-Project/main/scanny-db.sql"

# Check if the database exists
DB_EXISTS=$(mysql -u "$MYSQL_USER" -p"$MYSQL_PASS" -s -N -e "SHOW DATABASES LIKE '$DATABASE';")

if [ "$DB_EXISTS" == "$DATABASE" ]; then
    echo "Database '$DATABASE' already exists. Skipping import."
else
    echo "Database '$DATABASE' does not exist. Importing SQL file from GitHub..."
    # Import the SQL file directly from GitHub using curl
    curl -s "$SQL_URL" | mysql -u "$MYSQL_USER" -p"$MYSQL_PASS"
fi

DB_EXISTS2=$(mysql -u "$MYSQL_USER" -p"$MYSQL_PASS" -s -N -e "SHOW DATABASES LIKE '$DATABASE';")
if [ "$DB_EXISTS2" == "$DATABASE" ]; then
    echo "Database '$DATABASE' created/already exists!"
else
    echo "Database importing failed..."
    exit 1
fi
echo ""



#create update service with username and login to update python script ---------------------------------------------------





#invert display and touch inputs --------------------------------------------------------------------------------
# Define the line to add
LINE="wlr-randr --output HDMI-A-2 --transform 180 &"

# Check if the line already exists to avoid duplicates
grep -qxF "$LINE" /etc/xdg/labwc/autostart || echo "$LINE" | sudo tee -a /etc/xdg/labwc/autostart > /dev/null
echo "Display and touch rotation configurations applied successfully!"
echo ""

#enabling service for python script
sudo systemctl daemon-reload
sudo systemctl enable kiosk.service
echo "Kiosk mode successfully enabled!"
echo ""

# Reboot prompt -----------------------------------------------------------------
echo ""
echo "Installation complete!"
read -p "Reboot now for everything to work? (Y/N) " -n 1 -r
echo "" # move to new line

case $REPLY in
    [Yy]* )
        echo "System rebooting in 5 seconds (Ctrl+C to cancel)..."
        sudo systemctl start kiosk.service
        sleep 5
        sudo reboot
        ;;
    * )
        echo ""
        sudo systemctl start kiosk.service
        echo "WARNING: The RFID scanner and screen rotation changes will not function until reboot!"
        echo "         You must manually reboot later using: sudo reboot"
        ;;
esac
