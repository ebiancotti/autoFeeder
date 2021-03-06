from imapclient import IMAPClient, SEEN
import time
import smtplib
from email.mime.multipart import MIMEMultipart 
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
import sys
#import RPi.GPIO as GPIO

MOTORON = True

# Here is our logfile
#LOGFILE = "/tmp/petfeeder.log"
#LOGFILE = "C:/Users/EmilianoB.ADELINA/petfeeder.log"

# Variables for checking email
GMAILHOSTNAME = 'imap.gmail.com'
MAILBOX = 'Inbox'
GMAILUSER = 'dispensermila@gmail.com'
GMAILPASSWD = 'belemi18'
NEWMAIL_OFFSET = 0
lastEmailCheck = time.time()
MAILCHECKDELAY = 30

# GPIO pins for feeder control
MOTORCONTROLPIN = 19
FEEDBUTTONPIN = 6
RESETBUTTONPIN = 13

# Variables for feeding information
feedInterval = 30 #21600 # This translates to 6 hours in seconds
#FEEDFILE="/home/petfeeder/lastfeed"
FEEDFILE = "C:/Users/EmilianoB.ADELINA/oo.txt"
cupsToFeed = 1
motorTime = 3 #cupsToFeed * 27 # It takes 27 seconds of motor turning (~1.75 rotations) to get 1 cup of feed
anguloDeApertura = 45
duty = 2 + (anguloDeApertura/18)


# Function to check email
def checkmail():
    global lastEmailCheck
    global lastFeed
    global feedInterval
    
    if (time.time() > (lastEmailCheck + MAILCHECKDELAY)):  # Make sure that that a tleast MAILCHECKDELAY time has passed
        lastEmailCheck = time.time()
        server = IMAPClient(GMAILHOSTNAME, use_uid=True, ssl=True)  # Create the server class from IMAPClient with HOSTNAME mail server
        server.login(GMAILUSER, GMAILPASSWD)
        server.select_folder(MAILBOX)


        ##############    Mensajes WHEN    #####################
        

        # See if there are any messages with subject "When" that are unread
        whenMessages = server.search([u'UNSEEN', u'SUBJECT', u'When'])

        # Respond to the when messages
        if whenMessages:
            for msg in whenMessages:
                msginfo = server.fetch([msg], ['BODY[HEADER.FIELDS (FROM)]'])
                fromAddress = str(msginfo).replace("<class 'dict'>", "").split('<')[1].split('>')[0]          
                
                msgBody = "The last feeding was done on " + time.strftime("%b %d at %I:%M %p", time.localtime(lastFeed))

                if (time.time() - lastFeed) > feedInterval:
                    msgBody = msgBody + "\nReady to feed now!"
                else:
                    msgBody = msgBody + "\nThe next feeding can begin on " + time.strftime("%b %d at %I:%M %p", time.localtime(lastFeed + feedInterval))
                                              
                sendemail(fromAddress, "Thanks for your feeding query", msgBody)
                server.add_flags(whenMessages, [SEEN])


        ##############    Mensajes SET    #####################        


        # See if there are any messages with subject "SET" that are unread
        setMessages = server.search([u'UNSEEN', u'SUBJECT', u'Set'])

        # Respond to the set messages
        if setMessages:
            for msg in setMessages:
                msginfo = server.fetch([msg], ['BODY[HEADER.FIELDS (FROM)]'])
                fromAddress = str(msginfo).replace("<class 'dict'>", "").split('<')[1].split('>')[0]
                                   
                setLastFeed()
                
                msgBody = "The last feeding date was set on " + time.strftime("%b %d at %I:%M %p", time.localtime(lastFeed))
                                     
                sendemail(fromAddress, "\nThanks for setting time", msgBody)
                server.add_flags(whenMessages, [SEEN])          


        ##############    Mensajes Close    #####################


        # See if there are any messages with subject "Close" that are unread
        closeMessages = server.search([u'UNSEEN', u'SUBJECT', u'Close'])

        # Respond to the close messages
        if closeMessages:
            for msg in closeMessages:
                                                   
                sys.exit()


        ##############    Mensajes Feed    #####################    


        # See if there are any messages with subject "Feed" that are unread
        feedMessages = server.search([u'UNSEEN', u'SUBJECT', u'Feed'])
        
        # Respond to the feed messages and then exit
        if feedMessages:
            for msg in feedMessages:
                msginfo = server.fetch([msg], ['BODY[HEADER.FIELDS (FROM)]'])                
                fromAddress = str(msginfo).replace("<class 'dict'>", "").split('<')[1].split('>')[0]

                msgBody = "The last feeding was done at " + time.strftime("%b %d at %I:%M %p", time.localtime(lastFeed))
                if (time.time() - lastFeed) > feedInterval:
                    msgBody = msgBody + "\nReady to be fed, will be feeding Mila shortly"
                else:
                    msgBody = msgBody + "\nThe next feeding can begin at " + time.strftime("%b %d at %I:%M %p", time.localtime(lastFeed + feedInterval))
                                   
                sendemail(fromAddress, "Thanks for your feeding request", msgBody)

                server.add_flags(feedMessages, [SEEN])
            
            return True
    return False


def sendemail(to, subject, text, attach=None):
    msg = MIMEMultipart()
    msg['From'] = GMAILUSER
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(text))
    if attach:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(open(attach, 'rb').read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(attach))
        msg.attach(part)
    mailServer = smtplib.SMTP("smtp.gmail.com", 587)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(GMAILUSER, GMAILPASSWD)
    mailServer.sendmail(GMAILUSER, to, msg.as_string())
    mailServer.close()


def buttonpressed(PIN):
    # # Check if the button is pressed
    # global GPIO
    
    # # Cheap (sleep) way of controlling bounces / rapid presses
    # time.sleep(0.2)
    # button_state = GPIO.input(PIN)
    # if button_state == False:
    #     return True
    # else:
         return False


def remotefeedrequest():
    # At this time we are only checking for email
    
    return checkmail()
    

def feednow():
    # Run the motor for motorTime, messages in the LCD during the feeeding
    global GPIO
    global MOTORCONTROLPIN
    global motorTime
    global lastFeed
    global GMAILUSER
      
    if MOTORON:

        # Set GPIO numbering mode
        GPIO.setmode(GPIO.BOARD)

        # Set pin as an output, and set servo1 as pin PWM
        GPIO.setup(MOTORCONTROLPIN,GPIO.OUT)
        servo1 = GPIO.PWM(MOTORCONTROLPIN,50) # Note MOTORCONTROLPIN is pin, 50 = 50Hz pulse

        #start PWM running, but with value of 0 (pulse off)
        servo1.start(0)

        # Turn to 'anguloDeApertura' degrees

        print("Moviendo a " + anguloDeApertura + "grados")
        servo1.ChangeDutyCycle(duty)
        time.sleep(motorTime)

        #turn back to 0 degrees
        print ("Turning back to 0 degrees")
        servo1.ChangeDutyCycle(2)
        time.sleep(0.5)
        servo1.ChangeDutyCycle(0)       
        
        #logica vieja
        #GPIO.output(MOTORCONTROLPIN, True)
        #time.sleep(motorTime)
        #GPIO.output(MOTORCONTROLPIN, False)

        #Clean things up at the end
        servo1.stop()
        GPIO.cleanup()

        print("Done!")
        sendemail(GMAILUSER, "Fed at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(lastFeed)), "Feeding done!")
        time.sleep(2)
    return time.time()

def saveLastFeed():
    global FEEDFILE
    global lastFeed
    with open(FEEDFILE, 'w') as feedFile:
        feedFile.write(str(lastFeed))
    feedFile.close()

def setLastFeed():
    global FEEDTIME
    global lastFeed
    global now

    with open(FEEDFILE, 'w') as feedFile:
        lastFeed = time.time()
        feedFile.write(str(lastFeed))
    feedFile.close()
        

# This is the main program, essentially runs in a continuous loop looking for button press or remote request
try:

    #### Begin initializations #########################
    ####################################################
    
    # Initialize the logfile
    #logFile = open(LOGFILE, 'a')

   
    
    # Initialize the GPIO system
    # GPIO.setwarnings(False)
    # GPIO.setmode(GPIO.BCM)

    # # Initialize the pin for the motor control
    # GPIO.setup(MOTORCONTROLPIN, GPIO.OUT)
    # GPIO.output(MOTORCONTROLPIN, False)

    # # Initialize the pin for the feed and reset buttons
    # GPIO.setup(FEEDBUTTONPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    # GPIO.setup(RESETBUTTONPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    # Initialize lastFeed
    if os.path.isfile(FEEDFILE):
        with open(FEEDFILE, 'r') as feedFile:
            lastFeed = float(feedFile.read())
        feedFile.close()
    else:
        lastFeed = time.time()
        saveLastFeed()
        

    #### End of initializations ########################
    ####################################################

    #### The main loop ####
    
    while True:

        #### If reset button pressed, then reset the counter
        if buttonpressed(RESETBUTTONPIN):            
            print("Resetting...")
            time.sleep(2)
            lastFeed = time.time() - feedInterval + 5
            saveLastFeed()
        
        #### Check if we are ready to feed
        if (time.time() - lastFeed) > feedInterval:
            print(time.strftime("%m/%d %I:%M:%S %p", time.localtime(time.time())))
            print("Ready to feed")

            #### See if the button is pressed
            if buttonpressed(FEEDBUTTONPIN):
                lastFeed = feednow()
                saveLastFeed()
            
            ###SACAR FUERA ESTE IF SI QUIERO QUE EJECUTE FEED INDEPENDIENTEMENTE DE LA HORA
            #### Check if remote feed request is available
            elif remotefeedrequest():
                lastFeed = feednow()
                saveLastFeed()
                
        #### Since it is not time to feed yet, keep the countdown going
        else:
            timeToFeed = (lastFeed + feedInterval) - time.time()
            print(time.strftime("%m/%d/%Y, %H:%M:%S", time.localtime(time.time())))
            print('Next:' + time.strftime("%Hh %Mm %Ss", time.gmtime(timeToFeed)))
            checkmail()
            if buttonpressed(FEEDBUTTONPIN):                
                print("Not now, try at ")
                print(time.strftime("%b/%d %H:%M", time.localtime(lastFeed + feedInterval)))
                time.sleep(2)
        time.sleep(1)


#### Cleaning up at the end
except KeyboardInterrupt:
    #logFile.close()
    
    GPIO.cleanup()


except SystemExit:
    #logFile.close()
    
    GPIO.cleanup()