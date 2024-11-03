#THREADING
import threading

#ANIMATION
import os
import glob
import math
import random

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

#FUNCTIONS
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


#UPDATING FUNCTIONS
#STUDENTLIST POPULATION
def studentListPop(periodNumber, periodName):
    studentListCursor = db.cursor()
    for widget in studentList.winfo_children():
        widget.destroy()
    studentList.configure(label_text=(periodName + ': ' + str(periodNumber)))
    tempMASTERLIST = callMultiple(studentListCursor, 'SELECT * FROM MASTER WHERE period = %s', (periodNumber,))

    if tempMASTERLIST:
        for index, student in enumerate(tempMASTERLIST):
            name = (student[1].capitalize() + ' ' + student[2].capitalize())
            tempSCANSLIST = callMultiple(studentListCursor, 'SELECT time, present FROM SCANS WHERE macID = %s AND date = %s AND currentPeriod = %s',(student[0], strftime("%m-%d-%Y"), periodNumber))
            if tempSCANSLIST:
                present = tempSCANSLIST[0][1]
            else:
                present = -1

            studentFrame = ctk.CTkFrame(studentList, height=int(0.075*sHeight),width=0.30859375*sWidth,border_width=2, border_color='white')
            studentFrame.pack_propagate(0)
            if present == 2:
                studentFrame.configure(fg_color='green')
                presentImage = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/periodListCheck.png"),size=(40,30))
                ctk.CTkLabel(studentFrame, text=(name.strip() + ': On time at ' + timeConvert(tempSCANSLIST[0][0])),text_color='white', font=('Roboto', 15)).pack(side='left', padx=5, pady=2)
                ctk.CTkLabel(studentFrame, image=presentImage, text='',fg_color='transparent').pack(padx=10,pady=5,side='right')
            elif present == 1:
                studentFrame.configure(fg_color='orange')
                lateimage = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/periodListTardy.png"),size=(40,40))
                ctk.CTkLabel(studentFrame, text=(name.strip() + ': Late at ' + timeConvert(tempSCANSLIST[0][0])),text_color='white', font=('Roboto', 15)).pack(side='left', padx=5, pady=2)
                ctk.CTkLabel(studentFrame, image=lateimage, text='',fg_color='transparent').pack(padx=4,pady=2,side='right')
            else:
                studentFrame.configure(fg_color='red')
                absentimage = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/periodListX.png"),size=(30,30))
                thislbl = ctk.CTkLabel(studentFrame, text=(name.strip() + ': Absent'), text_color='white', font=('Roboto', 15))
                if present == 0:
                    thislbl.configure(text=(name.strip() + ': Absent at ' + timeConvert(tempSCANSLIST[0][0])))
                thislbl.pack(side='left', padx=5, pady=2)
                ctk.CTkLabel(studentFrame, image=absentimage, text='',fg_color='transparent').pack(padx=10,pady=2,side='right')

            # Calculate row and column dynamically
            row = index // 2  # Every two students per row
            column = index % 2

            studentFrame.grid(row=row, column=column, pady=5, padx=3, sticky='nsw')
    studentListCursor.close()


#PERIODLIST UPDATING
def updatePeriodList(newName, periodNum):
    for button in periodList.winfo_children():
        if button.cget('text')[-2:] == periodNum:
            button.configure(text=newName + ": " + periodNum)





#GETTER FUNCTIONS
#MASTER GETTER
def getMaster(query, params=None,fetchone=False,get=True):
    with db.cursor() as master_curs:
        return callMultiple(master_curs, query, params, fetchone, get)

#SCANNER GETTER
def getScans(query, params=None,fetchone=False,get=True):
    with db.cursor() as scans_curs:
        return callMultiple(scans_curs, query, params, fetchone, get)

#ACTIVITY GETTER
def getActivity(query, params=None,fetchone=False,get=True):
    with db.cursor() as activity_curs:
        return callMultiple(activity_curs, query, params, fetchone, get)


#PERIOD GETTER
def getPeriod(query, params=None,fetchone=False,get=True):
    with db.cursor() as period_curs:
        return callMultiple(period_curs, query, params, fetchone, get)

#TEACHER GETTER
def getTeacher(query, params=None,fetchone=False,get=True):
    with db.cursor() as teacher_curs:
        return callMultiple(teacher_curs, query, params, fetchone, get)





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


#DATABASE GETTER FUNCTIONS
def get_Activity():
    activity = getTeacher("""select ACTIVITY from TEACHERS""", None, True)
    if activity[0] == 0:
        return False
    elif activity[0] == 1:
        return True

def getAttendance(time, period):
    if time > period[0][1]:
        if time < period[0][2]:
            return 2
        else:
            if (time - period[0][2]) >= period[0][3]:
                return 0
            else:
                return 1

def getPeriodList():
    with db.cursor() as periodlist_curs:
        periodList1 = callMultiple(periodlist_curs, """select periodName, periodNum from PERIODS""", None)
        return periodList1

def getDiffPeriodList():
    tempList = []
    for period in getPeriodList():
        tempList.append(period[0] + ': ' + period[1])
    return tempList

def getFirstLastName(id):
    firstLast = getMaster("""select firstNAME, lastNAME from MASTER where macID = %s""",(id,),True)
    return firstLast[0], firstLast[1]

def getNamesFromPeriod(periodNumb):
    periodNumber = periodNumb[-2:]
    studentNames = getMaster("""select macID, firstNAME, lastNAME from MASTER where period = %s""",(periodNumber,))
    tempDict = {}
    for i in studentNames:
        tempDict[(i[1].capitalize() + " " + i[2].capitalize())] = i[0]
    return tempDict

def updateSchedType():
    global schedtype
    schedtype = getTeacher("""select SCHEDULE from TEACHERS""", None, True)[0]

def getAorB():
    activity = getTeacher("""select A_B from TEACHERS""", None, True)
    if activity is None:
        return None
    return activity[0]

schedtype = None
updateSchedType()

def getCurrentPeriod(time):
    currentperiod = "-"
    global arriveTimes
    for i in arriveTimes:
        if i[1] <= time:
            currentperiod = i[0]
        else:
            break
    return currentperiod

#CHECK IN FUNCTIONS
def checkInOverlap(scans, currPeriod):
    periodOverlap = False
    if scans:
        for checks in scans:
            if checks[0] == currPeriod: #CHECK IF THEY HAVE ALREADY CHECKED INTO THE CURRENT PERIOD
                periodOverlap = True
                break
    return periodOverlap

def getABperiods(periodList, A_B):
    newPeriodList = []
    for i in periodList:
        if A_B in i[0]:
            newPeriodList.append(i[0])
    return newPeriodList



#CHANGING DATA FUNCTIONS
def inputStudentData(fName, lName, periods, id):
    for period in periods:
        getMaster("""INSERT INTO MASTER(macID, firstNAME, lastNAME, period) values (%s, %s, %s, %s)""", (id,fName.lower(),lName.lower(),period), False, False)

arriveTimes = []
def updateArriveTimes():
    global arriveTimes
    tempTimes = getPeriod("""SELECT periodNum, arrive from PERIODS""", None, False, True)
    arriveTimes = reduceTimes(tempTimes)

activityArriveTimes = None
def updateActivityArriveTimes():
    global activityArriveTimes
    tempTimes = getActivity("""SELECT periodNum, arrive from ACTIVITY""", None, False, True)
    activityArriveTimes = reduceTimes(tempTimes)

def reduceTimes(times):
    global A_B
    global schedtype
    if schedtype == 'traditional':
        return times
    else:
        finalTimes = []
        for period in times:
            if period[0][0] == A_B:
                finalTimes.append(period)
        return finalTimes


def setAorB(AB):
    global A_B
    getTeacher("""update TEACHERS set A_B = %s""", (AB,), False, False)
    A_B = AB
A_B = getAorB()


def setActivity(val):
    getActivity("""update TEACHERS set ACTIVITY = %s""", (val,), False, False)

def setPeriodTiming(periodInfo, absentTime):
    with db.cursor() as period_timing_curs:
        for period in periodInfo:
            periodNumber = period[0][-2:]
            arrival = time_to_minutes(period[1])
            late = time_to_minutes(period[2])
            period_timing_curs.execute("""update PERIODS set arrive = %s, late = %s, whenAbsent = %s where periodNum = %s""", (arrival,late,absentTime,periodNumber))
        updateArriveTimes()

def setActivityPeriodTiming(periodInfo, absentTime):
    with db.cursor() as activity_timing_curs:
        for period in periodInfo:
            periodNumber = period[0][-2:]
            arrival = time_to_minutes(period[1])
            late = time_to_minutes(period[2])
            activity_timing_curs.execute("""update ACTIVITY set arrive = %s, late = %s, whenAbsent = %s where periodNum = %s""", (arrival,late,absentTime,periodNumber))
        updateActivityArriveTimes()

def tempResetArrivalTimes():
    data = [
        ['A1','Computer Science 1',490,495,30],
        ['A2','Conference',585,590,30],
        ['A3','Principles of Computer Science',715,720,30],
        ['A4','Principles of Applied Engineering',840,845,30],
        ['B1','Principles of Applied Engineering',490,495,30],
        ['B2','AP Computer Science',585,590,30],
        ['B3','Computer Science 1',715,720,30],
        ['B4','Conference',840,845,30]
    ]
    getActivity("""TRUNCATE TABLE ACTIVITY""", None, False, False)
    getActivity("""INSERT INTO ACTIVITY(periodNum, periodName, arrive, late, whenAbsent) values(%s,%s,%s,%s,%s)""", data, False, False)

def changePeriodName(name, per):
    getPeriod("""update PERIODS set periodName = %s where periodNum = %s""", (name, per), False, False)
    getActivity("""update ACTIVITY set periodName = %s where periodNum = %s""", (name,per), False, False)
    updatePeriodList(name, per)
    teacherFrame.periods = getDiffPeriodList()  # Update the period list
    teacherFrame.period_menu.configure(values=teacherFrame.periods)  # Update the dropdown menu with the new periods
    teacherFrame.period_menu.set(f"{name}: {per}")  # Auto-update the selected value to reflect the change
    historyFrame.period_menu.configure(values=teacherFrame.periods)
    getStudentInfoFrame.update_periods(teacherFrame.periods)


#NEW DAY FUNCTION
def newDay():
    if get_Activity():
        #CHANGE ARRIVAL TIMES BACK TO NORMAL TIMES
        setActivity(0) #RESET ACTIVITY SCHEDULE EVERY DAY

    #UPDATE A/B DAY
    day = (date.today().weekday())
    global schedtype
    global A_B
    if schedtype == 'block':
        if day == 4: #IS IT FRIDAY CHECK
            display_popup(fridayperiodframe)
        else:
            if (day == 0 or day == 2):
                setAorB('A')
                teacherFrame.ab_day_segmented.set("A Day")
            elif (day == 1 or day == 3):
                setAorB('B')
                teacherFrame.ab_day_segmented.set("B Day")

#TIME LOOP
prevDate = date.today() - timedelta(days=1)
def timeFunc():
    global prevDate
    currDate = date.today()
    if currDate != prevDate:
        newDay()
        prevDate = currDate
    timeLabel.configure(text=strftime('%I:%M:%S %p'))
    dateLabel.configure(text=strftime("%m-%d-%Y"))
    timeLabel.after(1000, timeFunc)

ten_after = time_to_minutes(strftime("%H:%M")) + 10


#CHECK IN FUNCTION
def checkIN():
    global currentPopup
    global ten_after
    while True:
        current_time = time_to_minutes(strftime("%H:%M"))
        current_period = getCurrentPeriod(current_time)
        current_date = strftime("%m-%d-%Y")
        if ten_after == current_time:
            with db.cursor() as alive_curs:
                # Execute a simple query to keep the connection alive
                result = callMultiple(alive_curs, """SELECT SCHEDULE FROM TEACHERS""", None, True)
                print("ten minute increment" + current_time)
            ten_after = current_time + 10
        if rfid.tagPresent():
            ID = rfid.readID()
            if ID:
                if str(ID) == "04:F7:2C:0A:68:19:90":
                    if teacherPWPopup.getDisplayed():
                        teacherPWPopup.close_popup()
                        tabSwap(teacherPWPopup.get_tab()+2)
                        sleep_ms(3000)
                elif currentTAB == 1 or currentTAB == 2:
                    if currentPopup != alreadyCheckFrame:
                        checkInCursor = db.cursor()
                        checkInCursor.execute("""SELECT arrive from PERIODS""")
                        arrive_times = checkInCursor.fetchall()
                        check = True
                        for i in arrive_times:
                            if None in i:
                                check = False
                                break
                            else:
                                continue
                        if check: #CHECK IF ARRIVAL TIMES ARE CREATED
                            checkInCursor.execute("""SELECT period from MASTER WHERE macID = %s""", (ID,))
                            studentPeriodList = checkInCursor.fetchall()
                            if studentPeriodList: #CHECK IF A PERIOD IS RETURNED (IF THEY'RE IN THE MASTER LIST)
                                #CHECK IF STUDENT IS IN THE CURRENT PERIOD
                                ABperiods = getABperiods(studentPeriodList, (A_B))
                                notInPeriod = True
                                for period in ABperiods:
                                    if period == current_period:
                                        notInPeriod = False
                                        checkInCursor.execute("""SELECT currentPeriod FROM SCANS WHERE macID = %s AND date = %s""", (ID, current_date))
                                        scanPeriods = checkInCursor.fetchall()
                                        if checkInOverlap(scanPeriods, current_period):
                                            alreadyChecktitlelabel.configure(text='Double Scan!')
                                            alreadyChecknoticelabel.configure(text="You have already checked in for this period.")
                                            display_popup(alreadyCheckFrame)
                                        else:
                                            #ADD CHECK IN DATA
                                            checkInCursor.execute("""select ACTIVITY from TEACHERS""")
                                            activity = checkInCursor.fetchone()
                                            if activity[0] == 1:
                                                checkInCursor.execute("""SELECT periodName, arrive, late, whenAbsent FROM ACTIVITY where periodNum = %s""", (period,))
                                            else:
                                                checkInCursor.execute("""SELECT periodName, arrive, late, whenAbsent FROM PERIODS WHERE periodNum = %s""", (period,))
                                            periodData = checkInCursor.fetchall()
                                            present = getAttendance(current_time, periodData)
                                            #ADD CHECK FOR DOCTORS APPOINTMENT IF MARKED ABSENT
                                            checkInCursor.execute("""select firstNAME, lastNAME from MASTER where macID = %s""", (ID,))
                                            firstLast = checkInCursor.fetchone()
                                            name = firstLast[0].capitalize() + " " + firstLast[1].capitalize()
                                            checkInCursor.execute("""INSERT INTO SCANS (macID, date, time, present, currentPeriod) values (%s, %s, %s, %s, %s)""", (ID, current_date, current_time, present, current_period))
                                            studentListPop(period, periodData[0][0])
                                            tabSwap(2)
                                            successScan(current_time, name, present)
                                    else:
                                        continue
                                if notInPeriod:
                                    #DISPLAY YOU ARE NOT IN THE CURRENT PERIOD
                                    alreadyChecktitlelabel.configure(text='Wrong period!')
                                    alreadyChecknoticelabel.configure(text="You are not in the current period (" + current_period + ").")
                                    display_popup(alreadyCheckFrame)
                            else: #CREATE NEW STUDENT ENTRY BECAUSE THEY ARE NOT IN MASTER DATABASE
                                #GET STUDENT DATA WITH POP UP
                                getStudentInfoFrame.setMACID(ID)
                                display_popup(getStudentInfoFrame)
                        else: #IF ARRIVAL TIMES ARE NOT CREATED
                            warninglabel.configure(text="Students cannot check in until the teacher\nhas assigned arrival times for each period.")
                            display_popup(arrivalWarningFrame)
                        checkInCursor.close()
                elif currentTAB == 4:
                    if currentPopup != getStudentInfoFrame:
                        editStudentData(ID)
                sleep_ms(100)
            else:
                sleep_ms(100)




#FRAME CLASSES
class setupClass(ctk.CTkFrame):
     def __init__(self, parent):
         super().__init__(parent)
         self.sWidth = sWidth
         self.sHeight = sHeight
         self.configure(width=sWidth, height=sHeight)
         self.pack_propagate(0)
         self.grid_propagate(0)
         self.deleteImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/deleteIcon.png"),size=(25,25))

         self.current_tab = 1  # Start with tab 1
         self.schedule_type = None
         self.period_data = []  # To store period data as a 2D list

         self.init_ui()

         self.confirmFrame = ctk.CTkFrame(parent, width=sWidth / 2, height=sHeight / 4, border_width=2, border_color='white', bg_color='white')
         self.confirmFrame.pack_propagate(0)
         self.confirmFrameLabel = ctk.CTkLabel(self.confirmFrame, text='Are you sure you want to continue?', font=('Space Grotesk', 20, 'bold'))
         self.confirmFrameLabel.pack(pady=(15, 5))
         self.notelabel = ctk.CTkLabel(self.confirmFrame, text='*Note: You can edit these later!')
         self.tempFrame = ctk.CTkFrame(self.confirmFrame, fg_color='#2b2b2b')
         self.tempFrame.pack(pady=20)
         self.confirmFrameYes = ctk.CTkButton(self.tempFrame, text="Yes", font=('Space Grotesk', 16, 'bold'), width=100, height=55, command=self.next_confirm)
         self.confirmFrameYes.pack(side='left', padx=20)
         self.confirmFrameExit = ctk.CTkButton(self.tempFrame, text="No", font=('Space Grotesk', 16, 'bold'), width=100, height=55, command=lambda: hide_popup(self.confirmFrame))
         self.confirmFrameExit.pack(side='right', padx=20)

     def next_confirm(self):
         self.show_second_tab()
         hide_popup(self.confirmFrame)

     def init_ui(self):
         # Create top bar
         self.top_bar = ctk.CTkFrame(self, border_width=4, border_color='white', fg_color="#2b2b2b")
         self.top_bar.pack(side='top', fill='x')
         self.top_bar.columnconfigure(0, weight=1)
         self.top_bar.columnconfigure(1, weight=8)

         self.left_bar = ctk.CTkFrame(self.top_bar, border_width=4, border_color='white', fg_color="#2b2b2b", bg_color='white')
         self.left_bar.grid(row=0, column=0, sticky='nsew')
         self.right_bar = ctk.CTkFrame(self.top_bar, border_width=4, border_color='white', fg_color="#2b2b2b", bg_color='white')
         self.right_bar.grid(row=0, column=1, sticky='nsew')

         # Title label
         self.title_label = ctk.CTkLabel(self.left_bar, text="Setup Mode", font=("Space Grotesk", 50, 'bold'))
         self.title_label.pack(side='left', padx=20, pady=10)

         # Schedule type selector and Next button
         self.schedule_type_label = ctk.CTkLabel(self.right_bar, text="Schedule Type:", font=("Space Grotesk", 30, 'bold'))
         self.schedule_type_label.pack(side='left', padx=20, pady=10)
         self.schedule_selector = ctk.CTkSegmentedButton(self.right_bar, values=["Block", "Traditional"], font=("Space Grotesk", 15), command=self.select_schedule_type, height=50, width=150)
         self.schedule_selector.pack(side='left', padx=20, pady=10)

         self.next_button = ctk.CTkButton(self.right_bar, text="Next", command= self.showCheck, height=50)
         self.next_button.pack(side='right', padx=20, pady=10)

         # Bottom frame (tab content)
         self.bottom_frame = ctk.CTkFrame(self)
         self.bottom_frame.pack(side='bottom', fill="both", expand=True)
         placeholder_label = ctk.CTkLabel(self.bottom_frame, text="Select a schedule type. . .", font=("Space Grotesk", 26), text_color='gray')
         placeholder_label.pack(expand=True)

     def showCheck(self):
         display_popup(self.confirmFrame)

     def select_schedule_type(self, value):
         self.schedule_type = value
         self.period_data = []
         for widget in self.bottom_frame.winfo_children():
             widget.destroy()  # Clear previous content

         if value == "Block":
             self.display_block_schedule()
         elif value == "Traditional":
             self.display_traditional_schedule()


     def display_block_schedule(self):
         # A Day and B Day scrollable frames
         self.a_day_frame = ctk.CTkScrollableFrame(self.bottom_frame)
         self.b_day_frame = ctk.CTkScrollableFrame(self.bottom_frame)
         scrollbar1 = self.a_day_frame._scrollbar
         scrollbar1.configure(width=25)
         scrollbar2 = self.b_day_frame._scrollbar
         scrollbar2.configure(width=25)


         self.a_day_frame.pack(side="left", expand=True, fill="both", padx=10, pady=10)
         self.b_day_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

         # Titles for A and B Day
         a_day_title = ctk.CTkLabel(self.a_day_frame, text="A Day Periods", font=("Space Grotesk", 25, 'bold'))
         a_day_title.pack(anchor="n")
         b_day_title = ctk.CTkLabel(self.b_day_frame, text="B Day Periods", font=("Space Grotesk", 25, 'bold'))
         b_day_title.pack(anchor="n")

         # Add Period button for both A and B Day
         self.add_period_button(self.a_day_frame, "A")
         self.add_period_button(self.b_day_frame, "B")

     def display_traditional_schedule(self):
         # Single scrollable frame for Traditional schedule
         self.class_periods_frame = ctk.CTkScrollableFrame(self.bottom_frame)
         self.class_periods_frame.pack(expand=True, fill="both", padx=10, pady=10)
         scrollbar3 = self.class_periods_frame._scrollbar
         scrollbar3.configure(width=25)

         # Title
         class_periods_title = ctk.CTkLabel(self.class_periods_frame, text="Class Periods", font=("Space Grotesk", 30, 'bold'))
         class_periods_title.pack(anchor="n")

         # Add Period button
         self.add_period_button(self.class_periods_frame, "A")

     def add_period_button(self, parent_frame, day_type):
         add_button = ctk.CTkButton(parent_frame, text="+ Add Period +", fg_color="#1f6aa5", command=lambda: self.add_period_frame(parent_frame, day_type), height=60, font=("Space Grotesk", 20))
         add_button.pack(side="bottom", pady=10, fill="x", padx=10)

     def add_period_frame(self, parent_frame, day_type):
         period_index = len([child for child in parent_frame.winfo_children() if isinstance(child, ctk.CTkFrame)]) + 1
         label_text = f"{day_type}{period_index}"

         period_frame = ctk.CTkFrame(parent_frame, border_color="white", border_width=1, fg_color="#1f6aa5", height = 35)
         period_frame.pack(fill="x", padx=10, pady=5)

         period_label = ctk.CTkLabel(period_frame, text=label_text, font=("Space Grotesk", 20, 'bold'))
         period_label.pack(side="left", padx=(10, 5))

         period_var = StringVar()
         period_entry = ctk.CTkEntry(period_frame, font=("Space Grotesk", 18), placeholder_text="Enter period name", height= 35, textvariable=period_var)
         period_entry.pack(side="left", padx=20, pady=5, fill='x', expand=True)

         delete_button = ctk.CTkButton(period_frame, text="Delete", font=("Space Grotesk", 18), fg_color="red", image=self.deleteImage, compound='right',width=80, height=35, command=lambda: self.delete_period_frame(period_frame, parent_frame, day_type))
         delete_button.pack(side="right", padx=10, pady=5)


         period_entry.bind("<FocusIn>", lambda e: self.entry_click_function(period_entry))

     def delete_period_frame(self, frame, parent_frame, day_type):
        # Find the index of the frame to be deleted in parent_frame
        frame_index = [child for child in parent_frame.winfo_children() if isinstance(child, ctk.CTkFrame)].index(frame)

        # Destroy the frame
        frame.destroy()


        # Rebuild the period labels and self.period_data entries after deletion
        self.update_period_labels(parent_frame, day_type)

     def update_period_labels(self, parent_frame, day_type):

        # Loop through each frame in parent_frame and update labels
        for i, child in enumerate([child for child in parent_frame.winfo_children() if isinstance(child, ctk.CTkFrame)], start=1):
            # Configure the label with the updated day type and index
            label = child.winfo_children()[0]  # Assuming label is the first child widget
            new_label = f"{day_type}{i}"
            label.configure(text=new_label)

            # Get the period variable (assuming it’s the second widget in the frame)
            period_var = child.winfo_children()[1].cget("textvariable")

     def show_second_tab(self):
         self.next_button.pack_forget()
         self.bottom_frame.pack_forget()
         self.schedule_selector.pack_forget()
         self.schedule_type_label.configure(text='Input Arrival Times:')
         if self.schedule_type == 'Block':
             for child in ([child for child in self.a_day_frame.winfo_children() if isinstance(child, ctk.CTkFrame)]):
                 self.period_data.append((child.winfo_children()[1].get(), child.winfo_children()[0].cget('text')))
             for child in ([child for child in self.b_day_frame.winfo_children() if isinstance(child, ctk.CTkFrame)]):
                 self.period_data.append((child.winfo_children()[1].get(), child.winfo_children()[0].cget('text')))
         else:
             for child in ([child for child in self.class_periods_frame.winfo_children() if isinstance(child, ctk.CTkFrame)]):
                 self.period_data.append((child.winfo_children()[1].get(), child.winfo_children()[0].cget('text')))

         #get rid of exit button on arrival time setup
         arrivalTimeInputFrame.update_setup(True)
         teacherFrame.change_arrival_window()


         for i in self.period_data:
             print(i[0] + " " + i[1])

     def entry_click_function(self, entry_widget):
         keyboardFrame.set_target(entry_widget)
         display_popup(keyboardFrame)

     def end_setup(self):
         create_period_curs = db.cursor()
         for period in self.period_data:
             create_period_curs("""update PERIODS set periodName = %s where periodNum = %s""", (period[0], period[1]))
             create_period_curs("""update ACTIVITY set periodName = %s where periodNum = %s""", (period[0], period[1]))
         update_periodList(self.period_data)
         teacherFrame.periods = getDiffPeriodList()  # Update the period list
         teacherFrame.period_menu.configure(values=teacherFrame.periods)  # Update the dropdown menu with the new periods
         historyFrame.period_menu.configure(values=teacherFrame.periods)
         getStudentInfoFrame.update_periods(teacherFrame.periods)

         self.place_forget()

         main()



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

        self.periods = getDiffPeriodList()

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

        self.top_name_vars = getNamesFromPeriod(selected_period)
        student_names = [i for i, var in self.top_name_vars.items()]
        if student_names:
            maX = len(max(student_names,key=len)) *14 + 15
            self.top_name_menu.configure(width=maX)
        self.top_name_menu.configure(values=student_names)

    def update_period_menu(self):
        self.periods = getDiffPeriodList()
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


        # Left side column takes full vertical space with padding at top and bottom
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, rowspan=2, sticky="ns", padx=10, pady=(10, 10))  # Takes full vertical space
        self.grid_rowconfigure(1, weight=1)

        # A or B Day Selection (set default to "A Day")
        self.ab_day_label = ctk.CTkLabel(self.left_frame, text='Select A or B Day:',font=('Arial',16,'bold'))
        self.ab_day_label.grid(row=0, column=0, pady=(10, 5))
        self.ab_day_vars = {"A Day": 'A', "B Day": "B"}
        self.ab_day_segmented = ctk.CTkSegmentedButton(self.left_frame, font=('Roboto',16),width=160,height=45,values=list(self.ab_day_vars.keys()), command=self.ab_day_function)
        global A_B
        if A_B == "A":
            self.ab_day_segmented.set("A Day")  # Set default value
        else:
            self.ab_day_segmented.set("B Day")
        self.ab_day_segmented.grid(row=1, column=0, pady=(10, 10))

        # Toggle Activity Schedule (set default to False)
        self.activity_switch = ctk.CTkSwitch(self.left_frame, text="Toggle Activity Schedule",width=60,height=30,font=('Arial',15),command=self.activity_toggle)
        if get_Activity():
            self.activity_switch.select()
        else:
            self.activity_switch.deselect()  # Set default value to False (off)
        self.activity_switch.grid(row=2, column=0, pady=(10, 10))

        # Regular buttons (no labels above)
        self.password_button = ctk.CTkButton(self.left_frame, text="Change Password", height=35,font=('Arial',16,'bold'),command=self.change_password)
        self.password_button.grid(row=3, column=0, pady=(10, 10))

        self.arrival_button = ctk.CTkButton(self.left_frame, text="Change Schedule",height=35,font=('Arial',16,'bold'), command=self.change_arrival_window)
        self.arrival_button.grid(row=4, column=0, pady=(10, 10))

        self.arrival_button2 = ctk.CTkButton(self.left_frame, text="Change Activity Schedule",height=35,font=('Arial',16,'bold'), command=self.change_activity_arrival_window)
        self.arrival_button2.grid(row=5, column=0, pady=(10, 10),padx=10)

        self.reset_button = ctk.CTkButton(self.left_frame, text="Factory Reset",height=35,font=('Arial',16,'bold'), command=self.factory_reset)
        self.reset_button.grid(row=6, column=0, pady=(10, 10))

        # Configure row stretching for the last row
        self.left_frame.grid_rowconfigure(7, weight=1)  # Ensures proper spacing at the bottom without affecting buttons

        # Top bar with period selection and entry box (full width, padding)
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 5))

        self.periods = getDiffPeriodList()
        self.period_menu = ctk.CTkComboBox(self.top_frame,dropdown_font=("Arial", 25),state='readonly', font=("Arial", 15), height=(.0666666*sHeight),values=self.periods, command=self.period_selected, width=sWidth * .24)
        self.period_menu.set('')
        self.period_menu.grid(row=0, column=0, padx=5, pady=10)
        self.period_menu.bind("<Button-1>", self.open_dropdown)

        self.entry_box = ctk.CTkEntry(self.top_frame, font=('Arial',18), height=(.0666666*sHeight),state='disabled',placeholder_text="Enter new period name", width=sWidth * .3)
        self.entry_box.grid(row=0, column=1, padx=5, pady=10)
        self.entry_box.bind("<FocusIn>", self.display_keyboard)

        # Scrollable Frame (takes remaining vertical space below top bar with padding)
        self.scrollable_frame = ctk.CTkScrollableFrame(self,label_text='Edit Student(s):',label_font=('Roboto',25,'bold'))
        self.scrollable_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=(5, 10))
        scrollbar = self.scrollable_frame._scrollbar
        scrollbar.configure(width=25)

        # Configure grid weights for resizing
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def display_keyboard(self):
        keyboardFrame.set_target(self.entry_box)
        keyboardFrame.show_keyboard()

    def open_dropdown(self,event):
        self.period_menu._open_dropdown_menu()

    def ab_day_function(self, value):
        setAorB(self.ab_day_vars.get(value))

    def activity_toggle(self):
        value = 1 if self.activity_switch.get() else 0
        setActivity(value)

    def change_password(self):
        teacherPWPopup.change_pw(True)
        teacherPWPopup.change_label('Change Teacher Password:')
        display_popup(teacherPWPopup)

    def change_arrival_window(self):
        arrivalTimeInputFrame.update_parameter(setPeriodTiming)
        arrivalTimeInputFrame.displayActivity(False)
        display_popup(arrivalTimeInputFrame)

    def change_activity_arrival_window(self):
        arrivalTimeInputFrame.update_parameter(setActivityPeriodTiming)
        arrivalTimeInputFrame.displayActivity(True)
        display_popup(arrivalTimeInputFrame)

    def factory_reset(self):
        print("Factory Reset clicked")
        # Add your functionality here

    def update_period_menu(self):
        self.periods = getDiffPeriodList()
        self.period_menu.configure(values=self.periods)

    def update_scrollableFrame_buttons(self, state):
        for button in self.scrollable_frame.winfo_children():
            button.configure(state=state)

    def period_selected(self, value):
        global currentPopup
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
        period = self.period_menu.get()
        entry_value = self.entry_box.get()
        if period:
            period_code = period[-2:]  # Extract period code
            changePeriodName(entry_value, period_code)  # Change the period name in the database
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






tempPeriodList = getPeriodList()
def buttonCommand(name, number):
    studentListPop(number, name)
    tabSwap(2)

def update_periodList(perList):
    for widget in periodList.winfo_children():
        widget.destroy()
    for i in perList:
        periodButton = ctk.CTkButton(periodList,text=(i[0] + ': ' + str(i[1])),border_color='white',border_width=2,bg_color='white',font=('Space Grotesk Medium', 20),command=lambda i0=i[0], i1=i[1]: buttonCommand(i0,i1))
        periodButton.pack(fill = 'both', expand = True)
update_periodList(tempPeriodList)


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
ctk.CTkButton(arrivalWarningFrame, image=arrivalWarningExitButtonImage, text='',command = lambda: hide_popup(arrivalWarningFrame),fg_color='#2B2B2B',border_color='#2B2B2B').pack(pady=5)

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
successLabel2.grid(row=0, column=0, pady = 30, sticky = 's')
successFrame.grid(row=0,column=0,sticky='nsew')

#PRESENT IMAGE
successCheckExitImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/successCheckExitButtonImage.png"),size=(int(sWidth/6),int(sWidth/6)))
imgSuccessLabel = ctk.CTkButton(successFrame, text='',image=successCheckExitImage, fg_color='#2B2B2B',border_color='#2B2B2B',state='disabled')
imgSuccessLabel.grid(row=1, column=0, pady=10)

#TARDY IMAGE
success_Tardy_CheckExitImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/success_Tardy_CheckExitButtonImage.png"),size=(int(sWidth/6),int(sWidth/6)))
imgSuccess_Tardy_Label = ctk.CTkButton(successFrame, text='',image=success_Tardy_CheckExitImage, fg_color='#2B2B2B',border_color='#2B2B2B',state='disabled')
imgSuccess_Tardy_Label.grid(row=1, column=0, pady=10)

#LATE IMAGE
success_Late_CheckExitImage = ctk.CTkImage(Image.open(r"/home/raspberry/Downloads/button_images/arrivalTimeWarningExitButtonImage.png"),size=(int(sWidth/6),int(sWidth/6)))
imgSuccess_Late_Label = ctk.CTkButton(successFrame, text='', image=success_Late_CheckExitImage, fg_color='#2B2B2B',border_color='#2B2B2B',state='disabled')
imgSuccess_Late_Label.grid(row=1, column=0, pady=10)

#TAB SWAPPING/POPUP DISPLAY FUNCTIONS
currentTAB = 1
def tabSwap(newTAB):
    global currentTAB
    if newTAB != currentTAB:
        currentTAB = newTAB
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
currentPopup = None
def display_popup(popup):
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
            popup.place(relx=.5,rely=.5,anchor='center')
            popup.lift()
            currentPopup = popup


def hide_popup(popup):
    popup.place_forget()
    update_buttons('normal')

def update_buttons(new_state, popup = None):
    global currentTAB
    global currentPopup
    parentDict = {1: periodList,3: historyFrame,4: teacherFrame, 5: setupFrame}

    if new_state == 'normal':
        currentPopup = None
        combostate = 'readonly'
    else:
        combostate = 'disabled'
    if currentTAB == 3 or currentTAB == 4 or currentTAB == 5:
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
    display_popup(getStudentInfoFrame)

def editAttendanceData(m, d, t, cP):
    editAttendanceFrame.setValues(m, d, t, cP)
    display_popup(editAttendanceFrame)

def successScan(time, studentName, attendance):
    status_dict = {2: ('Present', 'green', imgSuccessLabel),1: ('Tardy', 'orange', imgSuccess_Tardy_Label),0: ('Late', 'red', imgSuccess_Late_Label)}
    status, color, imgLabel = status_dict.get(attendance)
    successLabel.configure(text=status, text_color=color)
    successLabel2.configure(text=f"{studentName} checked in at {timeConvert(time)}")
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
class PeriodSelectionPopup(ctk.CTkFrame):
    def insert_text(self, entry, text):
        entry.insert(tk.END, text)

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.configure(width=(sWidth*.7), height=(sHeight*5/6),border_width=2,border_color='white',bg_color='white')
        self.pack_propagate(False)  # Prevent resizing based on widget content

        self.current_entry = None  # Track the currently selected entry
        self.macID = None
        self.editing = False

        self.nameandperiodFrame = ctk.CTkFrame(self, border_color='white',border_width=2,bg_color='white')
        self.nameandperiodFrame.pack(fill='both',expand=True)
        self.combineFrame = ctk.CTkFrame(self.nameandperiodFrame,bg_color='#333333')
        self.combineFrame.pack(anchor='center',side='bottom',pady=(0,10))
        self.exit_button = ctk.CTkButton(self.nameandperiodFrame, text="X", font=('Roboto',18,'bold'),width=(0.08333333*sHeight), height=(0.08333333*sHeight), command=self.close_popup)
        self.exit_button.place(relx=.92,rely=.02)
        self.nameFrame = ctk.CTkFrame(self.combineFrame,bg_color='#333333')
        self.nameFrame.pack(side='left',fill='y')
        self.periodFrame = ctk.CTkFrame(self.combineFrame,bg_color='#333333')
        self.periodFrame.pack(side='left')


        # Labels and Entry fields for First Name and Last Name
        self.newStudent_label = ctk.CTkLabel(self.nameandperiodFrame, text='New Student:', font=('Roboto',16,'bold'))
        self.newStudent_label.pack(side='top',pady=(10,5))
        self.first_name_label = ctk.CTkLabel(self.nameFrame, text="First Name:",font=('Roboto',15))
        self.first_name_label.pack(pady=(0,10))
        self.first_name_entry = ctk.CTkEntry(self.nameFrame,width=150,height=30,font=('Arial',14))
        self.first_name_entry.pack(padx=(10,10))

        self.last_name_label = ctk.CTkLabel(self.nameFrame, text="Last Name:",font=('Roboto',15))
        self.last_name_label.pack(pady=10)
        self.last_name_entry = ctk.CTkEntry(self.nameFrame,width=150,height=30,font=('Arial',14))
        self.last_name_entry.pack(padx=(10,10))

        # Bind click event to show on-screen keyboard
        self.first_name_entry.bind("<FocusIn>", lambda event: self.set_current_entry(self.first_name_entry))
        self.last_name_entry.bind("<FocusIn>", lambda event: self.set_current_entry(self.last_name_entry))

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

        trashImage = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/deleteIcon.png"),size=((0.08333333*sHeight),(0.08333333*sHeight)))
        self.delete_student = ctk.CTkButton(self.nameandperiodFrame, image=trashImage,text='',width=(0.08333333*sHeight), height=(0.08333333*sHeight), command=self.showCheck)


        #Submit button
        self.submit_button = ctk.CTkButton(self.nameFrame, text="Submit", font=('Arial',16),height=35,command=self.submit_and_close)
        self.submit_button.pack(pady=30)

        #Warning Label
        self.warning_label = ctk.CTkLabel(self.nameFrame,text="Missing Information!",fg_color='red',font=('Arial',16,'bold'))

        # Create on-screen keyboard and add to the frame
        self.create_keyboard()

        # Checkboxes for selecting multiple class periods
        self.class_label = ctk.CTkLabel(self.periodFrame, text="Select Class Period(s):",font=('Roboto',15))
        self.class_label.pack(pady=(0,5))

        self.period_vars = {}
        periods = getPeriodList()

        for period in periods:
            var = tk.IntVar()
            checkbox = ctk.CTkCheckBox(self.periodFrame, text=period[0] + ": " + period[1], checkbox_height=30,checkbox_width=40,font=('Arial',12), variable=var)
            checkbox.pack(anchor="w", padx=10,pady=1)
            self.period_vars[period[1]] = var

    def close_check(self):
        hide_popup(self.areyousure)

    def update_periods(self, val):
        for i, widget in enumerate(self.periodFrame.winfo_children()):
            if isinstance(widget, ctk.CTkCheckBox):
                widget.configure(text=val[i-1])

    def close_popup(self):
        hide_popup(self)
        self.reset_fields()

    def set_current_entry(self, entry):
        self.current_entry = entry

    def setMACID(self, ID):
        self.macID = ID

    def create_keyboard(self):
        # Create keyboard frame
        self.keyboard_frame = ctk.CTkFrame(self, border_width=2, border_color='white',bg_color='white')
        self.keyboard_frame.pack(side="bottom", fill="x")
        self.keyboardF = ctk.CTkFrame(self.keyboard_frame)
        self.keyboardF.place(relx=.5,rely=.5,anchor='center')

        # Add buttons for letters and numbers
        letters = "QWERTYUIXXOPASDFGHJKLZXCXXVBNM"
        keysize = ((sWidth*.8)/18)
        for i, letter in enumerate(letters):
            button = ctk.CTkButton(self.keyboardF, text=letter, width=keysize, height=keysize, command=lambda l=letter: self.insert_text(l))
            # Adjust grid placement if needed
            if i==8:
                delete_button = ctk.CTkButton(self.keyboardF, text="Delete", width=keysize*2, height=keysize, command=self.delete_text)
                delete_button.grid(row=0, column=i, columnspan=2, padx=2, pady=2)
            elif i==25:
                continue
            elif i==9:
                continue
            elif i==24:
                space_button = ctk.CTkButton(self.keyboardF, text="Space", width=keysize*2, height=keysize, command=lambda: self.insert_text(' '))
                space_button.grid(row=2, column=4, columnspan=2, padx=2, pady=2)
            else:
                button.grid(row=i//10, column=i%10, padx=2, pady=2)  # Adjust padx/pady as needed


    def insert_text(self, text):
        if self.current_entry:
            self.current_entry.insert(tk.END, text)

    def delete_text(self):
        if self.current_entry:
            current_text = self.current_entry.get()
            self.current_entry.delete(0, tk.END)
            self.current_entry.insert(0, current_text[:-1])

    def get_first_name(self):
        return self.first_name_entry.get()

    def get_last_name(self):
        return self.last_name_entry.get()

    def get_selected_periods(self):
        selected_periods = [period for period, var in self.period_vars.items() if var.get() == 1]
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
        self.first_name_entry.insert(tk.END, fname.upper())
        self.last_name_entry.insert(tk.END, lname.upper())
        for widget in self.periodFrame.winfo_children():
            if isinstance(widget, ctk.CTkCheckBox):
                for period in periods:
                    if widget.cget('text')[-2:] == period[0]:
                        widget.select()

    def submit_and_close(self):
        first_name = self.get_first_name()
        last_name = self.get_last_name()
        selected_periods = self.get_selected_periods()
        if first_name and last_name and selected_periods:
            hide_popup(self)
            if self.editing:
                getMaster("""delete from MASTER where macID = %s""", (self.macID,), False, False)
            inputStudentData(first_name, last_name, selected_periods, self.macID)
            self.reset_fields()
        else:
            self.warning_label.pack()



    def reset_fields(self):
        # Clear the text entries
        self.first_name_entry.delete(0, tk.END)
        self.last_name_entry.delete(0, tk.END)
        self.editing = False
        self.newStudent_label.configure(text='New Student:',text_color='white')
        self.delete_student.place_forget()
        self.warning_label.pack_forget()
        # Uncheck all checkboxes
        for var in self.period_vars.values():
            var.set(0)
        self.current_entry = None
getStudentInfoFrame = PeriodSelectionPopup(window)

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
        self.tab = 2 #HISTORY TAB IS 1 AND SETTINGS IS 2
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

#SET ARRIVAL TIMES
class ArrivalTimeSetup(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.configure(border_width=4, border_color='white')
        self.submit_function = setPeriodTiming
        self.tabs = []
        self.current_tab = 0
        self.periods = getPeriodList()
        self.period_data = {f"{i[0] + ': ' + i[1]}": {"arrival": "00:00", "late": "00:00"} for i in self.periods}
        self.absent_time = {'value': 0,'var':None}# Default minutes before a student is considered absent
        self.time_vars = {}
        self.setup = False

        self.setup_tabs()

        # Navigation Buttons and Submit Button setup
        self.update_tab()


    def setup_tabs(self):
        # Create each tab (Periods 1-8 and the last tab for absent time)
        time_selector_curs = db.cursor()
        for i in enumerate(self.periods):
            tab = self.create_period_tab(i, time_selector_curs)
            self.tabs.append(tab)
        time_selector_curs.close()
        self.tabs.append(self.create_absent_time_tab())

    def create_period_tab(self, period_number, curs):

        period_num = (period_number[1][0] + ': ' + period_number[1][1])
        tab = ctk.CTkFrame(self, border_width=4,border_color='white')

        # Period Label
        label = ctk.CTkLabel(tab, text=period_num, font=("Arial", 20))
        label.pack(pady=10,padx=10)

        # Arrival Time Selector
        arrival_label = ctk.CTkLabel(tab, text="Arrival Time:", font=("Arial", 16))
        arrival_label.pack(pady=5)
        arrival_frame = self.create_time_selector(tab, period_num, "arrival",curs)
        arrival_frame.pack(pady=5,padx=10)

        # Late Time Selector
        late_label = ctk.CTkLabel(tab, text="Late Time:", font=("Arial", 16))
        late_label.pack(pady=5)
        late_frame = self.create_time_selector(tab, period_num, "late",curs)
        late_frame.pack(pady=5,padx=10)

        # Navigation Arrows
        nav_frame = ctk.CTkFrame(tab,fg_color='#2B2B2B')
        nav_frame.pack(side="bottom", pady=20, fill="x",padx=10)

        # Left Arrow (not for the first tab)
        if period_number[0] > 0:
            left_button = ctk.CTkButton(nav_frame, text="←", command=self.prev_tab)
            left_button.pack(side="left", padx=20)

        # Right Arrow (not for the last tab)
        right_button = ctk.CTkButton(nav_frame, text="→", command=self.next_tab)
        right_button.pack(side="right", padx=20)

        # Exit Button
        exit_button = ctk.CTkButton(tab, text="Exit", command=self.hide)
        exit_button.pack(side="bottom", anchor="ne", padx=20, pady=10)

        return tab

    def create_absent_time_tab(self):
        tab = ctk.CTkFrame(self,border_color='white',border_width=4)

        # Absent Time Label
        label = ctk.CTkLabel(tab, text="How much time must pass before a student is absent?", font=("Arial", 18, 'bold'))
        label.pack(pady=10,padx=20)

        self.absentLabel = ctk.CTkLabel(tab,text='', font=("Arial", 14),text_color='orange')
        self.absentLabel.pack(pady=10,padx=10)

        # Time Input for Absence Minutes
        absence_frame = self.create_absent_time_selector(tab)
        absence_frame.pack(pady=10)

        # Submit Button
        submit_button = ctk.CTkButton(tab, text="Submit", command=self.submit_data)
        submit_button.pack(side="bottom", pady=10)

        #Error label
        self.error_label = ctk.CTkLabel(tab, text='')
        self.error_label.pack(side='bottom', pady=10)


        # Navigation Arrows
        nav_frame = ctk.CTkFrame(tab,fg_color='#2B2B2B')
        nav_frame.pack(side="bottom", pady=20, fill="x",padx=10)

        # Left Arrow (only if not the first tab)
        left_button = ctk.CTkButton(nav_frame, text="←", command=self.prev_tab)
        left_button.pack(side="left", padx=20)

        # Exit Button (same as other tabs)
        exit_button = ctk.CTkButton(nav_frame, text="Exit", command=self.hide)
        exit_button.pack(side="right", padx=20)

        return tab

    def create_time_selector(self, parent, period_num, time_type, cursor):
        try:
            cursor.execute("SELECT arrive, late FROM PERIODS WHERE periodNum = %s", (period_num[-2:],))
            result = cursor.fetchone()
            if result:
                earlyTime, lateTime = result[0], result[1]
            else:
                earlyTime, lateTime = 0, 0
        except:
            earlyTime, lateTime = 0, 0

        if time_type == "arrival":
            self.period_data[period_num]["arrival"] = f"{(earlyTime // 60):02d}:{(earlyTime % 60):02d}"
        else:
            self.period_data[period_num]["late"] = f"{(lateTime // 60):02d}:{(lateTime % 60):02d}"

    # Frame for Hour and Minute selectors
        time_frame = ctk.CTkFrame(parent)

        # Hour Selector
        if time_type == "arrival":
            hour_var = ctk.StringVar(value=f"{(earlyTime // 60):02d}")
        else:
            hour_var = ctk.StringVar(value=f"{(lateTime // 60):02d}")
        hour_label = ctk.CTkLabel(time_frame, textvariable=hour_var, font=("Arial", 20))
        hour_label.grid(row=1, column=0, padx=10)

        hour_up = ctk.CTkButton(time_frame, text="↑", command=lambda: self.change_hour(hour_var, period_num, time_type, +1))
        hour_up.grid(row=0, column=0, padx=10)

        hour_down = ctk.CTkButton(time_frame, text="↓", command=lambda: self.change_hour(hour_var, period_num, time_type, -1))
        hour_down.grid(row=2, column=0, padx=10)

        # Minute Selector
        if time_type == "arrival":
            minute_var = ctk.StringVar(value=f"{(earlyTime % 60):02d}")
        else:
            minute_var = ctk.StringVar(value=f"{(lateTime % 60):02d}")
        minute_label = ctk.CTkLabel(time_frame, textvariable=minute_var, font=("Arial", 20))
        minute_label.grid(row=1, column=1, padx=10)

        minute_up = ctk.CTkButton(time_frame, text="↑", command=lambda: self.change_minute(minute_var, period_num, time_type, +5))
        minute_up.grid(row=0, column=1, padx=10)

        minute_down = ctk.CTkButton(time_frame, text="↓", command=lambda: self.change_minute(minute_var, period_num, time_type, -5))
        minute_down.grid(row=2, column=1, padx=10)

        if period_num not in self.time_vars:
            self.time_vars[period_num] = {}  # Initialize if it doesn't exist

        self.time_vars[period_num][time_type] = {'hour_var': hour_var, 'minute_var': minute_var}

        return time_frame

    def create_absent_time_selector(self, parent):
        # Time selector for how many minutes pass before a student is absent
        try:
            result = getPeriod("SELECT whenAbsent FROM PERIODS", None, True)
            if result:
                abTime = result[0]
            else:
                abTime = 0
        except:
            abTime = 0
        for period in self.period_data.keys():
            self.period_data[period]["whenAbsent"] = abTime

        absent_frame = ctk.CTkFrame(parent)
        minute_var = ctk.StringVar(value=f"{abTime:02d}")

        minute_label = ctk.CTkLabel(absent_frame, textvariable=minute_var, font=("Arial", 20))
        minute_label.grid(row=1, column=0, padx=10)

        minute_up = ctk.CTkButton(absent_frame, text="↑", command=lambda: self.change_absent_time(minute_var, +1))
        minute_up.grid(row=0, column=0, padx=10)

        minute_down = ctk.CTkButton(absent_frame, text="↓", command=lambda: self.change_absent_time(minute_var, -1))
        minute_down.grid(row=2, column=0, padx=10)

        self.absent_time['value'] = abTime
        self.absent_time['var'] = minute_var
        return absent_frame

    def change_hour(self, var, period_num, time_type, delta):
        # Handle hour change for a period's time selector
        current_hour = int(var.get())
        new_hour = (current_hour + delta) % 24
        var.set(f"{new_hour:02d}")
        self.period_data[period_num][time_type] = f"{var.get()}:{self.period_data[period_num][time_type][3:]}"

    def change_minute(self, var, period_num, time_type, delta):
        # Handle minute change for a period's time selector
        current_minute = int(var.get())
        new_minute = (current_minute + delta) % 60
        var.set(f"{new_minute:02d}")
        self.period_data[period_num][time_type] = f"{self.period_data[period_num][time_type][:3]}{var.get()}"

    def change_absent_time(self, var, delta):
        # Handle minute change for the absent time selector
        current_time = int(var.get())
        new_time = max(0, current_time + delta)  # No negative time allowed
        var.set(f"{new_time}")
        self.absent_time['value'] = new_time

    def next_tab(self):
        if self.current_tab < 9:
            self.current_tab += 1
        self.update_tab()

    def prev_tab(self):
        if self.current_tab > 0:
            self.current_tab -= 1
        self.update_tab()

    def update_tab(self):
        for tab in self.tabs:
            tab.pack_forget()
        self.tabs[self.current_tab].pack(fill="both", expand=True)

    def hide(self):
        hide_popup(self)

    def update_setup(self, val):
        self.setup = val

    def update_parameter(self, param):
        self.submit_function = param

    def displayActivity(self, value):
        if value:
            self.absentLabel.configure(text='Tip: Give leniency on activity schedule')
            self.reset_fields('ACTIVITY')
        else:
            self.absentLabel.configure(text='')
            self.reset_fields('PERIODS')

    def update_exit(self, val):
        if val:
            #add exits back
            pass
        else:
            #remove exits
            pass

    def reset_fields(self, table):
        reset_curs = db.cursor()
        query = "SELECT arrive, late, whenAbsent FROM " + table + " WHERE periodNum = %s"
        for period_num, period_info in self.period_data.items():
            try:
                reset_curs.execute(query, (period_num[-2:],))
                result = reset_curs.fetchone()
                if result:
                    earlyTime, lateTime = result[0], result[1]
                else:
                    earlyTime, lateTime = 0, 0
            except:
                earlyTime, lateTime = 0, 0
            self.period_data[period_num]["arrival"] = f"{(earlyTime // 60):02d}:{(earlyTime % 60):02d}"
            self.period_data[period_num]["late"] = f"{(lateTime // 60):02d}:{(lateTime % 60):02d}"
            for time_type in self.time_vars[period_num]:
                if time_type == 'arrival':
                    self.time_vars[period_num][time_type]['hour_var'].set(f"{(earlyTime // 60):02d}")
                    self.time_vars[period_num][time_type]['minute_var'].set(f"{(earlyTime % 60):02d}")
                else:
                    self.time_vars[period_num][time_type]['hour_var'].set(f"{(lateTime // 60):02d}")
                    self.time_vars[period_num][time_type]['minute_var'].set(f"{(lateTime % 60):02d}")
            self.absent_time['value'] = result[2]
            self.absent_time['var'].set(f"{result[2]:02d}")
        reset_curs.close()



        self.error_label.configure(text="",fg_color='#2B2B2B')
        self.current_tab = 0
        self.update_tab()
        #for tab in self.tabs:


    def submit_data(self):
        # Check if all periods have input
        submit = True
        for period in self.period_data:
            if self.period_data[period]["arrival"] == "00:00" or self.period_data[period]["late"] == "00:00":
                self.error_label.configure(text="   Missing input data!   ",fg_color='red')
                submit = False
        if submit:
            period_times = [(period, data["arrival"], data["late"]) for period, data in self.period_data.items()]
            self.submit_function(period_times, self.absent_time['value'])
            hide_popup(self)
            if self.setup:
                if self.submit_function == setActivityPeriodTiming:
                    self.update_setup(False)
                    teacherPWPopup.update_setup(True)
                    setupFrame.top_bar.pack_forget()
                    teacherFrame.change_password()
                else:
                    setupFrame.schedule_type_label.configure(text='Input Activity Schedule Arrival Times:')
                    teacherFrame.change_activity_arrival_window()
arrivalTimeInputFrame = ArrivalTimeSetup(window)

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
         self.title_label = ctk.CTkLabel(self.titleFrame, text="Is Friday an A or B Day?", font=("Roboto", 20,'bold'))
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
         setAorB(daytype)
         if daytype == 'A':
             teacherFrame.ab_day_segmented.set("A Day")
         else:
             teacherFrame.ab_day_segmented.set("B Day")
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
         self.side_keys = ["Delete", "Rename", "Caps", "Clear", "EXIT"]


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
                 if widget.cget("text") == "CAPS":
                     new_text="Caps"
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
         elif key == "Caps":
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
             else:
                 self.target_entry.insert("end", key.lower())
                 self.copy_entry.insert("end", key.lower())


     def show_keyboard(self, event=None):
         """Place the keyboard at the center of the screen."""
         display_popup(self)


     def hide_keyboard(self, event=None):
         """Remove the keyboard from the screen."""
         self.focus_set()
         hide_popup(self)
keyboardFrame = CustomKeyboard(window)

def main():
    global schedtype
    if not schedtype:
        tabSwap(5)
    else:
        timeFunc()
        updateArriveTimes()
        updateActivityArriveTimes()
        periodList.lift()
        awaitingFrame.lift()
        spinning_image.start_spinning()
        checkin_thread = threading.Thread(target=checkIN, daemon=True)
        checkin_thread.start()
    window.mainloop()
main()