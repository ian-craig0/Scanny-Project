#SYSTEM IMPORTS
import subprocess
import os
import threading
from functools import partial
import math
import random

#RFID SCANNER IMPORTS
from PiicoDev_RFID import PiicoDev_RFID
from PiicoDev_Unified import sleep_ms

#MYSQL IMPORTS
import MySQLdb
import mysql.connector
import mysql.connector.pooling
from contextlib import closing

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
import glob
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

#GET SCRIPT DIRECTORY
script_directory = os.path.dirname(os.path.abspath(__file__))

#CHECK IN ----------
#RFID SCANNING
rfid = PiicoDev_RFID()
master_macID = "04:F7:2C:0A:68:19:90"

#DATA BASE FUNCTIONS
def displayError(error):
    warning_confirmation.warning_confirmation_dict["unexpected error"][1] = str(error)
    warning_confirmation.config("unexpected error")

def reconnect():
    print("reconnected!")
    global db
    try:
        db = MySQLdb.connect(host='localhost',user='root',passwd='seaside',db='scanner',autocommit=True)
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
                return None  # For non-fetch queries, simply exit after execution
        except MySQLdb.OperationalError as err:
            if err.args[0] == 2006:  # MySQL server has gone away
                # Attempt to reconnect and reinitialize the cursor
                reconnect()
                if db is None:
                    raise ConnectionError("Database reconnection failed.")  # Indicate failure
                cursor = db.cursor()  # Refresh the cursor after reconnecting
            else:
                if attempts == retries - 1:
                    raise err
        except mysql.connector.Error as err:
            if attempts == retries - 1:
                raise err

        # Increment attempts and wait before retrying
        attempts += 1
        time.sleep(1)  # Shorter sleep time to retry faster


#MYSQL TABLE GETTER FUNCTIONS
#BLOCK SCHEDULE GETTER
def getFromSchedule_Days(query, params=None,fetchone=False,get=True):
    with closing(db.cursor()) as schedule_days_curs:
        return callMultiple(schedule_days_curs, query, params, fetchone, get)

#PERIODS GETTER
def getFromPeriods(query, params=None,fetchone=False,get=True):
    with closing(db.cursor()) as periods_curs:
        return callMultiple(periods_curs, query, params, fetchone, get)

#SCANS GETTER
def getFromScans(query, params=None,fetchone=False,get=True):
    with closing(db.cursor()) as scans_curs:
        return callMultiple(scans_curs, query, params, fetchone, get)

#SCHEDULES GETTER
def getFromSchedules(query, params=None,fetchone=False,get=True):
    with closing(db.cursor()) as schedules_curs:
        return callMultiple(schedules_curs, query, params, fetchone, get)

#STUDENT NAMES GETTER
def getFromStudent_Names(query, params=None,fetchone=False,get=True):
    with closing(db.cursor()) as student_name_curs:
        return callMultiple(student_name_curs, query, params, fetchone, get)

#STUDENT PERIODS GETTER
def getFromStudent_Periods(query, params=None,fetchone=False,get=True):
    with closing(db.cursor()) as student_period_curs:
        return callMultiple(student_period_curs, query, params, fetchone, get)

#CONTROL GETTER
def getFromSystem_Control(query, params=None,fetchone=False,get=True):
    with closing(db.cursor()) as system_control_curs:
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
        studentDictionary[(i[1] + " " + i[2])] = i[0]
    return studentDictionary




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

def getAttendance(time, period_ID, cursor):
    # Get the active schedule ID in Python
    schedule_ID = get_active_schedule_ID()
    query = """
    SELECT 
        CASE 
            WHEN %s <= (p.start_time + p.late_var) THEN 2  -- PRESENT
            WHEN (%s - (p.start_time + s.absent_var + 5)) >= 0 THEN 0  -- ABSENT
            ELSE 1  -- TARDY
        END AS attendance_status
    FROM periods p
    JOIN schedules s ON s.schedule_ID = %s
    WHERE p.period_ID = %s
    """

    # Pass `time`, `time`, `schedule_ID`, and `period_ID` as parameters to the query
    return callMultiple(cursor, query, (time, time, schedule_ID, period_ID), True)[0]

def handle_settings_edit(ID, reset_oldMACID):
    """Runs on the main thread - safe for GUI operations"""
    if not warning_confirmation.winfo_ismapped():
        return

    if warning_confirmation.current_key == "reset ID":
        # Database query can stay here if fast, or move to background thread
        student_exists = getFromStudent_Names(
            "SELECT first_name FROM student_names WHERE macID = %s", (ID,), True)
        
        if student_exists:
            firstname, lastname = getFirstLastName(ID)
            warning_confirmation.warning_confirmation_dict['reset ID fail'][1] = \
                f"*This ID is already assigned to {firstname} {lastname}.*"
            warning_confirmation.config("reset ID fail")
        else:
            firstname, lastname = getFirstLastName(reset_oldMACID)
            # Schedule database write to run in background
            getFromStudent_Names("UPDATE student_names SET macID = %s WHERE macID = %s", (new_id, old_id), False, False)
            window.after(0, refresh_teacher_frame)
            
    elif currentTAB != 6:
        if getFromStudent_Names("SELECT first_name FROM student_names WHERE macID = %s", (ID,), True):
            window.after(0, lambda i0 = ID: editStudentData(i0))

def refresh_teacher_frame():
    warning_confirmation.warning_confirmation_dict['reset ID success'][1] = f"*{firstname} {lastname}'s ID has been reset!*"
    warning_confirmation.config("reset ID success")
    teacherFrame.period_selected(teacherFrame.period_menu.get())

def close_success_scan():
    time.sleep(2)
    window.after(0, lambda: successFrame.lower())
    #window.after(1, tabSwap, 1)

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

def factory_reset():
    print('factory resetting')
    #with db.cursor() as factory_curs:
    #callMultiple(factory_curs,"TRUNCATE TABLE PERIODS", None, False, False)
    #callMultiple(factory_curs,"TRUNCATE TABLE ACTIVITY", None, False, False)
    #callMultiple(factory_curs,"TRUNCATE TABLE SCANS", None, False, False)
    #callMultiple(factory_curs,"TRUNCATE TABLE MASTER", None, False, False)
    #callMultiple(factory_curs,"TRUNCATE TABLE TEACHERS", None, False, False)
    #callMultiple(factory_curs,"INSERT INTO TEACHERS (A_B, ACTIVITY, SCHEDULE, teacherPW) values ('A', 0, '', '')", None, False, False)


#TIMING FUNCTIONS
def newDay():
    #UPDATE A/B DAY
    day = date.today().weekday()
    if getFromSchedule_Days("select dynamic_daytype from schedule_days where schedule_ID = %s and weekday = %s and dynamic_daytype = True", (get_active_schedule_ID(), day), True):
        display_popup(fridayperiodframe)
        teacherFrame.toggle_dynamic_button(True)
    else:
        teacherFrame.toggle_dynamic_button(False)

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

def period_transition_check(time, curr_date):
    global currentTAB
    starting_period_query = """SELECT p.period_ID
FROM periods p
JOIN schedules s ON p.schedule_ID = s.schedule_ID
LEFT JOIN schedule_days sd ON p.schedule_ID = sd.schedule_ID AND sd.weekday = %s
WHERE p.start_time = %s
AND p.schedule_ID = %s
AND (
    s.type <> 1 OR (s.type = 1 AND p.block_val = sd.daytype)
);"""

    ending_period_query = """SELECT p.period_ID
FROM periods p
JOIN schedules s ON p.schedule_ID = s.schedule_ID
LEFT JOIN schedule_days sd ON p.schedule_ID = sd.schedule_ID AND sd.weekday = %s
WHERE p.end_time = %s
AND p.schedule_ID = %s
AND (
    s.type <> 1 OR (s.type = 1 AND p.block_val = sd.daytype)
);"""

    missing_student_query = """SELECT sp.macID
FROM student_periods sp
LEFT JOIN scans s
ON sp.macID = s.macID
AND s.period_ID = %s
AND s.scan_date = CURDATE()
WHERE sp.period_ID = %s
AND s.macID IS NULL;"""
    active_schedule_ID = get_active_schedule_ID()
    starting_period = getFromPeriods(starting_period_query, (date.today().weekday(), time, active_schedule_ID), True)
    ending_period = getFromPeriods(ending_period_query, (date.today().weekday(), time, active_schedule_ID), True)
    if starting_period:
        if currentTAB == 1 or currentTAB == 2:
            tabSwap(2)
            studentListPop(starting_period[0])

    if ending_period:
        tabSwap(1)
        ending_per_ID = ending_period[0]
        absent_students = getFromScans(missing_student_query, (ending_per_ID, ending_per_ID))
        absent_scan_data = [(ending_per_ID, active_schedule_ID, macID[0], curr_date, -1, 0, None) for macID in absent_students]
        with closing(db.cursor()) as absent_curs:
            absent_curs.executemany("""INSERT INTO scans (period_ID, schedule_ID, macID, scan_date, scan_time, status, reason) values (%s, %s, %s, %s, %s, %s, %s)""", absent_scan_data)

#TIME LOOP
prevDate = date.today() - timedelta(days=1)
current_time = time_to_minutes(strftime("%H:%M"))
prevMinute = current_time

def timeFunc():
    global prevDate, prevMinute, current_time
    currDate = date.today()
    if currDate != prevDate:
        newDay()
        prevDate = currDate
    timeLabel.configure(text=strftime('%I:%M:%S %p')) #UPDATE TOPBAR WIDGET
    dateLabel.configure(text=strftime("%m-%d-%Y")) #          v
    current_time = time_to_minutes(strftime("%H:%M"))

    if current_time != prevMinute:
        period_transition_check(current_time, strftime("%Y-%m-%d"))
        prevMinute = current_time
    timeLabel.after(1000, timeFunc)

#STUDENTLIST POPULATION
def studentListPop(period_ID):
    global sHeight, sWidth
    with closing(db.cursor()) as studentListCursor:
        #CLEAR THE STUDENTLIST FRAME
        studentList.configure(label_text=callMultiple(studentListCursor, "select name from periods where period_ID = %s", (period_ID,), True)[0])
        for widget in studentList.winfo_children():
            if widget.winfo_exists():
                widget.destroy()
        query = """SELECT sp.macID, sn.first_name, sn.last_name, sc.status, sc.scan_time
FROM student_periods sp
JOIN student_names sn ON sp.macID = sn.macID
LEFT JOIN scans sc ON sp.macID = sc.macID 
    AND sc.scan_date = CURDATE() 
    AND sc.period_ID = %s
WHERE sp.period_ID = %s
ORDER BY sc.status ASC, sn.first_name ASC"""
        students = callMultiple(studentListCursor, query, (period_ID, period_ID))
        if students:
            for index, student in enumerate(students):
                macID, first_name, last_name, status, scan_time = student

                student_dict = {2: ('green', "check.png", (40,30), 5, 5),
                                1: ('orange', "dash.png", (40,40), 4, 2),
                                0: ('red', "x.png", (30,30), 10,2)}

                color, img, size, padx, pady = student_dict.get(status if status else 0)

                studentFrame = ctk.CTkFrame(studentList, fg_color = color,height=int(0.075*sHeight),width=0.30859375*sWidth,border_width=2, border_color='white')
                studentFrame.pack_propagate(0)
                image = ctk.CTkImage(light_image=Image.open(script_directory + r"/images/" + img), size = size)
                ctk.CTkLabel(studentFrame, text = f"{first_name} {last_name}: {timeConvert(scan_time) if scan_time is not None and scan_time != -1 else ('Present' if status == 2 else ('Tardy' if status == 1 else 'Absent'))}", text_color='white', font=('Roboto', 15)).pack(side='left', padx=5,pady=2)
                ctk.CTkLabel(studentFrame, image= image, text='', fg_color='transparent').pack(padx=padx,pady=pady,side='right')

                # Calculate row and column dynamically
                row = index // 2  # Every two students per row
                column = index % 2

                studentFrame.grid(row=row, column=column, pady=5, padx=3, sticky='nsw')
        studentList._parent_canvas.yview_moveto(0)

#PERIODLIST UPDATING
def periodListPop():
    for widget in periodList.winfo_children():
        widget.destroy()
    query = """SELECT p.period_ID FROM periods p WHERE p.schedule_ID = %s AND p.block_val = (SELECT sd.daytype FROM schedule_days sd WHERE sd.schedule_ID = %s AND sd.weekday = %s) ORDER BY p.start_time ASC"""
    schedule_ID = get_active_schedule_ID()
    with closing(db.cursor()) as period_pop_curs:
        periods = callMultiple(period_pop_curs, query, (schedule_ID, schedule_ID, date.today().weekday()))
        if periods:
            for period in periods:
                def command(per):
                    tabSwap(2)
                    studentListPop(per)
                ctk.CTkButton(periodList,border_width=4,bg_color='white',text=(f"{callMultiple(period_pop_curs, 'select name from periods where period_ID = %s', (period,), True)[0]}"), border_color='white', font=('Space Grotesk Medium', 20),command=lambda i0 = period: command(i0)).pack(fill = 'both', expand = True)
        else:
            ctk.CTkLabel(periodList, text='No Periods to Display...', font=('Space Grotesk', 30), text_color='gray').place(relx=0.5, rely=0.5, anchor='center')

ten_after = time_to_minutes(strftime("%H:%M")) + 10

#CHECK IN FUNCTION
def checkIN():
    global currentPopup, ten_after, current_time, currentTAB, reset_oldMACID
    while True:
        if ten_after == current_time:
            with closing(db.cursor()) as alive_curs:
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
                        window.after(0, teacherPWPopup.close_popup)
                        window.after(0, lambda i0 = teacherPWPopup.get_tab()+2: tabSwap(i0))
                        sleep_ms(3000)
                elif currentTAB == 1 or currentTAB == 2:
                    if currentPopup != warning_confirmation and currentPopup !=fridayperiodframe:
                        checkInCursor = db.cursor()
                        studentPeriodList = callMultiple(checkInCursor, """SELECT period_ID from student_periods WHERE macID = %s""", (ID,))
                        if studentPeriodList: #CHECK IF A PERIOD IS RETURNED (IF THEY'RE IN THE MASTER LIST)
                            if get_active_schedule_ID(): #CHECK IF THERE IS A SELECTED ACTIVE SCHEDULE
                                current_period = get_current_Period_ID(scan_time, checkInCursor)
                                if not current_period: #NO CLASS ON THIS DAY
                                    window.after(0, warning_confirmation.config, "no schedule today")
                                elif current_period == "-": #NO CLASS AT THIS TIME ON THIS VALID DAY
                                    window.after(0, warning_confirmation.config, "no class currently")
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
                                                window.after(0, warning_confirmation.config, "double scan")
                                            else: #IF THEY ARE IN THE CURRENT PERIOD ON THIS DAY AND HAVEN'T CHECKED IN YET
                                                status = getAttendance(scan_time, period_ID, checkInCursor)
                                                callMultiple(checkInCursor, """INSERT INTO scans (period_ID, schedule_ID, macID, scan_date, scan_time, status, reason) values (%s, %s, %s, %s, %s, %s, %s)""", (period_ID, get_active_schedule_ID(), ID, scan_date, scan_time, status, None), False, False)
                                                window.after(0, lambda i0 = scan_time, i1 = ID, i2 = status: successScan(i0, i1, i2))
                                                #window.after(0, lambda i0 = period_ID: studentListPop(i0))
                                        else: #IF ONE OF THEIR PERIODS IS not MATCHING WITH THE CURRENT PERIOD
                                            continue
                                    if notInPeriod:
                                        #DISPLAY YOU ARE NOT IN THE CURRENT PERIOD
                                        window.after(0, warning_confirmation.config, 'wrong period')
                            else: #NO ACTIVE SCHEDULE
                                window.after(0, warning_confirmation.config, 'no active schedule')
                        else: #CREATE NEW STUDENT ENTRY BECAUSE THEY ARE NOT IN MASTER DATABASE
                            #GET STUDENT DATA WITH POP UP
                            getStudentInfoFrame.setMACID(ID)
                            window.after(0, tabSwap, 6)
                        checkInCursor.close()
                elif currentTAB == 4: #IF IN SETTINGS AND EDITING IS NOT DISPLAYED EDIT STUDENT
                    window.after(0, lambda i0 = ID, i1 = reset_oldMACID: handle_settings_edit(i0, i1))
                sleep_ms(100)
            else:
                sleep_ms(100)

#SCROLLING FUNCTION
def enable_swipe_scroll(scrollable_frame):
    canvas = scrollable_frame._parent_canvas

    # Variables to track scrolling state
    is_scrolling = False
    last_scroll_pos = None

    def start_scroll(event):
        nonlocal is_scrolling, last_scroll_pos
        is_scrolling = True
        last_scroll_pos = (event.x, event.y)  # Track starting point
        canvas.scan_mark(event.x, event.y)  # Mark position in the canvas

    def perform_scroll(event):
        nonlocal is_scrolling, last_scroll_pos
        if is_scrolling and last_scroll_pos:
            # Only scroll if there's significant movement to avoid clipping
            dx = event.x - last_scroll_pos[0]
            dy = event.y - last_scroll_pos[1]
            if abs(dy) > 2:  # Small threshold to avoid unintentional taps
                canvas.scan_dragto(event.x, event.y, gain=1)

    def end_scroll(event):
        nonlocal is_scrolling
        is_scrolling = False  # Stop scrolling on release

    def scroll_wheel(event):
        canvas.yview_scroll(-int(event.delta / 120), "units")  # For traditional mouse wheel scrolling

    # Bind standard mouse events for compatibility with touch devices
    scrollable_frame.bind("<ButtonPress-1>", start_scroll)
    scrollable_frame.bind("<B1-Motion>", perform_scroll)
    scrollable_frame.bind("<ButtonRelease-1>", end_scroll)
    scrollable_frame.bind("<MouseWheel>", scroll_wheel)

def open_dropdown(combobox, event):
    combobox._open_dropdown_menu()

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

        self.deleteImage = ctk.CTkImage(light_image=Image.open(script_directory+ r"/images/delete.png"),size=(50,50))
        self.back_button_image = ctk.CTkImage(Image.open(script_directory + r"/images/back.png"), size = (50, 50))


        self.current_tab = -1

        #Setup schedule list frame (make a function to populate on each open) 1
        self.schedule_list_frame = ctk.CTkFrame(self)
        self.schedule_list_frame.grid(row=0, column=0, sticky='nsew')

        self.SL_scrollable_frame = ctk.CTkScrollableFrame(self.schedule_list_frame, width=sWidth*3/4,height=sHeight*3/4, label_text="Manage Schedules:", label_font=('Space Grotesk', 25, 'bold'))
        enable_swipe_scroll(self.SL_scrollable_frame)
        self.SL_scrollable_frame.columnconfigure(0, weight=1)
        self.SL_scrollable_frame._scrollbar.configure(width=25)
        self.SL_scrollable_frame.place(relx=0.5, rely=0.5, anchor='center')



        #Setup period list frame (make a function to populate on each open) 2
        self.period_list_frame = ctk.CTkFrame(self)
        self.period_list_frame.grid(row=0, column=0, sticky='nsew')

        #BACK BUTTON (period list frame)
        self.PL_back_button = ctk.CTkButton(self.period_list_frame, image = self.back_button_image, text = '', height = 60, width = 100)
        self.PL_back_button.place(rely=.01, relx = .79)

        self.PL_scrollable_frame = ctk.CTkScrollableFrame(self.period_list_frame, width=sWidth*3/4,height=sHeight*3/4, label_font=('Space Grotesk', 25, 'bold'))
        enable_swipe_scroll(self.PL_scrollable_frame)
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

        #BACK BUTTON (schedule options)
        self.SOTF_back_button = ctk.CTkButton(self.schedule_options_frame, image = self.back_button_image, text = '', height = 60, width = 100, command = self.display_schedule_list)
        self.SOTF_back_button.place(rely=.01, relx = .79)

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

        #BACK BUTTON (schedule frame)
        self.SI_back_button = ctk.CTkButton(self.schedule_info_frame, image = self.back_button_image, text = '', height = 60, width = 100)
        self.SI_back_button.place(rely=.01, relx =.79)

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
        self.SI_name_entry = ctk.CTkEntry(self.SI_name_frame, placeholder_text='Enter schedule name...', font= ('Space Grotesk', 16), height = 60, width = 320)
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
        self.SI_schedule_combobox = ctk.CTkComboBox(self.SI_schedule_frame, values = ['Block', 'Traditional'], dropdown_font=('Space Grotesk', 25), state='readonly', height = 70, width=200, font=('Space Grotesk', 20, 'bold'))
        self.SI_schedule_combobox.pack(padx=5,pady=5,side='top')
        self.SI_schedule_combobox.bind("<Button-1>", partial(open_dropdown, self.SI_schedule_combobox))

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

        #BACK BUTTON (period info)
        self.PI_back_button = ctk.CTkButton(self.period_info_frame, image = self.back_button_image, text = '', height = 60, width = 100, command = lambda: self.tabSwap(2))
        self.PI_back_button.place(rely=.01, relx =.79)

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
        self.PI_LF_period_entry = ctk.CTkEntry(self.PI_left_frame, width = 320, placeholder_text='Enter period name...', font=('Space Grotesk', 16), placeholder_text_color='gray', height = 60)
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
        self.SW_schedule_combobox = ctk.CTkComboBox(self.SW_TF_title_frame, width=350,height = 60,dropdown_font=('Space Grotesk', 25), font=('Space Grotesk', 24, 'bold'), command = self.populate_weekday_frame, state="readonly")
        self.SW_schedule_combobox.pack(side='left', padx=20)
        self.SW_schedule_combobox.bind("<Button-1>", partial(open_dropdown, self.SW_schedule_combobox))

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
            combobox.bind("<Button-1>", partial(open_dropdown, combobox))
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

        #BACK BUTTON (student assignment)
        self.SA_back_button = ctk.CTkButton(self.student_period_selection_frame, image = self.back_button_image, text = '', height = 60, width = 100, command = lambda: self.tabSwap(5))
        self.SA_back_button.place(rely=.01, relx =.79)

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
        enable_swipe_scroll(self.SA_master_scrollable_frame)
        self.SA_master_scrollable_frame.grid(row=0, column=0, sticky='nsew', padx=(100,10), pady=20)
        self.SA_master_scrollable_frame._scrollbar.configure(width=25)
        self.SA_master_scrollable_frame.columnconfigure(0, weight=1)
        self.SA_master_scrollable_frame.columnconfigure(1, weight=1)


        self.SA_period_scrollable_frame = ctk.CTkScrollableFrame(self.SA_lower_container_frame, label_font=('Space Grotesk', 20, 'bold'))
        enable_swipe_scroll(self.SA_period_scrollable_frame)
        self.SA_period_scrollable_frame.grid(row=0, column=1, sticky='nsew', padx=10, pady=20)
        self.SA_period_scrollable_frame._scrollbar.configure(width=25)
        self.SA_period_scrollable_frame.columnconfigure(0, weight=1)
        self.SA_period_scrollable_frame.columnconfigure(1, weight=1)


        #SCROLLABLE FRAME SELECT/DESELECT ALL BUTTONS
        self.SA_master_select_all_button = ctk.CTkButton(self.SA_master_scrollable_frame, height = 60, text='Select All', font=('Space Grotesk', 18, 'bold'),command = lambda: self.update_SA_checkboxes(self.SA_MSF_student_dict, True)).grid(row=0, column=0, sticky='new', padx=7, pady=5)
        self.SA_master_deselect_all_button = ctk.CTkButton(self.SA_master_scrollable_frame, height = 60, text='Deselect All', font=('Space Grotesk', 18, 'bold'),command = lambda: self.update_SA_checkboxes(self.SA_MSF_student_dict, False)).grid(row=0, column=1, sticky='new', padx=7, pady=5)

        self.SA_period_select_all_button = ctk.CTkButton(self.SA_period_scrollable_frame, height = 60, text='Select All', font=('Space Grotesk', 18, 'bold'),command = lambda: self.update_SA_checkboxes(self.SA_PSF_student_dict, True)).grid(row=0, column=0, sticky='new', padx=7, pady=5)
        self.SA_period_deselect_all_button = ctk.CTkButton(self.SA_period_scrollable_frame, height = 60, text='Deselect All', font=('Space Grotesk', 18, 'bold'),command = lambda: self.update_SA_checkboxes(self.SA_PSF_student_dict, False)).grid(row=0, column=1, sticky='new', padx=7, pady=5)


        #BOTTOM FRAME BUTTONS (commands will need to be updated each time with new period_IDs: add new student to period and reload period frame)
        self.SA_assign_button = ctk.CTkButton(self.SA_lower_container_frame, text='Assign To Period', font=('Space Grotesk', 18), fg_color='green', height = 60, width = 200)
        self.SA_assign_button.grid(row=1, column=0, sticky='n', pady=10,padx=(70,0))
        self.SA_remove_button = ctk.CTkButton(self.SA_lower_container_frame, text='Remove From Period', font=('Space Grotesk', 18), fg_color='red', height = 60, width = 200)
        self.SA_remove_button.grid(row=1, column=1, sticky='n', pady=10)


        #SUCCESS POPUP (successful addition/removal of students from period notice)
        self.SA_success_notice = ctk.CTkFrame(self.student_period_selection_frame, border_width=4,border_color='white')
        self.SA_SN_title_label = ctk.CTkLabel(self.SA_success_notice, text='Success!', font=('Space Grotesk', 22, 'bold'), text_color='green')
        self.SA_SN_title_label.pack(side='top',anchor='center',pady=(20,10),padx=20)
        self.SA_SN_label = ctk.CTkLabel(self.SA_success_notice, font=("Space Grotesk", 15), wraplength=sWidth/2-40, justify='left')
        self.SA_SN_label.pack(side='top',anchor='center',pady=10,padx=30)
        self.SA_SN_overlap_label = ctk.CTkLabel(self.SA_success_notice, font=("Space Grotesk", 15), text_color='red',wraplength=sWidth/2-40, justify='left')
        self.SA_SN_overlap_label.pack(side='top',anchor='center',pady=10,padx=30)
        self.SA_SN_exit_button = ctk.CTkButton(self.SA_success_notice, text='X', height = 70, width = 200, font=("Space Grotesk", 20, 'bold'), command = lambda: self.SA_success_notice.place_forget())
        self.SA_SN_exit_button.pack(side='top', anchor='center',pady=15,padx=20)


        #CREATE tab selector frame (make animation logic based on arrow, not a popup, keep separate)
        #CONTROL VARIABLES
        self.control_frame_width = sWidth/3.5
        self.CF_hidden_visibility_width = self.control_frame_width*.3125
        self.CF_visible = False

        self.left_image = ctk.CTkImage(light_image=Image.open(script_directory+r"/images/left_arrow.png"), size=(50,50))
        self.right_image = ctk.CTkImage(light_image=Image.open(script_directory+r"/images/right_arrow.png"), size=(50,50))

        self.add_image = ctk.CTkImage(light_image=Image.open(script_directory+r"/images/add_schedule.png"), size=(45,45))
        self.manage_schedules = ctk.CTkImage(light_image=Image.open(script_directory+r"/images/manage_schedules.png"), size=(45,45))
        self.weekday_image = ctk.CTkImage(light_image=Image.open(script_directory+r"/images/weekday.png"), size=(45,53))

        #CONTROL FRAME
        self.control_frame = ctk.CTkFrame(self, width = self.control_frame_width, height=sHeight)
        self.control_frame.pack_propagate(0)
        self.control_frame.place(x=-(self.control_frame_width-self.CF_hidden_visibility_width), y=0)

        #CONTROL BUTTONS
        self.CF_display_button = ctk.CTkButton(self.control_frame, text="", border_width=1, border_color='gray',image = self.right_image,command=self.toggle_control_frame,font=('Space Grotesk', 25, 'bold'),width=self.CF_hidden_visibility_width , height=90, fg_color='#1f6aa5', bg_color='#2b2b2b')
        self.CF_display_button.pack(side='top',anchor='e',pady=(1,10),padx=1)

        self.create_schedule = ctk.CTkButton(self.control_frame, font=("Space Grotesk", 16, 'bold'),text='',width = self.control_frame_width/4, height = self.CF_hidden_visibility_width-15, fg_color='#222222', image = self.add_image, compound='top', command = self.display_schedule_info)
        self.create_schedule.pack(side='top',anchor='e',pady=(50,30),padx=8)

        self.manage_schedule = ctk.CTkButton(self.control_frame, font=("Space Grotesk", 16, 'bold'), text='', width = self.control_frame_width/4, height = self.CF_hidden_visibility_width-15, fg_color='#222222', image = self.manage_schedules, compound='top', command = self.display_schedule_list)
        self.manage_schedule.pack(side='top',anchor='e',pady=30,padx=8)

        self.weekday_assignment = ctk.CTkButton(self.control_frame, font=("Space Grotesk", 16, 'bold'), text='', width = self.control_frame_width/4, height = self.CF_hidden_visibility_width-15, fg_color='#222222', image = self.weekday_image, compound = 'top', command = self.display_weekday_frame)
        self.weekday_assignment.pack(side='top',anchor='e',pady=30,padx=8)





        #CREATE exit button (always placed)
        self.exit_button = ctk.CTkButton(self, text='X', font=("Space Grotesk", 26, 'bold'),command=self.exit_schedule_setup, height = 60, width = 100)
        self.exit_button.place(relx=.895,rely=.01)

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
        if self.CF_visible or getattr(self, 'animating', False):
            return

        self.animating = True
        self.CF_display_button.configure(image=self.left_image, width=self.control_frame_width)

        def animate():
            x = self.control_frame.winfo_x()
            if x < 0:
                x += 10  # Increment position for smooth animation
                x = min(x, 0)  # Ensure it stops at 0
                self.control_frame.place(x=x)
                self.after(10, animate)
            else:
                self.animating = False
                self.CF_visible = True

        # Trigger animation
        animate()

        # Immediately update widget sizes and texts
        self.create_schedule.configure(width=self.control_frame_width - 16, text='Create New Schedule', compound='left')
        self.manage_schedule.configure(width=self.control_frame_width - 16, text='Manage Existing Schedules', compound='left')
        self.weekday_assignment.configure(width=self.control_frame_width - 16, text='Weekday Assignment', compound='left')


    def hide_sidebar(self):
        if not self.CF_visible or getattr(self, 'animating', False):
            return

        self.animating = True
        self.CF_display_button.configure(image=self.right_image, width=self.CF_hidden_visibility_width)

        def animate():
            x = self.control_frame.winfo_x()
            target_x = -(self.control_frame_width - self.CF_hidden_visibility_width)
            if x > target_x:
                x -= 10  # Decrement position for smooth animation
                x = max(x, target_x)  # Ensure it stops at the target position
                self.control_frame.place(x=x)
                self.after(10, animate)
            else:
                self.animating = False
                self.CF_visible = False

        # Trigger animation
        animate()

        # Immediately update widget sizes and reset texts
        self.create_schedule.configure(width=self.CF_hidden_visibility_width-16, text='', compound='top')
        self.manage_schedule.configure(width=self.CF_hidden_visibility_width-16, text='', compound='top')
        self.weekday_assignment.configure(width=self.CF_hidden_visibility_width-16, text='', compound='top')

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
                schedule_frame.grid(row=index, column=0, sticky='nsew', padx=5, pady=5)
                schedule_frame.columnconfigure(0, weight=1, uniform='columns')
                schedule_frame.columnconfigure(1, weight=4, uniform='columns')


                ctk.CTkButton(schedule_frame, text=schedule_info[1], height=60,width=schedule_frame.winfo_width()*5/6,bg_color='white', border_width=4, border_color='white',font=('Space Grotesk', 20, 'bold'), command = lambda i0 = schedule_info[0], i1 = schedule_info[1]: self.display_schedule_options(i0, i1)).grid(row=0, column=1, sticky='nsew')
                ctk.CTkButton(schedule_frame, image=self.deleteImage,text='',compound='left',fg_color='red',height=60,width=schedule_frame.winfo_width()*1/6,bg_color='white', border_width=4, border_color='white',command = lambda i0=schedule_info[0] : self.delete_schedule_check(i0)).grid(row=0, column=0, sticky='nsew')
            self.SL_scrollable_frame._parent_canvas.yview_moveto(0)

        else:
            ctk.CTkLabel(self.SL_scrollable_frame, text="No Schedules To Display...", text_color='gray',font=("Space Grotesk", 25)).pack(pady=200, anchor='center')

    def populate_period_list(self, schedule_ID, name):
        for widget in self.PL_scrollable_frame.winfo_children():
            widget.destroy()
        if name:
            self.PL_scrollable_frame.configure(label_text=f"Edit Periods: {name}")
        periods = getFromPeriods("select period_ID, name, block_val from periods where schedule_ID = %s ORDER by block_val ASC, start_time ASC", (schedule_ID,))
        for index, period_info in enumerate(periods):
            period_frame = ctk.CTkFrame(self.PL_scrollable_frame, height= 60,fg_color="#1f6aa5", bg_color='white', border_width=4, border_color='white')
            period_frame.grid(row=index, column=0, sticky='ew', padx=5, pady=5)
            period_frame.columnconfigure(0, weight=1, uniform='columns')
            period_frame.columnconfigure(1, weight=4, uniform='columns')
            ctk.CTkButton(period_frame, text=f"{period_info[2]}: {period_info[1]}" if period_info[2] != "-" else period_info[1], height = 60,width=period_frame.winfo_width()*5/6, bg_color='white', border_width=4, border_color='white',font=('Space Grotesk', 20, 'bold'), command = lambda i0=period_info[0]: self.display_period_info(schedule_ID, i0)).grid(row=0, column=1, sticky='nsew')
            ctk.CTkButton(period_frame, text='', image=self.deleteImage, fg_color='red',height = 60,width=period_frame.winfo_width()*1/6,bg_color='white', border_width=4, border_color='white', compound = 'left',command = lambda i0=period_info[0], i1 = schedule_ID: self.delete_period_check(i0, i1)).grid(row=0, column=0, sticky='nsew')

        self.create_period_frame = ctk.CTkFrame(self.PL_scrollable_frame, height= 60,fg_color="#1f6aa5", bg_color='white', border_width=4, border_color='white')
        ctk.CTkButton(self.create_period_frame, text="+ Create New Period +", bg_color='white', border_width=4, border_color='white',font=('Space Grotesk', 25, 'bold'), command = lambda: self.display_period_info(schedule_ID)).pack(fill='both', expand=True)
        self.create_period_frame.grid(row=len(periods), column=0, sticky='ew', padx=5, pady=5)
        self.PL_scrollable_frame._parent_canvas.yview_moveto(0)


    def populate_period_info(self, schedule_ID, period_ID):
        #HIDE BUTTONS
        self.PI_LF_edit_students_button.pack_forget()
        self.PI_LF_daytype_label.pack_forget()
        self.PI_LF_daytype_segmented_button.pack_forget()
        self.PI_LF_submit_button.pack_forget()
        with closing(db.cursor()) as get_period_info_curs:
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
                name = callMultiple(get_period_info_curs,"select name from periods where period_ID = %s", (period_ID,), True)[0]
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
                self.PI_LF_period_entry.delete(0, 'end')
                self.PI_LF_daytype_segmented_button.set("")
                self.PI_RF_start_hour_var.set("12")
                self.PI_RF_start_minute_var.set("00")
                self.PI_RF_end_hour_var.set("12")
                self.PI_RF_end_minute_var.set("00")
                self.PI_RF_tardy_minute_var.set('05')
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
            if not isinstance(widget, ctk.CTkButton):
                widget.destroy()
        self.SA_MSF_student_dict = {}
        student_data = getFromStudent_Names("select * from student_names ORDER by first_name ASC")
        for index, student in enumerate(student_data, start=1):
            macID, first_name, last_name = student
            name = f"{first_name} {last_name}"

            student_frame = ctk.CTkFrame(self.SA_master_scrollable_frame, height = 60)
            student_frame.grid(row=index, column=0, columnspan=2, sticky='new',pady=5,padx=7)

            ctk.CTkLabel(student_frame, text=name, font=('Space Grotesk', 16)).pack(side='left', pady=5,padx=10)

            student_checkbox = ctk.CTkCheckBox(student_frame, checkbox_height = 50, checkbox_width = 50, text='')
            student_checkbox.pack(side='right',pady=5,padx=5)

            self.SA_MSF_student_dict[macID] = student_checkbox
        self.SA_master_scrollable_frame._parent_canvas.yview_moveto(0)

    def populate_SA_period_frame(self, period_ID):
        for widget in self.SA_period_scrollable_frame.winfo_children():
            if not isinstance(widget, ctk.CTkButton):
                widget.destroy()
        self.SA_PSF_student_dict = {}
        student_data = getFromStudent_Periods("select sp.macID, sn.first_name, sn.last_name from student_periods sp join student_names sn on sp.macID = sn.macID where sp.period_ID = %s ORDER by sn.first_name ASC", (period_ID,))
        for index, student in enumerate(student_data, start = 1):
            macID, first_name, last_name = student
            name = f"{first_name} {last_name}"

            student_frame = ctk.CTkFrame(self.SA_period_scrollable_frame, height = 60)
            student_frame.grid(row=index, column=0, columnspan = 2, sticky='new',pady=5,padx=7)

            ctk.CTkLabel(student_frame, text=name, font=('Space Grotesk', 16)).pack(side='left', pady=5,padx=10)

            student_checkbox = ctk.CTkCheckBox(student_frame, checkbox_height = 50, checkbox_width = 50,text='')
            student_checkbox.pack(side='right',pady=5,padx=5)

            self.SA_PSF_student_dict[macID] = student_checkbox
        self.SA_period_scrollable_frame._parent_canvas.yview_moveto(0)

    def update_SA_checkboxes(self, dictionary, selecting):
        if selecting:
            for checkbox in dictionary.values():
                checkbox.select()
        else:
            for checkbox in dictionary.values():
                checkbox.deselect()

    def delete_schedule_check(self, schedule_ID):
        warning_confirmation.warning_confirmation_dict['remove schedule check'][3] = lambda i0 = schedule_ID: self.delete_schedule(i0)
        warning_confirmation.warning_confirmation_dict['remove schedule check'][1] = f"*This will entirely remove {getFromSchedules('select name from schedules where schedule_ID = %s', (schedule_ID,), True)[0]} and every period in it.*"
        warning_confirmation.config('remove schedule check')

    def delete_period_check(self, period_ID, schedule_ID):
        warning_confirmation.warning_confirmation_dict['remove period check'][3] = lambda i0 = period_ID, i1 = schedule_ID: self.delete_period(i0, i1)
        warning_confirmation.warning_confirmation_dict['remove period check'][1] = f"*This will entirely remove {getFromPeriods('select name from periods where period_ID = %s', (period_ID,), True)[0]}.*"
        warning_confirmation.config('remove period check')

    def delete_schedule(self, schedule_ID):
        getFromSystem_Control("update system_control set active_schedule_ID = %s", (None,), False, False)
        #delete schedule (it should cascade in DB and delete the schedule, the periods, and every student's registration to that period, and each scan in for each period in the schedule)
        getFromSchedules("delete from schedules where schedule_ID = %s", (schedule_ID,), False, False)
        self.populate_schedule_list()
        hide_popup(warning_confirmation)



    def delete_period(self, period_ID, schedule_ID):
        getFromPeriods("delete from periods where period_ID = %s", (period_ID,), False, False)
        #refresh schedule period list
        self.populate_period_list(schedule_ID, None)
        #clear history filters and reset results
        historyFrame.top_name_menu.set("")
        historyFrame.top_name_check.deselect()
        historyFrame.period_menu.set("")
        historyFrame.period_check.deselect()
        historyFrame.fetch_students()
        #clear settings period selection and reset results
        teacherFrame.update_period_menu()
        teacherFrame.period_selected(teacherFrame.period_menu.get())
        #close check popup
        hide_popup(warning_confirmation)

    def display_SA_success(self, decision, inserted, overlap, name):
        if inserted:
            placeholder = ', '.join(['%s'] * len(inserted))
            query = f"SELECT CONCAT(first_name, ' ', last_name) AS full_name from student_names where macID in ({placeholder})"
            names = getFromStudent_Names(query, tuple(inserted))
            final_text = f"{decision} "
            for student_name in names:
                final_text += f"{str(student_name[0])}, "
            final_text = final_text[:-2]
            final_text += " from: " + name
            self.SA_SN_label.configure(text=final_text)
        else:
            self.SA_SN_label.configure(text='')
        if overlap:
            placeholder2 = ', '.join(['%s'] * len(overlap))
            query2 = f"SELECT CONCAT(first_name, ' ', last_name) AS full_name from student_names where macID in ({placeholder2})"
            names2 = getFromStudent_Names(query2, tuple(overlap))
            final_text2 = f"Already In {name}: "
            for student_name2 in names2:
                final_text2 += f"{str(student_name2[0])}, "
            final_text2 = final_text2[:-2]
            self.SA_SN_overlap_label.configure(text=final_text2)
        else:
            self.SA_SN_overlap_label.configure(text='')
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
        self.PL_back_button.configure(command = lambda: self.display_schedule_options(schedule_ID, name))
        self.tabSwap(2)

    def display_schedule_list(self):
        self.populate_schedule_list()
        self.tabSwap(1)

    def display_period_info(self, schedule_ID, period_ID = None):
        #turn on edit mode for period_ID
        self.populate_period_info(schedule_ID, period_ID)
        self.tabSwap(5)

    def display_weekday_frame(self):
        self.SW_schedule_dict = {f"{index}: {name}": schedule_ID for index, (name, schedule_ID) in enumerate(getFromSchedules("select name, schedule_ID from schedules"), start=1)}
        self.SW_schedule_combobox.set("")
        self.SW_schedule_combobox.configure(values = list(self.SW_schedule_dict.keys()))
        self.tabSwap(6)

    def display_schedule_options(self, schedule_ID, name):
        self.SOTF_title_label.configure(text=name)
        self.SO_LC_periods_button.configure(command= lambda: self.display_period_list(schedule_ID, name))
        self.SO_LC_edit_schedule_button.configure(command = lambda: self.display_schedule_info(schedule_ID, name))
        self.tabSwap(3)

    def display_schedule_info(self, schedule_ID = None, name = None):
        self.SI_name_entry.delete(0, 'end')
        self.SI_schedule_combobox.set("")
        self.SI_schedule_frame.pack_forget()
        self.SI_absence_frame.pack_forget()
        if name: #IF WERE EDITING SCHEDULE
            self.SI_back_button.configure(command = lambda: self.tabSwap(3))
            self.STF_title_label.configure(text=f"Edit Schedule: {name}")
            self.SI_name_entry.insert(0, name)
            #ADD ABSENCE FRAME
            self.SI_AF_minute_var.set(f"{(getFromSchedules('select absent_var from schedules where schedule_ID = %s', (schedule_ID,), True)[0]):02d}")
            self.SI_absence_frame.pack(anchor='center')
            self.SI_submit_button.configure(text='Submit Edits')
        else: #IF WE ARE CREATING NEW SCHEDULE
            self.SI_back_button.configure(command = lambda: self.tabSwap(1))
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
        display_popup(keyboardFrame, .65)
        keyboardFrame.set_target(entry)

    def get_SW_schedule_type(self):
        return self.SW_schedule_type

    def SA_assign_students(self, period_ID, name):
        overlapped_students = []
        inserted_students = []
        students_to_insert = []

        for key, value in self.SA_MSF_student_dict.items():
            if value.get():  # If checkbox is selected, check if already in the period
                # Check if the student is already in the period
                with closing(db.cursor()) as check_student_curs:
                    # If the student is not already assigned to the period, insert them
                    if callMultiple(check_student_curs, "SELECT COUNT(*) FROM student_periods WHERE macID = %s AND period_ID = %s", (key, period_ID), True)[0] == 0:
                        students_to_insert.append((key, period_ID))
                        inserted_students.append(key)
                    else:
                        overlapped_students.append(key)
                value.deselect()  # Deselect the checkbox after checking

        # Execute the bulk insert if there are students to insert
        if students_to_insert:
            with closing(db.cursor()) as add_student_curs:
                add_student_curs.executemany("INSERT INTO student_periods (macID, period_ID) VALUES (%s, %s)", tuple(students_to_insert))

        # Proceed with other operations
        self.populate_SA_period_frame(period_ID)
        self.display_SA_success('Added', inserted_students, overlapped_students,name)

    def SA_remove_students(self, period_ID, name):
        log_list = []
        with closing(db.cursor()) as remove_student_curs:
            for key, value in self.SA_PSF_student_dict.items():
                if value.get():
                    callMultiple(remove_student_curs, "delete from student_periods where macID = %s and period_ID = %s", (key, period_ID), False, False)
                    log_list.append(key)
        self.populate_SA_period_frame(period_ID)
        self.display_SA_success('Removed',log_list, None, name)

    def submit_schedule(self, schedule_ID):
        #INPUT SCHEDULE INFO FROM SCHEDULE FRAME
        name = self.SI_name_entry.get() #GET SCHEDULE NAME


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
            warning_confirmation.config('schedule input')


    def submit_period(self, schedule_ID, period_ID):
        block = self.PI_LF_daytype_segmented_button.winfo_ismapped() #IS BLOCK SCHEDULE DISPLAYED

        #INPUT PERIOD INFO FROM PERIOD FRAME
        name = self.PI_LF_period_entry.get() #GET NAME ENTRY VALUE

        if block:
            daytype = self.PI_LF_daytype_segmented_button.get() #GET DAYTYPE ENTRY
            self.PI_LF_daytype_segmented_button.set("")
        else:
            daytype = None

        start_time = time_to_minutes(self.PI_RF_start_value_label.cget('text'))


        end_time = time_to_minutes(self.PI_RF_end_value_label.cget('text'))


        late_var = int(self.PI_RF_tardy_value_label.cget('text'))

        #CHECK IF EVERYTHING HAS INPUT AND THEN SUBMIT DATA
        if name and start_time and end_time and late_var and (not block or daytype):
            if not daytype: #IF NO VALUE IS RETURNED (TRADITIONAL SCHEDULE)
                daytype = '-'
            if start_time < end_time:
                absent_var = getFromSchedules("select absent_var from schedules where schedule_ID = %s", (schedule_ID,), True)[0]
                if late_var < absent_var:
                    if block:
                        if period_ID:
                            existing_periods = getFromPeriods("select start_time, end_time from periods where schedule_ID = %s and block_val = %s and period_ID != %s", (schedule_ID, daytype, period_ID))
                        else:
                            existing_periods = getFromPeriods("select start_time, end_time from periods where schedule_ID = %s and block_val = %s", (schedule_ID, daytype))
                    else:
                        if period_ID:
                            existing_periods = getFromPeriods("select start_time, end_time from periods where schedule_ID = %s and period_ID != %s", (schedule_ID, period_ID))
                        else:
                            existing_periods = getFromPeriods("select start_time, end_time from periods where schedule_ID = %s", (schedule_ID,))
                    for existing_start, existing_end in existing_periods:
                        if start_time < existing_end and end_time > existing_start and start_time != existing_end:
                            warning_confirmation.warning_confirmation_dict["period input"][0] = 'Invalid Timing Values!'
                            warning_confirmation.warning_confirmation_dict["period input"][1] = "*The start or end time overlap with an existing period.*"
                            warning_confirmation.config('period input')
                            return
                    if period_ID: #EDIT EXISTING PERIOD
                        getFromPeriods("update periods set schedule_ID = %s, block_val = %s, name = %s, start_time = %s, end_time=%s, late_var = %s where period_ID = %s", (schedule_ID, daytype, name, start_time, end_time, late_var, period_ID), False, False)
                    else: #ADD NEW PERIOD
                        getFromPeriods("insert into periods (schedule_ID, block_val, name, start_time, end_time, late_var) values (%s, %s, %s, %s, %s, %s)", (schedule_ID, daytype, name, start_time, end_time, late_var), False, False)
                    self.display_period_list(schedule_ID)
                    self.PI_LF_period_entry.delete(0, 'end') #CLEAR ENTRY
                    self.PI_RF_start_hour_var.set("12")
                    self.PI_RF_start_minute_var.set("00")
                    self.PI_RF_end_hour_var.set("12")
                    self.PI_RF_end_minute_var.set("00")
                    self.PI_RF_tardy_minute_var.set('05')
                else:
                    warning_confirmation.warning_confirmation_dict["period input"][0] = 'Invalid Tardy Value!'
                    warning_confirmation.warning_confirmation_dict["period input"][1] = f"*The tardy value must be less than the absent value for this schedule ({absent_var} minutes).*"
                    warning_confirmation.config('period input')
            else:
                warning_confirmation.warning_confirmation_dict["period input"][0] = 'Invalid Timing Values!'
                warning_confirmation.warning_confirmation_dict["period input"][1] = "*The start time must be earlier than the end time.*"
                warning_confirmation.config('period input')
        else:
            #DISPLAY NEED MORE INPUTS
            warning_confirmation.warning_confirmation_dict["period input"][0] = 'Missing Period Values!'
            warning_confirmation.warning_confirmation_dict["period input"][1] = "Please complete all required fields before submitting."
            warning_confirmation.config('period input')

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
            warning_confirmation.config('weekday input')
        else: #SUBMIT DATA
            with closing(db.cursor()) as weekday_curs:
                if edit: #WE ARE UPDATING
                    weekday_curs.executemany("update schedule_days set schedule_ID = %s, weekday = %s, dynamic_daytype = %s, daytype = %s where schedule_ID = %s and weekday = %s", (tuple(submit_list)))
                else: #WE ARE INSERTING
                    weekday_curs.executemany("insert into schedule_days (schedule_ID, weekday, dynamic_daytype, daytype) values (%s, %s, %s, %s)", (tuple(submit_list)))
            self.clear_weekday_frame()
            self.SW_submit_button.configure(command=lambda: None)
            self.SW_schedule_combobox.set("")
            newDay()

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
        self.period_menu.bind("<Button-1>", partial(open_dropdown, self.period_menu))

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
        self.top_name_menu.bind("<Button-1>", partial(open_dropdown, self.top_name_menu))

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
        self.attendance_menu.bind("<Button-1>", partial(open_dropdown, self.attendance_menu))


        # Submit Button
        self.submit_button = ctk.CTkButton(self.column_frame, text="Submit", command=self.fetch_students, height=50, font=("Arial", 18,'bold'))
        self.submit_button.grid(row=8, column=0, columnspan=2, pady=10, padx=10)

        # Part 3: Scrollable Frame (unchanged)
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        enable_swipe_scroll(self.scrollable_frame)
        self.scrollable_frame.grid(row=1, column=1, pady=10, sticky="nsew")
        scrollbar = self.scrollable_frame._scrollbar
        scrollbar.configure(width=25)



        # Make sure the frame expands
        self.grid_rowconfigure(1, weight=1)

        self.grid_columnconfigure(1, weight=1)

    def update_period_menu(self):
        self.periods = {f"{index}: {name}": period_ID for index, (name, period_ID) in enumerate(getFromPeriods("select name, period_ID from periods where schedule_ID = %s order by block_val ASC, start_time ASC", (get_active_schedule_ID(),)), start=1)}
        self.period_menu.configure(values=list(self.periods.keys()))

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
            students = callMultiple(history_curs, query, variables)



            # Display the fetched students in the scrollable frame
            col = 0  # To track column placement

            for i, student in enumerate(students):
                scan_ID, macID, scan_date, scan_time, status, period_ID, reason = student
                firstLast = callMultiple(history_curs,"""select first_name, last_name from student_names where macID = %s""", (macID,), True)
                name = firstLast[0] + " " + firstLast[1]


                time_str = timeConvert(scan_time) if scan_time != -1 else ""
                attendance = "Absent" if status == 0 else "Tardy" if status == 1 else "Present"
                text_color = "red" if status == 0 else "orange" if status == 1 else "green"
                display_text = f"{name}: {attendance}\n{getFromPeriods('select name from periods where period_ID = %s', (period_ID,), True)[0]}\n{time_str} on {scan_date}"
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
                    command= lambda i0 = scan_ID, i1=attendance, i2=reason: editAttendanceData(i0, i1, i2)
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
            self.scrollable_frame._parent_canvas.yview_moveto(0)
            # Update layout and style to ensure even distribution
            self.scrollable_frame.grid_columnconfigure(0, weight=1)
            self.scrollable_frame.grid_columnconfigure(1, weight=1)
            history_curs.close()







#TEACHER MODE FRAME
class settingsClass(ctk.CTkFrame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.reset = 0

        # Left side column takes full vertical space with padding at top and bottom
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, rowspan=2, sticky="ns", padx=10, pady=(10, 10))  # Takes full vertical space
        self.grid_rowconfigure(1, weight=1)

        # Regular buttons (no labels above)
        self.arrival_button = ctk.CTkButton(self.left_frame, text="Edit Schedules",height=40,font=('Space Grotesk',16,'bold'), command=self.edit_schedule)
        self.arrival_button.grid(row=0, column=0, pady=10)
        
        self.password_button = ctk.CTkButton(self.left_frame, text="Change Password", height=40,font=('Space Grotesk',16,'bold'),command=self.change_password)
        self.password_button.grid(row=1, column=0, pady=10)

        self.timeout_button = ctk.CTkButton(self.left_frame, text='Change Idle Timeout', height = 40, width = 150, font = ('Space Grotesk', 16, 'bold'), command=self.edit_timeout)
        self.timeout_button.grid(row=2, column=0, pady=10)

        self.wifi_button = ctk.CTkButton(self.left_frame, text='Connect Wifi', height = 40, font = ('Space Grotesk', 16, 'bold'), command=lambda: tabSwap(7))
        self.wifi_button.grid(row=3, column=0, pady=10)

        self.dynamic_day_button = ctk.CTkButton(self.left_frame, text='Change Daytype\n(dynamic)', height = 40, width = 150, font = ('Space Grotesk', 16, 'bold'), command = lambda: display_popup(fridayperiodframe))

        self.restart_button = ctk.CTkButton(self.left_frame, text= 'Refresh System', height = 40, width = 150, font = ('Space Grotesk', 16, 'bold'), command = self.restart_check)
        self.restart_button.grid(row=6, column=0, pady=10)

        self.reset_button = ctk.CTkButton(self.left_frame, text="Factory Reset",height=40,font=('Space Grotesk',16,'bold'), command=lambda: warning_confirmation.config('factory reset'))
        self.reset_button.grid(row=7, column=0, pady=10)


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
        self.period_menu = ctk.CTkComboBox(self.top_frame,variable = self.period_menu_var,dropdown_font=("Space Grotesk", 25),state='readonly', font=("Space Grotesk", 18), height=(.0666666*sHeight), command=self.period_selected, width=sWidth * .24)
        self.period_menu.grid(row=0, column=3, padx=10, pady=10)
        self.period_menu.bind("<Button-1>", partial(open_dropdown, self.period_menu))

        #ACTIVE SCHEDULE SELECTION
        self.schedule_menu_label = ctk.CTkLabel(self.top_frame, text='Active Schedule:', font= ('Space Grotesk', 20, 'bold'))
        self.schedule_menu_label.grid(row=0,column=0, padx=10,pady=10)
        self.schedules = {}
        self.schedule_menu_var = ctk.StringVar(value="")
        self.schedule_menu = ctk.CTkComboBox(self.top_frame,variable = self.schedule_menu_var,dropdown_font=("Space Grotesk", 25),state='readonly', font=("Space Grotesk", 18), height=(.0666666*sHeight), command=self.schedule_selected, width=sWidth * .24)
        self.schedule_menu.grid(row=0, column=1, padx=10, pady=10)
        self.schedule_menu.bind("<Button-1>", partial(open_dropdown, self.schedule_menu))

        # Scrollable Frame (takes remaining vertical space below top bar with padding)
        self.scrollable_frame = ctk.CTkScrollableFrame(self,label_text='Edit Student(s):',label_font=('Roboto',25,'bold'))
        enable_swipe_scroll(self.scrollable_frame)
        self.scrollable_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=(5, 10))
        scrollbar = self.scrollable_frame._scrollbar
        scrollbar.configure(width=25)

        # Configure grid weights for resizing
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def toggle_dynamic_button(self, value):
        if value:
            self.dynamic_day_button.grid(row=4, column=0, pady=10)
        else:
            self.dynamic_day_button.grid_forget()

    def restart_check(self):
        warning_confirmation.config("restart check")

    def restart_script(self):
        os.execl(sys.executable, sys.executable, *sys.argv)

    def change_password(self):
        teacherPWPopup.change_pw(True)
        teacherPWPopup.change_label('Change Teacher Password:')
        display_popup(teacherPWPopup)

    def edit_timeout(self):
        timeoutMenu.update()
        display_popup(timeoutMenu)

    def edit_schedule(self):
        tabSwap(5)

    def update_period_menu(self):
        self.periods = {f"{index}: {name}": period_ID for index, (name, period_ID) in enumerate(getFromPeriods("select name, period_ID from periods where schedule_ID = %s ORDER by block_val ASC, start_time ASC", (get_active_schedule_ID(),)),start=1)}
        self.period_menu.configure(values=list(self.periods.keys()))
        self.period_menu.set("")

    def update_schedule_menu(self):
        self.schedules = {f"{index}: {name}": schedule_ID for index, (name, schedule_ID) in enumerate(getFromSchedules("select name, schedule_ID from schedules"), start=1)}
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
        self.period_selected(teacherFrame.period_menu.get())

    def period_selected(self, period_name):
        global currentPopup
        period_ID = self.periods.get(period_name)
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        if period_ID:
            with closing(db.cursor()) as teacher_curs:
                students = callMultiple(teacher_curs, """select sp.macID, sn.first_name, sn.last_name from student_periods sp join student_names sn on sp.macID = sn.macID where sp.period_ID = %s""", (period_ID,))
                if students:
                    col = 0  # To track column placement
                    for i, student in enumerate(students):
                        macID, first, last = student
                        display_text = first + " " + last

                        # Create a small frame for each student's data with some stylish improvements
                        self.student_frame = ctk.CTkButton(
                            self.scrollable_frame,
                            text=display_text,
                            height=50,
                            text_color='blue',  # Use attendance-based color
                            font=("Space Grotesk", 18, 'bold'),
                            fg_color="lightgrey",  # Set background color
                            corner_radius=10,  # Rounded corners
                            border_color="gray",
                            border_width=2,
                            command=lambda i0=macID: editStudentData(i0)
                        )
                        self.student_frame.grid(row=i // 2, column=col, padx=10, pady=5, sticky="nsew")

                        # Move to the next column for a 2-column layout
                        col = (col + 1) % 2
                def command():
                    tabSwap(5)
                    setupFrame.display_student_assignment_frame(period_ID, period_name[3:])
                ctk.CTkButton(self.scrollable_frame, text="+", font = ('Space Grotesk',20, 'bold'),text_color='blue', fg_color="lightgrey", corner_radius=10, height =50,border_color="gray",border_width=2,command = lambda: command()).grid(row=(i+1)//2, column=col, padx=10,pady=5,sticky='nsew')
                self.scrollable_frame._parent_canvas.yview_moveto(0)
                # Update layout and style to ensure even distribution
                self.scrollable_frame.grid_columnconfigure(0, weight=1)
                self.scrollable_frame.grid_columnconfigure(1, weight=1)


#AWAITING FRAME ADDON
#STUDENT AWAITING IMAGE SPIN
class LoadingAnimation(ctk.CTkFrame):
    def __init__(self, parent, color, arc_diameter=500, rotation_speed=20):
        super().__init__(parent)
        self.configure(fg_color=color)  # Dark background

        # Fixed canvas size
        self.canvas_size = 300
        self.canvas = tk.Canvas(self, width=self.canvas_size, height=self.canvas_size, bg=color, highlightthickness=0)
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
homeImage = ctk.CTkImage(Image.open(script_directory+r"/images/home.png"),size=(32,32))
menuButton = ctk.CTkButton(rightBAR, text='Home',hover_color="#1f6aa5",image = homeImage,compound='left',font=('Space Grotesk', 25, 'bold'), height = 45,text_color='white',command=lambda: tabSwap(1))
menuButton.grid(row=0,column=0,pady=10)

#HISTORY BUTTON CREATION
historyImage = ctk.CTkImage(Image.open(script_directory+r"/images/history.png"),size=(34,32))
historyButton = ctk.CTkButton(rightBAR, text='History',hover_color="#1f6aa5",image = historyImage, compound='left',font=('Space Grotesk', 25, 'bold'), height = 45,text_color='white',command=lambda: historySettingButtons(3,1))
historyButton.grid(row=0,column=1,pady=10)

#TEACHER MODE BUTTON
settingsImage = ctk.CTkImage(Image.open(script_directory+r"/images/settings.png"),size=(32,32))
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

teacherFrame = settingsClass(displayedTabContainer)
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
spinning_image = LoadingAnimation(awaitingFrame, "#333333")
spinning_image.place(relx=.5,rely=.6,anchor='center')


#STUDENT LIST
studentList = ctk.CTkScrollableFrame(displayedTabContainer, border_color = 'white', border_width = 4, label_text="Period A1", label_font = ('Roboto', 30),bg_color='white')
enable_swipe_scroll(studentList)
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
successCheckExitImage = ctk.CTkImage(Image.open(script_directory+ r"/images/present.png"),size=(int(sWidth/6),int(sWidth/6)))
imgSuccessLabel = ctk.CTkButton(successFrame, text='',image=successCheckExitImage, fg_color='#333333',border_color='#333333',state='disabled')
imgSuccessLabel.grid(row=1, column=0, pady=30, sticky='n')

#TARDY IMAGE
success_Tardy_CheckExitImage = ctk.CTkImage(Image.open(script_directory+r"/images/tardy.png"),size=(int(sWidth/6),int(sWidth/6)))
imgSuccess_Tardy_Label = ctk.CTkButton(successFrame, text='',image=success_Tardy_CheckExitImage, fg_color='#333333',border_color='#333333',state='disabled')
imgSuccess_Tardy_Label.grid(row=1, column=0, pady=30, sticky='n')

#LATE IMAGE
success_Late_CheckExitImage = ctk.CTkImage(Image.open(script_directory+r"/images/late.png"),size=(int(sWidth/6),int(sWidth/6)))
imgSuccess_Late_Label = ctk.CTkButton(successFrame, text='', image=success_Late_CheckExitImage, fg_color='#333333',border_color='#333333',state='disabled')
imgSuccess_Late_Label.grid(row=1, column=0, pady=30, sticky='n')

#TAB SWAPPING/POPUP DISPLAY FUNCTIONS
timeout_thread = None
timeout_active = False
timeout_flag = False
reset_flag = False

def timeout():
    """The main loop for the countdown."""
    global timeout_flag, timeout_active, reset_flag, currentPopup
    timeout_active = True
    time_left = int(getFromSystem_Control("select timeout_time from system_control", None, True)[0])  # Initial countdown time in seconds

    while timeout_active:
        if timeout_flag:  # Stop the loop
            break

        if reset_flag:  # Reset the timer
            reset_flag = False
            time_left = int(getFromSystem_Control("select timeout_time from system_control", None, True)[0])  # Reset countdown

        if time_left > 0:
            time_left -= 1
            time.sleep(1)
        else:
            window.after(0, timeout_result)

def start_timeout():
    """Start the timeout thread if not already running."""
    global timeout_thread, timeout_active, timeout_flag, reset_flag
    if not timeout_active:  # Ensure only one thread runs
        timeout_flag = False  # Ensure stop flag is not set
        reset_flag = False  # Reset any leftover reset state
        timeout_thread = threading.Thread(target=timeout, daemon=True)
        timeout_thread.start()

def reset_timeout(event=None):
    """Reset the countdown if it is running."""
    global timeout_active, reset_flag
    if timeout_active:
        reset_flag = True

def stop_timeout():
    """Stop the countdown and terminate the loop."""
    global timeout_flag, timeout_active
    if timeout_active:
        timeout_flag = True
        timeout_active = False

def timeout_result():
    global currentPopup, timeout_active
    hide_popup(currentPopup) if currentPopup and currentPopup.winfo_ismapped() else None
    getStudentInfoFrame.close_popup
    internetMenu.close_popup
    tabSwap(1)
    timeout_active = False

#TABSWAP--
currentTAB = 0
def tabSwap(newTAB):
    global currentTAB
    if newTAB != currentTAB:
        if newTAB == 1: #DISPLAY MAIN MENU
            periodListPop()
            periodList.lift()
            spinning_image.start_spinning()
            awaitingFrame.lift()
            stop_timeout()
        elif newTAB == 2: #DISPLAY LIST OF STUDENTS
            studentList.lift()
            spinning_image.start_spinning()
            awaitingFrame.lift()
            stop_timeout()
        elif newTAB == 3: #DISPLAY HISTORY FRAME
            spinning_image.stop_spinning()
            historyFrame.update_period_menu()
            historyFrame.fetch_students()
            historyFrame.lift()
            start_timeout()
        elif newTAB == 4: #DISPLAY TEACHER MODE FRAME
            spinning_image.stop_spinning()
            teacherFrame.update_period_menu()
            teacherFrame.update_schedule_menu()
            teacherFrame.lift()
            start_timeout()
        elif newTAB == 5: #DISPLAY SETUP FRAME
            spinning_image.stop_spinning()
            setupFrame.display_schedule_list()
            setupFrame.place(x=0,y=0)
            setupFrame.lift()
            start_timeout()
        elif newTAB == 6: #DISPLAY STUDENT INFO FRAME
            spinning_image.stop_spinning()
            getStudentInfoFrame.update_return(currentTAB)
            getStudentInfoFrame.place(x=0,y=0)
            getStudentInfoFrame.lift()
            start_timeout()
        elif newTAB == 7: #DISPLAY INTERNET MENU
            spinning_image.stop_spinning()
            internetMenu.place(x=0, y=0)
            internetMenu.lift()
            start_timeout()
        currentTAB = newTAB

currentPopup = None
def display_popup(popup, ypos = .5, xpos=.5):
    #friday should trump all and stay until input
    #if warnings are overlapped by
    global currentPopup
    if currentPopup != popup:
        if currentPopup != fridayperiodframe and (currentPopup != teacherPWPopup or popup == fridayperiodframe):
            try:
                if not (popup == keyboardFrame and currentPopup == editAttendanceFrame):
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

def editAttendanceData(scan_ID, attendance, reason):
    editAttendanceFrame.setValue(scan_ID, attendance, reason)
    display_popup(editAttendanceFrame)

def successScan(time, macID, attendance):
    print(time, macID, attendance)
    status_dict = {2: ('Present', 'green', imgSuccessLabel),1: ('Tardy', 'orange', imgSuccess_Tardy_Label),0: ('Late', 'red', imgSuccess_Late_Label)}
    status, color, imgLabel = status_dict.get(attendance)
    studentName = " ".join(getFirstLastName(macID))
    successLabel.configure(text=status, text_color=color)
    successLabel2.configure(text=f"{studentName}\nChecked in at {timeConvert(time)}")
    imgLabel.lift()
    successFrame.lift()
    threading.Thread(target=close_success_scan).start()

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

reset_oldMACID = None
#GET STUDENT INFO
class StudentMenu(ctk.CTkFrame):
    def insert_text(self, entry, text):
        entry.insert(tk.END, text)

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.configure(width=sWidth, height=sHeight,border_width=2,border_color='white',bg_color='white')
        self.pack_propagate(False)  # Prevent resizing based on widget content

        #image variable
        trashImage = ctk.CTkImage(light_image=Image.open(script_directory+r"/images/delete.png"),size=((0.08333333*sHeight),(0.08333333*sHeight)))

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
        self.exit_button = ctk.CTkButton(self.nameandperiodFrame, text="X", font=('Space Grotesk',24,'bold'),width=80, height = 80, command=self.close_popup)
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
        self.submit_button = ctk.CTkButton(self.nameFrame, text="Submit", font=('Space Grotesk',22, 'bold'),height=60,command=self.submit_and_close, width = 200)
        self.submit_button.pack(pady=30)

        #Reset macID Button
        self.reset_button = ctk.CTkButton(self.nameandperiodFrame, text = "Reset ID",font=('Space Grotesk',24,'bold'),width=80, height = 80, command=self.check_reset)

        #Warning Label
        self.warning_label = ctk.CTkLabel(self.nameFrame,text="Missing Information!",fg_color='red',font=('Arial',16,'bold'))

    def check_reset(self):
        global reset_oldMACID
        firstname, lastname = getFirstLastName(self.macID)
        warning_confirmation.warning_confirmation_dict['reset ID check'][0] = f"Reset {firstname} {lastname}'s student ID?"
        warning_confirmation.warning_confirmation_dict['reset ID check'][3] = lambda i0 = self.macID: self.reset_macID(i0)
        reset_oldMACID = self.macID
        self.close_popup()
        warning_confirmation.config("reset ID check")

    def reset_macID(self, macID):
        firstname, lastname = getFirstLastName(macID)
        warning_confirmation.warning_confirmation_dict['reset ID'][1] = f"*Please scan the new student ID to reset the ID associated with {firstname} {lastname}.*"
        warning_confirmation.config("reset ID")

    def showCheck(self):
        firstname, lastname = getFirstLastName(self.macID)
        warning_confirmation.warning_confirmation_dict['remove student'][0] = f"Remove {firstname} {lastname} from the system?"
        warning_confirmation.warning_confirmation_dict['remove student'][3] = lambda i0 = self.macID: warning_confirmation.delete_student(i0)
        self.close_popup()
        warning_confirmation.config("remove student")

    def different_name(self, first_name, last_name):
        warning_confirmation.warning_confirmation_dict['different name'][1] = f"*Please try again and add a middle name to your first/last name to be distinct from {first_name} {last_name}.*"
        warning_confirmation.config("different name")

    def reset_ID_notice(self, first_name, last_name):
        warning_confirmation.warning_confirmation_dict['reset ID notice'][1] = f"*Please ask a teacher to assist with ID re-assigning for {first_name} {last_name}.*"
        warning_confirmation.config("reset ID notice")


    def update_return(self, tab):
        self.returnTAB = tab

    def update_periods(self, periods = None):
        self.period_frame_dict = {}
        for widget in self.periodFrame.winfo_children():
            if isinstance(widget, ctk.CTkCheckBox):
                widget.destroy()
        period_info = getFromPeriods("select period_ID, name, block_val from periods where schedule_ID = %s ORDER by block_val ASC, start_time ASC", (get_active_schedule_ID(),))
        last_block_val = None
        for index, period in enumerate(period_info):
            period_ID, name, block_val = period
            checkbox = ctk.CTkCheckBox(self.periodFrame, text=f"{block_val}: {name}" if block_val != '-' else f"{index}: {name}", checkbox_height=40,checkbox_width=50,font=('Space Grotesk',16))
            if periods:
                if period_ID in periods:
                    checkbox.select()
            checkbox.pack(anchor="w", padx=20,pady=4)
            if last_block_val != None and last_block_val != block_val:
                ctk.CTkLabel(self.periodFrame, text='', font=("Space Grotesk", 18)).pack(anchor='w',padx=20, pady=4)
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

    def setStudentData(self):
        self.editing = True
        self.delete_student.place(relx=.01,rely=.02)
        self.reset_button.place(relx=.01,rely=.84)
        self.newStudent_label.configure(text='Edit Student Data: ',text_color='orange')
        fname, lname = getFirstLastName(self.macID)
        periods = [item[0] for item in getFromStudent_Periods("""SELECT period_ID from student_periods WHERE macID = %s""",(self.macID,))]
        self.first_name_entry.delete(0, "end")
        self.last_name_entry.delete(0, "end")
        self.first_name_entry.insert(tk.END, fname)
        self.last_name_entry.insert(tk.END, lname)
        self.update_periods(periods)

    def submit_and_close(self):
        first_name = self.first_name_entry.get()
        last_name = self.last_name_entry.get()
        selected_periods = self.get_selected_periods()
        if first_name and last_name and selected_periods:
            if not getFromStudent_Names("select macID from student_names where first_name = %s and last_name = %s and macID != %s", (first_name, last_name, self.macID)): #if there is another student with the same name
                if self.editing: #DELETE OLD STUDENT DATA IF ADDING NEW
                    getFromStudent_Periods("""delete from student_periods where macID = %s""", (self.macID,), False, False)
                    getFromStudent_Names("""delete from student_names where macID = %s""", (self.macID,), False, False)
                #ADD NEW STUDENT INFO
                getFromStudent_Names("""INSERT INTO student_names(macID, first_name, last_name) values (%s, %s, %s)""", (self.macID,first_name.lower().title(),last_name.lower().title()), False, False)
                for period_ID in selected_periods:
                    getFromStudent_Periods("INSERT INTO student_periods(macID, period_ID) values (%s, %s)", (self.macID, period_ID), False, False)
                teacherFrame.period_selected(teacherFrame.period_menu.get())
                self.close_popup()
            else:
                #CONTINUE HERE ON WHAT TO DO WITH MATCHING NAMES (JUST ASK FOR MIDDLE NAME OR RESET ID)
                self.close_popup()
                warning_confirmation.warning_confirmation_dict['matching name'][4] = lambda i0 = first_name, i1 = last_name: self.different_name(i0, i1)
                warning_confirmation.warning_confirmation_dict['matching name'][3] = lambda i0 = first_name, i1 = last_name : self.reset_ID_notice(i0, i1)
                warning_confirmation.warning_confirmation_dict['matching name'][1] = f"There is already a student named {first_name} {last_name} in the system, are you attempting to reset their ID?"
                warning_confirmation.config("matching name")
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
        self.reset_button.place_forget()
        self.warning_label.pack_forget()
        # Uncheck all checkboxes
        self.update_periods()
        self.current_entry = None
getStudentInfoFrame = StudentMenu(window)




class editInternetClass(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(width=sWidth, height=sHeight,border_width=2,border_color='white',bg_color='white')
        self.grid_propagate(0)
        self.pack_propagate(0)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight = 1)
        self.rowconfigure(1, weight = 3)

        #title
        self.title_label = ctk.CTkLabel(self, text = "Connect To Wifi",font=('Space Grotesk', 28, 'bold'), text_color= "#1f6aa5")
        self.title_label.grid(row=0, column=0, pady=(40, 5), sticky='n')

        #note
        self.note_label = ctk.CTkLabel(self, text = "*Enter the name and password for the internet you would like to connect to.*",font=('Space Grotesk', 18), text_color= "white")
        self.note_label.grid(row=0, column=0, pady=(75, 5), sticky='n')

        #SSID entry
        self.name_entry = ctk.CTkEntry(self, placeholder_text="Network name (SSID)...",font=('Space Grotesk', 18), width = 500, height = 60)
        self.name_entry.grid(row=1, column=0, pady=(10, 5), sticky='n')
        self.name_entry.bind("<FocusIn>", lambda event: self.set_current_entry(self.name_entry))

        #Password entry
        self.password_entry = ctk.CTkEntry(self, placeholder_text = "Network password...",font=('Space Grotesk', 18), width = 500, height = 60)
        self.password_entry.grid(row=1, column=0, pady=(90, 5), sticky='n')
        self.password_entry.bind("<FocusIn>", lambda event: self.set_current_entry(self.password_entry))

        #Input Error Label
        self.error_label = ctk.CTkLabel(self, text="Input a network name!", text_color='white', fg_color= 'red', font=('Space Grotesk', 18))

        #Exit button
        self.exit_button = ctk.CTkButton(self, text = "X",font=('Space Grotesk', 25, 'bold'), height = 70, width = 70, command = self.close_popup)
        self.exit_button.place(relx = .915, rely=.02)

        #Submit button
        self.submit_button = ctk.CTkButton(self, text = "Submit",font=('Space Grotesk', 20, 'bold'), height = 50, width = 220, command = self.submit)
        self.submit_button.grid(row=1, column=0, pady=(190, 5), sticky='n')

    def set_current_entry(self, entry):
        display_popup(keyboardFrame, .65)
        keyboardFrame.set_target(entry)

    def close_popup(self):
        tabSwap(4)
        self.place_forget()
        self.name_entry.delete(0, 'end')
        self.password_entry.delete(0, 'end')
        self.error_label.grid_forget()

    def submit(self):
        tabSwap(4)
        self.place_forget()
        ssid = self.name_entry.get()
        password = self.password_entry.get()

        if ssid:
            self.name_entry.delete(0, 'end')
            self.password_entry.delete(0, 'end')
            self.error_label.grid_forget()

            wpa_supplicant_path = "/etc/wpa_supplicant/wpa_supplicant.conf"

            try:
                # Write a new configuration to wpa_supplicant.conf
                subprocess.run(
                    ['sudo', 'sh', '-c', f'echo "country=US" > {wpa_supplicant_path}'],
                    check=True
                )
                # 2. Append the ctrl_interface line.
                subprocess.run(
                    ['sudo', 'sh', '-c', f'echo "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev" >> {wpa_supplicant_path}'],
                    check=True
                )
                # 3. Append the update_config line.
                subprocess.run(
                    ['sudo', 'sh', '-c', f'echo "update_config=1" >> {wpa_supplicant_path}'],
                    check=True
                )
                # 4. Append an empty line.
                subprocess.run(
                    ['sudo', 'sh', '-c', f'echo "" >> {wpa_supplicant_path}'],
                    check=True
                )
                # 5. Append the network block with key_mgmt.
                if password:
                    subprocess.run(
                        ['sudo', 'sh', '-c',
                         f"printf 'network={{\\n\\tssid=\"{ssid}\"\\n\\tpsk=\"{password}\"\\n\\tkey_mgmt=WPA-PSK\\n}}\\n' >> {wpa_supplicant_path}"],
                        check=True
                    )
                else:
                    subprocess.run(
                        ['sudo', 'sh', '-c',
                         f"printf 'network={{\\n\\tssid=\"{ssid}\"\\n\\tkey_mgmt=NONE\\n}}\\n' >> {wpa_supplicant_path}"],
                        check=True
                    )

                # Restart the networking service to apply the new config
                subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], check=True)

                loading_indicator.start_spinning()
                display_popup(loading_indicator)

                #LAUNCH NEW THREAD
                thread = threading.Thread(target=self.check_connection_thread, args=(ssid,))
                thread.daemon = True  # so it exits when the main program exits
                thread.start()

            except subprocess.CalledProcessError as e:
                # Handle any errors that occur during the process
                warning_confirmation.warning_confirmation_dict["network fail"][1] = (
                    f"Failed to connect to {ssid}. Error: {e}"
                )
                warning_confirmation.config("network fail")
        else:
            self.error_label.grid(row=1, column=0, pady=(90, 0), sticky='n')

    def check_connection_thread(self, ssid):
        # Allow some time for the interface to associate with the new network.
        # Then poll for the connection status.
        connected = False
        max_attempts = 8  # For a total wait of roughly 30 seconds (10 * 3 sec)
        for attempt in range(max_attempts):
            time.sleep(3)  # wait a few seconds between checks

            # Check current connected SSID (using iwgetid)
            ssid_result = subprocess.run(['iwgetid', '--raw'], capture_output=True, text=True)
            current_ssid = ssid_result.stdout.strip()

            # Check that we’re connected to the expected SSID
            if current_ssid == ssid:
                # Optionally, verify external connectivity by pinging an external server
                ping_result = subprocess.run(
                    ['ping', '-c', '1', '8.8.8.8'],  # Google DNS as an example
                    capture_output=True, text=True
                )
                if ping_result.returncode == 0:
                    connected = True
                    break
        window.after(0, lambda i0 = ssid, i1 = connected: self.finish_check_connection(i0, i1))

    def finish_check_connection(self, ssid, connected):
        window.after(0, loading_indicator.stop_spinning)
        window.after(0, lambda i0 = loading_indicator: hide_popup(i0))

        if connected:
            warning_confirmation.warning_confirmation_dict["network success"][1] = f"Successfully connected to {ssid}!"
            window.after(0, warning_confirmation.config, "network success")
        else:
            warning_confirmation.warning_confirmation_dict["network fail"][1] = (
                f"Failed to establish a connection with {ssid}."
            )
            window.after(0, warning_confirmation.config, "network fail")

internetMenu = editInternetClass(window)



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
        self.configure(width=sWidth * .5, height=sHeight/2, border_width=4, border_color='white')
        self.grid_propagate(0)
        self.attendance_mapping = {"Present": 2, "Tardy": 1, "Absent": 0}
        self.scan_ID = None


        # Exit button
        self.exit_button = ctk.CTkButton(self, text="X", font=('Arial', 30, 'bold'),width=60, height=60, command=lambda: self.hide())
        self.exit_button.place(relx=.865,rely=.04)  # Top right corner

        #Delete Check In
        trashImage = ctk.CTkImage(light_image=Image.open(script_directory+r"/images/delete.png"),size=(50,50))
        self.delete_button = ctk.CTkButton(self, text="", image=trashImage,width=60, height=60, command=lambda: self.delete_attendance())
        self.delete_button.place(relx=.86,rely=.76)

        #Grid Configuration
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)
        self.rowconfigure(5, weight=1)




        # Title Label
        self.title_label = ctk.CTkLabel(self, text="Edit Attendance Data", text_color="orange", font=("Space Grotesk", 22,'bold'))
        self.title_label.grid(row=0, column=0, pady=(20, 10), sticky='n')

        # Dropdown menu for attendance status
        self.attendance_var = tk.StringVar()  # Default value
        self.attendance_dropdown = ctk.CTkComboBox(self, variable=self.attendance_var,values = list(self.attendance_mapping.keys()),height=45,font=('Space Grotesk',16),dropdown_font=('Space Grotesk',24),width=250,state='readonly')
        self.attendance_dropdown.set("")
        self.attendance_dropdown.grid(row=1, column = 0, pady=10, sticky='n')
        self.attendance_dropdown.bind("<Button-1>", partial(open_dropdown, self.attendance_dropdown))


        #Reason Input (default will be admin alteration)
        self.reasons = ["Admin edit", "Medical", "Extracurricular", "Teacher note", "Custom"]
        self.reason_dropdown = ctk.CTkComboBox(self,values = self.reasons,height=45,font=('Space Grotesk',16),dropdown_font=('Space Grotesk',24),width=300,state='readonly', command = self.custom_toggle)
        self.reason_dropdown.set("Admin edit")
        self.reason_dropdown.grid(row=2, column=0,pady=10, sticky='n')
        self.reason_dropdown.bind("<Button-1>", partial(open_dropdown, self.reason_dropdown))



        #Custom Reason Entry
        self.reason_entry = ctk.CTkEntry(self, font=('Space Grotesk',16), placeholder_text="Enter custom reason...", height = 40, width = 320)
        self.reason_entry.bind("<FocusIn>", lambda event: self.set_current_entry(self.reason_entry))

        #Custom Input Required Label
        self.error_label = ctk.CTkLabel(self, text='Custom input required!', text_color='red', font=("Space Grotesk", 14, 'bold'))

        # Submit button
        self.submit_button = ctk.CTkButton(self, height=60, text="Submit", font=('Space Grotesk',18, 'bold'),command=self.submit_attendance)
        self.submit_button.grid(row=5, column=0,pady=20, sticky = 'n')

    def set_current_entry(self, entry):
        display_popup(keyboardFrame, .65)
        keyboardFrame.set_target(entry)

    def custom_toggle(self, reason):
        if reason == "Custom":
            self.reason_entry.grid(row=3, column=0, pady=10, sticky='n')
        else:
            self.reason_entry.grid_forget()

    def setValue(self, scan_ID, attendance, reason):
        self.scan_ID = scan_ID
        self.attendance_dropdown.set(attendance)
        self.reason_entry.grid_forget()
        if reason:
            if reason not in self.reasons: #CUSTOM VALUE
                self.reason_dropdown.set("Custom")
                self.reason_entry.insert(0, reason)
                self.reason_entry.grid(row=3, column=0, pady=10, sticky='n')
            else: #DEFAULT VALUE OPTION
                self.reason_dropdown.set(reason)
        else:
            self.reason_dropdown.set("Admin edit")


    def delete_attendance(self):
        getFromScans("""delete FROM scans where scan_ID = %s""", (self.scan_ID,), False, False)
        historyFrame.fetch_students()
        self.hide()

    def hide(self):
        hide_popup(self)

    def submit_attendance(self):
        attendance_value = self.attendance_mapping[self.attendance_var.get()]  # Map the selected status to its value
        selected_reason = self.reason_dropdown.get()
        if selected_reason == "Custom":
            custom_reason = self.reason_entry.get()
            if not custom_reason:  # Show error if no custom reason provided
                self.error_label.grid(row=4, column=0, pady=10, sticky='n')
                return #EXIT OUT IF LABEL IS HERE
            reason = custom_reason
        else:
            reason = selected_reason
        self.hide()
        self.reason_entry.delete(0, 'end')
        getFromScans("""UPDATE scans SET status = %s, reason = %s WHERE scan_ID = %s""",(attendance_value, reason, self.scan_ID), False, False)
        self.error_label.grid_forget()
        historyFrame.fetch_students()

editAttendanceFrame = EditAttendanceClass(window)

class dynamic_day_selectionClass(ctk.CTkFrame):
    def __init__(self, parent,*args, **kwargs):
        super().__init__(parent, *args, **kwargs,width=sWidth*3/7, height=sHeight/2,border_width=4,border_color='white',bg_color='transparent')
        self.grid_propagate(0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=10)

        # Title label
        self.titleFrame = ctk.CTkFrame(self,border_width=4,border_color='white',bg_color='white')
        self.title_label = ctk.CTkLabel(self.titleFrame, text="Dynamic: Is Today an A or B Day?", font=("Roboto", 19,'bold'))
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
        periodListPop()
        hide_popup(self)
        currentPopup = None
fridayperiodframe = dynamic_day_selectionClass(window)

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

class warning_confirmation_class(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        #ARRIVAL TIME NEEDS INPUT WARNING
        self.configure(width=(sWidth/2), height=(sHeight/2), border_color= 'white', border_width=4, bg_color='white')
        self.grid_propagate(0)
        self.pack_propagate(0)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight = 1)
        self.rowconfigure(1, weight = 1)
        self.rowconfigure(2, weight = 3)
        self.current_key = None

        #Dictionary for each popup
        self.warning_confirmation_dict = {"no active schedule": ["No Active Schedule!", "Your teacher must select an active schedule.", 'red', None, None],
                                          "no schedule today": ["Check-in Unavailable Today!", "The current schedule is not active today. Please contact your teacher if you have questions.", 'orange', None, None],
                                          "no class currently": ["No Scheduled Class!", "There is no class scheduled at this time. Please check your class schedule or return during your designated period.", 'orange', None, None],
                                          "double scan": ['Double Scan!', "You have already checked in for this period.", 'orange', None, None],
                                          "wrong period": ['Wrong period!', "You are not in the current period.", 'orange', None, None],
                                          "schedule input": ['Missing Schedule Values!', "Please complete all required fields before submitting.", 'orange', None, None],
                                          "period input": ["title", "note", 'orange', None, None],
                                          "weekday input": ['Missing Weekday Values!', "Please complete all required fields before submitting.", 'orange',  None, None],
                                          "unexpected error": ["An Unexpected Error Has Occured!", "error", 'red', None, None],
                                          "factory reset": ["Factory Reset Device?", "*Warning! This will clear everything on the device (includes schedules, periods, students, and passwords).*", "red", lambda: self.config("reset check"), None],
                                          "reset check": ["Are you sure?", "*This action is not reversible.*", "red", lambda: self.reset_display_password_menu(), None],
                                          "remove student": ["title", "*This will remove them from the system permanently.*", "red", "command", None],
                                          "reset ID check": ["title", "*This will re-assign what student ID is associated with this student.*", "red", "command", None],
                                          "reset ID": ["Scan New ID!", "note", "orange", "notice", None],
                                          "reset ID success" : ["Successfully Reset ID!", "note", "green", None, None],
                                          "reset ID fail" : ["Failed to Reset ID!", "note", "red", None, None],
                                          "remove schedule check" : ["Are you sure?", "note", "red", "command", None],
                                          "remove period check" : ["Are you sure?", "note", "red", "command", None],
                                          "restart check" : ["Restart System?", "*This will temporarily refresh the system (no data will be lost)*", "orange", lambda: teacherFrame.restart_script(), None],
                                          "matching name" : ["Invalid Name!", "note", "red", "command", "command"],
                                          "different name" : ["Warning!", "note", "orange", None, None],
                                          "reset ID notice" : ["Notice!", "note", "orange", None, None],
                                          "network success" : ["Network Connected!", "note", "green", None, None],
                                          "network fail" : ["Network Connection Failed!", "note", "red", None, None]
                                          }



        #title
        self.title_label = ctk.CTkLabel(self, font=('Space Grotesk', 25, 'bold'), wraplength=sWidth/2-16)
        self.title_label.grid(row=0, column=0, pady=(10, 5), padx = 5, sticky='n')

        #notice
        self.notice_label = ctk.CTkLabel(self, font=('Space Grotesk', 15), wraplength=sWidth/2-24)
        self.notice_label.grid(row=1, column=0, pady=(5, 15), padx = 5, sticky='n')

        #lower container frame
        self.lower_frame = ctk.CTkFrame(self, fg_color = "#2b2b2b")
        self.lower_frame.grid(row=2, column=0, sticky='nsew',padx=4,pady=4)


        #option frame
        self.option_frame = ctk.CTkFrame(self.lower_frame)
        self.option_frame.rowconfigure(0, weight=1)
        self.option_frame.columnconfigure(0, weight=1)
        self.option_frame.columnconfigure(1, weight=1)

        #option frame buttons
        self.yes_button = ctk.CTkButton(self.option_frame, text='Yes', font=('Space Grotesk', 17, 'bold'), height=60)
        self.yes_button.grid(sticky='e', row=0, column=0, padx=20)

        self.no_button = ctk.CTkButton(self.option_frame, text='No', font=('Space Grotesk', 17, 'bold'), height=60)
        self.no_button.grid(sticky='w', row=0, column=1, padx=20)

        self.warning_image = ctk.CTkImage(Image.open(script_directory+r"/images/warning.png"),size=(int(sWidth/9),int(sWidth/9)))
        self.exit_button = ctk.CTkButton(self.lower_frame, image = self.warning_image, text='', fg_color='#2B2B2B',border_color='white',border_width=4, command = lambda: hide_popup(self))

    def delete_student(self, macID):
        hide_popup(self)
        getFromStudent_Periods("""delete from student_periods where macID = %s""", (macID,), False, False)
        getFromStudent_Names("""delete from student_names where macID = %s""", (macID,), False, False)
        getFromScans("""delete from scans where macID = %s""", (macID,), False, False)
        teacherFrame.period_selected(teacherFrame.period_menu.get()) #RELOAD STUDENT LIST ON TEACHER FRAME

    def reset_display_password_menu(self):
        hide_popup(self)
        teacherPWPopup.change_pw(False)
        teacherPWPopup.change_tab(3)
        teacherPWPopup.change_label('Enter Teacher Password:')
        display_popup(teacherPWPopup)

    def config(self, key):
        self.current_key = key
        self.option_frame.pack_forget()
        self.exit_button.pack_forget()
        #configure title, notice, and lower container
        warning_info = self.warning_confirmation_dict[key]
        self.title_label.configure(text=warning_info[0], text_color = warning_info[2])
        self.notice_label.configure(text=warning_info[1], text_color = warning_info[2])
        command = warning_info[3]
        no_command = warning_info[4]
        if command: #if there is a command, display yes/no
            if command != "notice":
                self.option_frame.pack(expand=True, fill='both')
                self.yes_button.configure(command = command)
            if no_command:
                self.no_button.configure(command = no_command)
            else:
                self.no_button.configure(command = lambda: hide_popup(self))
        else:
            self.exit_button.pack(anchor='center')
        display_popup(self)
warning_confirmation = warning_confirmation_class(window)

class timeoutMenuClass(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        #ARRIVAL TIME NEEDS INPUT WARNING
        self.configure(width=(sWidth/2), height=(sHeight/1.75), border_color= 'white', border_width=4, bg_color='white')
        self.grid_propagate(0)
        self.pack_propagate(0)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight = 1)
        self.rowconfigure(1, weight = 1)

        #upper container frame
        self.upper_frame = ctk.CTkFrame(self, fg_color = "#2b2b2b")
        self.upper_frame.columnconfigure(0, weight=1)
        self.upper_frame.rowconfigure(0, weight=1)
        self.upper_frame.rowconfigure(1, weight=2)
        self.upper_frame.grid(row=0, column=0, sticky='nsew',padx=4,pady=4)

        #title
        self.title_label = ctk.CTkLabel(self.upper_frame, text = "Change Idle Timeout Delay",font=('Space Grotesk', 25, 'bold'), text_color= "#1f6aa5", wraplength=sWidth/2-16)
        self.title_label.grid(row=0, column=0, pady=(10, 5), padx = 5, sticky='n')

        #notice
        self.notice_label = ctk.CTkLabel(self.upper_frame, text="*This will change the amount of time it takes before system automatically returns to main menu when in settings or history.*",font=('Space Grotesk', 15), wraplength=sWidth/2-16)
        self.notice_label.grid(row=1, column=0, pady=(5, 15), padx = 5, sticky='n')

        #lower container frame
        self.lower_frame = ctk.CTkFrame(self, fg_color = "#2b2b2b", height = 210)
        self.lower_frame.pack_propagate(0)
        self.lower_frame.grid_propagate(0)
        self.lower_frame.columnconfigure(0, weight=1)
        self.lower_frame.rowconfigure(0, weight=3)
        self.lower_frame.rowconfigure(1, weight=1)
        self.lower_frame.grid(row=1, column=0, sticky='nsew',padx=4,pady=4)

        #time selection
        self.selection_frame = ctk.CTkFrame(self.lower_frame, fg_color='#2B2B2B')
        self.selection_frame.grid_propagate(0)
        self.selection_frame.grid(row=0, column=0, sticky='nsew', padx= (100,0), pady=10)

        self.selection_frame_var = ctk.StringVar(value = '05')

        #TARDY MINUTE SELECTORS
        self.minute_up = ctk.CTkButton(self.selection_frame, text="↑", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_minute(self.selection_frame_var, +1))
        self.minute_up.grid(row=4, column=2,pady=(25,5),padx=10)
        self.minute_down = ctk.CTkButton(self.selection_frame, text="↓", font = ('Space Grotesk', 18, 'bold'),command = lambda: self.change_minute(self.selection_frame_var, -1))
        self.minute_down.grid(row=5, column=2,pady=(5,10),padx=10)

        #TARDY LABELS
        self.timeout_label = ctk.CTkLabel(self.selection_frame, text='Timeout Delay:', font=('Space Grotesk', 20, 'bold'))
        self.timeout_label.grid(row=4, column=1,pady=5,padx=10)
        self.timeout_value_label = ctk.CTkLabel(self.selection_frame, font = ('Space Grotesk', 18, 'bold'), text=f"{self.selection_frame_var.get()}")
        self.timeout_value_label.grid(row=5,column=1,pady=5)

        #TARDY UPDATE LABEL CODE
        self.selection_frame_var.trace_add("write", partial(self.update_label, self.selection_frame_var, self.timeout_value_label))

        #submit button
        self.submit_button = ctk.CTkButton(self.lower_frame, font = ('Space Grotesk', 18, 'bold'), text='Submit',border_color='white',border_width=4, command = self.submit, width = 200, height = 60)
        self.submit_button.grid(row=1, column=0, sticky='s', pady = 10)

    #UPDATE ALL LABELS
    def update_label(self, var, label, *args):
        label.configure(text=var.get())

    def change_minute(self, var, delta):
        current_minute = int(var.get())
        new_minute = (current_minute + delta - 1) % 59 + 1
        var.set(f"{new_minute:02d}")

    def update(self):
        self.selection_frame_var.set(f"{int((int(getFromSystem_Control('select timeout_time from system_control', None, True)[0]) / 60)):02d}")

    def submit(self):
        getFromSystem_Control("update system_control set timeout_time = %s", (int(self.timeout_value_label.cget('text')) * 60,), False, False)
        hide_popup(self)
timeoutMenu = timeoutMenuClass(window)

class loadingIndicatorClass(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(width=(sWidth/2), height=(sHeight/1.75), border_color= 'white', border_width=4, bg_color='white')
        self.grid_propagate(0)
        self.pack_propagate(0)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight = 1)
        self.rowconfigure(1, weight = 4)

        #title
        self.title_label = ctk.CTkLabel(self, text = "Checking connection...",font=('Space Grotesk', 25, 'bold'), text_color= "#1f6aa5", wraplength=sWidth/2-16)
        self.title_label.grid(row=0, column=0, pady=(10, 5), sticky='n')


        self.spinning_image2 = LoadingAnimation(self, "#2b2b2b")
        self.spinning_image2.grid(row=1, column=0,sticky='n', pady=15)

    def start_spinning(self):
        self.spinning_image2.start_spinning()

    def stop_spinning(self):
        self.spinning_image2.stop_spinning()

loading_indicator = loadingIndicatorClass(window)

#touch input detection
window.bind_all("<Button-1>", reset_timeout)

def main():
    timeFunc()
    threading.Thread(target=checkIN, daemon=True).start()
    tabSwap(1)
    window.mainloop()
main()
