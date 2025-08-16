Scanny-Project

Project Goal: To develop the code that will create the GUI for an app that will help track/manage the attendance of students who use RFID-tagged student IDs on a Raspberry Pi 4 system.
This project is useful for attendance management in settings like school, work, etc, where the timing of arrival (and potentially later [in newer updates] departure) is a necessary element to record for a group of people.

Currently, I only have a few things in this repository, and they are far from organized:
1. The main.py file, which contains all of the code and structure for the GUI of my attendance management device, using CustomTkinter to run the GUI interactions.
2. The install_test.sh file, which contains a shell script that will install and configure a Raspberry Pi 4 (on a specific OS installation, which I forgot) to function with my main.py Python script.
3. The scanny-db.sql file, which contains the code for a template MySQL database that stores and manages all of the data for my GUI app (this is referenced inside the installation code to install the MySQL database during setup).
4. Lastly, the images folder, which contains all of the images/icons that my main.py script relies on for all of the buttons on the attendance management GUI app.

This project requires hardware and manual setup before this software is even remotely applicable.
Currently, we use a custom 3d printed case (which I might add a link to later), a small 7-inch display, a Raspberry Pi 4, a Piico RFID scanner, and all of the necessary wiring and screws to create our attendance management device.
The only requirement for this Raspberry Pi 4 is that it has the correct OS installation (our install script will break if not on a specific version, which I might go look for later [I forgot tbh])



#Will figure out usage instructions later
#Can get help solely from me

I (ian-craig0) fully contribute to and maintain this project.
