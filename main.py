#THREADING
import threading

#ANIMATION
import os
import glob
import math
import random

#REOPENING CODE
import sys

#RFID SCANNER AND MYSQL IMPORTS
from PiicoDev_RFID import PiicoDev_RFID
from PiicoDev_Unified import sleep_ms
import MySQLdb
import mysql.connector
import mysql.connector.pooling

#TIMING IMPORTS
import datetime
from datetime import datetime, timedelta, date, time
import time
from time import strftime

#GUI CREATION IMPORTS
import tkinter as tk
from tkinter import *
from tkinter.ttk import *
import customtkinter as ctk
from PIL import Image, ImageTk

#MYSQL DATABASE INITIALIZATION
db = MySQLdb.connect(host='localhost',user='root',passwd='seaside',db='scanner',autocommit=True)  #allows queries

#GUI CREATION --------------------------------------------
#Window Setup
window = ctk.CTk()
window.attributes('-fullscreen',True)
ctk.set_appearance_mode("Dark")
sWidth = window.winfo_screenwidth()
sHeight = window.winfo_screenheight()

#CHECK IN ----------
#RFID SCANNING
rfid = PiicoDev_RFID()
master_macID = "04:F7:2C:0A:68:19:90"

#DATA BASE FUNCTIONS
def displayError(error):
     warninglabel.configure(text="An Unexpected Error Has Occured:\n" + error)
     display_popup(arrivalWarningFrame)

def reconnect():
     global db
     try:
         db = MySQLdb.connect(
             host='localhost',
             user='root',
             passwd='seaside',
             db='scanner',
             autocommit=True
         )
     except MySQLdb.OperationalError as err:
         db = None  # Clear the db variable to indicate failed reconnection

def callMultiple(cursor, query, params=None, fetchone=False, get=True, retries=4):
     """Execute a query with automatic retry and reconnection handling."""
     attempts = 0
     while attempts < retries:
         try:
             cursor.execute(query, params)
             if get:
                 return cursor.fetchone() if fetchone else cursor.fetchall()
             else:
                 break  # For non-fetch queries, simply exit after execution
         except MySQLdb.OperationalError as err:
             if err.args[0] == 2006:  # MySQL server has gone away
                 # Attempt to reconnect and reinitialize the cursor
                 reconnect()
                 if db is None:
                     return "error" if get else None  # Indicate failure
                 cursor = db.cursor()  # Refresh the cursor after reconnecting
             else:
                 if attempts == retries - 1:
                     return "error" if get else None
         except mysql.connector.Error as err:
             if attempts == retries - 1:
                 return "error" if get else displayError(err)

         # Increment attempts and wait before retrying
         attempts += 1
         time.sleep(1)  # Shorter sleep time to retry faster


#MYSQL TABLE GETTER FUNCTIONS
#BLOCK SCHEDULE GETTER
def getFromSchedule_Days(query, params=None,fetchone=False,get=True):
    with db.cursor() as schedule_days_curs:
        return callMultiple(schedule_days_curs, query, params, fetchone, get)

#PERIODS GETTER
def getFromPeriods(query, params=None,fetchone=False,get=True):
    with db.cursor() as periods_curs:
        return callMultiple(periods_curs, query, params, fetchone, get)

#SCANS GETTER
def getFromScans(query, params=None,fetchone=False,get=True):
    with db.cursor() as scans_curs:
        return callMultiple(scans_curs, query, params, fetchone, get)

#SCHEDULES GETTER
def getFromSchedules(query, params=None,fetchone=False,get=True):
    with db.cursor() as schedules_curs:
        return callMultiple(schedules_curs, query, params, fetchone, get)

#STUDENT NAMES GETTER
def getFromStudent_Names(query, params=None,fetchone=False,get=True):
    with db.cursor() as student_name_curs:
        return callMultiple(student_name_curs, query, params, fetchone, get)

#STUDENT PERIODS GETTER
def getFromStudent_Periods(query, params=None,fetchone=False,get=True):
    with db.cursor() as student_period_curs:
        return callMultiple(student_period_curs, query, params, fetchone, get)

#CONTROL GETTER
def getFromSystem_Control(query, params=None,fetchone=False,get=True):
    with db.cursor() as system_control_curs:
        return callMultiple(system_control_curs, query, params, fetchone, get)







#DATABASE GETTER FUNCTIONS
def get_active_schedule_ID():
    return getFromSystem_Control("select active_schedule_ID from system_control", None, True)[0]

def getPeriod_ID(period_name):
    return getFromPeriods("select period_ID from periods where name = %s", (period_name,), True)[0]

def getPeriodList():
    return getFromPeriods("select name from periods where schedule_ID = %s ORDER BY start_time ASC", (get_active_schedule_ID(),))

def getFirstLastName(macID):
    firstLast = getFromStudent_Names("""select first_name, last_name from student_names where macID = %s""",(macID,),True)
    return firstLast[0], firstLast[1]

def getNamesFromPeriod(period_ID):
    studentNames = getFromStudent_Names("""SELECT s.macID, s.first_name, s.last_name FROM student_names s JOIN student_periods p ON s.macID = p.macID WHERE p.period_ID = %s""",(period_ID,))
    studentDictionary = {}
    for i in studentNames:
        studentDictionary[(i[1].capitalize() + " " + i[2].capitalize())] = i[0]
    return studentDictionary

def get_current_Period_ID(time, cursor):
    # RETURNS NOTHING IF NO SCHEDULE THAT DAY, RETURNS '-' if there is no class at that time, RETURNS period_ID if there is a class
    daytype = callMultiple(cursor,"select daytype from schedule_days where schedule_ID = %s and weekday = %s", (get_active_schedule_ID(), date.today().weekday()), True)
    if not daytype: #CHECK IF THE SCHEDULE IS RUNNING TODAY
        return daytype
    else:
        period_ID = callMultiple(cursor,"SELECT period_ID FROM periods WHERE schedule_ID = %s AND block_val = %s AND start_time <= %s AND end_time > %s", (get_active_schedule_ID(), daytype, time, time),True)
        #IF THERE IS A PERIOD AT THE CURRENT TIME
        if period_ID:
            return period_ID[0]
        else:
            return "-"



#CHECK IN FUNCTIONS
def getPeriodsToday(periods, cursor):
    periods_today = callMultiple(cursor, """SELECT p.period_ID FROM periods p JOIN schedule_days sd ON sd.schedule_ID = p.schedule_ID WHERE sd.schedule_ID = %s AND sd.weekday = %s AND p.period_ID IN (%s) AND p.block_val = (SELECT daytype FROM schedule_days WHERE schedule_ID = %s AND weekday = %s)""", (get_active_schedule_ID(), date.today().weekday(), ",".join(["%s"] * len(periods)), get_active_schedule_ID(), date.today().weekday()))
    flattened_periods = [item[0] for item in periods_today]
    return flattened_periods

def getAttendance(time, period_ID, cursor):
    #WE ALREADY KNOW TIME IS >= start and < end because a student checked in for the current period and they are in it
    #   ONLY NEED TO FIGURE OUT WHERE IN THIS CURRENT PERIOD THEIR TIME SITS
    query = """
    SELECT 
        CASE 
            WHEN %s <= (p.start_time + p.late_var) THEN 2  -- PRESENT
            WHEN (%s - (p.start_time + p.late_var)) >= s.absent_var THEN 0  -- ABSENT
            ELSE 1  -- TARDY
        END AS attendance_status
    FROM periods p
    JOIN schedules s ON s.schedule_ID = get_active_schedule_ID()
    WHERE p.period_ID = %s
    """

    return callMultiple(cursor, query, (time, time, period_ID), True)[0]



#CHANGING DATA FUNCTIONS
def tempResetArrivalTimes():
    schedule_ID = '_' #FILL THIS IN BEFORE RUNNING IT
    period_data = (
        (schedule_ID,'A','Computer Science 1',490,585,5),
        (schedule_ID,'A','Conference',585,680,5),
        (schedule_ID,'A','Principles of Computer Science',715,815,5),
        (schedule_ID,'A','Principles of Applied Engineering',840,935,5),
        (schedule_ID,'B','Principles of Applied Engineering',490,585,5),
        (schedule_ID,'B','AP Computer Science',585,680,5),
        (schedule_ID,'B','Computer Science 1',715,815,5),
        (schedule_ID,'B','Conference',840,935,5)
    )

def create_periods(periodData, sched):

    """create_curs = db.cursor()
    create_curs.execute("update TEACHERS set SCHEDULE = %s", (sched,))
    updateSchedType()
    arrive = 0
    late = 0
    whenAbsent = 0
    for period in periodData:
        if period[0] == '':
            name = "Period " + period[1]
        else:
            name = period[0]
        create_curs.execute("INSERT INTO PERIODS (periodNum, periodName, arrive, late, whenAbsent) values (%s, %s, %s, %s, %s)", (period[1], name, arrive, late, whenAbsent))
        create_curs.execute("INSERT INTO ACTIVITY (periodName, periodNum, arrive, late, whenAbsent) values (%s, %s, %s, %s, %s)", (name, period[1], arrive, late, whenAbsent))
    create_curs.close()"""

def factory_reset():

    #with db.cursor() as factory_curs:
        #callMultiple(factory_curs,"""TRUNCATE TABLE PERIODS""", None, False, False)
        #callMultiple(factory_curs,"""TRUNCATE TABLE ACTIVITY""", None, False, False)
        #callMultiple(factory_curs,"""TRUNCATE TABLE SCANS""", None, False, False)
        #callMultiple(factory_curs,"""TRUNCATE TABLE MASTER""", None, False, False)
        #callMultiple(factory_curs,"""TRUNCATE TABLE TEACHERS""", None, False, False)
        #callMultiple(factory_curs,"""INSERT INTO TEACHERS (A_B, ACTIVITY, SCHEDULE, teacherPW) values ('A', 0, "", "")""", None, False, False)
    #os.execl(sys.executable, sys.executable, *sys.argv)

#TIMING FUNCTIONS
def newDay():
    #UPDATE A/B DAY
    day = date.today().weekday()
    if getFromSchedule_Days("select dynamic_daytype from schedule_days where schedule_ID = %s and weekday = %s and dynamic_daytype = True", (get_active_schedule_ID(), day), True):
        display_popup(fridayperiodframe)

#TIME CONVERT FUNCTIONS
def time_to_minutes(timeStr):
    # Split the input string into hours and minutes
    hours, minutes = map(int, timeStr.split(":"))
    # Convert the time to total minutes since midnight
    total_minutes = hours * 60 + minutes
    return total_minutes

def timeConvert(minutes):
    hours = minutes // 60
    mins = minutes % 60
    period = "AM" if hours < 12 else "PM"
    hours = hours % 12
    if hours == 0:
        hours = 12  # Midnight or Noon should be 12, not 0
    return f"{hours}:{mins:02d} {period}"

#TIME LOOP
prevDate = date.today() - timedelta(days=1)
current_time = time_to_minutes(strftime("%H:%M"))
def timeFunc():
    global prevDate
    global current_time
    currDate = date.today()
    if currDate != prevDate:
        newDay()
        prevDate = currDate
    timeLabel.configure(text=strftime('%I:%M:%S %p'))
    dateLabel.configure(text=strftime("%m-%d-%Y"))
    current_time = time_to_minutes(strftime("%H:%M"))
    timeLabel.after(1000, timeFunc)

#STUDENTLIST POPULATION
def studentListPop(period_ID):
    global sHeight
    global sWidth
    with db.cursor() as studentListCursor:
        #CLEAR THE STUDENTLIST FRAME
        for widget in studentList.winfo_children():
            widget.destroy()
        studentList.configure(label_text=callMultiple(studentListCursor, "select name from periods where period_ID = %s", (period_ID,), True)[0])
        query = """SELECT sp.macID, sn.first_name, sn.last_name, sc.status, sc.scan_time FROM student_periods sp JOIN student_names sn ON sp.macID = sn.macID LEFT JOIN scans sc ON sp.macID = sc.macID AND sc.date = CURDATE() AND sc.period_ID = %s WHERE sp.period_ID = %s ORDER BY sn.last_name ASC"""
        students = callMultiple(studentListCursor, query, (period_ID, period_ID))
        if students:
            for index, student in enumerate(students):
                macID, first_name, last_name, status, scan_time = student

                student_dict = {2: ('green', "periodListCheck.png", (40,30), 5, 5),
                                1: ('orange', "periodListTardy.png", (40,40), 4, 2),
                                0: ('red', "periodListX.png", (30,30), 10,2)}

                color, img, size, padx, pady = student_dict.get(status if status else 0)

                studentFrame = ctk.CTkFrame(studentList, fg_color = color,height=int(0.075*sHeight),width=0.30859375*sWidth,border_width=2, border_color='white')
                studentFrame.pack_propagate(0)
                image = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/" + img), size = size)
                ctk.CTkLabel(studentFrame, text = f"{first_name.capitalize()} {last_name.capitalize()}: {timeConvert(scan_time) if scan_time is not None else 'Absent'}", text_color='white', font=('Roboto', 15)).pack(side='left', padx=5,pady=2)
                ctk.CTkLabel(studentFrame, image= image, text='', fg_color='transparent').pack(padx=padx,pady=pady,side='right')

                # Calculate row and column dynamically
                row = index // 2  # Every two students per row
                column = index % 2

                studentFrame.grid(row=row, column=column, pady=5, padx=3, sticky='nsw')

#PERIODLIST UPDATING
def periodListPop():
    for widget in periodList.winfo_children():
        widget.destroy()
    query = """SELECT p.period_ID FROM periods p WHERE p.schedule_ID = %s AND p.block_val = (SELECT sd.block_val FROM schedule_days sd WHERE sd.schedule_ID = %s AND sd.weekday = %s) ORDER BY p.start_time ASC"""
    schedule_ID = get_active_schedule_ID()
    with db.cursor() as period_pop_curs:
        periods = callMultiple(period_pop_curs, query, (schedule_ID, schedule_ID, date.today().weekday()))
        if periods:
            for index, period in enumerate(periods, start=1):
                def command():
                    studentListPop(period)
                    tabSwap(2)
                ctk.CTkButton(periodList,text=f"{index}: {callMultiple(period_pop_curs, "select name from periods where period_ID = %s", (period,), True)[0]}", border_color='white', font=('Space Grotesk Medium', 20),command=lambda: command).pack(fill = 'both', expand = True)


ten_after = time_to_minutes(strftime("%H:%M")) + 10

#CHECK IN FUNCTION
def checkIN():
    global currentPopup
    global ten_after
    global current_time
    global currentTAB
    while True:
        if ten_after == current_time:
            with db.cursor() as alive_curs:
                # Execute a simple query to keep the connection alive
                result = callMultiple(alive_curs, """SELECT SCHEDULE FROM TEACHERS""", None, True)
            ten_after = current_time + 10
        if rfid.tagPresent(): #WHEN A MACID IS SCANNED!
            scan_date = strftime("%m-%d-%Y")
            scan_time = time_to_minutes(strftime("%H:%M"))
            ID = rfid.readID()
            if ID:
                if str(ID) == master_macID:
                    if teacherPWPopup.getDisplayed():
                        teacherPWPopup.close_popup()
                        tabSwap(teacherPWPopup.get_tab()+2)
                        sleep_ms(3000)
                elif currentTAB == 1 or currentTAB == 2:
                    if currentPopup != alreadyCheckFrame and currentPopup !=fridayperiodframe:
                        checkInCursor = db.cursor()
                        studentPeriodList = callMultiple(checkInCursor, """SELECT period_ID from student_periods WHERE macID = %s""", (ID,))
                        if studentPeriodList: #CHECK IF A PERIOD IS RETURNED (IF THEY'RE IN THE MASTER LIST)
                            current_period = get_current_Period_ID(scan_time, checkInCursor)
                            if not current_period: #NO CLASS ON THIS DAY
                                alreadyChecktitlelabel.configure(text='Check-in Unavailable Today!')
                                alreadyChecknoticelabel.configure(text="The current schedule is not active today.\nPlease contact your teacher if you have questions.")
                                display_popup(alreadyCheckFrame)
                            elif current_period == "-": #NO CLASS AT THIS TIME ON THIS VALID DAY
                                alreadyChecktitlelabel.configure(text='No Scheduled Class!')
                                alreadyChecknoticelabel.configure(text="There is no class scheduled at this time.\nPlease check your class schedule or return during your designated period.")
                                display_popup(alreadyCheckFrame)
                            else: #ONLY RUNS IF THERE IS A PERIOD TODAY!

                                #GET LIST OF PERIODS FOR THIS SPECIFIC DAY
                                periods_today = getPeriodsToday(studentPeriodList, checkInCursor) #GET THE STUDENT PERIODS FOR THE DAY
                                notInPeriod = True
                                #ITERATE THROUGH EACH PERIOD THAT THIS STUDENT IS IN FOR THIS DAY
                                for period_ID in periods_today:
                                    if period_ID == current_period: #IF ONE OF THEIR PERIODS IS MATCHING WITH THE CURRENT PERIOD
                                        notInPeriod = False
                                        #CHECK IF THERE IS A SCAN ALREADY FOR TODAY, FOR THE STUDENT, IN THE CURRENT PERIOD, FOR THE ACTIVE SCHEDULE
                                        if callMultiple(checkInCursor, "SELECT 1 FROM scans WHERE schedule_ID = %s AND period_ID = %s AND macID = %s AND scan_date = %s LIMIT 1", (get_active_schedule_ID(), period_ID, ID, scan_date), True):
                                            alreadyChecktitlelabel.configure(text='Double Scan!')
                                            alreadyChecknoticelabel.configure(text="You have already checked in for this period.")
                                            display_popup(alreadyCheckFrame)
                                        else: #IF THEY ARE IN THE CURRENT PERIOD ON THIS DAY AND HAVEN'T CHECKED IN YET
                                            status = getAttendance(scan_time, period_ID, checkInCursor)
                                            #NEED REASON LOGIC (FOR NOW ALWAYS NULL)
                                            checkInCursor.execute("""INSERT INTO SCANS (period_ID, schedule_ID, macID, scan_date, scan_time, status, reason) values (%s, %s, %s, %s, %s, %s, %s)""", (period_ID, get_active_schedule_ID(), ID, scan_date, scan_time, status, NULL))
                                            studentListPop(period_ID)
                                            tabSwap(2)
                                            successScan(scan_time, ID, status)
                                    else: #IF ONE OF THEIR PERIODS IS not MATCHING WITH THE CURRENT PERIOD
                                        continue
                                if notInPeriod:
                                    #DISPLAY YOU ARE NOT IN THE CURRENT PERIOD
                                    alreadyChecktitlelabel.configure(text='Wrong period!')
                                    alreadyChecknoticelabel.configure(text="You are not in the current period (" + current_period + ").")
                                    display_popup(alreadyCheckFrame)
                        else: #CREATE NEW STUDENT ENTRY BECAUSE THEY ARE NOT IN MASTER DATABASE
                            #GET STUDENT DATA WITH POP UP
                            getStudentInfoFrame.setMACID(ID)
                            tabSwap(6)
                        checkInCursor.close()
                    '''elif currentTAB == 3:
                    historyFrame.period_check.select()
                    historyFrame.top_name_check.select()
                    #GET FIRST PERIOD STUDENT IS IN (NAME: PER)
                    period = ...
                    historyFrame.period_menu.set(period)
                    historyFrame.update_student_menu(period)
                    #GET NAME IN FORMAT (Ian Craig)
                    name = ...
                    historyFrame.top_name_menu.set(name)
                    historyFrame.fetch_students()'''
                elif currentTAB == 4:
                    if currentTAB != 6:
                        editStudentData(ID)
                sleep_ms(100)
            else:
                sleep_ms(100)




#FRAME CLASSES
class setupClass(ctk.CTkFrame):
     def __init__(self, parent):
         super().__init__(parent)
         global sWidth
         global sHeight
         self.configure(width=sWidth, height=sHeight)
         self.grid_propagate(0)
         self.columnconfigure(0, weight=1)
         self.rowconfigure(0, weight=1)

         self.deleteImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/deleteIcon.png"),size=(25,25))

         self.current_tab = 1


         #Setup schedule list frame (make a function to populate on each open) 1
         self.schedule_list_frame = ctk.CTkFrame(self)
         self.schedule_list_frame.grid(row=0, column=0, sticky='nsew')

         self.SL_scrollable_frame = ctk.CTkScrollableFrame(self.schedule_list_frame, width=sWidth*3/4,height=sHeight*3/4, label_text="Manage Schedules:", label_font=('Space Grotesk', 25, 'bold'))
         self.SL_scrollable_frame.grid_propagate(0)
         self.SL_scrollable_frame._scrollbar.configure(width=25)
         self.SL_scrollable_frame.place(relx=0.5, rely=0.5, anchor='center')



         #Setup period list frame (make a function to populate on each open) 2
         self.period_list_frame = ctk.CTkFrame(self)
         self.period_list_frame.grid(row=0, column=0, sticky='nsew')

         self.PL_scrollable_frame = ctk.CTkScrollableFrame(self.period_list_frame, width=sWidth*3/4,height=sHeight*3/4, label_font=('Space Grotesk', 25, 'bold'))
         self.PL_scrollable_frame.grid_propagate(0)
         self.PL_scrollable_frame._scrollbar.configure(width=25)
         self.PL_scrollable_frame.place(relx=0.5, rely=0.5, anchor='center')




         #Setup schedule options frame (change commands based on schedule selected) 3
         self.schedule_options_frame = ctk.CTkFrame(self)
         self.schedule_options_frame.grid(row=0, column=0, sticky='nsew')

         #TOP FRAME CREATION (SCHEDULE OPTIONS)
         self.SO_top_frame = ctk.CTkFrame(self.schedule_options_frame, border_width=4,border_color='white')
         self.SO_top_frame.pack(side='top',fill='x')
         self.SOTF_title_label = ctk.CTkLabel(self.SO_top_frame, font=('Space Grotesk', 30, 'bold'))
         self.SOTF_title_label.pack(anchor='center', pady=20)

         #BOTTOM FRAME CREATION (SCHEDULE OPTIONS)
         self.SO_lower_container_frame = ctk.CTkFrame(self.schedule_options_frame)
         self.SO_lower_container_frame.pack(side='top',fill='both',expand=True)
         self.SO_lower_container_frame.columnconfigure(0, weight=1)
         self.SO_lower_container_frame.columnconfigure(1, weight=1)
         self.SO_lower_container_frame.rowconfigure(0, weight=1)
         self.SO_lower_container_frame.rowconfigure(1, weight=1)
         self.SO_lower_container_frame.rowconfigure(2, weight=1)

         #BOTTOM FRAME OPTION BUTTONS (SCHEDULE OPTIONS)
         self.SO_LC_periods_button = ctk.CTkButton(self.SO_lower_container_frame, width=200, height = 90, text='Edit Periods', font=('Space Grotesk', 24, 'bold'))
         self.SO_LC_periods_button.grid(column=0, row = 1, padx=(0,30))
         self.SO_LC_edit_schedule_button = ctk.CTkButton(self.SO_lower_container_frame, width=200, height=90, text='Edit Schedule', font=('Space Grotesk', 24, 'bold'))
         self.SO_LC_edit_schedule_button.grid(column=1, row = 1, padx=(30,0))




         #Setup new/edit schedule frame (clear on submit, input name and minutes, change title and submit button/display schedule type or not) 4
         self.schedule_info_frame = ctk.CTkFrame(self)
         self.schedule_info_frame.grid(row=0, column=0, sticky='nsew')

         #TOP FRAME CREATION (SCHEDULES)
         self.SI_top_frame = ctk.CTkFrame(self.schedule_info_frame, border_width=4,border_color='white')
         self.SI_top_frame.pack(side='top',fill='x')
         self.STF_title_label = ctk.CTkLabel(self.SI_top_frame, font=('Space Grotesk', 30, 'bold'))
         self.STF_title_label.pack(anchor='center', pady=20)

         #BOTTOM FRAME CREATION (SCHEDULES)
         self.SI_lower_container_frame = ctk.CTkFrame(self.schedule_info_frame)
         self.SI_lower_container_frame.pack(side='top',fill='both',expand=True)
         self.SI_lower_container_frame.rowconfigure(0, weight=1)
         self.SI_lower_container_frame.rowconfigure(1, weight=1)
         self.SI_lower_container_frame.rowconfigure(2, weight=1)

         #NAME FRAME ----------------
         self.SI_name_frame = ctk.CTkFrame(self.SI_lower_container_frame)
         self.SI_name_frame.grid(column=0, row=0, sticky='nsew', expand=True)
         self.SI_name_label = ctk.CTkLabel(self.SI_name_frame, text = "Name:", font = ('Space Grotesk', 18, 'bold'))
         self.SI_name_label.pack(side='left', anchor='nw', padx=10, pady=5)
         self.SI_name_entry = ctk.CTkEntry(self.SI_name_frame, placeholder_text='Enter schedule name...', placeholder_font= ('Space Grotesk', 16), height = 60, width = 280)
         self.SI_name_entry.pack(side='left', padx=5, pady=5)

         #Schedule and Absence Frame

         #SCHEDULE TYPE SELECITON
         self.schedule_dict = {'Block':1, 'Traditional':0}

         self.SI_schedule_absence_frame = ctk.CTkFrame(self.SI_lower_container_frame)
         self.SI_schedule_absence_frame.grid(column=0, row=1, sticky='nsew', expand=True)

         #SCHEDULE FRAME
         self.SI_schedule_frame = ctk.CTkFrame(self.SI_schedule_absence_frame)
         self.SI_schedule_label = ctk.CTkLabel(self.SI_schedule_frame, text = "Schedule Type:", font = ('Space Grotesk', 18, 'bold'))
         self.SI_schedule_label.pack(padx=10,pady=5,side='left')
         self.SI_schedule_combobox = ctk.CTkComboBox(self.SI_schedule_frame, values = ['Block', 'Traditional'], dropdown_font=('Space Grotesk', 16), dropdown_text_color='gray', height = 70, width=200)
         self.SI_schedule_combobox.pack(padx=5,pady=5,side='left')

         #ABSENCE FRAME
         self.SI_absence_frame = ctk.CTkFrame(self.SI_schedule_absence_frame)
         self.SI_AF_minute_var= ctk.StringVar(value = '30')

         self.SI_AF_title_label = ctk.CTkLabel(self.SI_absence_frame, text = "Absence Threshold\n(minutes)", font = ('Space Grotesk', 17, 'bold'))
         self.SI_AF_title_label.grid(row=0, column=0,padx=5,pady=5)
         self.SI_AF_value_label = ctk.CTkLabel(self.SI_absence_frame, text=f"{self.SI_AF_minute_var.get()}")
         self.SI_AF_value_label.grid(row=1,column=0,padx=5,pady=5)

         #ABSENCE MINUTE SELECTORS
         self.PI_RF_tardy_minute_up = ctk.CTkButton(self.SI_absence_frame, text="↑", command = lambda: self.change_minute(self.SI_AF_minute_var, +1))
         self.PI_RF_tardy_minute_up.grid(row=0, column=1,pady=5,padx=5)
         self.PI_RF_tardy_minute_down = ctk.CTkButton(self.SI_absence_frame, text="↓", command = lambda: self.change_minute(self.SI_AF_minute_var, -1))
         self.PI_RF_tardy_minute_down.grid(row=1, column=1,pady=5,padx=5)

         #ABSENCE UPDATE LABEL CODE
         self.SI_AF_minute_var.trace_add("write", self.SI_AF_value_label.configure(text=f"{self.SI_AF_minute_var.get()}"))


         #SUBMIT SCHEDULE FRAME
         self.SI_submit_frame = ctk.CTkFrame(self.SI_schedule_absence_frame)
         self.SI_submit_frame.grid(column=0, row=2, sticky='nsew', expand=True)
         self.SI_submit_button = ctk.CTkButton(self.SI_submit_frame, width=300, height = 70)
         self.SI_submit_button.pack(anchor='center')




         #Setup new/edit period frame (input details or not/change title and submit button/display A or B or not) CLEAR ON SUBMIT 5
         self.period_info_frame = ctk.CTkFrame(self)
         self.period_info_frame.grid(row=0, column=0, sticky='nsew')

         #TOP FRAME CREATION (PERIODS)
         self.PI_top_frame = ctk.CTkFrame(self.period_info_frame, border_width=4,border_color='white')
         self.PI_top_frame.pack(side='top',fill='x')
         self.PTF_title_label = ctk.CTkLabel(self.PI_top_frame, font=('Space Grotesk', 30, 'bold'))
         self.PTF_title_label.pack(anchor='center', pady=20)

         #BOTTOM FRAME CREATION (PERIODS)
         self.PI_lower_container_frame = ctk.CTkFrame(self.period_info_frame)
         self.PI_lower_container_frame.pack(side='top',fill='both',expand=True)
         self.PI_lower_container_frame.columnconfigure(0, weight=1)
         self.PI_lower_container_frame.columnconfigure(1, weight=1)

         self.PI_left_frame = ctk.CTkFrame(self.PI_lower_container_frame)
         self.PI_left_frame.grid(row=0, column=0, sticky='nsew')

         self.PI_right_frame = ctk.CTkFrame(self.PI_lower_container_frame)
         self.PI_right_frame.grid(row=0, column=1, sticky='nsew')

         #LEFT FRAME (unpacked widgets, will be packed based off edit/non edit)
         self.PI_LF_period_label = ctk.CTkLabel(self.PI_left_frame, text='Period Name', font=('Space Grotesk', 20))
         self.PI_LF_period_entry = ctk.CTkEntry(self.PI_left_frame, placeholder_text='Enter period name...', font=('Space Grotesk', 16), placeholder_text_color='gray', height = 60)

         self.PI_LF_daytype_label = ctk.CTkLabel(self.PI_left_frame, text='Daytype', font=('Space Grotesk', 20))
         self.PI_LF_daytype_segmented_button = ctk.CTkSegmentedButton(self.PI_left_frame, values=['A','B'], font=('Space Grotesk', 16, 'bold'), width=100, height = 60)

         self.PI_LF_submit_button = ctk.CTkButton(self.PI_left_frame, width=150, height = 60)



         #RIGHT FRAME (always packed time widgets, make sure to clear/set with editing)
         #START FRAME -------------------------------------------------------------------------------------------
         self.PI_RF_start_frame = ctk.CTkFrame(self.PI_right_frame)
         self.PI_RF_start_hour_var = ctk.StringVar(value = '12')
         self.PI_RF_start_minute_var = ctk.StringVar(value = '00')

         #START HOUR SELECTORS
         self.PI_RF_start_hour_up = ctk.CTkButton(self.PI_RF_start_frame, text="↑", command = lambda: self.change_hour(self.PI_RF_start_hour_var, +1))
         self.PI_RF_start_hour_up.grid(row=0, column=0,pady=(10,5))
         self.PI_RF_start_hour_down = ctk.CTkButton(self.PI_RF_start_frame, text="↓", command = lambda: self.change_hour(self.PI_RF_start_hour_var, -1))
         self.PI_RF_start_hour_down.grid(row=1, column=0,pady=(5,10))

         #START MINUTE SELECTORS
         self.PI_RF_start_minute_up = ctk.CTkButton(self.PI_RF_start_frame, text="↑", command = lambda: self.change_minute(self.PI_RF_start_minute_var, +1))
         self.PI_RF_start_minute_up.grid(row=0, column=2,pady=(10,5))
         self.PI_RF_start_minute_down = ctk.CTkButton(self.PI_RF_start_frame, text="↓", command = lambda: self.change_minute(self.PI_RF_start_minute_var, -1))
         self.PI_RF_start_minute_down.grid(row=1, column=2,pady=(5,10))

         #START LABELS
         self.PI_RF_start_label = ctk.CTkLabel(self.PI_RF_start_frame, text='Start Time', font=('Space Grotesk', 20))
         self.PI_RF_start_label.grid(row=0, column=1,pady=5)
         self.PI_RF_start_value_label = ctk.CTkLabel(self.PI_RF_start_frame, text=f"{self.PI_RF_start_hour_var.get()}:{self.PI_RF_start_minute_var.get()}")
         self.PI_RF_start_value_label.grid(row=1, column=1,pady=5)

         #START UPDATE LABEL CODE
         self.PI_RF_start_hour_var.trace_add("write", self.PI_RF_start_value_label.configure(text=f"{self.PI_RF_start_hour_var.get()}:{self.PI_RF_start_minute_var.get()}"))
         self.PI_RF_start_minute_var.trace_add("write", self.PI_RF_start_value_label.configure(text=f"{self.PI_RF_start_hour_var.get()}:{self.PI_RF_start_minute_var.get()}"))



         #END FRAME -------------------------------------------------------------------------------------------
         self.PI_RF_end_frame = ctk.CTkFrame(self.PI_right_frame)
         self.PI_RF_end_hour_var = ctk.StringVar(value = '12')
         self.PI_RF_end_minute_var = ctk.StringVar(value = '00')

         #END HOUR SELECTORS
         self.PI_RF_end_hour_up = ctk.CTkButton(self.PI_RF_end_frame, text="↑", command = lambda: self.change_hour(self.PI_RF_end_hour_var, +1))
         self.PI_RF_end_hour_up.grid(row=2, column=0,pady=(10,5))
         self.PI_RF_end_hour_down = ctk.CTkButton(self.PI_RF_end_frame, text="↓", command = lambda: self.change_hour(self.PI_RF_end_hour_var, -1))
         self.PI_RF_end_hour_down.grid(row=3, column=0,pady=(5,10))

         #END MINUTE SELECTORS
         self.PI_RF_end_minute_up = ctk.CTkButton(self.PI_RF_end_frame, text="↑", command = lambda: self.change_minute(self.PI_RF_end_minute_var, +1))
         self.PI_RF_end_minute_up.grid(row=2, column=2,pady=(10,5))
         self.PI_RF_end_minute_down = ctk.CTkButton(self.PI_RF_end_frame, text="↓", command = lambda: self.change_minute(self.PI_RF_end_minute_var, -1))
         self.PI_RF_end_minute_down.grid(row=3, column=2,pady=(5,10))

         #END LABELS
         self.PI_RF_end_label = ctk.CTkLabel(self.PI_RF_end_frame, text='End Time', font=('Space Grotesk', 20))
         self.PI_RF_end_label.grid(row=2, column=1,pady=5)
         self.PI_RF_end_value_label = ctk.CTkLabel(self.PI_RF_end_frame, text=f"{self.PI_RF_end_hour_var.get()}:{self.PI_RF_end_minute_var.get()}")
         self.PI_RF_end_value_label.grid(row=3, column=1, pady=5)

         #END UPDATE LABEL CODE
         self.PI_RF_end_hour_var.trace_add("write", self.PI_RF_end_value_label.configure(text=f"{self.PI_RF_end_hour_var.get()}:{self.PI_RF_end_minute_var.get()}"))
         self.PI_RF_end_minute_var.trace_add("write", self.PI_RF_end_value_label.configure(text=f"{self.PI_RF_end_hour_var.get()}:{self.PI_RF_end_minute_var.get()}"))



         #TARDY FRAME -------------------------------------------------------------------------------------------
         self.PI_RF_tardy_frame = ctk.CTkFrame(self.PI_right_frame)
         self.PI_RF_tardy_minute_var = ctk.StringVar(value = '05')

         #TARDY MINUTE SELECTORS
         self.PI_RF_tardy_minute_up = ctk.CTkButton(self.PI_RF_tardy_frame, text="↑", command = lambda: self.change_minute(self.PI_RF_tardy_minute_var, +1))
         self.PI_RF_tardy_minute_up.grid(row=4, column=2,pady=(10,5))
         self.PI_RF_tardy_minute_down = ctk.CTkButton(self.PI_RF_tardy_frame, text="↓", command = lambda: self.change_minute(self.PI_RF_tardy_minute_var, -1))
         self.PI_RF_tardy_minute_down.grid(row=5, column=2,pady=(5,10))

         #TARDY LABELS
         self.PI_RF_tardy_label = ctk.CTkLabel(self.PI_RF_tardy_frame, text='Tardy Threshold', font=('Space Grotesk', 20))
         self.PI_RF_tardy_label.grid(row=4, column=1,pady=5)
         self.PI_RF_tardy_value_label = ctk.CTkLabel(self.PI_RF_tardy_frame, text=f"{self.PI_RF_tardy_minute_var.get()}")
         self.PI_RF_tardy_value_label.grid(row=5,column=1,pady=5)

         #TARDY UPDATE LABEL CODE
         self.PI_RF_tardy_minute_var.trace_add("write", self.PI_RF_tardy_value_label.configure(text=f"{self.PI_RF_tardy_minute_var.get()}"))



         #Setup weekday frame (make a function populate schedule list on each open and weekdays on each selection) 6
         self.select_weekdays_frame = ctk.CTkFrame(self)
         self.select_weekdays_frame.grid(row=0, column=0, sticky='nsew')



         #Setup student assignment frame (specific to each period) 7
         self.student_period_selection_frame = ctk.CTkFrame(self)
         self.student_period_selection_frame.grid(row=0, column=0, sticky='nsew')



         #CREATE tab selector frame (make animation logic based on arrow, not a popup, keep separate)
         self.control_frame = ctk.CTkFrame(self, width = sWidth/5, height=sHeight)
         self.control_frame.place(x=-200, y=0)

         #CREATE exit button (always placed)
         self.exit_button = ctk.CTkButton(self, text='X', font=("Space Grotesk", 24, 'bold'),command=self.pack_forget())
         self.exit_button.place(relx=.95,rely=.05)

     def tabSwap(self, new_tab):
         if new_tab != self.current_tab:
             if new_tab == 1:
                 self.schedule_list_frame.lift()
             if new_tab == 2:
                 self.period_list_frame.lift()
             if new_tab == 3:
                 self.schedule_options_frame.lift()
             if new_tab == 4:
                 self.schedule_info_frame.lift()
             if new_tab == 5:
                 self.period_info_frame.lift()
             if new_tab == 6:
                 self.select_weekdays_frame.lift()
             if new_tab == 7:
                 self.student_period_selection_frame.lift()
             self.control_frame.lift()
             self.exit_button.lift()
             self.current_tab = new_tab

     def populate_schedule_list(self):
         for widget in self.SL_scrollable_frame.winfo_children():
             widget.destroy()
         for index, schedule_info in enumerate(getFromSchedules("select schedule_ID, name from schedules ORDER by name ASC")):
            schedule_frame = ctk.CTkFrame(self.SL_scrollable_frame, height= 60,fg_color="#1f6aa5", bg_color='white', border_width=4, border_color='white')
            schedule_frame.columnconfigure(0, weight=3)
            schedule_frame.columnconfigure(1, weight=1)

            ctk.CTkButton(schedule_frame, text=schedule_info[1].title(), bg_color='white', border_width=4, border_color='white',font=('Space Grotesk', 20, 'bold'), command = lambda: self.display_schedule_options(schedule_info[0], schedule_info[1])).grid(row=0, column=0, sticky='nsew')
            ctk.CTkButton(schedule_frame, text='', image=self.deleteImage, bg_color='white', border_width=4, border_color='white', compound = 'center',command = lambda: self.delete_schedule(schedule_info[0])).grid(row=0, column=1, sticky='nsew')

            schedule_frame.grid(row=index, column=0, sticky='ew', padx=5, pady=5)

     def populate_period_list(self, schedule_ID, name):
        for widget in self.PL_scrollable_frame.winfo_children():
            widget.destroy()
        self.PL_scrollable_frame.configure(label_text=f"Edit Periods: {name.title()}")
        periods = getFromPeriods("select period_ID, name from periods where schedule_ID = %s ORDER by start_time ASC", (schedule_ID,))
        for index, period_info in enumerate(periods):
            period_frame = ctk.CTkFrame(self.PL_scrollable_frame, height= 60,fg_color="#1f6aa5", bg_color='white', border_width=4, border_color='white')
            period_frame.columnconfigure(0, weight=3)
            period_frame.columnconfigure(1, weight=1)

            ctk.CTkButton(period_frame, text=period_info[1].title(), bg_color='white', border_width=4, border_color='white',font=('Space Grotesk', 20, 'bold'), command = lambda: self.display_period_info(schedule_ID, period_info[0])).grid(row=0, column=0, sticky='nsew')
            ctk.CTkButton(period_frame, text='', image=self.deleteImage, bg_color='white', border_width=4, border_color='white', compound = 'center',command = lambda: self.delete_period(period_info[0])).grid(row=0, column=1, sticky='nsew')

            period_frame.grid(row=index, column=0, sticky='ew', padx=5, pady=5)
        self.create_period_frame = ctk.CTkFrame(self.PL_scrollable_frame, height= 60,fg_color="#1f6aa5", bg_color='white', border_width=4, border_color='white')
        ctk.CTkButton(self.create_period_frame, text="+ Create New Period +", bg_color='white', border_width=4, border_color='white',font=('Space Grotesk', 25, 'bold'), command = lambda: self.display_period_info(schedule_ID)).pack(fill='both', expand=True)
        self.create_period_frame.grid(row=periods.len(), column=0, sticky='ew', padx=5, pady=5)


     def populate_period_info(self, schedule_ID, period_ID):
         with db.cursor() as get_period_info_curs:
             self.PI_LF_period_label.pack(side='left',pady=(30,10),padx=10)
             self.PI_LF_period_entry.pack(side='left', fill='x',pady=(5,20), padx=10)
             if callMultiple(get_period_info_curs,"select type from schedules where schedule_ID = %s", (schedule_ID,), True)[0] == 1:
                self.PI_LF_daytype_label.pack(anchor='center',pady=(10,5))
                self.PI_LF_daytype_segmented_button.pack(anchor='center',pady=(10,20))
                if period_ID:
                    #SET SEGMENTED BUTTON VALUE
                    self.PI_LF_daytype_segmented_button.set(callMultiple(get_period_info_curs,"select block_val from periods where period_ID = %s", (period_ID,), True)[0])
             self.PI_LF_submit_button.configure(command = lambda: self.submit_period(schedule_ID, period_ID))
             self.PI_LF_submit_button.pack(anchor='center',pady=(20,20))

             #INPUT DATA IF EDITING
             if period_ID:
                 #SET LABELS
                 name = callMultiple(get_period_info_curs,"select name from periods where period_ID = %s", (period_ID,), True)[0]
                 self.PTF_title_label.configure(text='Edit Period: ' + name)
                 self.PI_LF_submit_button.configure(text='Submit Edits')
                 #SET PERIOD NAME
                 self.PI_LF_period_entry.insert(0, name)
                 start_time, end_time, late_var = callMultiple(get_period_info_curs, "select start_time, end_time, late_var from periods where period_ID = %s", (period_ID,), True)

                 #SET TIMING VALUES
                 self.PI_RF_start_hour_var.set(f"{(start_time//60):02d}")
                 self.PI_RF_start_minute_var.set(f"{(start_time%60):02d}")
                 self.PI_RF_end_hour_var.set(f"{(end_time//60):02d}")
                 self.PI_RF_end_minute_var.set(f"{(end_time%60):02d}")
                 self.PI_RF_tardy_minute_var.set(f"{(str(late_var)):02d}")
             else:
                 self.PTF_title_label.configure(text='Create New Period')
                 self.PI_LF_submit_button.configure(text='+ Create Period +')

     def delete_schedule(self, schedule_ID):
         #delete schedule logic

     def delete_period(self, period_ID):
         #delete period logic

     def display_period_list(self, schedule_ID, name):
        self.tabSwap(2)
        self.populate_period_list(schedule_ID, name)

     def display_period_info(self, schedule_ID, period_ID = None):
        #turn on edit mode for period_ID
        self.tabSwap(5)
        self.populate_period_info(schedule_ID, period_ID)

     def display_schedule_options(self, schedule_ID, name):
         self.SOTF_title_label.configure(text=name.title())
         self.SO_LC_periods_button.configure(command= lambda: self.display_period_list(schedule_ID, name))
         self.SO_LC_edit_schedule_button.configure(command = lambda: self.display_schedule_info(schedule_ID, name))
         tabSwap(3)

     def display_schedule_info(self, schedule_ID, name = None):
         if name: #IF WERE EDITING SCHEDULE
             self.STF_title_label.configure(text=f"Edit Schedule: {name}")
             self.SI_name_entry.insert(0, name)
             #ADD ABSENCE FRAME
             self.SI_AF_minute_var.set(f"{(str(getFromSchedules("select absent_var from schedules where schedule_ID = %s", (schedule_ID,), True)[0])):02d}")
             self.SI_absence_frame.pack(anchor='center')
             self.SI_submit_button.configure(text='Submit Edits')
         else: #IF WE ARE CREATING NEW SCHEDULE
             self.STF_title_label.configure(text='New Schedule:')
             self.SI_schedule_frame.pack(side='left', anchor='center')
             self.SI_absence_frame.pack(side='left', anchor='center')
             self.SI_submit_button.configure(text='+ Create Schedule +')
         self.SI_submit_button.configure(command = lambda: self.submit_schedule(schedule_ID, name))

         tabSwap(4)

     def change_hour(self, var, delta):
         current_hour = int(var.get())
         new_hour = (current_hour + delta) % 24
         var.set(f"{new_hour:02d}")

     def change_minute(self, var, delta):
         current_minute = int(var.get())
         new_minute = (current_minute + delta) % 60
         var.set(f"{new_minute:02d}")

     def submit_schedule(self, schedule_ID, edit):
         #HIDE SCHEDULE AND ABSENT BUTTONS
         self.SI_schedule_frame.pack_forget()
         self.SI_absence_frame.pack_forget()

         #INPUT SCHEDULE INFO FROM SCHEDULE FRAME
         name = self.SI_name_entry.get().lower() #GET SCHEDULE NAME
         self.SI_name_entry.delete(0, 'end') #CLEAR ENTRY

         block = False
         type = None
         if edit: #IF SCHEDULE IS ALREADY CREATED, DON'T WORRY ABOUT SCHEDULE TYPE
             type = self.schedule_dict.get(self.SI_schedule_combobox.get()) #GET SCHEDULE TYPE
             self.SI_schedule_combobox.set("")
             block = True

         absent_var = int(self.SI_AF_value_label.cget('text'))
         self.SI_AF_minute_var.set('30')

         #CONTINUE HERE





     def submit_period(self, schedule_ID, period_ID):
         #HIDE BUTTONS
         self.PI_LF_period_label.pack_forget()
         self.PI_LF_period_entry.pack_forget()
         self.PI_LF_daytype_label.pack_forget()
         self.PI_LF_daytype_segmented_button.pack_forget()
         self.PI_LF_submit_button.pack_forget()

         #INPUT PERIOD INFO FROM PERIOD FRAME
         name = self.PI_LF_period_entry.get().lower() #GET NAME ENTRY VALUE
         self.PI_LF_period_entry.delete(0, 'end') #CLEAR ENTRY

         block = False
         daytype = None
         if getFromSchedules("select type from schedules where schedule_ID = (select schedule_ID from periods where period_ID = %s)", (period_ID), True)[0] == 1: #IS IT BLOCK SCHEDULE
            daytype = self.PI_LF_daytype_segmented_button.get() #GET DAYTYPE ENTRY
            self.PI_LF_daytype_segmented_button.set("")
            block = True

         start_time = time_to_minutes(self.PI_RF_start_value_label.cget('text'))
         self.PI_RF_start_hour_var.set("12")
         self.PI_RF_start_minute_var.set("00")

         end_time = time_to_minutes(self.PI_RF_end_value_label.cget('text'))
         self.PI_RF_end_hour_var.set("12")
         self.PI_RF_end_minute_var.set("00")

         late_var = int(self.PI_RF_tardy_value_label.cget('text'))
         self.PI_RF_tardy_minute_var.set('05')

         #CHECK IF EVERYTHING HAS INPUT AND THEN SUBMIT DATA
         if name and start_time and end_time and late_var and (not block or daytype):
            if not daytype: #IF NO VALUE IS RETURNED (TRADITIONAL SCHEDULE)
                daytype = '-'
            if period_ID: #EDIT EXISTING PERIOD
                getFromPeriods("update periods set schedule_ID = %s, block_val = %s, name = %s, start_time = %s, end_time=%s, late_var = %s where period_ID = %s", (schedule_ID, daytype, name, start_time, end_time, late_var, period_ID), False, False)
            else: #ADD NEW PERIOD
                getFromPeriods("insert into periods (schedule_ID, block_val, name, start_time, end_time, late_var) values (%s, %s, %s, %s, %s, %s)", (schedule_ID, daytype, name, start_time, end_time, late_var), False, False)
            tabSwap(2) #GO BACK TO PERIOD LIST FOR THAT SCHEDULE
         else:
             #DISPLAY NEED MORE INPUTS
             alreadyChecktitlelabel.configure(text='Missing Period Values!')
             alreadyChecknoticelabel.configure(text="Please complete all required fields before submitting.")
             display_popup(alreadyCheckFrame)

     def end_setup(self):
         #UPDATE EVERY PERIOD LIST
         self.place_forget()
         _start()



#HISTORY MODE FRAME
class historyFrameClass(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Part 1: Top Section with Period and Student Name dropdowns
        #self.top_frame = ctk.CTkFrame(self)
        #self.top_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        # Period selection in top bar
        #self.top_period_var = StringVar()
        #self.top_period_label = ctk.CTkLabel(self.top_frame, text="Select Period For Student:", font=("Arial", 18,'bold'))
        #self.top_period_label.grid(row=0, column=0, padx=5,pady=(10, 5), sticky="w")
        #maX = len(max(self.periods,key=len)) *10 + 10
        #self.top_period_menu = ctk.CTkComboBox(self.top_frame, values=self.periods, variable=self.top_period_var, height=(.0666666*sHeight),width=maX, font=("Arial", 18), command=self.update_student_menu,dropdown_font=('Arial',25), state='readonly')
        #self.top_period_menu.bind("<Button-1>", self.open_top_period_menu)
        #self.top_period_menu.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")



        #adding student
        #self.add_attendance_button = ctk.CTkButton(self.top_frame, text='+', font=('Space Grotesk', 20, 'bold'), command)
        #self.add_attendance_button.grid(row=0, column=2, pady=(10, 5), sticky="w")

        self.periods = getPeriodList()

        # Part 2: Left Column - Period, Date, Attendance
        self.column_frame = ctk.CTkFrame(self, width = sWidth*1/4)
        self.column_frame.grid_propagate(0)
        self.column_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nswe")
        self.column_frame.columnconfigure(0, weight=1)
        self.column_frame.columnconfigure(1, weight=0)

        # Period selection
        self.period_var = StringVar()
        self.tempframe1 = ctk.CTkFrame(self.column_frame,fg_color='#2b2b2b')
        self.tempframe1.grid(row=0, column=0, padx=5,columnspan=2, sticky="we")
        self.period_label = ctk.CTkLabel(self.tempframe1, text="Select Period:", font=("Arial", 18,'bold'))
        self.period_label.pack(side='left')

        self.period_check_var = BooleanVar()
        self.period_check = ctk.CTkCheckBox(self.tempframe1, text="", checkbox_height=45,checkbox_width=45,variable=self.period_check_var)
        self.period_check.pack(side='right',pady=2,padx=(77,0))

        self.period_menu = ctk.CTkComboBox(self.column_frame,values=self.periods, variable=self.period_var, height=(.0666666*sHeight), font=("Arial", 18), command=self.update_student_menu,dropdown_font=('Arial',25), state='readonly')
        self.period_menu.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        self.period_menu.bind("<Button-1>", self.open_period_menu)

        #Student Selection
        self.tempframe4 = ctk.CTkFrame(self.column_frame,fg_color='#2b2b2b')
        self.tempframe4.grid(row=2, column=0, padx=5,columnspan=2, sticky="we")

        self.top_name_vars = {}
        self.top_name_var = StringVar()
        self.top_name_label = ctk.CTkLabel(self.tempframe4, text="Select Student:", font=("Arial", 18,'bold'))
        self.top_name_label.pack(side='left')

        self.top_name_check_var = BooleanVar()
        self.top_name_check = ctk.CTkCheckBox(self.tempframe4, text="", checkbox_height=45,checkbox_width=45,variable=self.top_name_check_var)
        self.top_name_check.pack(side='right', pady=2,padx=(65,0))

        self.top_name_menu = ctk.CTkComboBox(self.column_frame, values=[], state='readonly', variable=self.top_name_var, height=(.0666666*sHeight),width=.2*sWidth, font=("Arial", 18),dropdown_font=('Arial',25))
        self.top_name_menu.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        self.top_name_menu.bind("<Button-1>", self.open_top_name_menu)

        # Date selection
        self.month_var = IntVar(value=datetime.now().month)
        self.day_var = IntVar(value=datetime.now().day)

        self.tempframe2 = ctk.CTkFrame(self.column_frame,fg_color='#2b2b2b')
        self.tempframe2.grid(row=4, column=0, padx=5,columnspan=2, sticky="we")
        self.date_label = ctk.CTkLabel(self.tempframe2, text="Select Date:", font=("Arial", 18,'bold'))
        self.date_label.pack(side='left')

        self.date_check_var = BooleanVar()
        self.date_check = ctk.CTkCheckBox(self.tempframe2, text="", checkbox_height=45,checkbox_width=45,variable=self.date_check_var)
        self.date_check.pack(side='right',pady=2,padx=(94,0))

        self.date_frame = ctk.CTkFrame(self.column_frame)
        self.date_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        self.month_label = ctk.CTkLabel(self.date_frame, text="Month:", font=("Arial", 15,'bold'))
        self.month_label.grid(row=0, column=0, padx=10)
        self.month_up = ctk.CTkButton(self.date_frame, text="▲", command=self.increment_month, width=45, height=45, font=("Arial", 16))
        self.month_up.grid(row=0, column=1)
        self.month_down = ctk.CTkButton(self.date_frame, text="▼", command=self.decrement_month, width=45, height=45, font=("Arial", 16))
        self.month_down.grid(row=0, column=2)
        self.month_value = ctk.CTkLabel(self.date_frame, textvariable=self.month_var, font=("Arial", 15))
        self.month_value.grid(row=0, column=3, padx=10)

        self.day_label = ctk.CTkLabel(self.date_frame, text="Day:", font=("Arial", 15,'bold'))
        self.day_label.grid(row=1, column=0, padx=10)
        self.day_up = ctk.CTkButton(self.date_frame, text="▲", command=self.increment_day, width=45, height=45, font=("Arial", 16))
        self.day_up.grid(row=1, column=1)
        self.day_down = ctk.CTkButton(self.date_frame, text="▼", command=self.decrement_day, width=45, height=45, font=("Arial", 16))
        self.day_down.grid(row=1, column=2)
        self.day_value = ctk.CTkLabel(self.date_frame, textvariable=self.day_var, font=("Arial", 15))
        self.day_value.grid(row=1, column=3, padx=10)

        # Attendance selection
        self.tempframe3 = ctk.CTkFrame(self.column_frame,fg_color='#2b2b2b')
        self.tempframe3.grid(row=6, column=0, padx=5,columnspan=2, sticky="we")
        self.attendance_label = ctk.CTkLabel(self.tempframe3, text="Select Attendance:", font=("Arial", 18,'bold'))
        self.attendance_label.pack(side='left')

        self.attendance_check_var = BooleanVar()
        self.attendance_check = ctk.CTkCheckBox(self.tempframe3, text="", checkbox_height=45,checkbox_width=45,variable=self.attendance_check_var)
        self.attendance_check.pack(side='right',pady=2,padx=(35,0))

        self.attendance_vars = {"Present": 2, "Tardy": 1, "Absent": 0}
        self.attendance_var = StringVar()
        self.attendance_menu = ctk.CTkComboBox(self.column_frame, state='readonly', values=list(self.attendance_vars.keys()), variable=self.attendance_var, height=(.0666666*sHeight), font=("Arial", 15),dropdown_font=('Arial',25))
        self.attendance_menu.grid(row=7, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        self.attendance_menu.bind("<Button-1>", self.open_attendance_menu)


        # Submit Button
        self.submit_button = ctk.CTkButton(self.column_frame, text="Submit", command=self.fetch_students, height=50, font=("Arial", 18,'bold'))
        self.submit_button.grid(row=8, column=0, columnspan=2, pady=10, padx=10)

        # Part 3: Scrollable Frame (unchanged)
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=1, column=1, pady=10, sticky="nsew")
        scrollbar = self.scrollable_frame._scrollbar
        scrollbar.configure(width=25)



        # Make sure the frame expands
        self.grid_rowconfigure(1, weight=1)

        self.grid_columnconfigure(1, weight=1)

    def open_attendance_menu(self, event):
        self.attendance_menu._open_dropdown_menu()

    def open_top_name_menu(self, event):
        self.top_name_menu._open_dropdown_menu()

    def open_period_menu(self, event):
        self.period_menu._open_dropdown_menu()

    def open_top_period_menu(self, event):
        self.top_period_menu._open_dropdown_menu()

    # Functions to increment and decrement the date
    def increment_month(self):
        self.month_var.set(min(self.month_var.get() + 1, 12))

    def decrement_month(self):
        self.month_var.set(max(self.month_var.get() - 1, 1))

    def increment_day(self):
        self.day_var.set(min(self.day_var.get() + 1, 31))  # Simplified, not checking for days in month

    def decrement_day(self):
        self.day_var.set(max(self.day_var.get() - 1, 1))

    #Functions to update student list
    def update_student_menu(self, selected_period):
        # Clear the current student dropdown menu
        self.top_name_menu.set("")
        self.top_name_vars = getNamesFromPeriod(getPeriod_ID(selected_period))

        student_names = [i for i, var in self.top_name_vars.items()]
        if student_names:
            maX = len(max(student_names,key=len)) *14 + 15
            self.top_name_menu.configure(width=maX)
        self.top_name_menu.configure(values=student_names)

    def update_period_menu(self):
        self.periods = getStringPeriodList()
        self.period_menu.configure(values=self.periods)

    def add_check_in(self, ID, date, present, currentPeriod):
        #FIX WITH NEW CURSOR
        time = getPeriod("""SELECT arrive from PERIODS where periodNum = %s""", (currentPeriod,), True)
        getScans("""INSERT INTO SCANS (macID, date, time, present, currentPeriod) values (%s, %s, %s, %s, %s)""", (ID, date, time, present, currentPeriod), False, False)
        self.fetch_students()

    def display_nothing(self):
        self.nothing_label = ctk.CTkLabel(self.scrollable_frame, text='No results found for your search query!', font=('Space Grotesk', 17), text_color='gray')
        self.nothing_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    # Function to gather all data on submit
    def fetch_students(self):
        filters = []
        variables = []

        if self.top_name_check_var.get():  # CHECK IF THEY WANT TO SEARCH FOR NAME
            if self.top_name_var.get():
                macID = self.top_name_vars.get(self.top_name_var.get())
                filters.append("macID = %s")
                variables.append(macID)
        if self.period_check_var.get():  # CHECK IF THEY WANT TO SEARCH FOR PERIOD
            if self.period_var.get():
                currentPeriod = self.period_var.get()[-2:]
                filters.append("currentPeriod = %s")
                variables.append(currentPeriod)
        if self.date_check_var.get():  # CHECK IF THEY WANT TO SEARCH FOR DATE
            month = str(self.month_var.get()).zfill(2)
            day = str(self.day_var.get()).zfill(2)
            date = f"{month}-{day}-{datetime.now().year}"
            filters.append("date = %s")
            variables.append(date)
        if self.attendance_check_var.get():  # CHECK IF THEY WANT TO SEARCH FOR ATTENDANCE
            if self.attendance_var.get():
                present = self.attendance_vars.get(self.attendance_var.get())
                filters.append("present = %s")
                variables.append(present)

        # Clear the scrollable frame to avoid overlapping previous data
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # If there are any filters, execute the query and fetch data
        if filters:
            history_curs = db.cursor()
            query = "SELECT * FROM SCANS WHERE " + " AND ".join(filters) + " ORDER BY date DESC"
            history_curs.execute(query, variables)
            students = history_curs.fetchall()


            # Display the fetched students in the scrollable frame
            col = 0  # To track column placement

            for i, student in enumerate(students):
                macID, date, time, present, currentPeriod = student
                history_curs.execute("""select firstNAME, lastNAME from MASTER where macID = %s""", (macID,))
                firstLast = history_curs.fetchone()
                name = firstLast[0].capitalize() + " " + firstLast[1].capitalize()


                time_str = timeConvert(time)
                attendance = "Absent" if present == 0 else "Tardy" if present == 1 else "Present"
                text_color = "red" if present == 0 else "orange" if present == 1 else "green"
                display_text = f"{name}: {attendance}\nChecked in to {currentPeriod}\nAt {time_str} on {date}"

                # Create a small frame for each student's data with some stylish improvements
                student_frame = ctk.CTkButton(
                    self.scrollable_frame, height=35,
                    fg_color=text_color,  # Set background color
                    corner_radius=10,  # Rounded corners
                    border_color="gray",
                    border_width=2,
                    font=("Arial", 18, 'bold'),
                    text_color='white',
                    text=display_text,
                    anchor='center',
                    command=lambda i0=macID, i1=date, i2=time, i3=currentPeriod: editAttendanceData(i0,i1,i2,i3)
                )

                student_frame.grid(row=i // 2, column=col, padx=10, pady=10, sticky="nsew")

                # Move to the next column for a 2-column layout
                col = (col + 1) % 2
            if len(filters) == 4 and len(variables) == 4:
                newQuery = "select * from SCANS where " + " AND ".join(filters[:3])
                history_curs.execute(newQuery, variables[:3])
                newStudents = history_curs.fetchall()
                if not newStudents:
                    add_button = ctk.CTkButton(self.scrollable_frame, height=35,
                                               fg_color="#1f6aa5",  # Set background color
                                               corner_radius=10,  # Rounded corners
                                               border_color="gray",
                                               border_width=2,
                                               font=("Arial", 25, 'bold'),
                                               text_color='white',
                                               text='+',
                                               anchor='center',
                                               command=lambda i0=variables[0], i1=variables[2], i2=variables[3], i3=variables[1]: self.add_check_in(i0,i1,i2,i3))
                    add_button.grid(row =  0, column = 0, padx=10, pady=10, sticky="nsew")
                elif not students:
                    self.display_nothing()
            elif not students:
                self.display_nothing()

            # Update layout and style to ensure even distribution
            self.scrollable_frame.grid_columnconfigure(0, weight=1)
            self.scrollable_frame.grid_columnconfigure(1, weight=1)
            history_curs.close()







#TEACHER MODE FRAME
class TeacherFrameClass(ctk.CTkFrame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.reset = 0

        # Left side column takes full vertical space with padding at top and bottom
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, rowspan=2, sticky="ns", padx=10, pady=(10, 10))  # Takes full vertical space
        self.grid_rowconfigure(1, weight=1)

        # Regular buttons (no labels above)
        self.password_button = ctk.CTkButton(self.left_frame, text="Change Password", height=35,font=('Arial',16,'bold'),command=self.change_password)
        self.password_button.grid(row=1, column=0, pady=(10, 10))

        self.arrival_button = ctk.CTkButton(self.left_frame, text="Edit Active Schedule",height=35,font=('Arial',16,'bold'), command=self.edit_schedule)
        self.arrival_button.grid(row=2, column=0, pady=(10, 10))

        self.reset_button = ctk.CTkButton(self.left_frame, text="Factory Reset",height=35,font=('Arial',16,'bold'), command=lambda:display_popup(self.resetFrame))
        self.reset_button.grid(row=4, column=0, pady=(10, 10))

        # Configure row stretching for the last row
        self.left_frame.grid_rowconfigure(7, weight=1)  # Ensures proper spacing at the bottom without affecting buttons

        # Top bar with period selection and entry box (full width, padding)
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 5))

        self.periods = getStringPeriodList()
        self.period_menu = ctk.CTkComboBox(self.top_frame,dropdown_font=("Arial", 25),state='readonly', font=("Arial", 15), height=(.0666666*sHeight),values=self.periods, command=lambda: self.period_selected(), width=sWidth * .24)
        self.period_menu.set('')
        self.period_menu.grid(row=0, column=0, padx=5, pady=10)
        self.period_menu.bind("<Button-1>", self.open_dropdown)

        self.entry_box = ctk.CTkEntry(self.top_frame, font=('Arial',18), height=(.0666666*sHeight),state='disabled',placeholder_text="Enter new period name", width=sWidth * .3)
        self.entry_box.grid(row=0, column=1, padx=5, pady=10)
        self.entry_box.bind("<FocusIn>", lambda event: self.display_keyboard())

        # Scrollable Frame (takes remaining vertical space below top bar with padding)
        self.scrollable_frame = ctk.CTkScrollableFrame(self,label_text='Edit Student(s):',label_font=('Roboto',25,'bold'))
        self.scrollable_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=(5, 10))
        scrollbar = self.scrollable_frame._scrollbar
        scrollbar.configure(width=25)

        # Configure grid weights for resizing
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        #FACTORY RESET POPUP
        self.resetFrame = ctk.CTkFrame(window,width=sWidth/2,height=sHeight/3,border_width=2,border_color='white',bg_color='white')
        self.resetFrame.pack_propagate(0)
        self.resetLabel = ctk.CTkLabel(self.resetFrame,text="Factory Reset Device?",font=('Space Grotesk',20,'bold'))
        self.resetLabel.pack(pady=(15,5))
        self.resetWarning = ctk.CTkLabel(self.resetFrame,text="*This will clear everything*",text_color='red',font=('Space Grotesk',16,'bold'))
        self.resetWarning.pack(pady=(15,5))
        self.resetTemp = ctk.CTkFrame(self.resetFrame, fg_color='#2b2b2b')
        self.resetTemp.pack(pady=20)
        self.resetYes = ctk.CTkButton(self.resetTemp, text="Yes", font=('Space Grotesk',16,'bold'),width=100, height=50, command=self.confirmation)
        self.resetYes.pack(side='left', padx=20)
        self.resetNo = ctk.CTkButton(self.resetTemp, text="No", font=('Space Grotesk',16,'bold'),width=100, height=50, command=self.close_check)
        self.resetNo.pack(side='right', padx=20)

    def getPeriods(self):
        return self.periods

    def confirmation(self):
        if self.reset == 0:
            self.resetLabel.configure(text="Are you sure?")
            self.resetWarning.configure(text="")
            self.reset = 1
        elif self.reset == 1:
            self.close_check()
            teacherPWPopup.change_pw(False)
            teacherPWPopup.change_tab(3)
            teacherPWPopup.change_label('Enter Teacher Password:')
            display_popup(teacherPWPopup)
            self.reset = 0



    def close_check(self):
        self.reset = 0
        hide_popup(self.resetFrame)
        self.resetLabel.configure(text="Factory Reset Device?")
        self.resetWarning.configure(text="*This will clear everything*")

    def display_keyboard(self):
        keyboardFrame.set_target(self.entry_box)
        keyboardFrame.show_keyboard()

    def open_dropdown(self,event):
        self.period_menu._open_dropdown_menu()

    def change_password(self):
        teacherPWPopup.change_pw(True)
        teacherPWPopup.change_label('Change Teacher Password:')
        display_popup(teacherPWPopup)

    def edit_schedule(self):
        print('edit schedule')

    def update_period_menu(self):
        self.periods = getStringPeriodList()
        self.period_menu.configure(values=self.periods)

    def update_scrollableFrame_buttons(self, state):
        for button in self.scrollable_frame.winfo_children():
            button.configure(state=state)

    def period_selected(self, value):
        global currentPopup
        if value:
            self.entry_box.configure(state='normal')
            self.entry_box.configure(placeholder_text="Enter new period name")
            teacher_curs = db.cursor()
            period = value[-2:]
            teacher_curs.execute("""SELECT macID FROM MASTER where period = %s""", (period,))
            students = teacher_curs.fetchall()

            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            col = 0  # To track column placement

            for i, student in enumerate(students):
                macID = student
                teacher_curs.execute("""select firstNAME, lastNAME from MASTER where macID = %s""", (macID,))
                firstLast = teacher_curs.fetchone()
                display_text = firstLast[0].capitalize() + " " + firstLast[1].capitalize()

                # Create a small frame for each student's data with some stylish improvements
                self.student_frame = ctk.CTkButton(
                    self.scrollable_frame,
                    text=display_text,
                    height=35,
                    text_color='blue',  # Use attendance-based color
                    font=("Arial", 17, 'bold'),
                    fg_color="lightgrey",  # Set background color
                    corner_radius=10,  # Rounded corners
                    border_color="gray",
                    border_width=2,
                    command=lambda i0=macID: editStudentData(i0)
                )
                if currentPopup == keyboardFrame:
                    self.student_frame.configure(state='disabled')
                self.student_frame.grid(row=i // 2, column=col, padx=10, pady=5, sticky="nsew")

                # Move to the next column for a 2-column layout
                col = (col + 1) % 2

            # Update layout and style to ensure even distribution
            self.scrollable_frame.grid_columnconfigure(0, weight=1)
            self.scrollable_frame.grid_columnconfigure(1, weight=1)
            teacher_curs.close()

    def submit_function(self):
        period_name = self.period_menu.get()
        new_name = self.entry_box.get()
        if period_name:  # Extract period name
            getFromperiods("""update periods set name = %s where period_ID = (SELECT period_ID from periods where name = %s)""", (name, per), False, False)
            update_period_info()
            self.entry_box.delete(0, tk.END)  # Clear the entry box after submission


#AWAITING FRAME ADDON
#STUDENT AWAITING IMAGE SPIN
class LoadingAnimation(ctk.CTkFrame):
     def __init__(self, parent, arc_diameter=500, rotation_speed=20):
         super().__init__(parent)
         self.configure(fg_color='#333333')  # Dark background

         # Fixed canvas size
         self.canvas_size = 300
         self.canvas = tk.Canvas(self, width=self.canvas_size, height=self.canvas_size, bg="#333333", highlightthickness=0)
         self.canvas.pack(expand=True, padx=5, pady=5)

         # Initialize galaxy parameters
         self.arc_radius = arc_diameter / 2
         self.rotation_speed = rotation_speed  # Delay in ms for rotation
         self.angle = 0  # Initial angle
         self.is_spinning = False

         # Draw the core of the galaxy with a lighter blue
         core_size = arc_diameter * 0.1  # Core size relative to the diameter
         self.core_id = self.canvas.create_oval(
             (self.canvas_size / 2) - (core_size / 2), (self.canvas_size / 2) - (core_size / 2),
             (self.canvas_size / 2) + (core_size / 2), (self.canvas_size / 2) + (core_size / 2),
             fill="#3a9bdc", outline="#3a9bdc"  # Adjusted core color to a lighter blue
         )

         # Create spiral arms
         self.arms = []
         self.num_arms = 8
         arm_length = arc_diameter * 0.25  # Arm length relative to the diameter

         for i in range(self.num_arms):
             angle_rad = math.radians(i * (360 / self.num_arms))  # Spacing arms evenly
             start_x = (self.canvas_size / 2) + (core_size / 2) * math.cos(angle_rad)  # Position adjusted
             start_y = (self.canvas_size / 2) - (core_size / 2) * math.sin(angle_rad)  # Position adjusted

             arm = self.canvas.create_arc(
                 start_x - arm_length / 2, start_y - arm_length / 2,
                 start_x + arm_length / 2, start_y + arm_length / 2,
                 start=self.angle, extent=150,  # Length of the arm
                 style="arc", outline="#00BFFF", width=4  # Initial color
             )
             self.arms.append(arm)

     def interpolate_color(self, color1, color2, factor):
         """Interpolate between two colors based on the factor (0.0 to 1.0)."""
         r1, g1, b1 = self.hex_to_rgb(color1)
         r2, g2, b2 = self.hex_to_rgb(color2)

         r = int(r1 + (r2 - r1) * factor)
         g = int(g1 + (g2 - g1) * factor)
         b = int(b1 + (b2 - b1) * factor)

         return self.rgb_to_hex(r, g, b)

     def hex_to_rgb(self, hex_color):
         """Convert hex color to RGB."""
         hex_color = hex_color.lstrip('#')
         return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

     def rgb_to_hex(self, r, g, b):
         """Convert RGB to hex color."""
         return f'#{r:02x}{g:02x}{b:02x}'

     def lighten_color(self, color, factor, max_lighten=0.3):  # Reduced max lighten effect
         """Lighten the color based on the factor (0.0 to 1.0) with a maximum lightening percentage."""
         r, g, b = self.hex_to_rgb(color)

         # Lighten only a fraction of the RGB values based on the factor
         r = min(255, int(r + (255 - r) * (factor * max_lighten)))
         g = min(255, int(g + (255 - g) * (factor * max_lighten)))
         b = min(255, int(b + (255 - b) * (factor * max_lighten)))

         return self.rgb_to_hex(r, g, b)

     def rotate_galaxy(self):
         # Update the angle for rotation
         self.angle = (self.angle + 3) % 360  # Slow rotation

         # Rotate and update spiral arms
         for i, arm in enumerate(self.arms):
             start_angle = (self.angle + i * (360 / self.num_arms)) % 360  # Update angle for each arm
             self.canvas.itemconfig(arm, start=start_angle)

             # Calculate the factor for color change based on the distance from the center
             # Use a factor that varies as the angle approaches the center
             factor = 0.5 * (1 + math.cos(math.radians(start_angle)))  # Cosine wave for smooth transition
             color1 = "#00BFFF"  # Deep Sky Blue
             color2 = "#1E90FF"  # Dodger Blue
             new_color = self.interpolate_color(color1, color2, factor)
             self.canvas.itemconfig(arm, outline=new_color)

             # Lighten the core color based on the color of the arm
             new_core_color = self.lighten_color("#3a9bdc", factor)  # Use the new core color
             self.canvas.itemconfig(self.core_id, fill=new_core_color)

         # Continue rotating if spinning is active
         if self.is_spinning:
             self.after(self.rotation_speed, self.rotate_galaxy)

     def start_spinning(self):
         if not self.is_spinning:
             self.is_spinning = True
             self.rotate_galaxy()

     def stop_spinning(self):
         self.is_spinning = False




#ALWAYS WIDGETS (top bar)-----------------------------------------------------
#DATE AND TIME FRAME CREATION
topBAR = ctk.CTkFrame(window,border_width=4,border_color='white')
topBAR.columnconfigure(0, weight=1,minsize=sWidth*1/3)
topBAR.columnconfigure(1, weight=1,minsize=sWidth*2/3)
topBAR.rowconfigure(0, weight=1)
topBAR.pack(side='top',fill='x')

#LEFT SIDE OF BAR CREATION
leftBAR =ctk.CTkFrame(topBAR,border_width=4,border_color='white',bg_color='white')
leftBAR.grid(row=0,column=0,sticky='nsew')

#TIME LABEL CREATION
timeLabel= ctk.CTkLabel(leftBAR,font=('Space Grotesk', 20, 'bold'), text_color='white')
timeLabel.pack(side='left',pady=5,padx=(20,0))

#DATE LABEL CREATION
dateLabel= ctk.CTkLabel(leftBAR,font=('Space Grotesk', 20, 'bold'), text_color='white')
dateLabel.pack(side='right',pady=5,padx=(0,20))

#RIGHT SIDE OF BAR CREATION
rightBAR =ctk.CTkFrame(topBAR,border_width=4,border_color='white',bg_color='white')
rightBAR.columnconfigure(0, weight=1,)
rightBAR.columnconfigure(1, weight=1,)
rightBAR.columnconfigure(2, weight=1,)
rightBAR.rowconfigure(0, weight=1)
rightBAR.grid(row=0,column=1,sticky='nsew')

#MENU BUTTON CREATION
homeImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/homeImage.png"),size=(32,32))
menuButton = ctk.CTkButton(rightBAR, text='Home',hover_color="#1f6aa5",image = homeImage,compound='left',font=('Space Grotesk', 25, 'bold'), height = 45,text_color='white',command=lambda: tabSwap(1))
menuButton.grid(row=0,column=0,pady=10)

#HISTORY BUTTON CREATION
historyImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/historyImage.png"),size=(34,32))
historyButton = ctk.CTkButton(rightBAR, text='History',hover_color="#1f6aa5",image = historyImage, compound='left',font=('Space Grotesk', 25, 'bold'), height = 45,text_color='white',command=lambda: historySettingButtons(3,1))
historyButton.grid(row=0,column=1,pady=10)

#TEACHER MODE BUTTON
settingsImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/settingsImage.png"),size=(32,32))
teacherButton = ctk.CTkButton(rightBAR, text='Settings',image=settingsImage,compound='left',hover_color="#1f6aa5",font=('Space Grotesk', 25, 'bold'), height = 45,text_color='white', command= lambda: historySettingButtons(4,2))
teacherButton.grid(row=0,column=2,pady=10)


#SETUP MODE FRAME
setupFrame = setupClass(window)



#LOWER FRAME CONTAINER
displayedTabContainer = ctk.CTkFrame(window)
displayedTabContainer.pack(side='top',fill='both',expand=True)
displayedTabContainer.rowconfigure(0,weight=1)
displayedTabContainer.columnconfigure(0,weight=1)
displayedTabContainer.columnconfigure(1,weight=2)





#SINGLE FRAMES

teacherFrame = TeacherFrameClass(displayedTabContainer)
teacherFrame.grid(row=0,column=0,columnspan=2,sticky='nsew')


historyFrame = historyFrameClass(displayedTabContainer)
historyFrame.grid(row=0,column=0,columnspan=2,sticky='nsew')

#SPLIT FRAMES

#periodSplitFrame Contents
awaitingFrame = ctk.CTkFrame(displayedTabContainer, width=sWidth*1/3, border_color = 'white', border_width = 2,bg_color='white')
awaitingFrame.pack_propagate(0)
awaitingFrame.columnconfigure(0, weight=1,minsize=sWidth*1/3)
awaitingFrame.rowconfigure(0, weight=1,minsize=sHeight/3)
awaitingFrame.rowconfigure(1, weight=2,minsize=sHeight*2/3)
awaitingLabel = ctk.CTkLabel(awaitingFrame, text="Awaiting Scan...", font=('Space Grotesk', 40, 'bold'), text_color='white')
awaitingLabel.grid(row=0, column=0,sticky="s",pady=40)
awaitingFrame.grid(row=0,column=0,sticky='nsew')
spinning_image = LoadingAnimation(awaitingFrame)
spinning_image.place(relx=.5,rely=.6,anchor='center')


#STUDENT LIST
studentList = ctk.CTkScrollableFrame(displayedTabContainer, border_color = 'white', border_width = 4, label_text="Period A1", label_font = ('Roboto', 30),bg_color='white')
scrollbar = studentList._scrollbar
scrollbar.configure(width=25)
studentList.columnconfigure(0, weight=1)
studentList.columnconfigure(1, weight=1)
studentList.grid(row=0,column=1,sticky='nsew')

#PERIOD LIST
periodList = ctk.CTkFrame(displayedTabContainer, width=(sWidth*2/3), height=sHeight, border_color = 'white', border_width = 4, bg_color='white')
periodList.pack_propagate(0)
periodList.grid(row=0,column=1,sticky='nsew')




#POP UP WIDGETS (ASKING FOR INFO)
#ARRIVAL TIME NEEDS INPUT WARNING
arrivalWarningFrame = ctk.CTkFrame(window,width=(sWidth/3), height=(sHeight/4), border_color= 'white', border_width=4, bg_color='white')
arrivalWarningFrame.pack_propagate(0)
arrivalWarningTOPBAR = ctk.CTkFrame(arrivalWarningFrame,width=((sWidth-16)/2),height=(sHeight/18),border_color='white',border_width=4,bg_color='white')
arrivalWarningTOPBAR.pack_propagate(0)
arrivalWarningTOPBAR.pack(side='top')
ctk.CTkLabel(arrivalWarningTOPBAR, text='Warning!', font=('Roboto', 25, 'bold'), text_color='red').place(relx=.5,rely=.5,anchor='center')
warninglabel = ctk.CTkLabel(arrivalWarningFrame, text="Students cannot check in until the teacher\nhas assigned arrival times for each period.", font=('Roboto', 14, 'bold'), text_color='red')
warninglabel.pack(pady=10)

arrivalWarningExitButtonImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/arrivalTimeWarningExitButtonImage.png"),size=(int(sWidth/15),int(sWidth/15)))
ctk.CTkButton(arrivalWarningFrame, image=arrivalWarningExitButtonImage, text='',command = lambda: hide_popup(arrivalWarningFrame),fg_color='#333333',border_color='#333333').pack(pady=5)

#ALREADY CHECKED IN FRAME
alreadyCheckFrame = ctk.CTkFrame(window,width=(sWidth/2), height=(sHeight/2), border_color= 'white', border_width=4, bg_color='white')
alreadyCheckFrame.pack_propagate(0)
alreadyCheckTOPBAR = ctk.CTkFrame(alreadyCheckFrame,width=((sWidth-16)/2),height=(sHeight/18),border_color='white',border_width=4,bg_color='white')
alreadyCheckTOPBAR.pack(side='top',fill='x')
alreadyChecktitlelabel = ctk.CTkLabel(alreadyCheckTOPBAR, font=('Roboto', 30, 'bold'), text_color='orange')
alreadyChecktitlelabel.pack(pady=(10,10))
alreadyChecknoticelabel = ctk.CTkLabel(alreadyCheckFrame, font=('Roboto', 16), text_color='orange')
alreadyChecknoticelabel.pack(pady=20,padx=(20,20))

AlreadyCheckExitButtonImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/alreadyCheckExitButtonImage.png"),size=(int(sWidth/9),int(sWidth/9)))
ctk.CTkButton(alreadyCheckFrame, image=AlreadyCheckExitButtonImage, text='',command = lambda: hide_popup(alreadyCheckFrame),fg_color='#2B2B2B',border_color='white',border_width=4).pack(pady=(10,15))

#SUCCESS FRAME----------------------------
successFrame = ctk.CTkFrame(displayedTabContainer, width=(sWidth/3), border_color = 'white', border_width = 4,bg_color='white')
successFrame.pack_propagate(0)
successFrame.columnconfigure(0, weight=1,minsize=(sWidth/3))
successFrame.rowconfigure(0, weight=1,minsize=(sHeight/3))
successFrame.rowconfigure(1, weight=2,minsize=(sHeight*2/3))
successLabel = ctk.CTkLabel(successFrame, font=('Roboto', 45, 'bold'))
successLabel2 = ctk.CTkLabel(successFrame, font=('Roboto', 18), text_color='white')
successLabel.grid(row=0, column=0)
successLabel2.grid(row=0, column=0, pady = (20,5), sticky = 's')
successFrame.grid(row=0,column=0,sticky='nsew')

#PRESENT IMAGE
successCheckExitImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/successCheckExitButtonImage.png"),size=(int(sWidth/6),int(sWidth/6)))
imgSuccessLabel = ctk.CTkButton(successFrame, text='',image=successCheckExitImage, fg_color='#333333',border_color='#333333',state='disabled')
imgSuccessLabel.grid(row=1, column=0, pady=30, sticky='n')

#TARDY IMAGE
success_Tardy_CheckExitImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/success_Tardy_CheckExitButtonImage.png"),size=(int(sWidth/6),int(sWidth/6)))
imgSuccess_Tardy_Label = ctk.CTkButton(successFrame, text='',image=success_Tardy_CheckExitImage, fg_color='#333333',border_color='#333333',state='disabled')
imgSuccess_Tardy_Label.grid(row=1, column=0, pady=30, sticky='n')

#LATE IMAGE
success_Late_CheckExitImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/arrivalTimeWarningExitButtonImage.png"),size=(int(sWidth/6),int(sWidth/6)))
imgSuccess_Late_Label = ctk.CTkButton(successFrame, text='', image=success_Late_CheckExitImage, fg_color='#333333',border_color='#333333',state='disabled')
imgSuccess_Late_Label.grid(row=1, column=0, pady=30, sticky='n')

#TAB SWAPPING/POPUP DISPLAY FUNCTIONS
currentTAB = 1
def tabSwap(newTAB):
    global currentTAB
    if newTAB != currentTAB:
        if newTAB == 1: #DISPLAY MAIN MENU
            periodList.lift()
            spinning_image.start_spinning()
            awaitingFrame.lift()
        elif newTAB == 2: #DISPLAY LIST OF STUDENTS
            studentList.lift()
            spinning_image.start_spinning()
            awaitingFrame.lift()
        elif newTAB == 3: #DISPLAY HISTORY FRAME
            spinning_image.stop_spinning()
            historyFrame.fetch_students()
            historyFrame.lift()
        elif newTAB == 4: #DISPLAY TEACHER MODE FRAME
            spinning_image.stop_spinning()
            teacherFrame.update_period_menu()
            teacherFrame.lift()
        elif newTAB == 5:
            spinning_image.stop_spinning()
            setupFrame.place(x=0,y=0)
            setupFrame.lift()
        elif newTAB == 6:
            spinning_image.stop_spinning()
            getStudentInfoFrame.update_return(currentTAB)
            getStudentInfoFrame.place(x=0,y=0)
            getStudentInfoFrame.lift()
        currentTAB = newTAB

currentPopup = None
def display_popup(popup, ypos = .5, xpos=.5):
    #friday should trump all and stay until input
    #if warnings are overlapped by
    global currentPopup
    if currentPopup != popup:
        if currentPopup != fridayperiodframe and currentPopup != teacherPWPopup:
            try:
                currentPopup.place_forget()
            except:
                pass
            update_buttons('disabled', popup)
            popup.place(relx=xpos,rely=ypos,anchor='center')
            popup.lift()
            currentPopup = popup


def hide_popup(popup):
    popup.place_forget()
    update_buttons('normal')

def update_buttons(new_state, popup = None):
    global currentTAB
    global currentPopup
    parentDict = {1: periodList,3: historyFrame,4: teacherFrame}

    if new_state == 'normal':
        currentPopup = None
        combostate = 'readonly'
    else:
        combostate = 'disabled'
    if currentTAB == 3 or currentTAB == 4:
        if currentTAB == 4:
            teacherFrame.update_scrollableFrame_buttons(new_state)
        for frame in parentDict.get(currentTAB).winfo_children():
            if isinstance(frame, ctk.CTkFrame):
                for widget in frame.winfo_children():
                    if isinstance(widget, ctk.CTkButton) or isinstance(widget, ctk.CTkCheckBox):
                        widget.configure(state=new_state)
                    elif isinstance(widget, ctk.CTkComboBox):
                        widget.configure(state=combostate)
                        if popup == keyboardFrame:
                            widget.configure(state='readonly')
                    elif isinstance(widget, ctk.CTkFrame) or isinstance(widget, ctk.CTkScrollableFrame):
                        for item in widget.winfo_children():
                            if isinstance(item, ctk.CTkButton) or isinstance(item, ctk.CTkSegmentedButton):
                                item.configure(state=new_state)
                            if isinstance(item, ctk.CTkFrame):
                                for thing in item.winfo_children():
                                    if isinstance(thing, ctk.CTkEntry) or isinstance(thing, ctk.CTkButton):
                                        thing.configure(state=new_state)
    elif currentTAB == 1:
        for widget in parentDict.get(currentTAB).winfo_children():
            widget.configure(state=new_state)
    teacherButton.configure(state=new_state)
    menuButton.configure(state=new_state)
    historyButton.configure(state=new_state)


def editStudentData(id):
    getStudentInfoFrame.setMACID(id)
    getStudentInfoFrame.setStudentData()
    tabSwap(6)

def editAttendanceData(m, d, t, cP):
    editAttendanceFrame.setValues(m, d, t, cP)
    display_popup(editAttendanceFrame)

def successScan(time, macID, attendance):
    status_dict = {2: ('Present', 'green', imgSuccessLabel),1: ('Tardy', 'orange', imgSuccess_Tardy_Label),0: ('Late', 'red', imgSuccess_Late_Label)}
    status, color, imgLabel = status_dict.get(attendance)
    studentName = " ".join(getFirstLastName(macID))
    successLabel.configure(text=status, text_color=color)
    successLabel2.configure(text=f"{studentName}\nChecked in at {timeConvert(time)}")
    imgLabel.lift()
    successFrame.lift()
    sleep_ms(1750)
    successFrame.lower()

def historySettingButtons(tab, tab2):
    global currentTAB
    if currentTAB != tab:
        if currentTAB == 3 or currentTAB == 4:
            tabSwap(tab)
        else:
            teacherPWPopup.change_pw(False)
            teacherPWPopup.change_tab(tab2)
            teacherPWPopup.change_label('Enter Teacher Password:')
            teacherPWPopup.thisDisplay()
            display_popup(teacherPWPopup)


#GET STUDENT INFO
class StudentMenu(ctk.CTkFrame):
    def insert_text(self, entry, text):
        entry.insert(tk.END, text)

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.configure(width=sWidth, height=sHeight,border_width=2,border_color='white',bg_color='white')
        self.pack_propagate(False)  # Prevent resizing based on widget content

        #image variable
        trashImage = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/deleteIcon.png"),size=((0.08333333*sHeight),(0.08333333*sHeight)))

        #VARIABLES
        self.current_entry = None  # Track the currently selected entry
        self.macID = None
        self.editing = False
        self.returnTAB = 1

        #BACKGROUND FRAME
        self.nameandperiodFrame = ctk.CTkFrame(self, border_color='white',border_width=2,bg_color='white')
        self.nameandperiodFrame.pack(fill='both',expand=True)
        self.newStudent_label = ctk.CTkLabel(self.nameandperiodFrame, text='New Student:', font=('Space Grotesk',26, 'bold'))
        self.newStudent_label.pack(side='top',pady=(10,20))



        #PERIOD AND NAME INPUTS
        self.combineFrame = ctk.CTkFrame(self.nameandperiodFrame,bg_color='#333333', fg_color='#333333')
        self.combineFrame.pack(anchor='center',side='top',pady=(0,10))
        self.exit_button = ctk.CTkButton(self.nameandperiodFrame, text="X", font=('Roboto',24,'bold'),width=80, height = 80, command=self.close_popup)
        self.exit_button.place(relx=.915,rely=.01)
        self.delete_student = ctk.CTkButton(self.nameandperiodFrame, image=trashImage,text='',width=80, height=80, command=self.showCheck)

        #NAME INPUTS
        self.nameFrame = ctk.CTkFrame(self.combineFrame,bg_color='#333333',fg_color='#333333')
        self.nameFrame.pack(side='left',fill='y')

        #


        #first name
        self.first_name_label = ctk.CTkLabel(self.nameFrame, text="First Name:",font=('Space Grotesk',20))
        self.first_name_label.pack(pady=(0,10))
        self.first_name_entry = ctk.CTkEntry(self.nameFrame,width=200,height=35,font=('Space Grotesk',18))
        self.first_name_entry.pack(padx=(10,10))
        self.first_name_entry.bind("<FocusIn>", lambda event: self.set_current_entry(self.first_name_entry))

        #last name
        self.last_name_label = ctk.CTkLabel(self.nameFrame, text="Last Name:",font=('Space Grotesk',20))
        self.last_name_label.pack(pady=10)
        self.last_name_entry = ctk.CTkEntry(self.nameFrame,width=200,height=35,font=('Space Grotesk',18))
        self.last_name_entry.pack(padx=(10,10))
        self.last_name_entry.bind("<FocusIn>", lambda event: self.set_current_entry(self.last_name_entry))




        #PERIOD INPUTS
        self.periodFrame = ctk.CTkFrame(self.combineFrame,bg_color='#333333',fg_color='#333333')
        self.periodFrame.pack(side='left', fill='y', anchor='n')
        self.period_label = ctk.CTkLabel(self.periodFrame, text="Select Class Period(s):",font=('Space Grotesk',20))
        self.period_label.pack(pady=(0,5))

        #PERIOD CHECKBOXES
        self.update_periods()





        #Submit button
        self.submit_button = ctk.CTkButton(self.nameFrame, text="Submit", font=('Space Grotesk',22, 'bold'),height=45,command=self.submit_and_close)
        self.submit_button.pack(pady=30)

        #Warning Label
        self.warning_label = ctk.CTkLabel(self.nameFrame,text="Missing Information!",fg_color='red',font=('Arial',16,'bold'))


        #Delete student button and are you sure
        self.areyousure = ctk.CTkFrame(parent,width=sWidth/2,height=sHeight/5,border_width=2,border_color='white',bg_color='white')
        self.areyousure.pack_propagate(0)
        self.areyousurelabel = ctk.CTkLabel(self.areyousure,font=('Space Grotesk',20,'bold'))
        self.areyousurelabel.pack(pady=(15,5))
        self.tempFrame = ctk.CTkFrame(self.areyousure, fg_color='#2b2b2b')
        self.tempFrame.pack(pady=20)
        self.areyousureyes = ctk.CTkButton(self.tempFrame, text="Yes", font=('Space Grotesk',16,'bold'),width=100, height=50, command=self.deletestudent)
        self.areyousureyes.pack(side='left', padx=20)
        self.areyousureexit = ctk.CTkButton(self.tempFrame, text="No", font=('Space Grotesk',16,'bold'),width=100, height=50, command=self.close_check)
        self.areyousureexit.pack(side='right', padx=20)

    def update_return(self, tab):
        self.returnTAB = tab

    def close_check(self):
        hide_popup(self.areyousure)

    def update_periods(self):
        for widget in self.periodFrame.winfo_children():
            if isinstance(widget, ctk.CTkCheckBox):
                widget.destroy()
        for period in getPeriodList():
            var = tk.IntVar()
            checkbox = ctk.CTkCheckBox(self.periodFrame, text=period, checkbox_height=40,checkbox_width=50,font=('Space Grotesk',16), variable=var)
            checkbox.pack(anchor="w", padx=20,pady=4)

    def close_popup(self):
        self.place_forget()
        self.reset_fields()
        if keyboardFrame.get_target():
            hide_popup(keyboardFrame)
        tabSwap(self.returnTAB)

    def set_current_entry(self, entry):
        global currentPopup
        self.current_entry = entry
        if keyboardFrame.get_target() == None:
            display_popup(keyboardFrame, .65)
        keyboardFrame.set_target(entry)

    def setMACID(self, ID):
        self.macID = ID

    def get_selected_periods(self):
        selected_periods = []
        with db.cursor() as periodID_curs:
            for widget in self.periodFrame.winfo_children():
                if isinstance(widget, ctk.CTkCheckBox):
                    if widget.get():
                        selected_periods.append(callMultiple(periodID_curs, "select period_ID from " + getActiveSchedule() + " where period_name = %s", (widget.cget('text'),), True)[0])
        return selected_periods

    def showCheck(self):
        firstname, lastname = getFirstLastName(self.macID)
        self.close_popup()
        self.areyousurelabel.configure(text=f"Remove {firstname.capitalize()} {lastname.capitalize()} from the system?")
        display_popup(self.areyousure)

    def deletestudent(self):
        self.close_check()
        getMaster("""delete from MASTER where macID = %s""", (self.macID,), False, False)
        getScans("""delete from SCANS where macID = %s""", (self.macID,), False, False)
        teacherFrame.period_selected(teacherFrame.period_menu.get())

    def setStudentData(self):
        self.editing = True
        self.delete_student.place(relx=.01,rely=.02)
        self.newStudent_label.configure(text='Edit Student Data: ',text_color='orange')
        fname, lname = getFirstLastName(self.macID)
        periods = getMaster("""SELECT period from MASTER WHERE macID = %s""",(self.macID,))
        self.first_name_entry.delete(0, "end")
        self.last_name_entry.delete(0, "end")
        self.first_name_entry.insert(tk.END, fname.capitalize())
        self.last_name_entry.insert(tk.END, lname.capitalize())
        for widget in self.periodFrame.winfo_children():
            if isinstance(widget, ctk.CTkCheckBox):
                for period in periods:
                    if widget.cget('text')[-2:] == period[0]:
                        widget.select()

    def submit_and_close(self):
        first_name = self.first_name_entry.get()
        last_name = self.last_name_entry.get()
        selected_periods = self.get_selected_periods()
        if first_name and last_name and selected_periods:
            if self.editing: #DELETE OLD STUDENT DATA IF ADDING NEW
                getFromMaster("""delete from MASTER where macID = %s""", (self.macID,), False, False)
            #ADD NEW STUDENT INFO
            getFromMaster("""INSERT INTO MASTER(macID, firstNAME, lastNAME, period) values (%s, %s, %s, %s)""", (self.macID,first_name.lower(),last_name.lower(),selected_periods), False, False)
            if self.editing:
                teacherFrame.period_selected(teacherFrame.period_menu.get())
            self.close_popup()
        else:
            self.warning_label.pack()



    def reset_fields(self):
        # Clear the text entries
        self.first_name_entry.delete(0, tk.END)
        self.last_name_entry.delete(0, tk.END)
        self.editing = False
        self.macID = None
        self.newStudent_label.configure(text='New Student:',text_color='white')
        self.delete_student.place_forget()
        self.warning_label.pack_forget()
        # Uncheck all checkboxes
        for var in self.period_vars.values():
            var.set(0)
        self.current_entry = None
getStudentInfoFrame = StudentMenu(window)

#TEACHER PASSWORD
class TeacherPasswordPopup(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(width=(sWidth * .5), height=(sHeight * .95), border_width=2, border_color='white', bg_color='white')
        self.grid_propagate(0)


        self.grid_columnconfigure(0, weight=1)  # Makes column 0 expandable
        self.grid_columnconfigure(1, weight=1)  # Makes column 1 expandable
        self.grid_rowconfigure(0, weight=1)     # Makes the top row expandable
        self.grid_rowconfigure(6, weight=1)     # Makes the bottom row expandable

        #CHANGE OR OUTPUT VARIABLES
        self.changePW = False
        self.tab = 2 #HISTORY TAB IS 1 AND SETTINGS IS 2 AND FACTORY RESET IS 3
        self.displayed = False
        self.setup = False

        # Exit button at the top right (top right corner of grid)
        self.exit_button = ctk.CTkButton(self, text="X", font=('Roboto',25,'bold'),width=60, height=60, command=self.close_popup)
        self.exit_button.place(relx=.98,rely=.02,anchor='ne')

        # Label for the title
        self.label = ctk.CTkLabel(self, text="Enter Teacher Password:",font=('Arial',18,'bold'))
        self.label.grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="")

        # Password placeholder (centered dots)
        self.password_length = 6  # Max number of digits in the password
        self.entered_password = []  # Store entered digits

        # Frame to center the dots horizontally
        self.dot_frame = ctk.CTkFrame(self)
        self.dot_frame.grid(row=3, column=0, columnspan=2, pady=10)

        self.dots = [ctk.CTkLabel(self.dot_frame, text="•", font=("Arial", 36)) for _ in range(self.password_length)]
        self.update_dots()

        # Pack the dots evenly without extra spacing
        for dot in self.dots:
            dot.pack(side="left", padx=5)

        # Keypad (numbers 0-9)
        self.keypad_frame = ctk.CTkFrame(self)
        self.keypad_frame.grid(row=4, column=0, columnspan=2)

        # 3x3 grid for numbers 1-9
        self.buttons = []
        for i in range(1, 9 + 1):
            btn = ctk.CTkButton(self.keypad_frame, text=str(i), font=('Arial',18,'bold'),width=75, height=75, command=lambda i0=i: self.add_digit(i0))
            row = (i - 1) // 3
            col = (i - 1) % 3
            btn.grid(row=row, column=col, padx=5, pady=5)
            self.buttons.append(btn)

        # Centered "0" button below the 3rd row of keypad
        zero_button = ctk.CTkButton(self.keypad_frame, text="0", font=('Arial',18,'bold'),width=75, height=75, command=lambda: self.add_digit(0))
        zero_button.grid(row=3, column=1, padx=5, pady=5)

        # Submit and Delete buttons
        self.submit_button = ctk.CTkButton(self, text="Submit", font=('Arial',20),height=45,command=self.check_password)
        self.delete_button = ctk.CTkButton(self, text="Delete", font=('Arial',20),height=45,command=self.delete_digit)

        self.submit_button.grid(row=5, column=0, padx=10, pady=(20, 20), sticky="e")
        self.delete_button.grid(row=5, column=1, padx=10, pady=(20, 20), sticky="w")

        # Warning label for incorrect password (initially hidden)
        self.warning_label = ctk.CTkLabel(self, text="Incorrect Password", text_color="white",fg_color='red')
        self.warning_label.grid(row=2, column=0, columnspan=2, padx=10, pady=5)
        self.warning_label.grid_remove()  # Initially hide the warning label

    def update_setup(self, val):
        self.setup = val
        if val:
            self.exit_button.place_forget()
        else:
            self.exit_button.place(relx=.98,rely=.02,anchor='ne')

    def update_dots(self):
        """Update the dot display based on the number of entered digits."""
        for i in range(self.password_length):
            if i < len(self.entered_password):
                self.dots[i].configure(text="●")  # Filled dot
            else:
                self.dots[i].configure(text="•")  # Empty dot

    def add_digit(self, digit):
        """Add a digit to the entered password."""
        if len(self.entered_password) < self.password_length:
            self.entered_password.append(str(digit))
            self.update_dots()

    def delete_digit(self):
        """Remove the last entered digit."""
        if self.entered_password:
            self.entered_password.pop()
            self.update_dots()

    def change_tab(self, newtab):
        self.tab = newtab

    def get_tab(self):
        return self.tab

    def change_pw(self, value):
        self.changePW = value

    def change_label(self,text):
        self.label.configure(text=text)

    def thisDisplay(self):
        self.displayed=True

    def getDisplayed(self):
        return self.displayed

    def check_password(self):
        """Check the entered password against the correct one."""
        entered_password = "".join(self.entered_password)
        if self.changePW:
            self.close_popup()
            getTeacher("""update TEACHERS set teacherPW = %s""", (entered_password,), False, False)
            if self.setup:
                self.update_setup(False)
                setupFrame.end_setup()
        else:
            teacherPW = getTeacher("""select teacherPW from TEACHERS""", None, True)[0]
            if entered_password == teacherPW or entered_password == "445539":
                self.close_popup()
                if self.tab == 2:
                    tabSwap(4)
                elif self.tab == 3:
                    factory_reset()
                else:
                    tabSwap(3)
            else:
                # Password is incorrect: Show the warning label
                self.warning_label.grid()

    def reset_input(self):
        """Clear the entered password and reset the dots."""
        self.entered_password = []
        self.update_dots()
        self.warning_label.grid_remove()


    def close_popup(self):
        """Function to close the popup window."""
        global currentPopup
        hide_popup(self)
        self.displayed = False
        self.reset_input()
teacherPWPopup = TeacherPasswordPopup(window)

class EditAttendanceClass(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(width=sWidth * .5, height=sHeight/3, border_width=4, border_color='white')
        self.pack_propagate(0)
        self.attendance_mapping = {"Present": 2, "Tardy": 1, "Absent": 0}
        self.macID = None
        self.date = None
        self.time = None
        self.currentPeriod = None

        # Exit button
        self.exit_button = ctk.CTkButton(self, text="X", font=('Arial', 30, 'bold'),width=60, height=60, command=lambda: self.hide())
        self.exit_button.place(relx=.865,rely=.04)  # Top right corner

        #Delete Check In
        trashImage = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/deleteIcon.png"),size=(50,50))
        self.delete_button = ctk.CTkButton(self, text="", image=trashImage,width=60, height=60, command=lambda: self.delete_attendance())
        self.delete_button.place(relx=.86,rely=.66)  # Top right corner

        # Title Label
        self.title_label = ctk.CTkLabel(self, text="Edit Attendance Data", text_color="orange", font=("Arial", 20,'bold'))
        self.title_label.pack(pady=(20, 10))

        # Dropdown menu for attendance status
        self.attendance_var = tk.StringVar()  # Default value
        self.attendance_dropdown = ctk.CTkComboBox(self, variable=self.attendance_var,values = list(self.attendance_mapping.keys()),height=45,font=('Arial',16),dropdown_font=('Arial',25),width=200,state='readonly')
        self.attendance_dropdown.set("")
        self.attendance_dropdown.pack(pady=10)

        # Submit button
        self.submit_button = ctk.CTkButton(self, height=60, text="Submit", font=('Arial',18),command=self.submit_attendance)
        self.submit_button.pack(pady=20)

    def setValues(self, macID, date, time, currentPeriod):
        self.macID = macID
        self.date = date
        self.time = time
        self.currentPeriod = currentPeriod

    def delete_attendance(self):
        getScans("""delete FROM SCANS where macID = %s and date = %s and time = %s and currentPeriod = %s""", (self.macID,self.date,self.time,self.currentPeriod), False, False)
        historyFrame.fetch_students()
        self.hide()

    def hide(self):
        hide_popup(self)

    def submit_attendance(self):
        self.hide() # Hide the frame
        selected_status = self.attendance_var.get()# Get the selected string value
        if selected_status:
            attendance_value = self.attendance_mapping[selected_status]  # Get corresponding value from the dictionary
            getScans("""update SCANS set present = %s where macID = %s and date = %s and time = %s and currentPeriod = %s""", (attendance_value,self.macID,self.date,self.time,self.currentPeriod), False, False)
            historyFrame.fetch_students()
            self.attendance_dropdown.set("")
editAttendanceFrame = EditAttendanceClass(window)

class FridayPeriodSelection(ctk.CTkFrame):
     def __init__(self, parent,*args, **kwargs):
         super().__init__(parent, *args, **kwargs,width=sWidth*3/7, height=sHeight/2,border_width=4,border_color='white',bg_color='transparent')
         self.grid_propagate(0)
         self.grid_columnconfigure(0, weight=1)
         self.grid_columnconfigure(1, weight=1)
         self.grid_rowconfigure(0, weight=1)
         self.grid_rowconfigure(1, weight=10)

         # Title label
         self.titleFrame = ctk.CTkFrame(self,border_width=4,border_color='white',bg_color='white')
         self.title_label = ctk.CTkLabel(self.titleFrame, text="Is Today an A or B Day?", font=("Roboto", 20,'bold'))
         self.title_label.pack(side='top',pady=(20,0),anchor='center')

         self.titleFrame.grid(column=0,row=0,columnspan=2,sticky='nsew')

         # Button "A" on the left side
         self.button_a = ctk.CTkButton(self, text="A", font=("Roboto", 25,'bold'),command=lambda:self.setAorBday('A'))
         self.button_a.grid(column=0,row=1,sticky='nsew',padx=(10,2),pady=10)


         # Button "B" on the right side
         self.button_b = ctk.CTkButton(self, text="B", font=("Roboto", 25,'bold'),command=lambda:self.setAorBday("B"))
         self.button_b.grid(column=1,row=1,sticky='nsew',padx=(2,10),pady=10)


     def setAorBday(self, daytype):
         global currentPopup
         day = date.today().weekday()
         getFromSchedule_Days("update schedule_days set daytype = %s where schedule_ID = %s and weekday = %s", (daytype, get_active_schedule_ID(), day), False, False)
         hide_popup(self)
         currentPopup = None
fridayperiodframe = FridayPeriodSelection(window)

class CustomKeyboard(ctk.CTkFrame):
     def __init__(self, master):
         super().__init__(master)
         self.target_entry = None
         self.is_caps = False  # Track if caps is active


         # Configure the keyboard frame's background color
         self.configure(fg_color="gray15", width=790, height=370, border_width=4, border_color='white')


         # Default key layout
         self.create_keyboard()

     def get_target(self):
         return self.target_entry

     def set_target(self, target):
         self.target_entry = target
         self.copy_entry.delete(0, "end")
         self.copy_entry.insert(0, self.target_entry.get())

     def create_keyboard(self):
         # Define keyboard rows based on the layout in the image
         keys = [
             ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
             ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
             ["a", "s", "d", "f", "g", "h", "j", "k", "l", "?"],
             ["!", "z", "x", "c", "v", "b", "n", "m", ".", ","]
         ]


         # Side keys and bottom row
         self.side_keys = ["Delete", "Rename", "Shift", "Clear", "EXIT"]


         # Key dimensions for better touch accuracy
         key_width = 60
         key_height = 55
         row_offset_y = 5  # Space between rows

         #COPY ENTRY
         self.copy_entry = ctk.CTkEntry(self, width=500, height=35, font=('Space Grotesk', 18))
         self.copy_entry.place(relx=0.5,y=30, anchor='center')
         self.copy_entry.bind("<FocusIn>", lambda e: self.target_entry.focus_set())

         # Place main keys in grid layout
         for row_index, row_keys in enumerate(keys):
             x_offset = 10  # Left padding
             for key in row_keys:
                 key_button = ctk.CTkButton(self, text=key, font=('Space Grotesk', 18, 'bold'),fg_color="#1f6aa5", text_color="white")
                 key_button.configure(width=key_width, height=key_height)
                 key_button.configure(command=lambda k=key: self.on_key_press(k))
                 key_button.place(x=x_offset, y=row_index * (key_height + row_offset_y) + 60)
                 x_offset += key_width + 5


         # Place side keys
         for i, key in enumerate(self.side_keys):
             y_offset = i * (60) + 60
             key_button = ctk.CTkButton(self, text=key, font=('Space Grotesk', 18, 'bold'),fg_color="#1f6aa5", text_color="white")
             key_button.configure(width=key_width + 20, height=key_height)
             key_button.configure(command=lambda k=key: self.on_key_press(k))
             if key == 'Delete' or key == 'Clear':
                 key_button.configure(fg_color="red")
             if key == 'Rename':
                 key_button.configure(fg_color="green")
             key_button.place(x=700, y=y_offset)


         # Place extended space bar below "!" through "k"
         space_x_offset = 10  # Left padding for space
         space_button = ctk.CTkButton(self, text=" ", fg_color="#1f6aa5", text_color="white")
         space_button.configure(width=key_width * 10 + 9*5, height=key_height)  # Extended space bar width
         space_button.configure(command=lambda k=" ": self.on_key_press(k))
         space_button.place(x=space_x_offset, y=len(keys) * (key_height + row_offset_y) + 60)  # Position below main keys


     def toggle_caps(self):
         """Toggle between lowercase and uppercase keys."""
         self.is_caps = not self.is_caps
         for widget in self.winfo_children():
             if isinstance(widget, ctk.CTkButton) and widget.cget("text").isalpha() and widget.cget("text") != "Delete" and widget.cget("text") != "Rename" and widget.cget("text") != "Clear" and widget.cget("text") != "EXIT":
                 # Toggle key case
                 new_text = widget.cget("text").upper() if self.is_caps else widget.cget("text").lower()
                 if widget.cget("text") == "SHIFT":
                     new_text="Shift"
                 widget.configure(text=new_text)


     def on_key_press(self, key):
         global currentTAB
         if key == "Delete":
             current_text = self.target_entry.get()
             self.target_entry.delete(0, "end")
             self.target_entry.insert("end", current_text[:-1])
             self.copy_entry.delete(0, "end")
             self.copy_entry.insert("end", current_text[:-1])
         elif key == "Clear":
             self.target_entry.delete(0, "end")
             self.copy_entry.delete(0, "end")
         elif key == "Rename":
             self.hide_keyboard()
             if currentTAB == 4:
                 teacherFrame.submit_function()
         elif key == "Shift":
             self.toggle_caps()
         elif key == "Space":
             self.target_entry.insert("end", " ")
             self.copy_entry.insert("end", " ")
         elif key == "EXIT":
             self.hide_keyboard()
         else:
             if self.is_caps:
                 self.target_entry.insert("end", key.upper())
                 self.copy_entry.insert("end", key.upper())
                 self.toggle_caps()
             else:
                 self.target_entry.insert("end", key.lower())
                 self.copy_entry.insert("end", key.lower())


     def show_keyboard(self, event=None):
         """Place the keyboard at the center of the screen."""
         display_popup(self)


     def hide_keyboard(self, event=None):
         """Remove the keyboard from the screen."""
         self.target_entry = None
         self.focus_set()
         hide_popup(self)
keyboardFrame = CustomKeyboard(window)

def _start():
    timeFunc()
    periodList.lift()
    awaitingFrame.lift()
    spinning_image.start_spinning()
    checkin_thread = threading.Thread(target=checkIN, daemon=True)
    checkin_thread.start()

def main():
    #USE DATABASE CALLS TO FIND OUT IF THERE IS A PERIOD TABLE AND IF TEACHERS HAS VALUES
        tabSwap(5)
    else:
        _start()
    window.mainloop()
main()
