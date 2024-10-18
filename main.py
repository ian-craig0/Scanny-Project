 #THREADING
import threading

#ANIMATION
import os
import glob

#RFID SCANNER AND MYSQL IMPORTS
from PiicoDev_RFID import PiicoDev_RFID
from PiicoDev_Unified import sleep_ms
import MySQLdb


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


#SQL MANAGEMENT
db = MySQLdb.connect(host='localhost',user='root',passwd='seaside',db='scanner',autocommit=True)
cur = db.cursor()   #allows queries

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

def setupMode():
    #MOVE ACCESSOR TO TEACHER MODE AND PROMPT SOMEHOW FOR SCHEDULE TYPE AND ARRIVAL TIMES
    print('we in setup')



#UPDATING FUNCTIONS
#STUDENTLIST POPULATION
def studentListPop(periodNumber, periodName):
    studentListCursor = db.cursor()
    for widget in studentList.winfo_children():
        widget.destroy()
    studentList.configure(label_text=(periodName + ': ' + str(periodNumber)))
    studentListCursor.execute('SELECT * FROM MASTER WHERE period = %s', (periodNumber,))
    tempMASTERLIST = studentListCursor.fetchall()
    if tempMASTERLIST:
        for index, student in enumerate(tempMASTERLIST):
            name = (student[1].capitalize() + ' ' + student[2].capitalize())
            studentListCursor.execute('SELECT time, present FROM SCANS WHERE macID = %s AND date = %s AND currentPeriod = %s',(student[0], strftime("%m-%d-%Y"), periodNumber))
            tempSCANSLIST = studentListCursor.fetchall()
            if tempSCANSLIST:
                present = tempSCANSLIST[0][1]
            else:
                present = 0

            studentFrame = ctk.CTkFrame(studentList, height=int(0.025*sHeight),border_width=2, border_color='white')
            if present == 2:
                studentFrame.configure(fg_color='green')
                presentImage = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/periodListCheck.png"),size=(40,30))
                ctk.CTkLabel(studentFrame, text=(name.strip() + ' - Checked in at ' + timeConvert(tempSCANSLIST[0][0])),text_color='white', font=('Roboto', 15)).pack(side='left', padx=5, pady=2)
                ctk.CTkLabel(studentFrame, image=presentImage, text='',fg_color='transparent').pack(padx=5,pady=5,side='left')
            elif present == 1:
                studentFrame.configure(fg_color='orange')
                #presentImage = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/periodListCheck.png"))
                ctk.CTkLabel(studentFrame, text=(name.strip() + ' - Checked in late at ' + timeConvert(tempSCANSLIST[0][0])),text_color='white', font=('Roboto', 15)).pack(side='left', padx=5, pady=2)
                #ctk.CTkLabel(studentFrame, image=presentImage, text='',fg_color='transparent').pack(padx=5,pady=2,side='left')
            else:
                studentFrame.configure(fg_color='red')
                #presentImage = ctk.CTkImage(light_image=Image.open(r"/home/raspberry/Downloads/button_images/periodListCheck.png"))
                ctk.CTkLabel(studentFrame, text=(name.strip() + ' - Absent'), text_color='white', font=('Roboto', 15)).pack(side='left', padx=5, pady=2)
                #ctk.CTkLabel(studentFrame, image=presentImage, text='',fg_color='transparent').pack(padx=5,pady=2,side='left')

            # Calculate row and column dynamically
            row = index // 2  # Every two students per row
            column = index % 2

            studentFrame.grid(row=row, column=column, pady=10, sticky='nswe', padx=3)
    studentListCursor.close()



#PERIODLIST UPDATING
def updatePeriodList(newName, periodNum):
    for button in periodList.winfo_children():
        if button.cget('text')[-2:] == periodNum:
            button.configure(text=newName + ": " + periodNum)



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
def getActivity():
    cur.execute("""select ACTIVITY from TEACHERS""")
    activity = cur.fetchone()
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
    cur.execute("""select periodName, periodNum from PERIODS""")
    periodList1 = cur.fetchall()
    return periodList1

def getName(id):
    cur.execute("""select firstNAME, lastNAME from MASTER where macID = %s""", (id,))
    firstLast = cur.fetchone()
    return (firstLast[0].capitalize() + " " + firstLast[1].capitalize())

def getFirstLastName(id):
    cur.execute("""select firstNAME, lastNAME from MASTER where macID = %s""", (id,))
    firstLast = cur.fetchone()
    print(firstLast)
    return firstLast[0], firstLast[1]

def getNamesFromPeriod(periodNumb):
    periodNumber = periodNumb[-2:]
    cur.execute("""select macID, firstNAME, lastNAME from MASTER where period = %s""", (periodNumber,))
    studentNames = cur.fetchall()
    tempDict = {}
    for i in studentNames:
        tempDict[(i[1].capitalize() + " " + i[2].capitalize())] = i[0]
    return tempDict

def getTeacherPW():
    cur.execute("""select teacherPW from TEACHERS""")
    return cur.fetchone()[0]

def getSchedType():
    cur.execute("""select SCHEDULE from TEACHERS""")
    schedType = cur.fetchone()
    if schedType:
        return schedType[0]
    else:
        return ()

def getAorB():
    cur.execute("""select A_B from TEACHERS""")
    activity = cur.fetchone()
    if activity is None:
        return None
    return activity[0]

schedtype = getSchedType()
def getCurrentPeriod(time):
    currentperiod = ""
    global arriveTimes
    global schedtype
    tempTimes = arriveTimes
    if schedtype == 'block':
        AB = getAorB()
        if AB == 'A':
            tempTimes = tempTimes[:-4]
        else:
            tempTimes = tempTimes[4:]
    for i in tempTimes:
        if i[1] <= time:
            currentperiod = i[0]
        else:
            break
    return currentperiod

def getStudentPeriods(macID):
    cur.execute("""SELECT period from MASTER WHERE macID = %s""", (macID,))
    return cur.fetchall()

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
        cur.execute("""INSERT INTO MASTER(macID, firstNAME, lastNAME, period) values (%s, %s, %s, %s)""", (id,fName.lower(),lName.lower(),period))

arriveTimes = None
def updateArriveTimes():
    global arriveTimes
    cur.execute("""SELECT periodNum, arrive from PERIODS""")
    arriveTimes = cur.fetchall()

activityArriveTimes = None
def updateActivityArriveTimes():
    global activityArriveTimes
    cur.execute("""SELECT periodNum, arrive from ACTIVITY""")
    activityArriveTimes = cur.fetchall()


def setAorB(AB):
    cur.execute("""update TEACHERS set A_B = %s""", (AB,))

def setActivity(val):
    cur.execute("""update TEACHERS set ACTIVITY = %s""", (val,))

def setPeriodTiming(periodInfo, absentTime):
    for period in periodInfo:
        periodNumber = period[0][-2:]
        arrival = time_to_minutes(period[1])
        late = time_to_minutes(period[2])
        cur.execute("""update PERIODS set arrive = %s, late = %s, whenAbsent = %s where periodNum = %s""", (arrival,late,absentTime,periodNumber))
    updateArriveTimes()

def setActivityPeriodTiming(periodInfo, absentTime):
    for period in periodInfo:
        periodNumber = period[0][-2:]
        arrival = time_to_minutes(period[1])
        late = time_to_minutes(period[2])
        cur.execute("""update ACTIVITY set arrive = %s, late = %s, whenAbsent = %s where periodNum = %s""", (arrival,late,absentTime,periodNumber))
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
    cur.execute("""TRUNCATE TABLE PERIODS""")
    cur.executemany("""INSERT INTO PERIODS(periodNum, periodName, arrive, late, whenAbsent) values(%s,%s,%s,%s,%s)""",data)

def changePeriodName(name, per):
    cur.execute("""update PERIODS set periodName = %s where periodNum = %s""", (name, per))
    cur.execute("""update ACTIVITY set periodName = %s where periodNum = %s""", (name,per))
    updatePeriodList(name, per)


#NEW DAY FUNCTION
def newDay():
    if getActivity():
        #CHANGE ARRIVAL TIMES BACK TO NORMAL TIMES
        setActivity(0) #RESET ACTIVITY SCHEDULE EVERY DAY

    #UPDATE A/B DAY
    day = (date.today().weekday())
    if getSchedType() == 'block':
        if day == 4: #IS IT FRIDAY CHECK
            display_popup(fridayperiodframe)
        else:
            if (day == 0 or day == 2):
                setAorB('A')
            elif (day == 1 or day == 3):
                setAorB('B')

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


#CHECK IN FUNCTION
def checkIN():
    while True:
        current_time = time_to_minutes(strftime("%H:%M"))
        current_period = getCurrentPeriod(current_time)
        current_date = strftime("%m-%d-%Y")
        if rfid.tagPresent():
            ID = rfid.readID()
            if ID:
                if str(ID) == "04:F7:2C:0A:68:19:90":
                    if teacherPWPopup.getDisplayed():
                        teacherPWPopup.close_popup()
                        tabSwap(teacherPWPopup.get_tab()+2)
                        sleep_ms(3000)
                elif currentTAB == 1 or currentTAB == 2:
                    checkInCursor = db.cursor()
                    checkInCursor.execute("""SELECT arrive from PERIODS""")
                    arriveTimes = checkInCursor.fetchall()
                    check = True
                    for i in arriveTimes:
                        if None in i:
                            check = False
                            break
                        else:
                            continue
                    if check: #CHECK IF ARRIVAL TIMES ARE CREATED
                        studentPeriodList = getStudentPeriods(ID)
                        if studentPeriodList: #CHECK IF A PERIOD IS RETURNED (IF THEY'RE IN THE MASTER LIST)
                            #CHECK IF STUDENT IS IN THE CURRENT PERIOD
                            ABperiods = getABperiods(studentPeriodList, (getAorB()))
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
                                        if getActivity():
                                            checkInCursor.execute("""SELECT periodName, arrive, late, whenAbsent FROM ACTIVITY where periodNum = %s""", (period,))
                                        else:
                                            checkInCursor.execute("""SELECT periodName, arrive, late, whenAbsent FROM PERIODS WHERE periodNum = %s""", (period,))
                                        periodData = checkInCursor.fetchall()
                                        present = getAttendance(current_time, periodData)
                                        #ADD CHECK FOR DOCTORS APPOINTMENT IF MARKED ABSENT
                                        name = getName(ID)
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
                        display_popup(arrivalWarningFrame)
                    checkInCursor.close()
                sleep_ms(100)
            else:
                sleep_ms(100)




#FRAME CLASSES
#HISTORY MODE FRAME
class historyFrameClass(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Part 1: Top Section with Period and Student Name dropdowns
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Period selection in top bar
        self.top_period_var = StringVar()
        self.top_period_label = ctk.CTkLabel(self.top_frame, text="Select Period For Student:", font=("Arial", 18,'bold'))
        self.top_period_label.grid(row=0, column=0, padx=5,pady=(10, 5), sticky="w")

        self.periods = [f"{i[0]}: {i[1]}" for i in getPeriodList()]
        maX = len(max(self.periods,key=len)) *10 + 10
        self.top_period_menu = ctk.CTkComboBox(self.top_frame, values=self.periods, variable=self.top_period_var, height=(.0666666*sHeight),width=maX, font=("Arial", 18), command=self.update_student_menu,dropdown_font=('Arial',25), state='readonly')
        self.top_period_menu.bind("<Button-1>", lambda event: self.top_period_menu.event_generate('<Alt-Down>'))
        self.top_period_menu.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Student name selection (initially empty, will be populated later)
        self.top_name_vars = {}
        self.top_name_var = StringVar()
        self.top_name_label = ctk.CTkLabel(self.top_frame, text="Select Student:", font=("Arial", 18,'bold'))
        self.top_name_label.grid(row=0, column=1, pady=(10, 5), sticky="w")

        self.top_name_check_var = BooleanVar()
        self.top_name_check = ctk.CTkCheckBox(self.top_frame, text="", checkbox_height=45,checkbox_width=45,variable=self.top_name_check_var)
        self.top_name_check.grid(row=0, column=2,rowspan=2,padx=20, pady= 8,sticky='s')

        self.top_name_menu = ctk.CTkComboBox(self.top_frame, values=[], state='readonly', variable=self.top_name_var, height=(.0666666*sHeight),width=.2*sWidth, font=("Arial", 18),dropdown_font=('Arial',25))
        self.top_name_menu.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="ew")

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

        self.period_menu = ctk.CTkComboBox(self.column_frame,state='readonly',values=self.periods, variable=self.period_var, height=(.0666666*sHeight), font=("Arial", 14),dropdown_font=('Arial',25))
        self.period_menu.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        # Date selection
        self.month_var = IntVar(value=datetime.now().month)
        self.day_var = IntVar(value=datetime.now().day)

        self.tempframe2 = ctk.CTkFrame(self.column_frame,fg_color='#2b2b2b')
        self.tempframe2.grid(row=2, column=0, padx=5,columnspan=2, sticky="we")
        self.date_label = ctk.CTkLabel(self.tempframe2, text="Select Date:", font=("Arial", 18,'bold'))
        self.date_label.pack(side='left')

        self.date_check_var = BooleanVar()
        self.date_check = ctk.CTkCheckBox(self.tempframe2, text="", checkbox_height=45,checkbox_width=45,variable=self.date_check_var)
        self.date_check.pack(side='right',pady=2,padx=(94,0))

        self.date_frame = ctk.CTkFrame(self.column_frame)
        self.date_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

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
        self.tempframe3.grid(row=4, column=0, padx=5,columnspan=2, sticky="we")
        self.attendance_label = ctk.CTkLabel(self.tempframe3, text="Select Attendance:", font=("Arial", 18,'bold'))
        self.attendance_label.pack(side='left')

        self.attendance_check_var = BooleanVar()
        self.attendance_check = ctk.CTkCheckBox(self.tempframe3, text="", checkbox_height=45,checkbox_width=45,variable=self.attendance_check_var)
        self.attendance_check.pack(side='right',pady=2,padx=(35,0))

        self.attendance_vars = {"Present": 2, "Tardy": 1, "Absent": 0}
        self.attendance_var = StringVar()
        self.attendance_menu = ctk.CTkComboBox(self.column_frame, state='readonly', values=list(self.attendance_vars.keys()), variable=self.attendance_var, height=(.0666666*sHeight), font=("Arial", 15),dropdown_font=('Arial',25))
        self.attendance_menu.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        # Submit Button
        self.submit_button = ctk.CTkButton(self.column_frame, text="Submit", command=self.fetch_students, height=50, font=("Arial", 18,'bold'))
        self.submit_button.grid(row=6, column=0, columnspan=2, pady=10, padx=10)

        # Part 3: Scrollable Frame (unchanged)
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=1, column=1, pady=10, sticky="nsew")
        scrollbar = self.scrollable_frame._scrollbar
        scrollbar.configure(width=25)

        # Make sure the frame expands
        self.grid_rowconfigure(1, weight=1)

        self.grid_columnconfigure(1, weight=1)

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
        self.periods = [f"{i[0]}: {i[1]}" for i in getPeriodList()]
        self.top_period_menu.configure(values=self.periods)
        self.period_menu.configure(values=self.periods)

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
            query = "SELECT * FROM SCANS WHERE " + " AND ".join(filters)
            cur.execute(query, variables)
            students = cur.fetchall()


            # Display the fetched students in the scrollable frame
            col = 0  # To track column placement

            for i, student in enumerate(students):
                macID, date, time, present, currentPeriod = student
                name = getName(macID)
                time_str = timeConvert(time)
                attendance = "Absent" if present == 0 else "Tardy" if present == 1 else "Present"
                text_color = "red" if present == 0 else "orange" if present == 1 else "green"
                display_text = f"{name} checked in to {currentPeriod} at {time_str}\n{date}: {attendance}"

                # Create a small frame for each student's data with some stylish improvements
                student_frame = ctk.CTkButton(
                    self.scrollable_frame, height=35,
                    fg_color=text_color,  # Set background color
                    corner_radius=10,  # Rounded corners
                    border_color="gray",
                    border_width=2,
                    font=("Arial", 15, 'bold'),
                    text_color='white',
                    text=display_text,
                    anchor='center',
                    command=lambda i0=macID, i1=date, i2=time, i3=currentPeriod: editAttendanceData(i0,i1,i2,i3)
                )

                student_frame.grid(row=i // 2, column=col, padx=10, pady=10, sticky="nsew")

                # Move to the next column for a 2-column layout
                col = (col + 1) % 2

            # Update layout and style to ensure even distribution
            self.scrollable_frame.grid_columnconfigure(0, weight=1)
            self.scrollable_frame.grid_columnconfigure(1, weight=1)








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
        if getAorB() == "A":
            self.ab_day_segmented.set("A Day")  # Set default value
        else:
            self.ab_day_segmented.set("B Day")
        self.ab_day_segmented.grid(row=1, column=0, pady=(10, 10))

        # Toggle Activity Schedule (set default to False)
        self.activity_switch = ctk.CTkSwitch(self.left_frame, text="Toggle Activity Schedule",width=60,height=30,font=('Arial',15),command=self.activity_toggle)
        if getActivity():
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

        self.periods = [f"{i[0]}: {i[1]}" for i in getPeriodList()]
        self.period_menu = ctk.CTkComboBox(self.top_frame,dropdown_font=("Arial", 25),state='readonly', font=("Arial", 15), height=(.0666666*sHeight),values=self.periods, command=self.period_selected, width=sWidth * .24)
        self.period_menu.set('')
        self.period_menu.grid(row=0, column=0, padx=5, pady=10)

        self.entry_box = ctk.CTkEntry(self.top_frame, font=('Arial',18), height=(.0666666*sHeight),placeholder_text="Enter new period name", width=sWidth * .3)
        self.entry_box.grid(row=0, column=1, padx=5, pady=10)

        self.submit_button = ctk.CTkButton(self.top_frame, text="Rename", height=35,font=('Arial',18,'bold'),command=self.submit_function)
        self.submit_button.grid(row=0, column=2, padx=5, pady=10)

        # Scrollable Frame (takes remaining vertical space below top bar with padding)
        self.scrollable_frame = ctk.CTkScrollableFrame(self,label_text='Edit Student(s):',label_font=('Roboto',25,'bold'))
        self.scrollable_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=(5, 10))
        scrollbar = self.scrollable_frame._scrollbar
        scrollbar.configure(width=25)

        # Configure grid weights for resizing
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

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
        self.periods = [f"{i[0]}: {i[1]}" for i in getPeriodList()]
        self.period_menu.configure(values=self.periods)

    def update_scrollableFrame_buttons(self, state):
        for button in self.scrollable_frame.winfo_children():
            button.configure(state=state)

    def period_selected(self, value):
        period = value[-2:]
        cur.execute("""SELECT macID FROM MASTER where period = %s""", (period,))
        students = cur.fetchall()

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        col = 0  # To track column placement

        for i, student in enumerate(students):
            macID = student
            display_text = getName(macID)

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

    def submit_function(self):
        period = self.period_menu.get()
        entry_value = self.entry_box.get()
        if period:
            period_code = period[-2:]  # Extract period code
            changePeriodName(entry_value, period_code)  # Change the period name in the database
            self.periods = [f"{i[0]}: {i[1]}" for i in getPeriodList()]  # Update the period list
            self.period_menu.configure(values=self.periods)  # Update the dropdown menu with the new periods
            self.period_menu.set(f"{entry_value}: {period_code}")  # Auto-update the selected value to reflect the change
        self.entry_box.delete(0, tk.END)  # Clear the entry box after submission












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
timeLabel= ctk.CTkLabel(leftBAR,font=('Roboto', 20, 'bold'), text_color='white')
timeLabel.pack(side='left',pady=5,padx=(20,0))

#DATE LABEL CREATION
dateLabel= ctk.CTkLabel(leftBAR,font=('Roboto', 20, 'bold'), text_color='white')
dateLabel.pack(side='right',pady=5,padx=(0,20))

#RIGHT SIDE OF BAR CREATION
rightBAR =ctk.CTkFrame(topBAR,border_width=4,border_color='white',bg_color='white')
rightBAR.columnconfigure(0, weight=1,)
rightBAR.columnconfigure(1, weight=1,)
rightBAR.columnconfigure(2, weight=1,)
rightBAR.rowconfigure(0, weight=1)
rightBAR.grid(row=0,column=1,sticky='nsew')

#MENU BUTTON CREATION
menuButton = ctk.CTkButton(rightBAR, text='Main Menu',font=('Roboto', 25, 'bold'), text_color='white',command=lambda: tabSwap(1))
menuButton.grid(row=0,column=0,pady=10)

#HISTORY BUTTON CREATION
#def toHistory():
historyButton = ctk.CTkButton(rightBAR, text='History',font=('Roboto', 25, 'bold'), text_color='white',command=lambda: historySettingButtons(3,1))
historyButton.grid(row=0,column=1,pady=10)

#TEACHER MODE BUTTON
teacherButton = ctk.CTkButton(rightBAR, text='Settings',font=('Roboto', 25, 'bold'), text_color='white', command= lambda: historySettingButtons(4,2))
teacherButton.grid(row=0,column=2,pady=10)







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
awaitingLabel = ctk.CTkLabel(awaitingFrame, text="Awaiting Scan", font=('Roboto', 40, 'bold'), text_color='white')
awaitingLabel.grid(row=0, column=0,sticky="s",pady=40)
awaitingFrame.grid(row=0,column=0,sticky='nsew')


studentList = ctk.CTkScrollableFrame(displayedTabContainer, border_color = 'white', border_width = 4, label_text="Period A1", label_font = ('Roboto', 30),bg_color='white')
scrollbar = studentList._scrollbar
scrollbar.configure(width=25)
studentList.columnconfigure(0, weight=1)
studentList.columnconfigure(1, weight=1)
for i in range(80):
    studentList.rowconfigure(i,weight=1)
studentList.grid(row=0,column=1,sticky='nsew')


periodList = ctk.CTkFrame(displayedTabContainer, width=(sWidth*2/3), height=sHeight, border_color = 'white', border_width = 4, bg_color='white')
periodList.pack_propagate(0)
periodList.grid(row=0,column=1,sticky='nsew')
tempPeriodList = getPeriodList()
def buttonCommand(name, number):
    studentListPop(number, name)
    tabSwap(2)
for i in tempPeriodList:
    periodButton = ctk.CTkButton(periodList,text=(i[0] + ': ' + str(i[1])),border_color='white',border_width=2,bg_color='white',font=('Roboto', 20, 'bold'),command=lambda i0=i[0], i1=i[1]: buttonCommand(i0,i1))
    periodButton.pack(fill = 'both', expand = True)

'''
#STUDENT AWAITING GIF
class AwaitingAnimation(tk.Frame):
    def __init__(self, master, image_folder, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.image_folder = image_folder
        self.images = self.load_images()
        self.index = 0
        self.label = ctk.CTkLabel(self)
        self.label.pack()

        self.is_visible = False  # Track visibility
        self.animation_running = False  # Track animation state

    def load_images(self):
        # Load images from the specified folder
        image_files = glob.glob(os.path.join(self.image_folder, "*.png"))  # Change "*.png" if needed
        images = [ImageTk.PhotoImage(Image.open(image)) for image in image_files]
        return images

    def animate(self):
        if self.images and self.is_visible:
            # Update the label with the next image
            self.label.configure(image=self.images[self.index])
            self.index = (self.index + 1) % len(self.images)  # Loop back to the start
            self.after(300, self.animate)  # Adjust the delay as needed (in milliseconds)

    def start_animation(self):
        self.is_visible = True  # Set visibility flag to True
        if not self.animation_running:
            self.animation_running = True
            self.animate()  # Start the animation loop

    def stop_animation(self):
        self.is_visible = False  # Set visibility flag to False
        self.animation_running = False  # Stop the animation loop
animation_frame = AwaitingAnimation(awaitingFrame, r"/home/raspberry/Downloads/loadingAnimation")  # Replace with your folder path
animation_frame.grid(row=1,column=0,sticky='n',pady=20)'''


#POP UP WIDGETS (ASKING FOR INFO)
#ARRIVAL TIME NEEDS INPUT WARNING
arrivalWarningFrame = ctk.CTkFrame(window,width=(sWidth/3), height=(sHeight/4), border_color= 'white', border_width=4, bg_color='white')
arrivalWarningFrame.pack_propagate(0)
arrivalWarningTOPBAR = ctk.CTkFrame(arrivalWarningFrame,width=((sWidth-16)/2),height=(sHeight/18),border_color='white',border_width=4,bg_color='white')
arrivalWarningTOPBAR.pack_propagate(0)
arrivalWarningTOPBAR.pack(side='top')
ctk.CTkLabel(arrivalWarningTOPBAR, text='Warning!', font=('Roboto', 25, 'bold'), text_color='red').place(relx=.5,rely=.5,anchor='center')
ctk.CTkLabel(arrivalWarningFrame, text="Students cannot check in until the teacher\nhas assigned arrival times for each period.", font=('Roboto', 14, 'bold'), text_color='red').pack(pady=10)


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
            awaitingFrame.lift()
            #animation_frame.start_animation()
        elif newTAB == 2: #DISPLAY LIST OF STUDENTS
            studentList.lift()
            awaitingFrame.lift()
            #animation_frame.start_animation()
        elif newTAB == 3: #DISPLAY HISTORY FRAME
            historyFrame.update_period_menu()
            historyFrame.fetch_students()
            historyFrame.lift()
        elif newTAB == 4: #DISPLAY TEACHER MODE FRAME
            teacherFrame.update_period_menu()
            teacherFrame.lift()

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
            update_buttons('disabled')
            popup.place(relx=.5,rely=.5,anchor='center')
            currentPopup = popup


def hide_popup(popup):
    popup.place_forget()
    update_buttons('normal')

def update_buttons(new_state):
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
                    elif isinstance(widget, ctk.CTkFrame):
                        for item in widget.winfo_children():
                            if isinstance(item, ctk.CTkButton):
                                item.configure(state=new_state)
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

        self.areyousure = ctk.CTkFrame(parent,width=sWidth/4,height=sHeight/6,border_width=2,border_color='white',bg_color='white')
        self.areyousure.pack_propagate(0)
        self.areyousurelabel = ctk.CTkLabel(self.areyousure, text='Are you sure?',font=('Arial',18,'bold'))
        self.areyousurelabel.pack(pady=(15,5))
        self.tempFrame = ctk.CTkFrame(self.areyousure)
        self.tempFrame.pack()
        self.areyousureyes = ctk.CTkButton(self.tempFrame, text="Yes", width=75, height=35, command=self.deletestudent)
        self.areyousureyes.pack(side='left')
        self.areyousureexit = ctk.CTkButton(self.tempFrame, text="No", width=75, height=35, command=self.close_check)
        self.areyousureexit.pack(side='right')

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
        self.areyousure.place_forget()
        update_buttons('normal')


    def close_popup(self):
        self.place_forget()
        update_buttons("normal")
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
        self.close_popup()
        display_popup(self.areyousure)

    def deletestudent(self):
        self.close_check()
        cur.execute("""delete from MASTER where macID = %s""", (self.macID,))
        cur.execute("""delete from SCANS where macID = %s""", (self.macID,))
        teacherFrame.period_selected(teacherFrame.period_menu.get())


    def setStudentData(self):
        self.editing = True
        self.delete_student.place(relx=.01,rely=.02)
        self.newStudent_label.configure(text='Edit Student Data: ',text_color='orange')
        fname, lname = getFirstLastName(self.macID)
        periods = getStudentPeriods(self.macID)
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
            self.place_forget()
            update_buttons("normal")
            if self.editing:
                cur.execute("""delete from MASTER where macID = %s""", (self.macID,))
            inputStudentData(first_name, last_name, selected_periods, self.macID)
            self.reset_fields()
        else:
            self.warning_label.pack()



    def reset_fields(self):
        # Clear the text entries
        self.first_name_entry.delete(0, tk.END)
        self.last_name_entry.delete(0, tk.END)
        self.macID= None
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
            cur.execute("""update TEACHERS set teacherPW = %s""", (entered_password,))
        else:
            if entered_password == getTeacherPW() or entered_password == "445539":
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
        self.place_forget()
        update_buttons('normal')
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
        self.absent_time = 0  # Default minutes before a student is considered absent



        self.setup_tabs()

        # Navigation Buttons and Submit Button setup
        self.update_tab()


    def setup_tabs(self):
        # Create each tab (Periods 1-8 and the last tab for absent time)
        for i in enumerate(self.periods):
            tab = self.create_period_tab(i)
            self.tabs.append(tab)
        self.tabs.append(self.create_absent_time_tab())

    def create_period_tab(self, period_number):
        period_num = (period_number[1][0] + ': ' + period_number[1][1])
        tab = ctk.CTkFrame(self, border_width=4,border_color='white')

        # Period Label
        label = ctk.CTkLabel(tab, text=period_num, font=("Arial", 20))
        label.pack(pady=10,padx=10)

        # Arrival Time Selector
        arrival_label = ctk.CTkLabel(tab, text="Arrival Time:", font=("Arial", 16))
        arrival_label.pack(pady=5)
        arrival_frame = self.create_time_selector(tab, period_num, "arrival")
        arrival_frame.pack(pady=5,padx=10)

        # Late Time Selector
        late_label = ctk.CTkLabel(tab, text="Late Time:", font=("Arial", 16))
        late_label.pack(pady=5)
        late_frame = self.create_time_selector(tab, period_num, "late")
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

    def create_time_selector(self, parent, period_num, time_type):
        try:
            cur.execute("SELECT arrive, late FROM PERIODS WHERE periodNum = %s", (period_num[-2:],))
            result = cur.fetchone()
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

        return time_frame

    def create_absent_time_selector(self, parent):
        # Time selector for how many minutes pass before a student is absent
        try:
            cur.execute("SELECT whenAbsent FROM PERIODS")
            result = cur.fetchone()
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
        self.absent_time = new_time

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
        self.place_forget()
        update_buttons('normal')
        self.reset_fields()

    def update_parameter(self, param):
        self.submit_function = param

    def displayActivity(self, value):
        if value:
            self.absentLabel.configure(text='Tip: Give leniency on activity schedule')
        else:
            self.absentLabel.configure(text='')

    def reset_fields(self):
        for period_num, period_info in self.period_data.items():
            try:
                cur.execute("SELECT arrive, late FROM PERIODS WHERE periodNum = %s", (period_num[-2:],))
                result = cur.fetchone()
                if result:
                    earlyTime, lateTime = result[0], result[1]
                else:
                    earlyTime, lateTime = 0, 0
            except:
                earlyTime, lateTime = 0, 0


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
            self.submit_function(period_times, self.absent_time)
            self.place_forget()
            update_buttons('normal')
            self.reset_fields()
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
        self.attendance_dropdown = ctk.CTkComboBox(self, variable=self.attendance_var,values = list(self.attendance_mapping.keys()),height=45,dropdown_font=('Arial',25),width=200,state='readonly')
        self.attendance_dropdown.set("")
        self.attendance_dropdown.pack(pady=10)

        # Submit button
        self.submit_button = ctk.CTkButton(self, text="Submit", font=('Arial',18),height=35,command=self.submit_attendance)
        self.submit_button.pack(pady=25)

    def setValues(self, macID, date, time, currentPeriod):
        self.macID = macID
        self.date = date
        self.time = time
        self.currentPeriod = currentPeriod

    def delete_attendance(self):
        cur.execute("""delete FROM SCANS where macID = %s and date = %s and time = %s and currentPeriod = %s""", (self.macID,self.date,self.time,self.currentPeriod))
        historyFrame.fetch_students()
        self.hide()

    def hide(self):
        self.place_forget()
        update_buttons('normal')

    def submit_attendance(self):
        self.hide() # Hide the frame
        selected_status = self.attendance_var.get()# Get the selected string value
        if selected_status:
            attendance_value = self.attendance_mapping[selected_status]  # Get corresponding value from the dictionary
            cur.execute("""update SCANS set present = %s where macID = %s and date = %s and time = %s and currentPeriod = %s""", (attendance_value,self.macID,self.date,self.time,self.currentPeriod))
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
         self.place_forget()
         update_buttons('normal')
         currentPopup = None
fridayperiodframe = FridayPeriodSelection(window)

def main():
    timeFunc()

    updateArriveTimes()
    updateActivityArriveTimes()

    if not getSchedType():
        setupMode()
    else:
        periodList.lift()
        awaitingFrame.lift()
        threading.Thread(target=checkIN, daemon=True).start()
    window.mainloop()
main()