'''This Python script, mainClient.py, is the main script which handles all the data collected by the monitor node of a
   particular water usage monitoring network. It processes all the incoming data and determines where they in the
   database server. mainClient.py also monitors the status of measurement nodes belonging to its network. If any node
   ceases to be operational, error data will be uploaded to the database server to notify the user or admin of the
   error.'''
import threading
from datetime import datetime
import time
import serialConnection
import pymongoClient
import memcacheClient
from collections import deque
import netifaces as ni

#connFail is a Boolean parameter which indicates whether the script has lost connection with the database server.
connFail = False
nodeList = []
lastRecord = {}

'''allowedSet is the set of characters allowed in the serial messages sent over by the monitor node. It is a basic
   check for possible data corruption.'''
allowedSet = set("_0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ,;")
NODEFILENAME = "nodelist.txt"
backupLock = threading.Lock()
mainReturn = None
piID = 1

#IP address of the MongoDB database server
MONGO_IP = "ds033018.mongolab.com"
meterDict = {}
#dataQ = deque()

#The Serial Connection client instance
ser = serialConnection.serialConnection()
#The Pymongo Client instance
dbClient = pymongoClient.pymongoClient(MONGO_IP)
#The Python Memcached Client instance
mem = memcacheClient.memcacheClient()
configTimer = None

'''This is the measurement node heartbeat threshold value, in terms of milliseconds. This means if a measurement node
   has not sent over usage data within the past period of this many milliseconds, it is considered non-operational.
   An error message will be uploaded to the database server, informing the user/admin of the node's status.'''
TIME_THRESHOLD = 120000

CONFIG_NAME = "config.txt"

oldNU = None
oldLeakInterval = None
oldLeakStreak = None
oldKeyValue = None
networkID = None

newNU = None
newLeakInterval = None
newLeakStreak = None
newKeyValue = None

nodeCount = 0
acknowledgeCount = 0



'''The backupThread class is a thread object which is used to constantly monitor the status of cache memory.
   If backed up data exists in cache memory, and connection to the database server has resumed, then backupThread
   will attempt to push all the backed up data to the database server.'''
class backupThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        '''This backupReturn parameter is to check the return value of the backup data insert attempts.'''
        self.backupReturn = None

    def run(self):
        global connFail
        backupLock.acquire()
        '''Initialization: set the backed up data entry count in cache memory.'''
        mem.updateCacheCount()
        backupLock.release()

        while 1:
            '''If there is backed up data in cache memory due to previous connection failure to the database server,
               and connection has been re-established now, then begin pushing the backed up data back to the server.'''
            if (mem.getCacheCount() > 0) and (not connFail):
                print "Pushing backup data to server..."
                while (mem.getCacheCurr() < mem.getCacheCount()) and (not connFail):
                    toUpload = mem.valueGet(str(mem.getCacheCurr()))
                    if (toUpload):
                        self.backupReturn = dbClient.backupUsageInsert(toUpload[0], toUpload[1],
                                                                       toUpload[2], toUpload[3],
                                                                       toUpload[4], toUpload[5],
                                                                       toUpload[6], toUpload[7])

                        '''If the backed up data push for this particular data entry is successful, then we delete that
                           entry from cache memory, and increment the current counter to the next piece of backed up
                           data in cache memory.'''
                        if (self.backupReturn):
                            connFail = False
                            mem.valueDelete(str(mem.getCacheCurr()))
                            mem.cacheCurrIncrement()
                        else:
                            connFail = True

                '''If all the backed up data has been pushed back to the database server, then we reset both the cache
                   count and the current cache index pointer back to zero, indicating that everything has been cleared
                   in cache memory.'''
                if (mem.getCacheCurr() >= mem.getCacheCount()):
                    backupLock.acquire()
                    mem.cacheCountReset()
                    backupLock.release()
                    mem.cacheCurrReset()
            else:
                time.sleep(60)



'''The heartbeatThread class is a thread object which is used to monitor the operational status of all measurement nodes
   belonging to the current water usage monitoring network. If any measurement node belonging to this network is deemed
   non-operational, an error message known as a "heartbeat error" for that node is uploaded to the database server to
   inform the user/admin of its status. In addition, the heartbeatThread also monitors the operational status of the
   Raspberry Pi unit itself. It does so by sending over a Raspberry Pi heartbeat message to the pi_heartbeat collection
   once every hour.'''
class heartbeatThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.piID = piID
        self.piTimer = None
        self.IPTimer = None
        self.timeThreshold = TIME_THRESHOLD
        self.lastHeartBeat = None
        self.timeNow = None
        self.timeDiff = None
        
        '''The insertReturn parameter is for checking the return values of any heartbeat error inserts or Raspberry Pi
           heartbeat inserts'''
        self.insertReturn = None
        self.dbPost = None
        self.status = None

    def run(self):
        global dataQ
        global connFail
        global meterDict
        global networkID
        time.sleep(10)
        self.piTimer = time.time()
        self.IPTimer = time.time()
        while 1:
            time.sleep(15)
            print "Performing Heartbeat Check"
            #print "dataQ length is %d" %(len(dataQ))
            self.timeNow = long(1000*time.time())

            '''A heartbeat is performed for each node ID belong to the current water usage monitoring network.'''
            for value in nodeList:
                self.status = meterDict[value]
                
                '''Obtain the timestamp when the last usage data record belong to this node was received. Then compare
                   the time difference between then and the current time. If the time difference exceeds the time
                   threshold, this indicates a heartbeat error for that particular measurement node, and a corresponding
                   heartbeat error message is uploaded to the database server.'''
                if (self.status[0] in lastRecord):
                    self.lastHeartBeat = lastRecord[self.status[0]]
                    self.timeDiff = self.timeNow - self.lastHeartBeat[2]
                    #print "now:", self.timeNow, "last:", self.lastHeartBeat[2]
                    print self.timeDiff
                    if (self.timeDiff > self.timeThreshold):
                        print "Heartbeat error detected 1"
                        #print "%d", self.timeDiff
                        self.insertReturn = dbClient.attemptErrorInsert(self.status[0], self.lastHeartBeat[0], -1,
                                                                        self.lastHeartBeat[2], self.timeNow,
                                                                        0, "Heartbeat")
                        if (self.insertReturn):
                            connFail = False
                        else:
                            connFail = True

                        '''The online status of the measurement node also needs to be checked. If a heartbeat error is
                           detected for the current node, but its status is still set as online, then its status needs
                           to be flipped offline.'''
                        if self.status[1]:
                            self.insertReturn = dbClient.attemptStatusUpdate(value, False)
                            if (self.insertReturn):
                                connFail = False
                                meterDict[value] = (self.status[0], False)
                            else:
                                connFail = True

                    #If no heartbeat error is detected for the this measurement node, but its online status is
                    #currently set as False (offline), then its status needs to be flipped back to online.
                    else:
                        if not self.status[1]:
                            self.insertReturn = dbClient.attemptStatusUpdate(value, True)
                            if (self.insertReturn):
                                connFail = False
                                meterDict[value] = (self.status[0], True)
                            else:
                                connFail = True
                                
                #If no record exists so far for this measurement node, this means the node has been non-operational
                #since the mainClient script has begun running. Thus, an error message still needs to be uploaded
                #for this measurement node.
                else:
                    print "Heartbeat error detected 2"
                    print "NodeID: %d" %(value)
                    self.insertReturn = dbClient.attemptErrorInsert(self.status[0], -1, -1, -1,
                                                                    self.timeNow, 0, "Heartbeat")
                    if (self.insertReturn):
                        connFail = False
                    else:
                        connFail = True

                    '''The online status of the measurement node also needs to be checked. If a heartbeat error is
                       detected for the current node, but its status is still set as online, then its status needs
                       to be flipped offline.'''
                    if self.status[1]:
                        self.insertReturn = dbClient.attemptStatusUpdate(value, False)
                        if (self.insertReturn):
                            connFail = False
                            meterDict[value] = (self.status[0], False)
                        else:
                            connFail = True

            #print meterDict
            for (k, v) in meterDict.items():
                print "%d   %s" %(k, v[1])

            '''If one hour has passed since the last time a Raspberry Pi heartbeat message has been uploaded, we upload
               a new Raspberry Pi heartbeat message to the pi_heartbeat collection of the database server.'''
            if (time.time() > self.piTimer + 3600):
                self.insertReturn = dbClient.piHeartbeatInsert(self.piID, long(1000*time.time()),
                                                               ni.ifaddresses('eth0')[17][0]['addr'])
                if (self.insertReturn):
                    connFail = False
                else:
                    connFail = True
                self.piTimer = time.time()

            if (time.time() > self.IPTimer + 21600):
                if ("eth0" in ni.interfaces()):
                    dbClient.pushIP(networkID, ni.ifaddresses('eth0')[17][0]['addr'])
                self.IPTimer = time.time()



'''The function singleUsageInsert performs a single usage data using the arguments wmid, counter, diff, intTemp,
   extTemp, timestamp and timesstring. It uploads the data entry to the database server collection corresponding
   to the dbStr argument.'''
def singleUsageInsert(dbStr, wmid, counter, diff, intTemp, extTemp, timestamp, timestring):
    mainReturn = dbClient.attemptUsageInsert(dbStr, wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
    '''If the upload is successful, the Boolean flag connFail is switched to False.'''
    if (mainReturn == 1):
        connFail = False

    #If the upload is unsuccessful, we determine whether the data needs to be backed up for future upload when
    #connection is re-established.
    elif (mainReturn == 0):
        connFail = True
        '''If the usage data is monthly, daily, hourly, or per-minute data, we will need to back up the data to
           cache memory.'''
        if (dbStr in ["month", "day", "hour", "min"]):
            #print "Usage upload failed. Pushing to memcache..."
            mem.valueSet(str(mem.getCacheCount()),[dbStr, wmid, counter, diff, intTemp, extTemp, timestamp, timestring])
            backupLock.acquire()
            mem.cacheCountIncrement()
            backupLock.release()
            #print "Memcache push successful"

    else:
        print "Corrupt Usage Upload Data. Discarded."



'''The function multipleUsageInsert determines how many single usage insert uploads needs to be performed for each
   piece of usage data. The possible collection tables a single piece of usage data needs to be uploaded to are the
   monthly table (data_month), the daily table (data_day), the hourly (data_hour), the per-minute (data_min), and the
   per-second table (data_sec).'''
def multipleUsageInsert(dbStr, wmid, counter, diff, intTemp, extTemp, timestamp, timestring):
    if (dbStr == "month"):
        singleUsageInsert("month", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
        singleUsageInsert("day", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
        singleUsageInsert("hour", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
        singleUsageInsert("min", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
        #singleUsageInsert("sec", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
    elif (dbStr == "day"):
        singleUsageInsert("day", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
        singleUsageInsert("hour", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
        singleUsageInsert("min", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
        #singleUsageInsert("sec", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
    elif (dbStr == "hour"):
        singleUsageInsert("hour", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
        singleUsageInsert("min", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
        #singleUsageInsert("sec", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
    elif (dbStr == "min"):
        singleUsageInsert("min", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
        #singleUsageInsert("sec", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)
    #elif (dbStr == "sec"):
        #singleUsageInsert("sec", wmid, counter, diff, intTemp, extTemp, timestamp, timestring)



'''The function tempConvert takes in one argument hexStr, which is a hexadecimal string indicating a temperature value.
   tempConvert will convert hexStr to a decimal integer value indicating the temperature, and return that value.'''
def tempConvert(hexStr):
    try:
        value = int(hexStr, 16)
        if (value > 32767):
            value -= 65536
        return value
    #Upon ValueError, the function returns 99999 which is a value out of expressable range by hexStr.
    except ValueError, e:
        return 99999
    


if __name__ == "__main__":

    #Establish connection of the Serial Connection client.
    ser.connect()

    #Establish connection of the Pymongo Client.
    dbClient.connect()

    #Flush serial input and output.
    ser.flushInput()
    ser.flushOutput()

    #Populate the nodeList.
    nodeFile = open(NODEFILENAME, "r")
    for line in nodeFile:
        line = long(line.strip().strip('\n'))
        nodeList.append(line)
    nodeFile.close()
    nodeCount = len(nodeList)
    print "Here is the node list:\n"
    print nodeList

    #Read the config file to obtain configuration values and the network ID
    configFile = open(CONFIG_NAME, "r")
    oldNU = int(configFile.readline().strip('\n').split(',')[1])
    leakResult = configFile.readline().strip('\n').split(',')
    oldLeakInterval = int(leakResult[1])
    oldLeakStreak = int(leakResult[2])
    oldKeyValue = configFile.readline().strip('\n').split(',')[1]
    networkID = configFile.readline().strip('\n').split(',')[1]
    configFile.close()

    #Send over a serial message to the monitor node to signal the main script is ready to operate.
    #ser.write(";main;")

    #Populate the meterDict
    meterList = dbClient.getMeterID(networkID)
    if (meterList):
        for entry in meterList:
            meterDict[entry["nodeid"]] = (entry["wmid"], entry["status"])
    elif (meterList == []):
        print "No water meter ID to node device ID associations have been established yet."
        time.sleep(1)
        print "You must provide these associations first through the web application initialization procedure."
        time.sleep(1)
        print "Please make sure you follow the manual instructions."
        time.sleep(10)
    print "Here is the meterDict: \n"
    print meterDict

    #Populate the lastRecord
    #lastRecord keys should now be meterIDs rather than nodeIDs
    for value in nodeList:
        result = dbClient.retrieveLastRecord(meterDict[value][0])
        if (result):
            lastRecord[result[0]["wmid"]] = [result[0]["counter"], result[0]["diff"], result[0]["timestamp"], result[0]["timestring"]]
    print "Here is the last record:\n"
    print lastRecord

    #Establish the Python Memcached client.
    mem.connect()

    #Send over a serial message to the monitor node to signal the main script is ready to operate.
    ser.write(";main;")

    #Start both the backupThread and heartbeatThread instances.
    myBackupThread = backupThread()
    myHeartbeatThread = heartbeatThread()
    myBackupThread.start()
    myHeartbeatThread.start()
    
    #configTimer = time.time()

    while 1:
        #Read the next message sent via the serial port
        message = ser.read()
        #print "Received message: "
        #print message

        message = message.strip("\n").strip(";")

        #Check the message received is not corrupt.
        if (set(message).issubset(allowedSet)):

            '''If the message is an encryption key request from the monitor node, reply by providing the encryption
               key value of the current network.'''
            if (message.startswith('key_req')):
                configFile = open(CONFIG_NAME, "r")
                configFile.readline()
                configFile.readline()
                keyValue = configFile.readline().strip('\n').split(',')[1]
                configFile.close()
                ser.write(";key_update,%s;\n" %(keyValue))

            '''If the message is a time request from the monitor node, reply by providing the current time as a
               timestring.'''
            if (message.startswith('time_req')):
                ser.write(datetime.now().strftime(';time,%Y,%m,%d,%H,%M,%S;\n'))

            
            '''if (message.startswith('boot')):
                result = message.split(",")
                idValue = long(result[1], 16)
                if (idValue not in nodeList):
                    nodeList.append(idValue)
                    nodeCount += 1
                    nodeFile = open(NODEFILENAME, "a")
                    nodeFile.write(str(idValue) + '\n')       
                    nodeFile.close()
                    #check if idValue exists in onlineStatus
                    if idValue in onlineStatus:
                        #if so, check true or false
                        if not onlineStatus[idValue]: 
                            #if false, set it true and update data_stat
                            #onlineStatus[idValue] = True
                            mainReturn = dbClient.attemptStatusUpdate(idValue, True)
                            if (mainReturn):
                                connFail = False
                                onlineStatus[idValue] = True
                            else:
                                connFail = True
                    #if idValue does not exist in onlineStatus
                    else:
                        #then add to onlineStatus with True setting
                        onlineStatus[idValue] = True
                        #and insert new entry to data_stat
                        mainReturn = dbClient.attemptStatusInsert(idValue, piID, True)
                        if (mainReturn):
                            connFail = False
                        else:
                            connFail = True'''
            

            #Caution: tempID is now meterID, rather than nodeID. Thus, lastRecord keys should now be meterIDs as well.
            '''If the message is usage data from a measurement node, then process the data accordingly.'''
            if (message.startswith('usage')):
                result = message.split(",")
                #print result

                #tempID is the water meter ID.
                tempID = meterDict[long(result[1], 16)][0]
                #tempCounter is the cumulative usage of this particular node.
                tempCounter = long(result[2], 16)
                #tempDiff is the difference in water usage between now and the last usage data of this node.
                tempDiff = long(result[3], 16)
                #tempIntTemp is the measured internal temperature of the measurement node device.
                tempIntTemp = tempConvert(result[4])
                #tempExtTemp is the measured temperature of the measurement node device's surrounding environment.
                tempExtTemp = tempConvert(result[5])
                #tempTime is the number of milliseconds since Epoch time of the timestamp sent by the measurement node.
                try:
                    tempTime = long(1000*time.mktime(time.strptime(result[6], "%Y%m%d%H%M%S")))
                except:
                    print "Timestamp error. Using timestamp of last upload as approximation."
                    

                '''If tempID is not in lastRecord, it means this entry is the first usage data being sent over by this
                   particular measurement node.'''
                if (tempID not in lastRecord):
                    '''If the difference in usage data is negative, the network suspects possible hacking and tampering
                       of usage data. A corresponding error message will be uploaded to inform the user or admin.'''
                    if (tempDiff < 0):
                        mainReturn = dbClient.attemptErrorInsert(tempID, 0L, tempCounter, -1,
                                                                 tempTime, 4, "Altered Data")
                        if (mainReturn):
                            connFail = False
                        else:
                            connFail = True

                    #If we do not suspect data tampering, the usage data is uploaded to the usage collections.
                    else:
                        multipleUsageInsert("month", tempID, tempCounter, tempDiff,
                                            tempIntTemp, tempExtTemp, tempTime, result[6])
                        '''The last record of this particular measurement node is updated.'''
                        lastRecord[tempID] = [tempCounter, tempDiff, tempTime, result[6]]

                #If tempID is in lastRecord, we will compare the usage data collected this time around to the last
                #usage data collected.
                else:
                    tempLast = lastRecord[tempID]

                    '''If the cumulative usage actually gets decremented, an error message is uploaded to the database
                       server to inform the user or admin of possible tampering of data.'''
                    if (tempCounter < tempLast[0]):
                        '''if (tempDiff < 0) or (tempCounter - tempDiff != tempLast[0]):
                           print "difference check error detected. Last record data of this node will be reset"'''
                        mainReturn = dbClient.attemptErrorInsert(tempID, tempLast[0], tempCounter,
                                                                 tempLast[2], tempTime, 1, "Decrement")
                        if (mainReturn):
                            connFail = False
                        else:
                            connFail = True

                    else:
                        '''Compare the timestamps of the current usage data and the last record of this node.'''
                        '''If the year is not equal, this means we have entered a new year. Thus, we need to upload
                           this usage data to all the usage collections (month, day, hour, minute and second).'''
                        if (result[6][0:4] != tempLast[3][0:4]):
                            #push into data_month, day, hour, min and sec
                            multipleUsageInsert("month", tempID, tempCounter, tempDiff, tempIntTemp,
                                                tempExtTemp, tempTime, result[6])

                        #If year is equal but not the month, this means we have entered a new month. Thus, we need
                        #to upload this usage data to all the usage collections (month, day, hour, minute and
                        #second).
                        elif (result[6][4:6] != tempLast[3][4:6]):
                            #push into data_month, day, hour, min and sec
                            multipleUsageInsert("month", tempID, tempCounter, tempDiff, tempIntTemp,
                                                tempExtTemp, tempTime, result[6])

                        #If year and month are equal, but not the day, this means we have entered a new day. Thus,
                        #we need to upload this usage data to the day, hour, minute and second collections.
                        elif (result[6][6:8] != tempLast[3][6:8]):
                            #push into data_day, hour, min and sec
                            multipleUsageInsert("day", tempID, tempCounter, tempDiff, tempIntTemp,
                                                tempExtTemp, tempTime, result[6])

                        #If year, month and day are equal, but not the hour, this means we have entered a new hour.
                        #Thus, we need to upload this usage data to the hour, minute and second collections.
                        elif (result[6][8:10] != tempLast[3][8:10]):
                            #push into data_hour, min and sec
                            multipleUsageInsert("hour", tempID, tempCounter, tempDiff, tempIntTemp,
                                                tempExtTemp, tempTime, result[6])

                        #If year, month, hour and day are equal, but not the minute, this means we have entered a new
                        #minute. Thus, we need to upload this usage data to the minute and second collections.
                        elif (result[6][10:12] != tempLast[3][10:12]):
                            #push into data_min and sec
                            multipleUsageInsert("min", tempID, tempCounter, tempDiff, tempIntTemp,
                                                tempExtTemp, tempTime, result[6])

                        #If year, month, hour, day and minute are equal, but not the second, this means we have
                        #entered a new minute. Thus, we need to upload this usage data to the second collection.
                        elif (result[6][12:14] != tempLast[3][12:14]):
                            #push into data_sec
                            multipleUsageInsert("sec", tempID, tempCounter, tempDiff, tempIntTemp,
                                                tempExtTemp, tempTime, result[6])

                    '''Update the last record of this particular measurement node.'''
                    lastRecord[tempID] = [tempCounter, tempDiff, tempTime, result[6]]                 


            '''If the message is an error message from a measurement node, we process the data and upload the
               corresponding error message to the error database so the user/admin is notified.'''
            if (message.startswith('error')):
                result = message.split(",")
                tempID = meterDict[long(result[1], 16)][0]

                #This is a Security Pin Disconnect error message.
                if ("00" == result[6]):
                    try:
                        mainReturn = dbClient.attemptErrorInsert(tempID, long(result[2], 16), long(result[3], 16),
                                                                 long(1000*time.mktime(time.strptime(result[4], "%Y%m%d%H%M%S"))),
                                                                 long(1000*time.mktime(time.strptime(result[5], "%Y%m%d%H%M%S"))),
                                                                 1, "Security Pin Disconnect")
                        dbClient.securityBreach(tempID)
                    except ValueError, e:
                        print "Security Pin Timestamp Error. Bypass."

                #This is a No Usage error message.
                elif ("01" == result[6]):
                    try:
                        mainReturn = dbClient.attemptErrorInsert(tempID, long(result[2], 16), long(result[3], 16),
                                                                 long(1000*time.mktime(time.strptime(result[4], "%Y%m%d%H%M%S"))),
                                                                 long(1000*time.mktime(time.strptime(result[5], "%Y%m%d%H%M%S"))),
                                                                 2, "No Usage")
                    except ValueError, e:
                        print "No Usage Timestamp Error. Bypass."

                #This is a Leakage error message.
                elif ("10" == result[6]):
                    try:
                        mainReturn = dbClient.attemptErrorInsert(tempID, long(result[2], 16), long(result[3], 16),
                                                                 long(1000*time.mktime(time.strptime(result[4], "%Y%m%d%H%M%S"))),
                                                                 long(1000*time.mktime(time.strptime(result[5], "%Y%m%d%H%M%S"))),
                                                                 3, "Leakage")
                    except ValueError, e:
                        print "Leakage Timestamp Error. Bypass."

                #This is a Decrement error message.
                elif ("11" == result[6]):
                    try:
                        mainReturn = dbClient.attemptErrorInsert(tempID, long(result[2], 16), long(result[3], 16),
                                                                 long(1000*time.mktime(time.strptime(result[4], "%Y%m%d%H%M%S"))),
                                                                 long(1000*time.mktime(time.strptime(result[5], "%Y%m%d%H%M%S"))),
                                                                 3, "Decrement")
                    except valueError, e:
                        print "Decrement Timestamp Error. Bypass."
                if (mainReturn == 1):
                    connFail = False
                elif (mainReturn == 0):
                    connFail = True
                else:
                    print "Corrupt data. Bypass."

                    
    ser.close()
