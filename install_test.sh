#!/bin/bash
# Installer for GUI App on Raspberry Pi with MySQL, Database Import, and Required Python Libraries
# This script installs system packages, Python libraries, MySQL server,
# imports a local database, copies your application files,
# sets up a cron job, and configures display settings.

# ensure user has sudo access
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script with sudo access. (run the command in the tutorial doc)"
  exit 1
fi

#check for internet connection
echo "Checking internet connectivity..."
if ! ping -c 1 google.com > /dev/null 2>&1; then
  echo "No internet connection detected. Please connect to the internet and try again."
  exit 1
fi

echo "Internet connection confirmed. Proceeding with installation..."

# update system packages
echo "Updating system packages..."
apt-get update
apt-get upgrade -y
echo "System packages updated successfully!"


#installing system packages
echo "Installing system packages..."
echo "System packages installed successfully!"


#installing python libraries
#echo "Installing python libraries..."

#echo "Python libraries installed successfully!"


#start mysql server

#import empty mysql database

#download script from github
echo "Creating directory for scanny..."
mkdir -p /home/pi/Desktop/scanny
echo "Directory created successfully!"

echo "Downloading scanny from github..."
git clone --filter=blob:none --no-checkout https://github.com/ian-craig0/Scanny-Project.git /home/pi/Desktop/scanny
cd /home/pi/Desktop/scanny

git sparse-checkout init --cone
git sparse-checkout set scanny
echo "Repository cloned successfully!"




#setup cron job for python script

#invert display and touch inputs