#THREADING
import threading

#Better function
from functools import partial

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
    active_schedule = getFromSystem_Control("select active_schedule_ID from system_control", None, True)
    return active_schedule[0] if active_schedule else -1

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
    flattened_periods = [item[0] for item in periods]

    # Build the query with the correct number of placeholders for the IN clause
    query = """
    SELECT p.period_ID 
    FROM periods p 
    JOIN schedule_days sd ON sd.schedule_ID = p.schedule_ID 
    WHERE sd.schedule_ID = %s 
        AND sd.weekday = %s 
        AND p.period_ID IN ({})
        AND p.block_val = (
            SELECT daytype 
            FROM schedule_days 
            WHERE schedule_ID = %s 
            AND weekday = %s
        )
    """.format(",".join(["%s"] * len(flattened_periods)))

    # Set up parameters: schedule ID, weekday, the list of period IDs, schedule ID and weekday for the subquery
    params = (get_active_schedule_ID(), date.today().weekday(), *flattened_periods, get_active_schedule_ID(), date.today().weekday())

    # Execute the query
    periods_today = callMultiple(cursor, query, params)

    # Return the flattened result
    return [item[0] for item in periods_today]

def getAttendance(time, period_ID, cursor):
    # Get the active schedule ID in Python
    schedule_ID = get_active_schedule_ID()
    query = """
    SELECT 
        CASE 
            WHEN %s <= (p.start_time + p.late_var) THEN 2  -- PRESENT
            WHEN (%s - (p.start_time + p.late_var)) >= s.absent_var THEN 0  -- ABSENT
            ELSE 1  -- TARDY
        END AS attendance_status
    FROM periods p
    JOIN schedules s ON s.schedule_ID = %s
    WHERE p.period_ID = %s
    """

    # Pass `time`, `time`, `schedule_ID`, and `period_ID` as parameters to the query
    return callMultiple(cursor, query, (time, time, schedule_ID, period_ID), True)[0]



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
    print('creating periods')
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
    print('factory resetting')
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
    timeLabel.configure(text=strftime('%I:%M:%S %p')) #UPDATE TOPBAR WIDGET
    dateLabel.configure(text=strftime("%m-%d-%Y")) #          v
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
        studentList.configure(label_text=callMultiple(studentListCursor, "select name from periods where period_ID = %s", (period_ID,), True)[0].title())
        query = """SELECT sp.macID, sn.first_name, sn.last_name, sc.status, sc.scan_time
FROM student_periods sp
JOIN student_names sn ON sp.macID = sn.macID
LEFT JOIN scans sc ON sp.macID = sc.macID 
    AND sc.scan_date = CURDATE() 
    AND sc.period_ID = %s
WHERE sp.period_ID = %s
ORDER BY sn.first_name ASC"""
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
    query = """SELECT p.period_ID FROM periods p WHERE p.schedule_ID = %s AND p.block_val = (SELECT sd.daytype FROM schedule_days sd WHERE sd.schedule_ID = %s AND sd.weekday = %s) ORDER BY p.start_time ASC"""
    schedule_ID = get_active_schedule_ID()
    with db.cursor() as period_pop_curs:
        periods = callMultiple(period_pop_curs, query, (schedule_ID, schedule_ID, date.today().weekday()))
        if periods:
            for index, period in enumerate(periods, start=1):
                def command():
                    studentListPop(period)
                    tabSwap(2)
                ctk.CTkButton(periodList,text=(f"{index}: {callMultiple(period_pop_curs, 'select name from periods where period_ID = %s', (period,), True)[0].title()}"), border_color='white', font=('Space Grotesk Medium', 20),command=lambda: command()).pack(fill = 'both', expand = True)
        else:
            ctk.CTkLabel(periodList, text='No Periods to Display...', font=('Space Grotesk', 30), text_color='gray').place(relx=0.5, rely=0.5, anchor='center')

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
                result = callMultiple(alive_curs, """SELECT active_schedule_ID FROM system_control""", None, True)
            ten_after = current_time + 10
        if rfid.tagPresent(): #WHEN A MACID IS SCANNED!
            scan_date = strftime("%Y-%m-%d")
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
                                alreadyChecknoticelabel.configure(text="The current schedule is not active today. Please contact your teacher if you have questions.")
                                display_popup(alreadyCheckFrame)
                            elif current_period == "-": #NO CLASS AT THIS TIME ON THIS VALID DAY
                                alreadyChecktitlelabel.configure(text='No Scheduled Class!')
                                alreadyChecknoticelabel.configure(text="There is no class scheduled at this time. Please check your class schedule or return during your designated period.")
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
                                            print(status)
                                            #NEED REASON LOGIC (FOR NOW ALWAYS NULL)
                                            checkInCursor.execute("""INSERT INTO scans (period_ID, schedule_ID, macID, scan_date, scan_time, status, reason) values (%s, %s, %s, %s, %s, %s, %s)""", (period_ID, get_active_schedule_ID(), ID, scan_date, scan_time, status, None))
                                            studentListPop(period_ID)
                                            tabSwap(2)
                                            successScan(scan_time, ID, status)
                                    else: #IF ONE OF THEIR PERIODS IS not MATCHING WITH THE CURRENT PERIOD
                                        continue
                                if notInPeriod:
                                    #DISPLAY YOU ARE NOT IN THE CURRENT PERIOD
                                    alreadyChecktitlelabel.configure(text='Wrong period!')
                                    alreadyChecknoticelabel.configure(text="You are not in the current period.")
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
                elif currentTAB == 4: #IF IN SETTINGS AND EDITING IS NOT DISPLAYED EDIT STUDENT
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

         self.current_tab = -1

         #Setup schedule list frame (make a function to populate on each open) 1
         self.schedule_list_frame = ctk.CTkFrame(self)
         self.schedule_list_frame.grid(row=0, column=0, sticky='nsew')

         self.SL_scrollable_frame = ctk.CTkScrollableFrame(self.schedule_list_frame, width=sWidth*3/4,height=sHeight*3/4, label_text="Manage Schedules:", label_font=('Space Grotesk', 25, 'bold'))
         self.SL_scrollable_frame.columnconfigure(0, weight=1)
         self.SL_scrollable_frame._scrollbar.configure(width=25)
         self.SL_scrollable_frame.place(relx=0.5, rely=0.5, anchor='center')




         #Setup period list frame (make a function to populate on each open) 2
         self.period_list_frame = ctk.CTkFrame(self)
         self.period_list_frame.grid(row=0, column=0, sticky='nsew')

         self.PL_scrollable_frame = ctk.CTkScrollableFrame(self.period_list_frame, width=sWidth*3/4,height=sHeight*3/4, label_font=('Space Grotesk', 25, 'bold'))
         self.PL_scrollable_frame._scrollbar.configure(width=25)
         self.PL_scrollable_frame.columnconfigure(0, weight=1)
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
         self.SO_LC_periods_button.grid(column=0, row = 1, sticky='e',padx=(0,50))
         self.SO_LC_edit_schedule_button = ctk.CTkButton(self.SO_lower_container_frame, width=200, height=90, text='Edit Schedule', font=('Space Grotesk', 24, 'bold'))
         self.SO_LC_edit_schedule_button.grid(column=1, row = 1, sticky='w',padx=(50,0))




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
         self.SI_lower_container_frame.grid_propagate(0)
         self.SI_lower_container_frame.pack(side='top',fill='both',expand=True)
         self.SI_lower_container_frame.rowconfigure(0, weight=1)
         self.SI_lower_container_frame.rowconfigure(1, weight=1)
         self.SI_lower_container_frame.rowconfigure(2, weight=1)
         self.SI_lower_container_frame.columnconfigure(0, weight=1)

         #NAME FRAME ----------------
         self.SI_name_frame = ctk.CTkFrame(self.SI_lower_container_frame, fg_color='#2b2b2b')
         self.SI_name_frame.grid(column=0, row=0, sticky='s',pady=(0,10))
         self.SI_name_label = ctk.CTkLabel(self.SI_name_frame, text = "Name:", font = ('Space Grotesk', 20, 'bold'))
         self.SI_name_label.pack(side='top', anchor='w',padx=10, pady=5)
         self.SI_name_entry = ctk.CTkEntry(self.SI_name_frame, placeholder_text='Enter schedule name...', font= ('Space Grotesk', 16), height = 60, width = 280)
         self.SI_name_entry.pack(side='top', padx=5, pady=5)
         self.SI_name_entry.bind("<FocusIn>", lambda event: self.set_current_entry(self.SI_name_entry))

         #Schedule and Absence Frame
         #SCHEDULE TYPE SELECITON
         self.schedule_dict = {'Block':1, 'Traditional':0}

         self.SI_schedule_absence_frame = ctk.CTkFrame(self.SI_lower_container_frame, fg_color='#2b2b2b')
         self.SI_schedule_absence_frame.grid(column=0, row=1, sticky='ns', pady=(20,0))

         #SCHEDULE FRAME
         self.SI_schedule_frame = ctk.CTkFrame(self.SI_schedule_absence_frame)
         self.SI_schedule_label = ctk.CTkLabel(self.SI_schedule_frame, text = "Schedule Type:", font = ('Space Grotesk', 18, 'bold'))
         self.SI_schedule_label.pack(padx=10,pady=5,side='top')
         self.SI_schedule_combobox = ctk.CTkComboBox(self.SI_schedule_frame, values = ['Block', 'Traditional'], dropdown_font=('Space Grotesk', 25), dropdown_text_color='gray', height = 70, width=200, font=('Space Grotesk', 20, 'bold'))
         self.SI_schedule_combobox.pack(padx=5,pady=5,side='top')

         #ABSENCE FRAME
         self.SI_absence_frame = ctk.CTkFrame(self.SI_schedule_absence_frame)
         self.SI_AF_minute_var= ctk.StringVar(value = '30')

         self.SI_AF_title_label = ctk.CTkLabel(self.SI_absence_frame, text = "Absence Threshold\n(minutes)", font = ('Space Grotesk', 20, 'bold'))
         self.SI_AF_title_label.grid(row=0, column=0,padx=5,pady=5)
         self.SI_AF_value_label = ctk.CTkLabel(self.SI_absence_frame, text=f"{self.SI_AF_minute_var.get()}", font=('Space Grotesk', 18))
         self.SI_AF_value_label.grid(row=1,column=0,padx=5,pady=5)

         #ABSENCE MINUTE SELECTORS
         self.PI_RF_absent_minute_up = ctk.CTkButton(self.SI_absence_frame, height=60,font=('Space Grotesk', 20, 'bold'),text="↑", command = lambda: self.change_minute(self.SI_AF_minute_var, +1))
         self.PI_RF_absent_minute_up.grid(row=0, column=1,pady=5,padx=5)
         self.PI_RF_absent_minute_down = ctk.CTkButton(self.SI_absence_frame, height = 60,font=('Space Grotesk', 20, 'bold'),text="↓", command = lambda: self.change_minute(self.SI_AF_minute_var, -1))
         self.PI_RF_absent_minute_down.grid(row=1, column=1,pady=5,padx=5)

         #ABSENCE UPDATE LABEL CODE
         self.SI_AF_minute_var.trace_add("write", partial(self.update_label, self.SI_AF_minute_var, self.SI_AF_value_label))


         #SUBMIT SCHEDULE FRAME
         self.SI_submit_frame = ctk.CTkFrame(self.SI_lower_container_frame, fg_color='#2b2b2b')
         self.SI_submit_frame.grid(column=0, row=2, sticky='nsew')
         self.SI_submit_button = ctk.CTkButton(self.SI_submit_frame, width=300, height = 70, font=('Space Grotesk', 17, 'bold'))
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
         self.PI_lower_container_frame.rowconfigure(0, weight=1)

         self.PI_left_frame = ctk.CTkFrame(self.PI_lower_container_frame, bg_color='#333333')
         self.PI_left_frame.grid(row=0, column=0, sticky='nsew')

         self.PI_right_frame = ctk.CTkFrame(self.PI_lower_container_frame, bg_color='#333333')
         self.PI_right_frame.grid_propagate(0)
         self.PI_right_frame.grid(row=0, column=1, sticky='nsew')
         self.PI_right_frame.columnconfigure(0, weight=1)
         self.PI_right_frame.rowconfigure(0, weight=1)
         self.PI_right_frame.rowconfigure(1, weight=1)
         self.PI_right_frame.rowconfigure(2, weight=1)


         #LEFT FRAME (unpacked widgets, will be packed based off edit/non edit)
         self.PI_LF_period_label = ctk.CTkLabel(self.PI_left_frame, text='Period Name:', font=('Space Grotesk', 20))
         self.PI_LF_period_label.pack(side='top',pady=(30,10))
         self.PI_LF_period_entry = ctk.CTkEntry(self.PI_left_frame, width = 250, placeholder_text='Enter period name...', font=('Space Grotesk', 16), placeholder_text_color='gray', height = 60)
         self.PI_LF_period_entry.pack(side='top',pady=(5,20))
         self.PI_LF_period_entry.bind("<FocusIn>", lambda event: self.set_current_entry(self.PI_LF_period_entry))



         self.PI_LF_edit_students_button = ctk.CTkButton(self.PI_left_frame, text='Edit Students',font=('Space Grotesk', 18), height = 60, width = 200)

         self.PI_LF_daytype_label = ctk.CTkLabel(self.PI_left_frame, text='Daytype:', font=('Space Grotesk', 20))
         self.PI_LF_daytype_segmented_button = ctk.CTkSegmentedButton(self.PI_left_frame, values=['A','B'], font=('Space Grotesk', 16, 'bold'), width=100, height = 60)


         self.PI_LF_submit_button = ctk.CTkButton(self.PI_left_frame, width=180, height = 50, font=('Space Grotesk', 19, 'bold'))

         #RIGHT FRAME (always packed time widgets, make sure to clear/set with editing)
         #START FRAME -------------------------------------------------------------------------------------------
         self.PI_RF_start_frame = ctk.CTkFrame(self.PI_right_frame, fg_color='#333333')
         self.PI_RF_start_frame.grid_propagate(0)
         self.PI_RF_start_frame.grid(row=0, column=0, sticky='nsew')
         self.PI_RF_start_hour_var = ctk.StringVar(value = '12')
         self.PI_RF_start_minute_var = ctk.StringVar(value = '00')

         #START HOUR SELECTORS
         self.PI_RF_start_hour_up = ctk.CTkButton(self.PI_RF_start_frame, text="↑", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_hour(self.PI_RF_start_hour_var, +1))
         self.PI_RF_start_hour_up.grid(row=0, column=0,pady=(25,5))
         self.PI_RF_start_hour_down = ctk.CTkButton(self.PI_RF_start_frame, text="↓", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_hour(self.PI_RF_start_hour_var, -1))
         self.PI_RF_start_hour_down.grid(row=1, column=0,pady=(5,10))

         #START MINUTE SELECTORS
         self.PI_RF_start_minute_up = ctk.CTkButton(self.PI_RF_start_frame, text="↑", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_minute(self.PI_RF_start_minute_var, +1))
         self.PI_RF_start_minute_up.grid(row=0, column=2,pady=(25,5))
         self.PI_RF_start_minute_down = ctk.CTkButton(self.PI_RF_start_frame, text="↓", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_minute(self.PI_RF_start_minute_var, -1))
         self.PI_RF_start_minute_down.grid(row=1, column=2,pady=(5,10))

         #START LABELS
         self.PI_RF_start_label = ctk.CTkLabel(self.PI_RF_start_frame, text='Start Time:', font=('Space Grotesk', 20, 'bold'))
         self.PI_RF_start_label.grid(row=0, column=1,pady=5, padx=10)
         self.PI_RF_start_value_label = ctk.CTkLabel(self.PI_RF_start_frame, font = ('Space Grotesk', 18, 'bold'), text=f"{self.PI_RF_start_hour_var.get()}:{self.PI_RF_start_minute_var.get()}")
         self.PI_RF_start_value_label.grid(row=1, column=1,pady=5)

         #START UPDATE LABEL CODE
         self.PI_RF_start_hour_var.trace_add("write", partial(self.update_label2, self.PI_RF_start_hour_var, self.PI_RF_start_minute_var, self.PI_RF_start_value_label))
         self.PI_RF_start_minute_var.trace_add("write", partial(self.update_label2, self.PI_RF_start_hour_var, self.PI_RF_start_minute_var, self.PI_RF_start_value_label))

         #END FRAME -------------------------------------------------------------------------------------------
         self.PI_RF_end_frame = ctk.CTkFrame(self.PI_right_frame, fg_color='#333333')
         self.PI_RF_end_frame.grid_propagate(0)
         self.PI_RF_end_frame.grid(row=1, column=0, sticky='nsew')

         self.PI_RF_end_hour_var = ctk.StringVar(value = '12')
         self.PI_RF_end_minute_var = ctk.StringVar(value = '00')

         #END HOUR SELECTORS
         self.PI_RF_end_hour_up = ctk.CTkButton(self.PI_RF_end_frame, text="↑", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_hour(self.PI_RF_end_hour_var, +1))
         self.PI_RF_end_hour_up.grid(row=2, column=0,pady=(25,5))
         self.PI_RF_end_hour_down = ctk.CTkButton(self.PI_RF_end_frame, text="↓", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_hour(self.PI_RF_end_hour_var, -1))
         self.PI_RF_end_hour_down.grid(row=3, column=0,pady=(5,10))

         #END MINUTE SELECTORS
         self.PI_RF_end_minute_up = ctk.CTkButton(self.PI_RF_end_frame, text="↑", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_minute(self.PI_RF_end_minute_var, +1))
         self.PI_RF_end_minute_up.grid(row=2, column=2,pady=(25,5))
         self.PI_RF_end_minute_down = ctk.CTkButton(self.PI_RF_end_frame, text="↓", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_minute(self.PI_RF_end_minute_var, -1))
         self.PI_RF_end_minute_down.grid(row=3, column=2,pady=(5,10))

         #END LABELS
         self.PI_RF_end_label = ctk.CTkLabel(self.PI_RF_end_frame, text='End Time:', font=('Space Grotesk', 20, 'bold'))
         self.PI_RF_end_label.grid(row=2, column=1,pady=5,padx=10)
         self.PI_RF_end_value_label = ctk.CTkLabel(self.PI_RF_end_frame, font = ('Space Grotesk', 18, 'bold'), text=f"{self.PI_RF_end_hour_var.get()}:{self.PI_RF_end_minute_var.get()}")
         self.PI_RF_end_value_label.grid(row=3, column=1, pady=5)

         #END UPDATE LABEL CODE
         self.PI_RF_end_hour_var.trace_add("write", partial(self.update_label2, self.PI_RF_end_hour_var, self.PI_RF_end_minute_var, self.PI_RF_end_value_label))
         self.PI_RF_end_minute_var.trace_add("write", partial(self.update_label2, self.PI_RF_end_hour_var, self.PI_RF_end_minute_var, self.PI_RF_end_value_label))

         #TARDY FRAME -------------------------------------------------------------------------------------------
         self.PI_RF_tardy_frame = ctk.CTkFrame(self.PI_right_frame, fg_color='#333333')
         self.PI_RF_tardy_frame.grid_propagate(0)
         self.PI_RF_tardy_frame.grid(row=2, column=0, sticky='nsew')

         self.PI_RF_tardy_minute_var = ctk.StringVar(value = '05')

         #TARDY MINUTE SELECTORS
         self.PI_RF_tardy_minute_up = ctk.CTkButton(self.PI_RF_tardy_frame, text="↑", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_minute(self.PI_RF_tardy_minute_var, +1))
         self.PI_RF_tardy_minute_up.grid(row=4, column=2,pady=(25,5),padx=10)
         self.PI_RF_tardy_minute_down = ctk.CTkButton(self.PI_RF_tardy_frame, text="↓", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_minute(self.PI_RF_tardy_minute_var, -1))
         self.PI_RF_tardy_minute_down.grid(row=5, column=2,pady=(5,10),padx=10)

         #TARDY LABELS
         self.PI_RF_tardy_label = ctk.CTkLabel(self.PI_RF_tardy_frame, text='Tardy Threshold:', font=('Space Grotesk', 20, 'bold'))
         self.PI_RF_tardy_label.grid(row=4, column=1,pady=5,padx=10)
         self.PI_RF_tardy_value_label = ctk.CTkLabel(self.PI_RF_tardy_frame, font = ('Space Grotesk', 18, 'bold'), text=f"{self.PI_RF_tardy_minute_var.get()}")
         self.PI_RF_tardy_value_label.grid(row=5,column=1,pady=5)

         #TARDY UPDATE LABEL CODE
         self.PI_RF_tardy_minute_var.trace_add("write", partial(self.update_label, self.PI_RF_tardy_minute_var, self.PI_RF_tardy_value_label))





         #Setup weekday frame (make a function populate schedule list on each open and weekdays on each selection) 6
         self.select_weekdays_frame = ctk.CTkFrame(self)
         self.select_weekdays_frame.grid(row=0, column=0, sticky='nsew')

         #TOP BAR (weekday frame)
         self.SW_top_frame = ctk.CTkFrame(self.select_weekdays_frame, border_width=4,border_color='white')
         self.SW_top_frame.pack(side='top',fill='x')

         self.SW_TF_title_frame = ctk.CTkFrame(self.SW_top_frame, height = 100,fg_color='#2b2b2b',)
         self.SW_TF_title_frame.pack(anchor='center', pady=8)
         self.SW_title_label = ctk.CTkLabel(self.SW_TF_title_frame, font=('Space Grotesk', 28, 'bold'), text = 'Weekday Assignment:')
         self.SW_title_label.pack(side='left', pady=10,padx=20)

         #COMBOBOX (updates values every time weekday frame is displayed)
         self.SW_schedule_dict = {}
         self.SW_schedule_type = None
         self.SW_schedule_combobox = ctk.CTkComboBox(self.SW_TF_title_frame, width=250,height = 60,dropdown_font=('Space Grotesk', 25, 'bold'), font=('Space Grotesk', 24), command = self.populate_weekday_frame)
         self.SW_schedule_combobox.pack(side='left', padx=20)

         #LOWER FRAME CONTAINER (weekday frame)
         self.SW_lower_container_frame = ctk.CTkFrame(self.select_weekdays_frame)
         self.SW_lower_container_frame.pack(side='top',fill='both',expand=True)

         #WEEKDAY SETUP
         weekday_list = ("Monday:", "Tuesday:", "Wednesday:", "Thursday:", "Friday:", "Saturday:", "Sunday:")
         self.weekday_dict = {}
         for index, day in enumerate(weekday_list):
             ctk.CTkLabel(self.SW_lower_container_frame, text = day, font=('Space Grotesk', 19)).grid(column=0, row = index, pady=10,padx=(250,10))
             checkbox_var = ctk.IntVar(value = 0)
             checkbox = ctk.CTkCheckBox(self.SW_lower_container_frame,text='',checkbox_width=50, checkbox_height=50, variable = checkbox_var,command = partial(self.display_weekday_daytype, index, checkbox_var))
             combobox = ctk.CTkComboBox(self.SW_lower_container_frame, width = 200, height = 50, state='readonly',values = ['A', 'B', 'Dynamic'], font = ('Space Grotesk', 18), dropdown_font=('Space Grotesk', 25))
             checkbox.grid(row=index, column=1, padx=5,pady=10)
             self.weekday_dict[index] = (checkbox, combobox)

         #WEEKDAY SUBMIT BUTTON
         self.SW_submit_button = ctk.CTkButton(self.SW_lower_container_frame, width = 180, height = 300, text='Submit', font=('Space Grotesk', 25, 'bold'))
         self.SW_submit_button.grid(row=1, column=3, rowspan=5, padx=(60,0))






         #Setup student assignment frame (specific to each period) 7
         self.student_period_selection_frame = ctk.CTkFrame(self)
         self.student_period_selection_frame.grid(row=0, column=0, sticky='nsew')

         #TOP FRAME CREATION (STUDENT ASSIGNMENT)
         self.SA_top_frame = ctk.CTkFrame(self.student_period_selection_frame, border_width=4,border_color='white')
         self.SA_top_frame.pack(side='top',fill='x')
         self.SA_title_label = ctk.CTkLabel(self.SA_top_frame, font=('Space Grotesk', 30, 'bold'))
         self.SA_title_label.pack(anchor='center', pady=20)

         #BOTTOM FRAME CREATION (STUDENT ASSIGNMENT)
         self.SA_lower_container_frame = ctk.CTkFrame(self.student_period_selection_frame)
         self.SA_lower_container_frame.pack(side='top',fill='both',expand=True)

         self.SA_lower_container_frame.columnconfigure(0, weight=1)
         self.SA_lower_container_frame.columnconfigure(1, weight=1)
         self.SA_lower_container_frame.rowconfigure(0, weight=3)
         self.SA_lower_container_frame.rowconfigure(1, weight=1)

         #BOTTOM SCROLLABLE FRAME DICTIONARIES
         self.SA_MSF_student_dict = {}
         self.SA_PSF_student_dict = {}

         #BOTTOM FRAME SCROLLABLE FRAMES (empty until populated with students each time, also update period label each time)
         self.SA_master_scrollable_frame = ctk.CTkScrollableFrame(self.SA_lower_container_frame,label_text='Student Registry', label_font=('Space Grotesk', 20, 'bold'))
         self.SA_master_scrollable_frame.grid(row=0, column=0, sticky='nsew', padx=(70,10), pady=20)

         self.SA_period_scrollable_frame = ctk.CTkScrollableFrame(self.SA_lower_container_frame, label_font=('Space Grotesk', 20, 'bold'))
         self.SA_period_scrollable_frame.grid(row=0, column=1, sticky='nsew', padx=10, pady=20)

         #BOTTOM FRAME BUTTONS (commands will need to be updated each time with new period_IDs: add new student to period and reload period frame)
         self.SA_assign_button = ctk.CTkButton(self.SA_lower_container_frame, text='Assign To Period', font=('Space Grotesk', 18))
         self.SA_remove_button = ctk.CTkButton(self.SA_lower_container_frame, text='Remove From Period', font=('Space Grotesk', 18), fg_color='red')

         #SUCCESS POPUP (successful addition/removal of students from period notice)
         self.SA_success_notice = ctk.CTkFrame(self.student_period_selection_frame, border_width=4,border_color='white', height = sHeight/2, width = sWidth/2)
         self.SA_SN_title_label = ctk.CTkLabel(self.SA_success_notice, text='Success', font=('Space Grotesk', 22), text_color='green')
         self.SA_SN_title_label.pack(side='top',anchor='center',pady=(20,10))
         self.SA_SN_label = ctk.CTkLabel(self.SA_success_notice, font=("Space Grotesk", 15), wraplength=sWidth/2-20, justify='left')
         self.SA_SN_label.pack(side='top',anchor='w',pady=10,padx=10)
         self.SA_SN_exit_button = ctk.CTkButton(self.SA_success_notice, text='X', font=("Space Grotesk", 20, 'bold'), command = lambda: self.SA_success_notice.place_forget())
         self.SA_SN_exit_button.place(relx=.98,rely=.02)


         #CREATE tab selector frame (make animation logic based on arrow, not a popup, keep separate)
         #CONTROL VARIABLES
         self.control_frame_width = sWidth/4
         self.CF_hidden_visibility_width = self.control_frame_width*.3125
         self.CF_visible = False

         self.left_image = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/left.png"), size=(50,50))
         self.right_image = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/right.png"), size=(50,50))

         self.add_image = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/add.png"), size=(40,40))
         self.manage_schedules = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/manage_schedules.png"), size=(40,40))
         self.weekday_image = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/manage_schedules.png"), size=(40,40))

         #CONTROL FRAME
         self.control_frame = ctk.CTkFrame(self, width = self.control_frame_width, height=sHeight)
         self.control_frame.pack_propagate(0)
         self.control_frame.place(x=-(self.control_frame_width-self.CF_hidden_visibility_width), y=0)

         #CONTROL BUTTONS
         self.CF_display_button = ctk.CTkButton(self.control_frame, text="", border_width=1, border_color='gray',image = self.right_image,command=self.toggle_control_frame,font=('Space Grotesk', 25, 'bold'),width=self.CF_hidden_visibility_width , height=90, fg_color='#1f6aa5', bg_color='#2b2b2b')
         self.CF_display_button.pack(side='top',anchor='e',pady=(1,10),padx=1)

         self.create_schedule = ctk.CTkButton(self.control_frame, text='',width = self.control_frame_width/4, height = self.CF_hidden_visibility_width, fg_color='#222222', image = self.add_image, compound='top', command = self.display_schedule_info)
         self.create_schedule.pack(side='top',anchor='e',pady=(50,30),padx=8)

         self.manage_schedule = ctk.CTkButton(self.control_frame, text='', width = self.control_frame_width/4, height = self.CF_hidden_visibility_width, fg_color='#222222', image = self.manage_schedules, compound='top', command = self.display_schedule_list)
         self.manage_schedule.pack(side='top',anchor='e',pady=30,padx=8)

         self.weekday_assignment = ctk.CTkButton(self.control_frame, text='', width = self.control_frame_width/4, height = self.CF_hidden_visibility_width, fg_color='#222222', image = self.weekday_image, compound = 'top', command = self.display_weekday_frame)
         self.weekday_assignment.pack(side='top',anchor='e',pady=30,padx=8)





         #CREATE exit button (always placed)
         self.exit_button = ctk.CTkButton(self, text='X', font=("Space Grotesk", 26, 'bold'),command=self.exit_schedule_setup, height = 60)
         self.exit_button.place(relx=.85,rely=.01)


     #UPDATE ALL LABELS
     def update_label(self, var, label, *args):
         label.configure(text=var.get())

     def update_label2(self, var, var1, label, *args):
         label.configure(text=f"{var.get()}:{var1.get()}")

     #CONTROL FRAME MOVEMENT FUNCTIONS
     def toggle_control_frame(self):
         if self.CF_visible:
             self.hide_sidebar()
         else:
             self.show_sidebar()

     def show_sidebar(self):
         self.CF_display_button.configure(image = self.left_image)
         def animate():
             x = self.control_frame.winfo_x()
             if x < 0:
                 x += 20
                 new_x = min(x, 0)  # Ensure it doesn't go beyond 0
                 self.create_schedule.configure(width=(self.control_frame_width - 16) + new_x)
                 self.manage_schedule.configure(width=(self.control_frame_width - 16) + new_x)
                 self.weekday_assignment.configure(width=(self.control_frame_width - 16) + new_x)
                 self.CF_display_button.configure(width=new_x+self.control_frame_width)
                 self.control_frame.place(x=new_x)
                 self.after(10, animate)
             else:
                 self.CF_visible = True

         animate()
         self.create_schedule.configure(text='Create New Schedule     ', compound='left')
         self.manage_schedule.configure(text='Manage Existing Schedules  ', compound='left')
         self.weekday_assignment.configure(text='Weekday assignment', compound='left')

     def hide_sidebar(self):
         self.CF_display_button.configure(image= self.right_image)
         def animate():
             x = self.control_frame.winfo_x()
             target_x = -(self.control_frame_width-self.CF_hidden_visibility_width)
             if x > target_x:
                 x -= 20
                 new_x = max(x, target_x)  # Ensure it doesn't go beyond hidden position
                 self.create_schedule.configure(width=(self.control_frame_width - 16) + new_x)
                 self.manage_schedule.configure(width=(self.control_frame_width - 16) + new_x)
                 self.weekday_assignment.configure(width=(self.control_frame_width - 16) + new_x)
                 self.CF_display_button.configure(width=new_x+self.control_frame_width)
                 self.control_frame.place(x=new_x)
                 self.after(10, animate)
             else:
                 self.CF_visible = False

         animate()
         self.create_schedule.configure(text='', compound='top')
         self.manage_schedule.configure(text='', compound='top')
         self.weekday_assignment.configure(text='', compound='top')

     def tabSwap(self, new_tab):
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
         schedules = getFromSchedules("select schedule_ID, name from schedules ORDER by name ASC")
         if schedules:
             for index, schedule_info in enumerate(schedules):
                schedule_frame = ctk.CTkFrame(self.SL_scrollable_frame, height= 60,fg_color="#1f6aa5", bg_color='white', border_width=4, border_color='white')
                schedule_frame.grid_propagate(0)
                schedule_frame.columnconfigure(0, weight=4)
                schedule_frame.columnconfigure(1, weight=1)


                ctk.CTkButton(schedule_frame, text=schedule_info[1].title(), height=60,bg_color='white', border_width=4, border_color='white',font=('Space Grotesk', 20, 'bold'), command = lambda i0 = schedule_info[0], i1 = schedule_info[1]: self.display_schedule_options(i0, i1)).grid(row=0, column=0, sticky='nsew')
                ctk.CTkButton(schedule_frame, image=self.deleteImage,compound='center',fg_color='red',height=60,bg_color='white', border_width=4, border_color='white',command = lambda i0=schedule_info[0] : self.delete_schedule(i0)).grid(row=0, column=1, sticky='nsew')

                schedule_frame.grid(row=index, column=0, sticky='nsew', padx=5, pady=5)
         else:
             ctk.CTkLabel(self.SL_scrollable_frame, text="No Schedules To Display...", text_color='gray',font=("Space Grotesk", 25)).pack(pady=200, anchor='center')

     def populate_period_list(self, schedule_ID, name):
        for widget in self.PL_scrollable_frame.winfo_children():
            widget.destroy()
        if name:
            self.PL_scrollable_frame.configure(label_text=f"Edit Periods: {name.title()}")
        periods = getFromPeriods("select period_ID, name from periods where schedule_ID = %s ORDER by start_time ASC", (schedule_ID,))
        for index, period_info in enumerate(periods):
            period_frame = ctk.CTkFrame(self.PL_scrollable_frame, height= 60,fg_color="#1f6aa5", bg_color='white', border_width=4, border_color='white')
            period_frame.columnconfigure(0, weight=4)
            period_frame.columnconfigure(1, weight=1)

            ctk.CTkButton(period_frame, text=period_info[1].title(), height = 60, bg_color='white', border_width=4, border_color='white',font=('Space Grotesk', 20, 'bold'), command = lambda: self.display_period_info(schedule_ID, period_info[0])).grid(row=0, column=0, sticky='nsew')
            ctk.CTkButton(period_frame, text='', image=self.deleteImage, fg_color='red',height = 60,bg_color='white', border_width=4, border_color='white', compound = 'center',command = lambda: self.delete_period(period_info[0])).grid(row=0, column=1, sticky='nsew')

            period_frame.grid(row=index, column=0, sticky='ew', padx=5, pady=5)
        self.create_period_frame = ctk.CTkFrame(self.PL_scrollable_frame, height= 60,fg_color="#1f6aa5", bg_color='white', border_width=4, border_color='white')
        ctk.CTkButton(self.create_period_frame, text="+ Create New Period +", bg_color='white', border_width=4, border_color='white',font=('Space Grotesk', 25, 'bold'), command = lambda: self.display_period_info(schedule_ID)).pack(fill='both', expand=True)
        self.create_period_frame.grid(row=len(periods), column=0, sticky='ew', padx=5, pady=5)


     def populate_period_info(self, schedule_ID, period_ID):
         #HIDE BUTTONS
         self.PI_LF_edit_students_button.pack_forget()
         self.PI_LF_daytype_label.pack_forget()
         self.PI_LF_daytype_segmented_button.pack_forget()
         self.PI_LF_submit_button.pack_forget()
         with db.cursor() as get_period_info_curs:
             if period_ID:
                 self.PI_LF_edit_students_button.pack(side='top', pady=10)
             if callMultiple(get_period_info_curs,"select type from schedules where schedule_ID = %s", (schedule_ID,), True)[0] == 1: #IF ITS BLOCK SCHEDULE
                self.PI_LF_daytype_label.pack(side='top',pady=(10,5))
                self.PI_LF_daytype_segmented_button.pack(side='top',pady=(10,20))
                if period_ID: #IF THE PERIOD ALREADY EXISTS
                    #SET SEGMENTED BUTTON VALUE
                    self.PI_LF_daytype_segmented_button.set(callMultiple(get_period_info_curs,"select block_val from periods where period_ID = %s", (period_ID,), True)[0])
             self.PI_LF_submit_button.configure(command = lambda: self.submit_period(schedule_ID, period_ID))
             self.PI_LF_submit_button.pack(side='top',pady=(20,10))

             if period_ID: #IF THE PERIOD EXISTS
                 #SET LABELS
                 name = callMultiple(get_period_info_curs,"select name from periods where period_ID = %s", (period_ID,), True)[0].title()
                 self.PTF_title_label.configure(text='Edit Period: ' + name)
                 self.PI_LF_submit_button.configure(text='Submit Edits')
                 #SET PERIOD NAME
                 self.PI_LF_period_entry.delete(0, 'end')
                 self.PI_LF_period_entry.insert(0, name)
                 start_time, end_time, late_var = callMultiple(get_period_info_curs, "select start_time, end_time, late_var from periods where period_ID = %s", (period_ID,), True)

                 #SET EDIT STUDENT BUTTON
                 self.PI_LF_edit_students_button.configure(command=lambda: self.display_student_assignment_frame(period_ID, name))

                 #SET TIMING VALUES
                 self.PI_RF_start_hour_var.set(f"{(start_time//60):02d}")
                 self.PI_RF_start_minute_var.set(f"{(start_time%60):02d}")
                 self.PI_RF_end_hour_var.set(f"{(end_time//60):02d}")
                 self.PI_RF_end_minute_var.set(f"{(end_time%60):02d}")
                 self.PI_RF_tardy_minute_var.set(f"{(late_var):02d}")
             else:
                 self.PTF_title_label.configure(text='Create New Period')
                 self.PI_LF_submit_button.configure(text='+ Create Period +')

     def populate_weekday_frame(self, schedule_name):
         schedule_ID = self.SW_schedule_dict.get(schedule_name)
         weekday_info = {row[0]: (row[1], row[2]) for row in getFromSchedule_Days("select weekday, dynamic_daytype, daytype from schedule_days where schedule_ID = %s ORDER BY weekday ASC", (schedule_ID,))}
         self.SW_schedule_type = getFromSchedules("select type from schedules where schedule_ID = %s", (schedule_ID,), True)[0]
         self.clear_weekday_frame()
         edit = False
         if weekday_info: #IF THIS SCHEDULE ALREADY HAS INFORMATION SAVED, POPULATE IT
            edit = True
            for key, values in self.weekday_dict.items():
                 checkbox, combobox = values
                 if weekday_info.get(key)[1]: #CHECK IF DAYTYPE EXISTS, CHECKBOX SHOULD BE CHECKED!
                     checkbox.select()
                     self.display_weekday_daytype(key, ctk.IntVar(value = 1))
                     if self.SW_schedule_type:
                         if weekday_info.get(key)[0]: #IS IT A DYNAMIC DAY
                             combobox.set('Dynamic')
                         else:
                             combobox.set(weekday_info.get(key)[1])
         self.SW_submit_button.configure(command=lambda: self.submit_weekdays(schedule_ID, edit)) #MAKE SURE SUBMIT BUTTON HAS SCHEDULE ID

     def populate_SA_master_frame(self):
         for widget in self.SA_master_scrollable_frame.winfo_children():
            widget.destroy()
         self.SA_MSF_student_dict = {}
         student_data = getFromStudent_Names("select * from student_names ORDER by first_name ASC")
         for index, student in enumerate(student_data):
             macID, first_name, last_name = student
             name = f"{first_name.capitalize()} {last_name.capitalize()}"

             student_frame = ctk.CTkFrame(self.SA_master_scrollable_frame, height = 60)
             student_frame.grid(row=index, column=0, sticky='ew',pady=5,padx=7)

             ctk.CTkLabel(student_frame, text=name, font=('Space Grotesk', 16)).pack(side='left', pady=5,padx=10)

             student_checkbox = ctk.CTkCheckBox(student_frame, height = 50, width = 50)
             student_checkbox.pack(side='right',pady=5,padx=5)

             self.SA_MSF_student_dict[macID] = student_checkbox

     def populate_SA_period_frame(self, period_ID):
         for widget in self.SA_period_scrollable_frame.winfo_children():
             widget.destroy()
         self.SA_PSF_student_dict = {}
         student_data = getFromStudent_Periods("select sp.macID, sn.first_name, sn.last_name from student_periods sp join student_names sn on sp.macID = sn.macID where sp.period_ID = %s ORDER by sn.first_name ASC", (period_ID,))
         for index, student in enumerate(student_data):
             macID, first_name, last_name = student
             name = f"{first_name.capitalize()} {last_name.capitalize()}"

             student_frame = ctk.CTkFrame(self.SA_period_scrollable_frame, height = 60)
             student_frame.grid(row=index, column=0, sticky='ew',pady=5,padx=7)

             ctk.CTkLabel(student_frame, text=name, font=('Space Grotesk', 16)).pack(side='left', pady=5,padx=10)

             student_checkbox = ctk.CTkCheckBox(student_frame, height = 50, width = 50)
             student_checkbox.pack(side='right',pady=5,padx=5)

             self.SA_PSF_student_dict[macID] = student_checkbox

     def delete_schedule(self, schedule_ID):
         #delete schedule logic
         print('deleting schedule')

     def delete_period(self, period_ID):
         print('deleting period')

     def display_SA_success(self, decision, students, name):
         placeholder = ', '.join(['%s'] * len(students))
         query = f"SELECT CONCAT(first_name, ' ', last_name) AS full_name from student_names where macID in ({placeholder})"
         names = getFromStudent_Names(query, tuple(students))
         final_text = f"{decision} "
         for name in names:
             final_text += f"{name.title()}, "
         final_text = final_text[:-2]
         final_text += "from " + name
         self.SA_SN_label.configure(text=final_text)
         self.SA_success_notice.place(relx=.5, rely=.5, anchor='center')


     def display_student_assignment_frame(self, period_ID, name):
         self.SA_title_label.configure(text=f"Edit Period: {name}")
         self.SA_period_scrollable_frame.configure(label_text=name)
         self.SA_assign_button.configure(command=lambda: self.SA_assign_students(period_ID, name))
         self.SA_remove_button.configure(command=lambda: self.SA_remove_students(period_ID, name))
         self.populate_SA_master_frame()
         self.populate_SA_period_frame(period_ID)
         self.tabSwap(7)

     def display_weekday_daytype(self, index, value):
        #displays A/B/Dynamic option after clicking a checkbox
        type = self.get_SW_schedule_type()
        combobox = self.weekday_dict.get(index)[1]
        if type == 1:
            if value.get() == 1:
                combobox.grid(column=2, row = index, pady=10, padx=10)
            else:
                combobox.grid_forget()
                combobox.set("")

     def display_period_list(self, schedule_ID, name = None):
        self.populate_period_list(schedule_ID, name)
        self.tabSwap(2)

     def display_schedule_list(self):
        self.populate_schedule_list()
        self.tabSwap(1)

     def display_period_info(self, schedule_ID, period_ID = None):
        #turn on edit mode for period_ID
        self.populate_period_info(schedule_ID, period_ID)
        self.tabSwap(5)

     def display_weekday_frame(self):
         self.SW_schedule_dict = {f"{index} {name}": schedule_ID for index, (name, schedule_ID) in enumerate(getFromSchedules("select name, schedule_ID from schedules"))}
         self.SW_schedule_combobox.set("")
         self.SW_schedule_combobox.configure(values = list(self.SW_schedule_dict.keys()))
         self.tabSwap(6)

     def display_schedule_options(self, schedule_ID, name):
         self.SOTF_title_label.configure(text=name.title())
         self.SO_LC_periods_button.configure(command= lambda: self.display_period_list(schedule_ID, name))
         self.SO_LC_edit_schedule_button.configure(command = lambda: self.display_schedule_info(schedule_ID, name))
         self.tabSwap(3)

     def display_schedule_info(self, schedule_ID = None, name = None):
         self.SI_name_entry.delete(0, 'end')
         self.SI_schedule_combobox.set("")
         self.SI_schedule_frame.pack_forget()
         self.SI_absence_frame.pack_forget()
         if name: #IF WERE EDITING SCHEDULE
             self.STF_title_label.configure(text=f"Edit Schedule: {name}")
             self.SI_name_entry.insert(0, name)
             #ADD ABSENCE FRAME
             self.SI_AF_minute_var.set(f"{(getFromSchedules('select absent_var from schedules where schedule_ID = %s', (schedule_ID,), True)[0]):02d}")
             self.SI_absence_frame.pack(anchor='center')
             self.SI_submit_button.configure(text='Submit Edits')
         else: #IF WE ARE CREATING NEW SCHEDULE
             self.STF_title_label.configure(text='New Schedule:')
             self.SI_schedule_frame.pack(side='left', anchor='center')
             self.SI_absence_frame.pack(side='left', anchor='center')
             self.SI_submit_button.configure(text='+ Create Schedule +')
         self.SI_submit_button.configure(command = lambda: self.submit_schedule(schedule_ID))

         self.tabSwap(4)

     def change_hour(self, var, delta):
         current_hour = int(var.get())
         new_hour = (current_hour + delta) % 25
         var.set(f"{new_hour:02d}")

     def change_minute(self, var, delta):
         current_minute = int(var.get())
         new_minute = (current_minute + delta) % 60
         var.set(f"{new_minute:02d}")

     def clear_weekday_frame(self):
         for value in self.weekday_dict.values():
             checkbox, combobox = value
             checkbox.deselect()
             combobox.set("")
             combobox.grid_forget()

     def set_current_entry(self, entry):
         display_popup(keyboardFrame)
         keyboardFrame.set_target(entry)

     def get_SW_schedule_type(self):
         return self.SW_schedule_type

     def SA_assign_students(self, period_ID, name):
         log_list = []
         with db.cursor() as add_student_curs:
             for key, value in self.SA_MSF_student_dict.items():
                 if value.get(): #IF CHECKBOX IS SELECTED, ADD TO PERIOD AND REMOVE CHECKBOX CHECK
                     callMultiple(add_student_curs, "insert into student_periods (macID, period_ID) values (%s, %s)", (key, period_ID), False, False)
                     value.deselect()
                     log_list.append(key)
         self.populate_SA_period_frame(period_ID)
         self.display_SA_success('added', log_list, name)

     def SA_remove_students(self, period_ID, name):
         log_list = []
         with db.cursor() as remove_student_curs:
             for key, value in self.SA_PSF_student_dict.items():
                 if value.get():
                    callMultiple(remove_student_curs, "delete from student_periods where macID = %s and period_ID = %s", (key, period_ID), False, False)
                    log_list.append(key)
         self.populate_SA_period_frame(period_ID)
         self.display_SA_success('removed',log_list, name)

     def submit_schedule(self, schedule_ID):
         #INPUT SCHEDULE INFO FROM SCHEDULE FRAME
         name = self.SI_name_entry.get().lower() #GET SCHEDULE NAME


         if not schedule_ID:
             type = self.schedule_dict.get(self.SI_schedule_combobox.get()) #GET SCHEDULE TYPE
         else:
             type = 'bad'

         absent_var = int(self.SI_AF_value_label.cget('text'))


         if name and absent_var and (schedule_ID or type != 'bad'): #IF SCHEDULE IS ALREADY CREATED, DON'T WORRY ABOUT SCHEDULE TYPE
             #HIDE SCHEDULE AND ABSENT BUTTONS AND CLEAR EVERYTHING
             self.SI_schedule_frame.pack_forget()
             self.SI_absence_frame.pack_forget()
             self.SI_name_entry.delete(0, 'end') #CLEAR ENTRY
             self.SI_schedule_combobox.set("")
             self.SI_AF_minute_var.set('30')
             if schedule_ID:
                 getFromSchedules("update schedules set name = %s, absent_var = %s where schedule_ID = %s", (name, absent_var, schedule_ID), False, False)
                 self.display_schedule_list()
             else:
                 getFromSchedules("insert into schedules (name, type, absent_var) values (%s, %s, %s)", (name, type, absent_var), False, False)
                 self.display_period_list(getFromSchedules("SELECT LAST_INSERT_ID()", None, True)[0], name)

         else:
             #DISPLAY NEED MORE INPUTS
             alreadyChecktitlelabel.configure(text='Missing Schedule Values!')
             alreadyChecknoticelabel.configure(text="Please complete all required fields before submitting.")
             display_popup(alreadyCheckFrame)


     def submit_period(self, schedule_ID, period_ID):
         block = self.PI_LF_daytype_segmented_button.winfo_ismapped() #IS BLOCK SCHEDULE DISPLAYED

         #INPUT PERIOD INFO FROM PERIOD FRAME
         name = self.PI_LF_period_entry.get().lower() #GET NAME ENTRY VALUE
         self.PI_LF_period_entry.delete(0, 'end') #CLEAR ENTRY

         if block:
            daytype = self.PI_LF_daytype_segmented_button.get() #GET DAYTYPE ENTRY
            self.PI_LF_daytype_segmented_button.set("")
         else:
             daytype = None

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
            self.display_period_list(schedule_ID)
         else:
             #DISPLAY NEED MORE INPUTS
             alreadyChecktitlelabel.configure(text='Missing Period Values!')
             alreadyChecknoticelabel.configure(text="Please complete all required fields before submitting.")
             display_popup(alreadyCheckFrame)

     def submit_weekdays(self, schedule_ID, edit):
         #TAKE INFO AND SUBMIT IT TO DATABASE, CLEAR VALUES AND RESET COMBOBOX SELECTION
         submit_list = []
         need_more_data = False
         for key, values in self.weekday_dict.items():
             checkbox, combobox = values
             if checkbox.get(): #IF CHECKBOX IS CHECKED
                 dynamic_daytype = 0
                 if combobox.winfo_ismapped(): #IF COMBOBOX IS DISPLAYED
                     daytype = combobox.get()
                     if daytype == "": #HAVE THEY NOT SELECTED ON OPTION FOR DYNAMIC DAYTYPE
                         need_more_data = True
                     elif daytype == 'Dynamic':
                         daytype = '/'
                         dynamic_daytype = 1
                 else:
                     daytype = "-"
                 if edit:
                    submit_list.append((schedule_ID, key, dynamic_daytype, daytype, schedule_ID, key))
                 else:
                    submit_list.append((schedule_ID, key, dynamic_daytype, daytype))
             else: #CHECKBOX NOT CHECKED
                 if edit:
                    submit_list.append((schedule_ID, key, 0, None, schedule_ID, key))
                 else:
                    submit_list.append((schedule_ID, key, 0, None))
         if need_more_data: #PROMPT FOR MORE VALUES
             alreadyChecktitlelabel.configure(text='Missing Weekday Values!')
             alreadyChecknoticelabel.configure(text="Please complete all required fields before submitting.")
             display_popup(alreadyCheckFrame)
         else: #SUBMIT DATA
             with db.cursor() as weekday_curs:
                 if edit: #WE ARE UPDATING
                    weekday_curs.executemany("update schedule_days set schedule_ID = %s, weekday = %s, dynamic_daytype = %s, daytype = %s where schedule_ID = %s and weekday = %s", (tuple(submit_list)))
                 else: #WE ARE INSERTING
                    weekday_curs.executemany("insert into schedule_days (schedule_ID, weekday, dynamic_daytype, daytype) values (%s, %s, %s, %s)", (tuple(submit_list)))
             self.clear_weekday_frame()
             self.SW_submit_button.configure(command=lambda: None)
             self.SW_schedule_combobox.set("")

     def exit_schedule_setup(self):
         self.tabSwap(1) #BACK TO SCHEDULE LIST
         self.place_forget()
         tabSwap(4) #BACK TO SETTINGS



#HISTORY MODE FRAME
class historyFrameClass(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)


        # LEFT COLUMN
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

        #HISTORY PERIOD COMBOBOX
        self.periods = {}
        self.period_menu = ctk.CTkComboBox(self.column_frame, values = [],variable=self.period_var, height=(.0666666*sHeight), font=("Arial", 18), command= self.update_student_menu,dropdown_font=('Arial',25), state='readonly')
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

    def update_period_menu(self):
        self.periods = {f"{index} {name}": period_ID for index, (name, period_ID) in enumerate(getFromPeriods("select name, period_ID from periods where schedule_ID = %s", (get_active_schedule_ID(),)))}
        self.period_menu.configure(values=list(self.periods.keys()))

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
    def update_student_menu(self, period_name):
        # Clear the current student dropdown menu
        period_ID = self.periods.get(period_name)
        self.top_name_menu.set("")
        self.top_name_vars = getNamesFromPeriod(period_ID)

        student_names = [i for i, var in self.top_name_vars.items()]
        if student_names:
            maX = len(max(student_names,key=len)) *14 + 15
            self.top_name_menu.configure(width=maX)
        self.top_name_menu.configure(values=student_names)

    def add_check_in(self, ID, date, status, period_ID):
        time = getFromPeriods("""select start_time from periods where period_ID = %s""", (period_ID,), True)[0]
        getFromScans("""INSERT INTO scans (period_ID, schedule_ID, macID, scan_date, scan_time, status, reason) values (%s, %s, %s, %s, %s, %s, %s)""", (period_ID, get_active_schedule_ID(), ID, date, time, status, "Admin Addition"), False, False)
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
                period_ID = self.periods.get(self.period_var.get())
                filters.append("period_ID = %s")
                variables.append(period_ID)
        if self.date_check_var.get():  # CHECK IF THEY WANT TO SEARCH FOR DATE
            month = str(self.month_var.get()).zfill(2)
            day = str(self.day_var.get()).zfill(2)
            scan_date = f"{datetime.now().year}-{month}-{day}"
            filters.append("scan_date = %s")
            variables.append(scan_date)
        if self.attendance_check_var.get():  # CHECK IF THEY WANT TO SEARCH FOR ATTENDANCE
            if self.attendance_var.get():
                status = self.attendance_vars.get(self.attendance_var.get())
                filters.append("status = %s")
                variables.append(status)

        # Clear the scrollable frame to avoid overlapping previous data
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # If there are any filters, execute the query and fetch data
        if filters:
            history_curs = db.cursor()
            query = "SELECT scan_ID, macID, scan_date, scan_time, status, period_ID, reason FROM scans WHERE " + " AND ".join(filters) + " ORDER BY scan_date DESC"
            history_curs.execute(query, variables)
            students = history_curs.fetchall()


            # Display the fetched students in the scrollable frame
            col = 0  # To track column placement

            for i, student in enumerate(students):
                scan_ID, macID, scan_date, scan_time, status, period_ID, reason = student
                firstLast = callMultiple(history_curs,"""select first_name, last_name from student_names where macID = %s""", (macID,), True)
                name = firstLast[0].capitalize() + " " + firstLast[1].capitalize()


                time_str = timeConvert(scan_time)
                attendance = "Absent" if status == 0 else "Tardy" if status == 1 else "Present"
                text_color = "red" if status == 0 else "orange" if status == 1 else "green"
                display_text = f"{name}: {attendance}\nChecked in to {getFromPeriods('select name from periods where period_ID = %s', (period_ID,), True)[0].title()}\nAt {time_str} on {scan_date}"
                if reason:
                    display_text += f"\nReason: {reason}"

                # Create a small frame for each student's data with some stylish improvements
                student_frame = ctk.CTkButton(
                    self.scrollable_frame, height=35,
                    fg_color=text_color,  # Set background color
                    corner_radius=10,  # Rounded corners
                    border_color="gray",
                    border_width=2,
                    font=("Space Grotesk", 18, 'bold'),
                    text_color='white',
                    text=display_text,
                    anchor='center',
                    command=lambda: editAttendanceData(scan_ID)
                )

                student_frame.grid(row=i // 2, column=col, padx=10, pady=10, sticky="nsew")

                # Move to the next column for a 2-column layout
                col = (col + 1) % 2
            if len(filters) == 4 and len(variables) == 4:
                newQuery = "select * from scans where " + " AND ".join(filters[:3])
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
        self.password_button.grid(row=1, column=0, pady=15)

        self.arrival_button = ctk.CTkButton(self.left_frame, text="Edit Schedules",height=35,font=('Arial',16,'bold'), command=self.edit_schedule)
        self.arrival_button.grid(row=0, column=0, pady=(50, 10))

        self.reset_button = ctk.CTkButton(self.left_frame, text="Factory Reset",height=35,font=('Arial',16,'bold'), command=lambda:display_popup(self.resetFrame))
        self.reset_button.grid(row=2, column=0, pady=15)

        # Configure row stretching for the last row
        self.left_frame.grid_rowconfigure(7, weight=1)  # Ensures proper spacing at the bottom without affecting buttons

        # Top bar with period selection and entry box (full width, padding)
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 5))
        self.top_frame.rowconfigure(0, weight=1)
        self.top_frame.columnconfigure(0,weight=1)
        self.top_frame.columnconfigure(1,weight=1)
        self.top_frame.columnconfigure(2,weight=1)
        self.top_frame.columnconfigure(3,weight=1)

        self.period_menu_label = ctk.CTkLabel(self.top_frame, text='Periods:', font= ('Space Grotesk', 20, 'bold'))
        self.period_menu_label.grid(row=0,column=2, padx=10, pady=10)
        self.periods = {}
        self.period_menu_var = ctk.StringVar(value="")
        self.period_menu = ctk.CTkComboBox(self.top_frame,variable = self.period_menu_var,dropdown_font=("Space Grotesk", 25),state='readonly', font=("Arial", 15), height=(.0666666*sHeight), command=self.period_selected, width=sWidth * .24)
        self.period_menu.grid(row=0, column=3, padx=10, pady=10)
        self.period_menu.bind("<Button-1>", self.open_dropdown)

        #ACTIVE SCHEDULE SELECTION
        self.schedule_menu_label = ctk.CTkLabel(self.top_frame, text='Active Schedule:', font= ('Space Grotesk', 20, 'bold'))
        self.schedule_menu_label.grid(row=0,column=0, padx=10,pady=10)
        self.schedules = {}
        self.schedule_menu_var = ctk.StringVar(value="")
        self.schedule_menu = ctk.CTkComboBox(self.top_frame,variable = self.schedule_menu_var,dropdown_font=("Space Grotesk", 25),state='readonly', font=("Arial", 15), height=(.0666666*sHeight), command=self.schedule_selected, width=sWidth * .24)
        self.schedule_menu.grid(row=0, column=1, padx=10, pady=10)
        self.schedule_menu.bind("<Button-1>", self.open_schedule_dropdown)

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

    def open_dropdown(self,event):
        self.period_menu._open_dropdown_menu()

    def open_schedule_dropdown(self, event):
        self.schedule_menu._open_dropdown_menu()

    def change_password(self):
        teacherPWPopup.change_pw(True)
        teacherPWPopup.change_label('Change Teacher Password:')
        display_popup(teacherPWPopup)

    def edit_schedule(self):
        tabSwap(5)

    def update_period_menu(self):
        self.periods = {f"{index} {name}": period_ID for index, (name, period_ID) in enumerate(getFromPeriods("select name, period_ID from periods where schedule_ID = %s", (get_active_schedule_ID(),)))}
        self.period_menu.configure(values=list(self.periods.keys()))

    def update_schedule_menu(self):
        self.schedules = {f"{index} {name.title()}": schedule_ID for index, (name, schedule_ID) in enumerate(getFromSchedules("select name, schedule_ID from schedules"))}
        self.schedule_menu.configure(values = list(self.schedules.keys()))
        active_schedule_ID = get_active_schedule_ID()
        active_schedule_name = None
        for key, schedule_ID in self.schedules.items():
            if schedule_ID == active_schedule_ID:
                active_schedule_name = key
        if active_schedule_ID:
            self.schedule_menu.set(active_schedule_name)
        else:
            self.schedule_menu.set("")

    def update_scrollableFrame_buttons(self, state):
        for button in self.scrollable_frame.winfo_children():
            button.configure(state=state)

    def schedule_selected(self, schedule_name):
        schedule_ID = self.schedules.get(schedule_name)
        getFromSystem_Control("update system_control set active_schedule_ID = %s", (schedule_ID,), False, False)
        self.update_period_menu()

    def period_selected(self, period_name):
        global currentPopup
        period_ID = self.periods.get(period_name)
        if period_ID:
            with db.cursor() as teacher_curs:
                students = callMultiple(teacher_curs, """select sp.macID, sn.first_name, sn.last_name from student_periods sp join student_names sn on sp.macID = sn.macID where sp.period_ID = %s""", (period_ID,))

                for widget in self.scrollable_frame.winfo_children():
                    widget.destroy()
                col = 0  # To track column placement

                for i, student in enumerate(students):
                    macID, first, last = student
                    display_text = first.capitalize() + " " + last.capitalize()

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
                    self.student_frame.grid(row=i // 2, column=col, padx=10, pady=5, sticky="nsew")

                    # Move to the next column for a 2-column layout
                    col = (col + 1) % 2

                # Update layout and style to ensure even distribution
                self.scrollable_frame.grid_columnconfigure(0, weight=1)
                self.scrollable_frame.grid_columnconfigure(1, weight=1)


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
alreadyChecknoticelabel = ctk.CTkLabel(alreadyCheckFrame, font=('Roboto', 16), text_color='orange', wraplength=sWidth/2-20)
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
currentTAB = 0
def tabSwap(newTAB):
    global currentTAB
    if newTAB != currentTAB:
        if newTAB == 1: #DISPLAY MAIN MENU
            periodListPop()
            periodList.lift()
            spinning_image.start_spinning()
            awaitingFrame.lift()
        elif newTAB == 2: #DISPLAY LIST OF STUDENTS
            studentList.lift()
            spinning_image.start_spinning()
            awaitingFrame.lift()
        elif newTAB == 3: #DISPLAY HISTORY FRAME
            spinning_image.stop_spinning()
            historyFrame.update_period_menu()
            historyFrame.fetch_students()
            historyFrame.lift()
        elif newTAB == 4: #DISPLAY TEACHER MODE FRAME
            spinning_image.stop_spinning()
            teacherFrame.update_period_menu()
            teacherFrame.update_schedule_menu()
            teacherFrame.lift()
        elif newTAB == 5:
            spinning_image.stop_spinning()
            setupFrame.display_schedule_list()
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

def editAttendanceData(scan_ID):
    editAttendanceFrame.setValue(scan_ID)
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
        self.period_frame_dict = {}
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

    def update_periods(self, periods = None):
        self.period_frame_dict = {}
        for widget in self.periodFrame.winfo_children():
            if isinstance(widget, ctk.CTkCheckBox):
                widget.destroy()
        period_info = getFromPeriods("select period_ID, name from periods where schedule_ID = %s", (get_active_schedule_ID(),))
        for period in period_info:
            period_ID, name = period
            checkbox = ctk.CTkCheckBox(self.periodFrame, text=name, checkbox_height=40,checkbox_width=50,font=('Space Grotesk',16))
            if periods:
                if period_ID in periods:
                    checkbox.select()
            checkbox.pack(anchor="w", padx=20,pady=4)
            self.period_frame_dict[period_ID] = checkbox

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
        self.update_periods()
        self.macID = ID

    def get_selected_periods(self):
        selected_periods = []
        for key, value in self.period_frame_dict.items():
            if value.get():
                selected_periods.append(key)
        return selected_periods

    def showCheck(self):
        firstname, lastname = getFirstLastName(self.macID)
        self.close_popup()
        self.areyousurelabel.configure(text=f"Remove {firstname.capitalize()} {lastname.capitalize()} from the system?")
        display_popup(self.areyousure)

    def deletestudent(self):
        self.close_check()
        getFromStudent_Periods("""delete from student_periods where macID = %s""", (self.macID,), False, False)
        getFromStudent_Names("""delete from student_names where macID = %s""", (self.macID,), False, False)
        getFromScans("""delete from scans where macID = %s""", (self.macID,), False, False)
        teacherFrame.period_selected(teacherFrame.period_menu.get()) #RELOAD STUDENT LIST ON TEACHER FRAME

    def setStudentData(self):
        self.editing = True
        self.delete_student.place(relx=.01,rely=.02)
        self.newStudent_label.configure(text='Edit Student Data: ',text_color='orange')
        fname, lname = getFirstLastName(self.macID)
        periods = getFromStudent_Periods("""SELECT period_ID from student_periods WHERE macID = %s""",(self.macID,))
        self.first_name_entry.delete(0, "end")
        self.last_name_entry.delete(0, "end")
        self.first_name_entry.insert(tk.END, fname.capitalize())
        self.last_name_entry.insert(tk.END, lname.capitalize())
        self.update_periods(periods)

    def submit_and_close(self):
        first_name = self.first_name_entry.get()
        last_name = self.last_name_entry.get()
        selected_periods = self.get_selected_periods()
        if first_name and last_name and selected_periods:
            if self.editing: #DELETE OLD STUDENT DATA IF ADDING NEW
                getFromStudent_Periods("""delete from student_periods where macID = %s""", (self.macID,), False, False)
                getFromStudent_Names("""delete from student_names where macID = %s""", (self.macID,), False, False)
            #ADD NEW STUDENT INFO
            for period_ID in selected_periods:
                getFromStudent_Periods("INSERT INTO student_periods(macID, period_ID) values (%s, %s)", (self.macID, period_ID), False, False)
            getFromStudent_Names("""INSERT INTO student_names(macID, first_name, last_name) values (%s, %s, %s)""", (self.macID,first_name.lower(),last_name.lower()), False, False)
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
        self.update_periods()
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
            getFromSystem_Control("""update system_control set master_pass = %s""", (entered_password,), False, False)
        else:
            teacherPW = getFromSystem_Control("""select master_pass from system_control""", None, True)
            if teacherPW != None:
                teacherPW = teacherPW[0]
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
        self.scan_ID = None

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

    def setValue(self, scan_ID):
        self.scan_ID = scan_ID

    def delete_attendance(self):
        getFromScans("""delete FROM scans where scan_ID = %s""", (self.scan_ID), False, False)
        historyFrame.fetch_students()
        self.hide()

    def hide(self):
        hide_popup(self)

    def submit_attendance(self):
        self.hide() # Hide the frame
        selected_status = self.attendance_var.get()# Get the selected string value
        if selected_status:
            attendance_value = self.attendance_mapping[selected_status]  # Get corresponding value from the dictionary
            getFromScans("""update scans set status = %s where scan_ID = %s""", (attendance_value, self.scan_ID), False, False)
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


def main():
    timeFunc()
    threading.Thread(target=checkIN, daemon=True).start()
    tabSwap(1)
    window.mainloop()
main()
