'''This Python script, networkConfig.py, is a manual alternative to changing the configuration settings
to the particular water usage network monitored by this RaspberryPi unit. The script guides the user
along the way towards completing the desired configuration changes.'''
import serial
import time
import pymongoClient

#The IP address of the MongoDB database server
MONGO_IP = "ds033018.mongolab.com"
#Establish an instance of the Pymongo Client class
dbClient = pymongoClient.pymongoClient(MONGO_IP)

CONFIG_NAME = "config.txt"
NODEFILE_NAME = "nodelist.txt"
nodeList = []
nodeCount = 0
acknowledgeCount = 0

oldNU = None
oldLeakInterval = None
oldLeakStreak = None
oldKeyValue = None

newNU = None
newLeakInterval = None
newLeakStreak = None
newKeyValue = None

finalNU = None
finalLeakInterval = None
finalLeakStreak = None
finalKeyValue = None

networkID = None


def collectNewNU():
    while 1:
        print "Current no usage threshold value: %s" %(oldNU)
        print "Provide new no usage threshold (in seconds; range: 10800-86400):"
        newNU = raw_input()
        try:
            if (0 <= int(newNU) <= 86400):
                return newNU.zfill(5)
            else:
                print "Threshold out of acceptable range. Try again."
        except ValueError, e:
            print "Invalid value. Try again."



def collectNewLeakInterval():
    while 1:
        print "Current leakage check interval value: %s" %(oldLeakInterval)
        print "Provide new leakage check interval value (in minutes; range: 1-60):"
        newValue = raw_input()
        try:
            if (1 <= int(newValue) <= 60):
                return newValue.zfill(2)
            else:
                print "Threshold out of acceptable range. Try again."
        except ValueError, e:
            print "Invalid value. Try again."



def collectNewLeakStreak():
    while 1:
        print "Current leakage continuation threshold value: %s" %(oldLeakStreak)
        print "Provide new leakage continuation threshold value (range: 1-24):"
        newValue = raw_input()
        try:
            if (1 <= int(newValue) <= 24):
                return newValue.zfill(2)
            else:
                print "Threshold out of acceptable range. Try again."
        except ValueError, e:
            print "Invalid value. Try again."



def collectNewKey():
    while 1:
        print "Current encryption key value: %s" %(oldKeyValue)
        print "Provide new encryption key value (16-digit HEX):"
        newValue = raw_input()
        try:
            int(newValue, 16)
            if (len(newValue) == 16):
                return newValue
            else:
                print "Not 16 digits long. Try again."
        except ValueError, e:
            print "Invalid hexadecimal value. Try again."



if __name__ == "__main__":

    #Establish the connection of this Pymongo Client instance.
    dbClient.connect()

    ser = serial.Serial("/dev/ttyAMA0", 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, timeout=0.5, writeTimeout=0.5)

    if (ser.isOpen() == False):
        ser.open()

    print "Serial port opened"
    print ser.portstr

    ser.flushInput()
    ser.flushOutput()

    configFile = open(CONFIG_NAME, "r")
    oldNU = configFile.readline().strip('\n').split(',')[1]
    leakResult = configFile.readline().strip('\n').split(',')
    oldLeakInterval = leakResult[1]
    oldLeakStreak = leakResult[2]
    oldKeyValue = configFile.readline().strip('\n').split(',')[1]
    networkID = configFile.readline().strip('\n').split(',')[1]
    configFile.close()

    nodeFile = open(NODEFILE_NAME, "r")
    for line in nodeFile:
        line = long(line.strip().strip('\n'))
        nodeList.append(line)
    nodeFile.close()
    nodeCount = len(nodeList)
    print nodeList
    
    while 1:
        print "Would you like to change the no usage threshold value? (Y/N)"
        answer = raw_input()
        if (answer in ['Y', 'y']):
            newNU = collectNewNU()
            #update XBee network
            
            for i in range(5):
                print ";config,NU,%s;" %(newNU)
                ser.write(";config,NU,%s;" %(newNU))
                timer = time.time()
                while (time.time() <= (timer + 10)) and (acknowledgeCount < nodeCount):
                    message = ser.readline()
                    print message
                    message = message.strip('\n').strip(';')
                    #print message

                    if message.startswith('ack_config'):
                        result = message.split(',')
                        print result
                        tempID = long(result[1], 16)
                        print tempID
                        if tempID in nodeList:
                            print "Node acknowledged: %s" %(tempID)
                            acknowledgeCount += 1

                if (acknowledgeCount >= nodeCount):
                    print "All nodes acknowledged. New no usage threshold value is now %s" %(newNU)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    finalNU = newNU
                    acknowledgeCount = 0
                    break
                else:
                    print "Acknowledgment process failed. Retrying..."
                    if (i == 4):
                        print "Reconfiguration failed after 5 tries. Restoring old no usage threshold value of %s" %(oldNU)
                        finalNU = oldNU
                    acknowledgeCount = 0

            break
            
        elif (answer in ['N', 'n']):
            finalNU = oldNU
            break
        else:
            print "Incorrect response. Try again."

    configFile = open(CONFIG_NAME, "r+")
    configFile.truncate()
    configFile.write('NU,' + finalNU + '\n')
    configFile.write('LK,' + oldLeakInterval + ',' + oldLeakStreak + '\n')
    configFile.write('KY,' + oldKeyValue + '\n')
    configFile.close()

    while 1:
        print "Would you like to change the leakage check interval and continuation threshold values? (Y/N)"
        answer = raw_input()
        if (answer in ['Y', 'y']):
            newLeakInterval = collectNewLeakInterval()
            newLeakStreak = collectNewLeakStreak()
            #update XBee network

            for i in range(5):
                ser.write(";config,LK,%s,%s;" %(newLeakInterval, newLeakStreak))
                timer = time.time()
                while (time.time() <= (timer + 10)) and (acknowledgeCount < nodeCount):
                    message = ser.readline()
                    print message
                    message = message.strip('\n').strip(';')

                    if message.startswith('ack_config') and message.endswith('LK'):
                        result = message.split(',')
                        tempID = int(result[1], 16)
                        if tempID in nodeList:
                            print "Node acknowledged: %s" %(tempID)
                            acknowledgeCount += 1

                if (acknowledgeCount >= nodeCount):
                    print "All nodes acknowledged. New leakage check interval is now %s" %(newLeakInterval)
                    print "New leakage continuation threshold value is now %s" %(newLeakStreak)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    finalLeakInterval = newLeakInterval
                    finalLeakStreak = newLeakStreak
                    acknowledgeCount = 0
                    break
                else:
                    print "Acknowledgment process failed. Retrying..."
                    if (i == 4):
                        print "Reconfiguration failed after 5 tries. Restoring old leakage check interval of %s" %(oldLeakInterval)
                        print "Restoring old leakage continuation threshold value of %s" %(oldLeakStreak)
                        finalLeakInterval = oldLeakInterval
                        finalLeakStreak = oldLeakStreak
                    acknowledgeCount = 0
            
            break;
        
        elif (answer in ['N', 'n']):
            finalLeakInterval = oldLeakInterval
            finalLeakStreak = oldLeakStreak
            break;
        else:
            print "Incorrect response. Try again."

    configFile = open(CONFIG_NAME, "r+")
    configFile.truncate()
    configFile.write('NU,' + finalNU + '\n')
    configFile.write('LK,' + finalLeakInterval + ',' + finalLeakStreak + '\n')
    configFile.write('KY,' + oldKeyValue + '\n')
    configFile.close()

    while 1:
        print "Would you like to change the encryption key value? (Y/N)"
        answer = raw_input()
        if (answer in ['Y', 'y']):
            newKeyValue = collectNewKey()
            #update XBee network

            for i in range(5):
                ser.write(";config,KY,%s;" %(newKeyValue))
                timer = time.time()
                while (time.time() <= (timer + 10)) and (acknowledgeCount < nodeCount):
                    message = ser.readline()
                    print message
                    message = message.strip('\n').strip(';')

                    if message.startswith('ack_config') and message.endswith('KY'):
                        result = message.split(',')
                        tempID = int(result[1], 16)
                        if tempID in nodeList:
                            print "Node acknowledged: %s" %(tempID)
                            acknowledgeCount += 1

                if (acknowledgeCount >= nodeCount):
                    print "All nodes acknowledged. New no encryption key value is now %s" %(newKeyValue)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    ser.write(";apply_config;")
                    time.sleep(2)
                    finalKeyValue = newKeyValue
                    acknowledgeCount = 0
                    break
                else:
                    print "Acknowledgment process failed. Retrying..."
                    if (i == 4):
                        print "Reconfiguration failed after 5 tries. Restoring old encryption key value of %s" %(oldKeyValue)
                        finalKeyValue = oldKeyValue
                    acknowledgeCount = 0
            
            break;
        
        elif (answer in ['N', 'n']):
            finalKeyValue = oldKeyValue
            break;
        else:
            print "Incorrect response. Try again."

    #Update config.txt
    configFile = open(CONFIG_NAME, "r+")
    configFile.truncate()
    configFile.write('NU,' + finalNU + '\n')
    configFile.write('LK,' + finalLeakInterval + ',' + finalLeakStreak + '\n')
    configFile.write('KY,' + finalKeyValue + '\n')
    configFile.write('NWID,' + networkID + '\n')
    configFile.close()

    #Need to update database as well
    dbClient.manualConfigUpdate(networkID, int(finalNU), int(finalLeakInterval),
                                int(finalLeakStreak), finalKeyValue)

    print "Update complete"
    print "Final NU: %s" %(finalNU)
    print "Final LK: %s, %s" %(finalLeakInterval, finalLeakStreak)
    print "Final KY: %s" %(finalKeyValue)

'''while 1:
    message = ser.readline()
    print "Received message: "
    print message'''
