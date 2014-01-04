'''This Python script, pymongoClient.py, imports the PyMongo library to allow access to a database server using Python.
   This allows retrieval and uploading of water usage data from and to the database server.'''
import pymongo
import time
from pymongo.errors import AutoReconnect
from pymongo.errors import ConnectionFailure



'''The pymongoClient class creates a Pymongo Client Object, which establishes the environment for access to a
   MongoDB database server, along with methods to access its data, and upload data to it. '''
class pymongoClient(object):

    '''The following are properties needed to establish the pymongoClient instance:
       IP address and port of the database server
       Username and Password authentication'''
    def __init__(self, IP, port=33018, username="kherani", password="stevey"):
        #IP is a string, port is an int
        self.hostname = IP
        self.port = port
        self.username = username
        self.password = password
        self.dbDict = None
        self.conn = None
        self.db = None
        '''self.data_month = None
        self.data_day = None
        self.data_hour = None
        self.data_min = None
        self.data_sec = None
        self.pi_heartbeat = None
        self.device_data = None'''


    '''The method connect makes the official connection to the MongoDB database server based on the parameters
       provided in the init method. In addition, it sets the timeout for each upload and data retrieval method
       to 400 milliseconds. This method will attempt to connect to the database server continuously until a
       connection is successfully established.'''
    def connect(self):
        while 1:
            try:
                self.conn = pymongo.MongoClient(self.hostname, self.port, socketTimeoutMS=400, connectTimeoutMS=400)
                print "Successfully connected to server"
                break
            except AutoReconnect, e:
                print "Connection to server failed. Retrying in 3 seconds..."
                time.sleep(3)
            except ConnectionFailure, e:
                print "Connection Failure. Retrying in 3 seconds..."
                time.sleep(3)
            except:
                pass
        self.db = self.conn.heroku_app16536491
        self.db.authenticate(self.username, self.password)
        '''self.data_month = self.db.data_month
        self.data_day = self.db.data_day
        self.data_hour = self.db.data_hour
        self.data_min = self.db.data_min
        self.data_sec = self.db.data_sec
        self.data_error = self.db.data_error
        self.pi_heartbeat = self.db.pi_heartbeat
        self.device_data = self.db.device_data'''
        #initialize the dbDict
        self.dbDict = {"month":self.db.data_month, "day":self.db.data_day, "hour":self.db.data_hour,
                       "min":self.db.data_min, "sec":self.db.data_sec}


    '''The method retrieveLastRecord queries the database server collection data_min, to obtain the latest usage data
       uploaded to the database, which belongs to the measurement node with the water meter ID "value". It returns the
       data in the format of a list with one data entry. This method will attempt to query continuously until a result
       is returned. If connection to the server fails, it will retry again after 3 seconds.'''
    def retrieveLastRecord(self, value):
        while 1:
            try:
                return list(self.db.data_min.find({"wmid": value}).sort("timestamp", pymongo.DESCENDING).limit(1))
            except AutoReconnect, e:
                print "Connection to server failed. Retrying in 3 seconds..."
                time.sleep(3)
            except ConnectionFailure, e:
                print "Connection Failure. Retrying in 3 seconds..."
                time.sleep(3)
            except:
                pass


    '''The method attemptUsageInsert takes the parameters wmid, counter, diff, intTemp, extTemp, tstamp and tstring,
       forms one usage data entry (JSON), and attempts to upload the entry to the usage collection belonging to dbStr.
       Upon successful uploading, the method returns one. Otherwise, a corresponding error message is printed and zero
       is returned.'''
    def attemptUsageInsert(self, dbStr, wmid, counter, diff, intTemp, extTemp, tstamp, tstring):
        try:
            tempPost = {"wmid": wmid, "counter": counter, "diff": diff, "intTemp": intTemp,
                        "extTemp": extTemp, "timestamp": tstamp, "timestring": tstring}
            #Find the corresponding database collection from the database dictionary, with dbStr as the key.
            self.dbDict[dbStr].insert(tempPost)
            return 1
        except AutoReconnect, e:
            print "Usage upload unsuccessful. Error: AutoReconnect."
            return 0
        except ConnectionFailure, e:
            print "Usage upload unsuccessful. Error: ConnectionFailure."
            return 0
        except:
            return -1


    '''The method attemptErrorInsert takes the parameters wmid, prevUsage, currUsage, prevTS, currTS, errorNo and
       errorMsg, forms one error data entry (JSON), and attempts to upload the entry to the error message collection
       in the database server. Upon successful uploading, the method returns one. Otherwise, a corresponding error
       message is printed and zero is returned.'''
    def attemptErrorInsert(self, wmid, prevUsage, currUsage, prevTS, currTS, errorNo, errorMsg):
        try:
            tempPost = {"wmid": wmid, "prev_usage": prevUsage, "curr_usage": currUsage,
                        "prev_ts": prevTS, "curr_ts": currTS, "errorNo": errorNo, "errorMsg": errorMsg}
            self.db.data_error.insert(tempPost)
            return 1
        except AutoReconnect, e:
            print "Error upload unsuccessful. Error: AutoReconnect."
            return 0
        except ConnectionFailure, e:
            print "Error upload unsuccessful. Error: ConnectionFailure."
            return 0
        except:
            return -1


    '''The method attemptStatusUpdate takes the parameters "wmid" and a boolean value "status", and attempts to update
       the data_meterID collection in the database server, such that the entry corresponding to the Water Meter ID
       with the value "wmid" will have its online status "Online" switches to "status". Upon successful uploading,
       the method returns one. Otherwise, a corresponding error message is printed and zero is returned.'''
    def attemptStatusUpdate(self, NodeID, status):
        try:
            self.db.device_data.update({"nodeid": NodeID}, {"$set": {"status": status}})
            return 1
        except AutoReconnect, e:
            print "Status update unsuccessful. Error: AutoReconnect."
            return 0
        except ConnectionFailure, e:
            print "Status update unsuccessful. Error: ConnectionFailure."
            return 0


    '''The method backupUsageInsert takes the parameters wmid, counter, diff, intTemp, extTemp, tstamp and tstring,
       which have been stored as backup data in cache memory, forms one usage data entry (JSON), and attempts to
       upload the entry to the usage collection belonging to dbStr. Upon successful uploading, the method returns
       one. Otherwise, a corresponding error message is printed and zero is returned.'''
    def backupUsageInsert(self, dbStr, wmid, counter, diff, intTemp, extTemp, tstamp, tstring):
        try:
            tempPost = {"wmid": wmid, "counter": counter, "diff": diff, "intTemp": intTemp,
                        "extTemp": extTemp, "timestamp": tstamp, "timestring": tstring}
            self.dbDict[dbStr].insert(tempPost)
            return 1
        except AutoReconnect, e:
            print "Backup Usage upload unsuccessful. Error: AutoReconnect."
            return 0
        except ConnectionFailure, e:
            print "Backup Usage upload unsuccessful. Error: ConnectionFailure."
            return 0
        except:
            return -1


    '''The method piHeartbeatInsert takes the parameters piID, timestamp, forms one Raspberry Pi heartbeat data entry,
       and attempts to upload the entry to the pi_heartbeat collection in the database server. This entry is for
       monitoring the online status of a Raspberry Pi device that manages a water usage network. Upon successful
       uploading, the method returns one. Otherwise, zero is returned.'''
    def piHeartbeatInsert(self, piID, timestamp, IP):
        try:
            tempPost = {"piID": piID, "timestamp": timestamp, "IPAddress": IP}
            self.db.pi_heartbeat.insert(tempPost)
            return 1
        except AutoReconnect, e:
            return 0
        except ConnectionFailure, e:
            return 0
        except:
            return -1


    '''The method meterIDUpdate is used for the node replacement procedure. It takes in two arguments, an oldID and a
       newID. The method locates the entry in the data_meterID collection of the database server that contains the
       "NodeID" of oldID, and replaces that with the newID. This method will attempt the update continuously until it
       is successful.'''
    def meterIDUpdate(self, oldID, newID):
        while 1:
            try:
                self.db.device_data.update({"nodeid": oldID}, {"$set": {"nodeid": newID}})
                break
            except AutoReconnect, e:
                pass
            except ConnectionFailure, e:
                pass


    '''The method manualConfigUpdate takes in four arguments, the new No Usage Threshold value "noUsage", the new
       Leakage Check Interval value "leakInterval", the new Leakage Continuation Threshold value "leakStreak", and
       the new Encryption Key value "keyValue". It removes the only entry in the data_config collection containing
       the old configuration values. Then it will upload a new entry containing the new configuration values along
       with a boolean "Updated" value of True. to data_config. This method will attempt the update continuously until
       it is successful.'''
    def manualConfigUpdate(self, NWID, noUsage, leakInterval, leakStreak, keyValue):
        while 1:
            try:
                self.db.data_config.remove({"nwid": NWID})
                tempPost = {"nwid": NWID, "NoUsage": noUsage,
                            "LeakInterval": leakInterval, "LeakStreak": leakStreak,
                            "EncryptionKey": keyValue, "Updated": True}
                self.db.data_config.insert(tempPost)
                break
            except AutoReconnect, e:
                pass
            except ConnectionFailure, e:
                pass


    '''The method autoConfigUpdate is for acknowledging the configuration value updates have been made successfully
       in the main client script. The method will attempt to update the lone data entry in the data_config collection
       by flipping the "Updated" value from False to True. Upon successful updating, the method returns one.
       Otherwise, zero is returned.'''
    def autoConfigUpdate(self):
        try:
            self.db.data_config.update({"Updated": False}, {"$set": {"Updated": True}})
            return 1
        except AutoReconnect, e:
            return 0
        except ConnectionFailure, e:
            return 0

        
    '''The method retrieveConfig returns the data entry from the data_config collection if the configuration values of
       that entry have not been updated and applied to the water usage monitoring network yet. In other words, the
       "Updated" value from the entry is still False. If the configuration values have not been updated, the method
       returns the entry containing the values. If the configuration have been updated, the method return an empty data
       entry. If the query is unsuccessful due to connection issue, None is returned.'''
    def retrieveConfig(self, NWID, needFalseFlag):
        try:
            if (needFalseFlag):
                result = list(self.db.data_config.find({"nwid": NWID, "Updated": False}).limit(1))
            else:
                result = list(self.db.data_config.find({"nwid": NWID}).limit(1))
                
            if result:
                return result[0]
            else:
                return {}
        except AutoReconnect, e:
            return None
        except ConnectionFailure, e:
            return None


    '''The method getMeterID returns all the data entries from the data_meterID collection of the database server which
       belong to the water usage network represented by the ID of NWID. The data entries are returned in the form of a
       list of all the entries. This method will attempt the query continuously until it is successful.'''
    def getMeterID(self, NWID):
        while 1:
            try:
                return list(self.db.device_data.find({"nwid": NWID}))
            except AutoReconnect, e:
                time.sleep(1)
            except ConnectionFailure, e:
                time.sleep(1)


    def pushIP(self, networkID, IPAddress):
        try:
            for i in range(5):
                self.db.data_ip.remove()
                self.db.data_ip.insert({nwid: networkID, "address": IPAddress})
        except AutoReconnect, e:
            pass
        except ConnectionFailure, e:
            pass


    def securityBreach(self, WMID):
        try:
            self.db.device_data.update({"wmid": WMID}, {"$set": {"security": True}})
        except AutoReconnect, e:
            pass
        except ConnectionFailure, e:
            pass
