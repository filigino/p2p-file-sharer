#!/usr/bin/python3
#==============================================================================
#description     :SFWRENG 4C03 Programming assignment 3
#usage           :python fileSynchronizer.py trackerIP trackerPort
#python_version  :3.5
#Authors         :Gino Salayo, Chenhe Li, Yongyong Wei, Rong Zheng
#==============================================================================

import socket, sys, threading, json,time,os,ssl
import os.path
import glob
import json
import optparse


#Validate the IP address of the correct format
def validate_ip(s):
    '''
    Arguments:
    s -- dot decimal IP address in string
    Returns:
    True if valid; False otherwise
    '''
    a = s.split('.')
    if len(a) != 4:
        return False
    for x in a:
        if not x.isdigit():
            return False
        i = int(x)
        if i < 0 or i > 255:
            return False
    return True

# Validate the port number is in range [0,2^16 -1 ]
def validate_port(x):
    '''
    Arguments:
    x -- port number
    Returns:
    True if valid; False, otherwise
    '''
    if not x.isdigit():
        return False
    i = int(x)
    if i < 0 or i > 65535:
            return False
    return True


# Get file info in the local directory (subdirectories are ignored)
# Note: Exclude files with .so, .py, .dll suffixes
def get_file_info():
    '''
    Get file information in the current folder. which is used to construct the
    intial message as the instructions (exclude subfolder, you may also exclude *.py)

    Return: an array, with each element is {'name':filename,'mtime':mtime}
    i.e, [{'name':filename,'mtime':mtime},{'name':filename,'mtime':mtime},...]

    hint: use os.path.getmtime to get mtime, due to the fact mtime is handled
    differntly in different platform (ref: https://docs.python.org/2/library/os.path.html)
    here mtime should be rounded *down* to the closest integer. just use int(number)
    '''
    #YOUR CODE

    # Iterate through each entry in same directory as fileSynchronizer.py and
    # add filenames and their mtimes to the array (ignoring subdirectories and
    # specific file types
    file_info = []
    ignoredTypes = [".exe", ".py", ".pyd", ".dll"]

    entryList = os.scandir(sys.path[0])
    for entry in entryList:
        if os.path.isfile(entry):
            isValidFile = True

            for type in ignoredTypes:
                if type in entry.name:
                    isValidFile = False
                    break

            if isValidFile:
                file_info.append({"name": entry.name, "mtime": int(os.path.getmtime(entry))})

    return file_info


#Check if a port is available
def check_port_available(check_port):
    '''
    Arguments:
    check_port -- port number
    Returns:
    True if valid; False otherwise
    '''
    if str(check_port) in os.popen("netstat -na").read():
        return False
    return True

#Get the next available port by searching from initial_port to 2^16 - 1
#Hint: use check_port_avaliable() function
def get_next_available_port(initial_port):
    '''
    Arguments:
    initial_port -- the first port to check

    Hint: you can call check_port_available until find one or no port available.
    Return:
    port found to be available; False if no any port is available.
    '''

    #YOUR CODE
    next_available_port = -1

    for port in range(initial_port, 2**16):
        if check_port_available(port):
            next_available_port = port
            break

    return next_available_port


class FileSynchronizer(threading.Thread):
    def __init__(self, trackerhost,trackerport,port, host='0.0.0.0'):

        threading.Thread.__init__(self)
        #Port for serving file requests
        self.port = port #YOUR CODE
        self.host = host #YOUR CODE

        #Tracker IP/hostname and port
        self.trackerhost = trackerhost #YOUR CODE
        self.trackerport = trackerport #YOUR CODE

        self.BUFFER_SIZE = 8192

        #Create a TCP socket to communicate with tracker
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #YOUR CODE
        self.client.settimeout(180)

        #Store the message to be sent to tracker. Initialize to Init message
        #that contains port number and local file info. (hint: json.dumps)

        self.msg = json.dumps({"port": self.port, "files": get_file_info()}) #YOUR CODE

        #Create a TCP socket to serve file requests.
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #YOUR CODE

        try:
            self.server.bind((self.host, self.port))
        except socket.error:
            print(('Bind failed %s' % (socket.error)))
            sys.exit()
        self.server.listen(10)

    # Not currently used. Ensure sockets are closed on disconnect
    def exit(self):
        self.server.close()

    #Handle file requests from a peer(i.e., send requested file content to peers)
    def process_message(self, conn, addr):
        '''
        Arguments:
        self -- self object
        conn -- socket object for an accepted connection from a peer
        addr -- address bound to the socket of the accepted connection
        '''
        #YOUR CODE - DONE
        #Step 1. read the file name contained in the request
        #Step 2. read the file from the local directory (assumming binary file <4MB)
        #Step 3. send the file to the requester
        #Note: use socket.settimeout to handle unexpected disconnection of a peer
        #or prolonged responses to file requests
        timeout = 60.0
        conn.settimeout(timeout)

        print("Client connected with " + addr[0] + ":" + str(addr[1]))

        try:
            # Read file name
            requestedFile = ""
            while True:
                requestedFile += conn.recv(self.BUFFER_SIZE).decode()
                if len(requestedFile) < self.BUFFER_SIZE:
                    break
            # Read file
            with open(sys.path[0] + "\\" + requestedFile, "rb") as file:
                content = file.read()
            # Send file
            conn.send(content)
        except socket.timeout:
            print("Conn socket timeout!")
        except socket.error as e:
            print('Socket error: %s' % e)

        conn.close()

    def run(self):
        self.client.connect((self.trackerhost,self.trackerport))
        t = threading.Timer(5, self.sync)
        t.start()
        print(('Waiting for connections on port %s' % (self.port)))
        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.process_message, args=(conn,addr)).start()

    #Send Init or KeepAlive message to tracker, handle directory response message
    #and  request files from peers
    def sync(self):
        print(('connect to:' + self.trackerhost, self.trackerport))
        #Step 1. send self.msg (when sync is called the first time, self.msg contains
        #the Init message. Later, in Step 4, it will be populated with a KeepAlive message)
        #YOUR CODE
        self.client.send(bytes(self.msg, "utf-8"))

        #Step 2. receive a directory response message from a tracker
        directory_response_message = ""
        #YOUR CODE
        try:
            while True:
                directory_response_message += self.client.recv(self.BUFFER_SIZE).decode()
                if len(directory_response_message) < self.BUFFER_SIZE:
                    self.client.close()
                    break
        except socket.error as e:
            print('Socket error: %s' % e)

        #Step 3. parse the directory response message. If it contains new or
        #more up-to-date files, request the files from the respective peers and
        #set the modified time for the synced files to mtime of the respective file
        #in the directory response message (hint: using os.utime).

        #YOUR CODE
        localFileList = get_file_info()

        for filename, fileInfo in json.loads(directory_response_message).items():
            isNew = True
            for localFile in localFileList:
                if filename == localFile["name"]:
                    isNew = False
                    if fileInfo["mtime"] > localFile["mtime"]:
                        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.client.connect((fileInfo["ip"], fileInfo["port"]))
                        self.client.send(bytes(filename, "utf-8"))

                        try:
                            with open(sys.path[0] + "\\" + filename, "wb") as file:
                                while True:
                                    content = self.client.recv(self.BUFFER_SIZE)
                                    file.write(content)
                                    if len(content) < self.BUFFER_SIZE:
                                        self.client.close()
                                        break
                        except socket.error as e:
                            print('Socket error: %s' % e)
                        os.utime(filename, (os.path.getatime(filename), fileInfo["mtime"]))
                        break
            if isNew:
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.connect((fileInfo["ip"], fileInfo["port"]))
                self.client.send(bytes(filename, "utf-8"))

                try:
                    with open(sys.path[0] + "\\" + filename, "wb") as file:
                        while True:
                            content = self.client.recv(self.BUFFER_SIZE)
                            file.write(content)
                            if len(content) < self.BUFFER_SIZE:
                                self.client.close()
                                break
                except socket.error as e:
                    print('Socket error: %s' % e)
                os.utime(filename, (os.path.getatime(filename), fileInfo["mtime"]))

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.trackerhost, self.trackerport))

        #Step 4. construct a KeepAlive message (hint: json.dumps)
        self.msg = json.dumps({"port": self.port}) #YOUR CODE

        #Step 5. start timer
        t = threading.Timer(5, self.sync)
        t.start()

if __name__ == '__main__':
    # parse command line arguments
    parser = optparse.OptionParser(usage="%prog ServerIP ServerPort")
    options, args = parser.parse_args()
    if len(args) < 1:
        parser.error("No ServerIP and ServerPort")
    elif len(args) < 2:
        parser.error("No ServerIP or ServerPort")
    else:
        if validate_ip(args[0]) and validate_port(args[1]):
            tracker_ip = args[0]
            tracker_port = int(args[1])

        else:
            parser.error("Invalid ServerIP or ServerPort")
    # get free port
    synchronizer_port = get_next_available_port(8000)
    synchronizer_thread = FileSynchronizer(tracker_ip,tracker_port,synchronizer_port)
    synchronizer_thread.start()
