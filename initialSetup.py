'''This Python script, initialSetup.py, establishes the appropriate environment for the Main Client script to operate.
   It does so by initializing the default configuration values for this water usage monitoring network, and determining
   which measurement nodes are part of this particular network, based on its network ID.'''
import pymongoClient
import time
import serial

#The IP address of the MongoDB database server
MONGO_IP = "ds033018.mongolab.com"
#Establish an instance of the Pymongo Client class
dbClient = pymongoClient.pymongoClient(MONGO_IP)
#The name of the file storing the IDs of all measurement nodes of this network
NODEFILE_NAME = "nodelist.txt"
#The name of the file storing the configuration values of this network
CONFIG_NAME = "config.txt"
meterList = None
configSettings = None
hardNetworkID = "0000"

if __name__ == "__main__":

    #Establish the connection of this Pymongo Client instance.
    dbClient.connect()

    #Establish connection of the serial port using PySerial.
    ser = serial.Serial("/dev/ttyAMA0", 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, timeout=0.5, writeTimeout=0.5)

    if (ser.isOpen() == False):
        ser.open()

    #Open the file containing IDs of all measurement nodes of this water usage network, and delete all of its contents.
    nodeFile = open(NODEFILE_NAME, "r+")
    nodeFile.truncate()

    #Open the file storing configuration values for this water usage network, and delete all of its contents.
    configFile = open(CONFIG_NAME, "r+")
    configFile.truncate()

    ser.flushInput()
    ser.flushOutput()

    print "Power up your monitor node now."
    time.sleep(5)

    '''
    #Send a serial message to the water usage monitor, requesting the ID of this water usage monitoring network.
    ser.write(";nwid_req;")
    
    #Continue reading through the serial port until the network ID is sent over from the monitor node.
    while 1:
        message = ser.readline()
        print message
        message = message.strip('\n').strip(';')

        if (message.startswith('nwid')):
            result = message.split(',')
            nwid = result[1]
            break'''


    '''while 1:
        configSettings = dbClient.retrieveConfig(nwid, False)
        if (configSettings):
            #Copy over config settings present in database
            configFile.write("NU,%s\n" %(str(configSettings["NoUsage"]).zfill(5)) )
            configFile.write("LK,%s,%s\n" %(str(configSettings["LeakInterval"]).zfill(2),
                                            str(configSettings["LeakStreak"]).zfill(2)) )
            configFile.write("KY,%s\n" %(configSettings["EncryptionKey"]))
            break
        elif (configSettings == {}):
            #Go with default settings
            configFile.write("NU,21600\n")
            configFile.write("LK,30,02\n")
            configFile.write("KY,0000000000000000\n")
            #And push default settings to the database since it is missing
            dbClient.manualConfigUpdate(nwid, 21600, 30, 2, "0000000000000000")
            break
        elif (configSettings == None):
            print "Failed to connect to database. Retrying..."'''
            

    #Write in the default configuration values to the configuration file.
    configFile.write("NU,21600\n")
    configFile.write("LK,60,06\n")
    configFile.write("KY,z8PUsGeMY10kOBOy\n")



    '''#Write the network ID to the configuration file and close the file.
    configFile.write("NWID,%s\n" %(nwid))'''
    configFile.write("NWID,%s\n" %(hardNetworkID))
    configFile.close()

    
    while 1:
        #Query the database server to get the list of measurement node IDs associated with this water usage network.
        meterList = dbClient.getMeterID(nwid)
        if (meterList):
            #Store the list of IDs in the node list file.
            for entry in meterList:
                idValue = entry["nodeid"]
                nodeFile.write(str(idValue) + '\n')
            break
        #If an empty list is returned from the query, this indicates an error in the initialization process.
        elif (meterList == []):
            print "No water meter ID to node device ID associations have been established yet."
            time.sleep(1)
            print "You must provide these associations first through the web application initialization procedure."
            time.sleep(1)
            print "Please make sure you follow the manual instructions."
            time.sleep(1)
            break
        #If None is returned, it means the connection to the database server has failed during the query.
        #The query will be performed again in 3 seconds.
        elif (meterList == None):
            print "Connection to database server failed. Retrying in 3 seconds..."
            time.sleep(3)

    #Close the node list file.
    nodeFile.close()

    print "Initialization complete."
