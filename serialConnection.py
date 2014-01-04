'''This Python script, serialConnection.py, imports the PySerial library to create a serial connection between
   the Raspberry Pi and the water usage monitor node, to allow transmission of data and communication across
   the two platforms.'''
import serial

'''The serialConnection class creates a Serial Connection Client object, which provides access to the serial port
   of the Raspberry Pi for communicating with the water usage monitor node.'''
class serialConnection(object):

    '''The Serial Connection Client properties are as follows:
       It occupies the serial port of the Raspberry Pi for communication.
       Baud Rate: 115200
       Bytesize: 8 bits
       Parity: None
       Stopbits: 1
       Read Timeout: 0.5 seconds
       Write Timeout: 0.5 seconds'''
    def __init__(self, port="/dev/ttyAMA0", baud=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE, readTimeout=0.5, writeTimeout=0.5):
        self.port = port
        self.baud = baud
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = readTimeout
        self.writeTimeout = writeTimeout
        self.connection = None

    '''The connect method switches on the connection of the Serial Connection Client with the aforementioned
       properties.'''
    def connect(self):
        self.connection = serial.Serial(self.port, self.baud, self.bytesize, self.parity,
                                        self.stopbits, timeout=self.timeout, writeTimeout=self.writeTimeout)
        if (self.connection.isOpen() == False):
            self.connection.open()
        print "Serial port opened"
        print self.connection.portstr

    '''The write method sends the string message toWrite from the Raspberry Pi to the water usage monitor node.
       It will timeout after 0.5 seconds if the write attempt is still unsuccessful then.'''
    def write(self, toWrite):
        self.connection.write(toWrite)

    '''The read method reads the next line sent over from the water usage monitor node via the serial port.
       It will read until an end of line character is reached. The read will stall for 0.5 seconds before
       timing out if there is nothing available for reading.'''
    def read(self):
        return self.connection.readline()

    '''The flushInput method empties the input that has been stored in the buffer that the Raspberry Pi has yet
       to read.'''
    def flushInput(self):
        self.connection.flushInput()

    '''The flushOutput method empties the output that has been stored in the buffer that the water usage monitor
       node has yet to read.'''
    def flushOutput(self):
        self.connection.flushOutput()

    '''The close method closes the open serial connection of the Serial Connection Client.'''
    def close(self):
        self.connection.close()
