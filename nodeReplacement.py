'''This Python script, nodeReplacement.py, guides the user through the process of replacing a malfunctioning
   measurement node from an existing water usage monitoring network.'''
import serial
import time
import pymongoClient

#The IP address of the MongoDB database server
MONGO_IP = "ds033018.mongolab.com"
#Establish an instance of the Pymongo Client class
dbClient = pymongoClient.pymongoClient(MONGO_IP)
#The name of the file storing the configuration values of this network
CONFIG_NAME = "config.txt"
#The name of the file storing the IDs of all measurement nodes of this network
NODEFILE_NAME = "nodelist.txt"
nodeList = []
nodeCount = 0
acknowledgeCount = 0

oldID = None
newID = None
noUsageValue = None
leakInterval = None
leakStreak = None
keyValue = None
cumUsage = None
newNodeBooted = False
newNodeAcknowledged = False


'''The function oldIDCheck requests the ID of the old (malfunctioning) measurement node from the user. If the ID the
   provides does indeed exist in the current network, the ID is return in the form of an integer/long. If not, the
   function will notify the user and request for another ID.'''
def oldIDCheck(nodeList):
    while 1:
        try:
            print "Please provide the old node ID (16-digit number):"
            response = int(raw_input(), 16)
            if (response in nodeList):
                return response
            else:
                print "Old node ID does not exist in the network. Please check the ID and try again."
        except ValueError, e:
            print "Node value is not a number. Please check the ID and try again."



'''The function newIDCheck requests the ID of the new (replacement) measurement node from the user. The function
   checks if the ID provided is 16 digits long, and return the ID in string format if that is the case.'''
def newIDCheck():
    while 1:
        try:
            print "Please provide the new node ID (16-digit number):"
            response = raw_input()
            if (len(response) == 16):
                return response
                '''return long(response)'''
            else:
                print "New node ID is not a 16-digit number. Please check the ID and try again."
        except ValueError, e:
            print "New node ID is not a 16-digit number. Please check the ID and try again...."



'''The function getCumulativeUsage takes in an integer/long value nodeID as the lone argument. It searches the
database server to retrieve the last usage record belonging to the measurement node with nodeID, and obtains the
cumulative usage so far from that particular node. It returns the cumulative usage in integer/long format, or if
no usage data exists for nodeID, zero is returned.'''
def getCumulativeUsage(nodeID):
    result = dbClient.retrieveLastRecord(nodeID)
    if result:
        return result[0]["counter"]
    else:
        return 0        



if __name__ == "__main__":

    print "Setting up the environment for node replacement..."
    print "Please make sure not to connect the new node online yet."
    print "You will be instructed to do so later on."

    #Establish connection of the serial port using PySerial
    ser = serial.Serial("/dev/ttyAMA0", 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, timeout=0.5, writeTimeout=0.5)

    if (ser.isOpen() == False):
        ser.open()

    #Establish the connection of this Pymongo Client instance.
    dbClient.connect()

    #Open the file containing the IDs of all measurement nodes of the current water usage network.
    #Append all the IDs in the file to the nodeList structure.
    nodeFile = open(NODEFILE_NAME, "r")
    for line in nodeFile:
        line = long(line.strip().strip('\n'))
        nodeList.append(line)
    nodeFile.close()
    #print nodeList

    #Print out the list of measurement node IDs in nodeList, in hexadecimal format.
    print "List of nodes in the current network:"
    for node in nodeList:
        print '00' + hex(node)[2:-1]

    #Open the configuration file and obtain the current configuration values.
    configFile = open(CONFIG_NAME, "r")
    noUsageValue = configFile.readline().strip('\n').split(',')[1]
    leakResult = configFile.readline().strip('\n').split(',')
    leakInterval = leakResult[1]
    leakStreak = leakResult[2]
    keyValue = configFile.readline().strip('\n').split(',')[1]
    configFile.close()

    #Using the function oldIDCheck, request for the ID of the malfunctioning node and remove it from the nodeList.
    oldID = oldIDCheck(nodeList)
    nodeList.remove(oldID)
    nodeCount = len(nodeList)

    #cumUsage = 12563748
    '''Using the function getCumulativeUsage, obtain the cumulative usage measured by the old measurement node up to
       the point of malfunctioning.'''
    cumUsage = getCumulativeUsage(oldID)

    #Using the function newIDCheck, request for the ID of the new replacement node.
    #newID is stored as a hexadecimal string.
    newID = newIDCheck()

    ser.flushInput()
    ser.flushOutput()

    while 1:
        #Attempt to reset the Encryption Key to default (i.e., without encryption at all)
        ser.write(";config,KY,0000000000000000;")
        timer = time.time()

        #Collect acknowledgement messages from measurement nodes for 30 seconds.
        while (time.time() <= (timer + 30)) and (acknowledgeCount < nodeCount):
            message = ser.readline()
            print message
            message = message.strip('\n').strip(';')

            if (message.startswith('ack_config') and message.endswith('KY')):
                result = message.split(',')
                tempID = int(result[1], 16)
                if tempID in nodeList:
                    print "Node acknowledged: %d" %(tempID)
                    acknowledgeCount += 1

        #If acknowledgements from all the measurement nodes have been collected,
        #then apply the new configuration.
        if (acknowledgeCount >= nodeCount):
            time.sleep(3)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            acknowledgeCount = 0
            break

        #If not all measurement nodes have acknowledged the change, attempt a retry.
        else:
            print "Encryption key reset failed."
            print "Please check that all other nodes in the network are operational."
            print "Retrying in 5 seconds..."
            time.sleep(5)

    print "Encryption key has successfully been reset."
    print "Please plug in and power up the replacement node now."
    time.sleep(10)

    #After the encryption key reset, include the new node ID in nodeList.
    nodeList.append(int(newID, 16))
    nodeCount += 1

    while 1:
        #Attempt to change the No Usage Threshold value of the network, this time including the new replacement node.
        ser.write(";config,NU,%s;" %(noUsageValue))
        timer = time.time()

        #Collect acknowledgement messages from measurement nodes for 30 seconds.
        while (time.time() <= (timer + 30)) and (acknowledgeCount < nodeCount):
            message = ser.readline()
            print message
            message = message.strip('\n').strip(';')
            #print message

            if (message.startswith('ack_config') and message.endswith('NU')):
                result = message.split(',')
                print result
                tempID = long(result[1], 16)
                print tempID
                if tempID in nodeList:
                    print "Node acknowledged: %s" %(tempID)
                    acknowledgeCount += 1

        #If acknowledgements from all the measurement nodes have been collected,
        #then apply the new configuration.
        if (acknowledgeCount >= nodeCount):
            print "All nodes acknowledged. No usage threshold value is now set to %s" %(noUsageValue)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(1)
            acknowledgeCount = 0
            break

        #If not all measurement nodes have acknowledged the change, attempt a retry.
        else:
            print "Acknowledgment process failed. Retrying in 5 seconds..."
            print "Please make sure the replacement node is powered up."
            print "Please make sure all other nodes in the existing network are functioning as well."
            acknowledgeCount = 0
            time.sleep(5)

    time.sleep(3)


    while 1:
        #Attempt to change the Leakage configuration values of the network,
        #this time including the new replacement node.
        ser.write(";config,LK,%s,%s;" %(leakInterval, leakStreak))
        timer = time.time()

        #Collect acknowledgement messages from measurement nodes for 30 seconds.
        while (time.time() <= (timer + 30)) and (acknowledgeCount < nodeCount):
            message = ser.readline()
            print message
            message = message.strip('\n').strip(';')
            #print message

            if (message.startswith('ack_config') and message.endswith('LK')):
                result = message.split(',')
                print result
                tempID = long(result[1], 16)
                print tempID
                if tempID in nodeList:
                    print "Node acknowledged: %s" %(tempID)
                    acknowledgeCount += 1

        #If acknowledgements from all the measurement nodes have been collected,
        #then apply the new configuration.
        if (acknowledgeCount >= nodeCount):
            print "All nodes acknowledged. Leakage check interval is now set to %s" %(leakInterval)
            print "Leakage continuation threshold value is now set to %s" %(leakStreak)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(1)
            acknowledgeCount = 0
            break

        #If not all measurement nodes have acknowledged the change, attempt a retry.
        else:
            print "Acknowledgment process failed. Retrying in 5 seconds..."
            print "Please make sure the replacement node is powered up."
            print "Please make sure all other nodes in the existing network are functioning as well."
            acknowledgeCount = 0
            time.sleep(5)

    time.sleep(3)


    while 1:
        #Attempt to change the Encryption Key value back to the original value,
        #before the new replacement node was introduced.
        ser.write(";config,KY,%s;" %(keyValue))
        timer = time.time()

        #Collect acknowledgement messages from measurement nodes for 30 seconds.
        while (time.time() <= (timer + 30)) and (acknowledgeCount < nodeCount):
            message = ser.readline()
            print message
            message = message.strip('\n').strip(';')
            #print message

            if (message.startswith('ack_config') and message.endswith('KY')):
                result = message.split(',')
                print result
                tempID = long(result[1], 16)
                print tempID
                if tempID in nodeList:
                    print "Node acknowledged: %s" %(tempID)
                    acknowledgeCount += 1

        #If acknowledgements from all the measurement nodes have been collected,
        #then apply the new configuration.
        if (acknowledgeCount >= nodeCount):
            print "All nodes acknowledged. Encryption key is now set to %s" %(keyValue)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(2)
            ser.write(";apply_config;")
            time.sleep(1)
            acknowledgeCount = 0
            break

        #If not all measurement nodes have acknowledged the change, attempt a retry.
        else:
            print "Acknowledgment process failed. Retrying in 5 seconds..."
            print "Please make sure the replacement node is powered up."
            print "Please make sure all other nodes in the existing network are functioning as well."
            acknowledgeCount = 0
            time.sleep(5)

    time.sleep(3)

    while not newNodeAcknowledged:
        #Attempt to pass over the cumulative usage of the malfunctioning node to the new replacement node,
        #such that the replacement node can start measuring usage from the point that the old node stopped functioning.
        ser.write(";config_new,0,%s;" %(newID[0:8] + "-" + newID[8:16]))
        time.sleep(1)
        print "Cumulative usage is %d" %(cumUsage)
        time.sleep(1)
        ser.write(";config_new,1,%s;" %(('00' + hex(cumUsage)[2:]).zfill(16)))
        timer = time.time()

        #Wait for 30 seconds or until the replacement node has sent over a message acknowledging the cumulative usage.
        while (time.time() <= (timer + 30)) and (not newNodeAcknowledged):
            message = ser.readline()
            print message
            message = message.strip('\n').strip(';')

            if (message.startswith('ack_rplcmt')):
                result = message.split(",")
                #hexadecimal string ID comparison
                if (result[1] == newID):
                    newNodeAcknowledged = True
                    print "New node acknowledged."

    #Update node list file to include the new replacement node ID in the file along with the other existing nodes.
    nodeFile = open(NODEFILE_NAME, "r+")
    nodeFile.truncate()
    for idValue in nodeList:
        nodeFile.write(str(idValue) + '\n')
    nodeFile.close()

    #Update the corresponding table in the database server,
    #to associate the meter ID to the new replacement node,
    #rather the old malfunctioning node.
    dbClient.meterIDUpdate(oldID, newID)
