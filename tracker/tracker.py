__author__      = "Gino Salayo"

import socket, sys, threading, json, time, optparse, os


def validate_ip(s):
    """
    Check if an input string is a valid IP address dot decimal format
    Inputs:
    - a: a string

    Output:
    - True or False
    """
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


def validate_port(x):
    """
    Check if the port number is within range
    Inputs:
    - x: port number

    Output:
    - True or False
    """
    if not x.isdigit():
        return False
    i = int(x)
    if i < 0 or i > 65535:
            return False
    return True


class Tracker(threading.Thread):
    def __init__(self, port, host='0.0.0.0'):
        threading.Thread.__init__(self)
        self.port = port #port used by tracker
        self.host = host #tracker's IP address
        self.BUFFER_SIZE = 8192
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #socket to accept connections from peers

         # Track (ip, port, exp time) for each peer using a dictionary
         # You can optionally use (ip,port) as key
        self.users = {}

        # Track (ip, port, modified time) for each file
        # Only the most recent modified time and the respective peer are store
        # {'ip':,'port':,'mtime':}
        self.files = {}

        self.lock = threading.Lock()
        try:
            #YOUR CODE
            #Bind to address and port
            self.server.bind((self.host, self.port))
        except socket.error:
            print(('Bind failed %s' % (socket.error)))
            sys.exit()

        #YOUR CODE
        #listen for connections
        self.server.listen(1)

    def check_user(self):
        #Check if the peers are alive or not
        """Steps:
            1. check if a peer has expired or not
            2. if expired, remove items self.users and self.files ()
            [Pay attention to race conditions (Hint: use self.lock)]
        """
        #YOUR CODE
        deleteUser = ''
        deleteFile = ''
        for user, TTL in self.users.items():
            if time.perf_counter() - TTL > 180:
                self.lock.acquire()
                for file, info in self.files.items():
                    if info['port'] == user[1]:
                        deleteFile = file
                deleteUser = user
                self.lock.release()
                break

        if deleteUser and deleteFile:
            del self.users[deleteUser]
            del self.files[deleteFile]
            deleteUser = ''
            deleteFile = ''

        #schedule the method to be called periodically
        t = threading.Timer(20, self.check_user)
        t.start()

   #Ensure sockets are closed on disconnect (This function is Not used)
    def exit(self):
        self.server.close()

    def run(self):
        # start the timer to check if peers are alive or not
        t = threading.Timer(20, self.check_user)
        t.start()

        print(('Waiting for connections on port %s' % (self.port)))
        while True:
            #accept incoming connection
            # YOUR CODE
            conn, addr = self.server.accept()

            #process the message from a peer
            threading.Thread(target=self.process_messages, args=(conn, addr)).start()


    def process_messages(self, conn, addr):
        conn.settimeout(180.0)
        print(('Client connected with ' + addr[0] + ':' + str(addr[1])))

        while True:
            #receiving data from a peer
            data = ''
            while True:
                part = conn.recv(self.BUFFER_SIZE).decode()
                data = data + part
                if len(part) < self.BUFFER_SIZE:
                    break

            # Check if the received data is a json string of the anticipated format. If not, ignore.
            #YOUR CODE
            try:
                #deserialize
                data_dic = json.loads(data)
            except json.decoder.JSONDecodeError:
                print('Incorrect format (JSON required)')


            """
            1) Update self.users and self.files if nessesary
            2) Send directory response message
            Steps:1. Check message type (initial or keepalive). See Table I in description.
                  2. If this is an initial message from a peer and the peer is not in self.users, create the corresponding entry in self.users
                  2. If this is a  keepalive message, update the expire time with the respective peer
                  3. For an intial message, check the list of files. Create a new entry in user.files if one does not exist,
                  or, update the last modifed time to the most recent one
                  4. Pay attention to race conditions (Hint: use self.lock)
            """
            #YOUR CODE

            # Initial message
            if len(data_dic) > 1:
                # Check if new peer
                newUser = True
                for user in self.users:
                    if user[1] == data_dic['port']:
                        newUser = False
                        break

                # Track new peer
                if newUser:
                    self.lock.acquire()
                    self.users[(self.host, data_dic['port'])] = time.perf_counter()
                    self.lock.release()

                # Check if new file
                for peerFile in data_dic['files']:
                    newFile = True
                    oldFile = ''
                    for file in self.files:
                        if file == peerFile['name']:
                            newFile = False
                            oldFile = file
                            break

                    # Track new file
                    if newFile:
                        self.lock.acquire()
                        self.files[peerFile['name']] = {'ip' : self.host, 'mtime' : peerFile['mtime'], 'port' : data_dic['port']}
                        self.lock.release()
                    # Update IP addreess, mtime, and port for already existing file
                    elif self.files[oldFile]['mtime'] > peerFile['mtime']:
                        self.lock.acquire()
                        self.files[oldFile]['ip'] = self.host
                        self.files[oldFile]['mtime'] = peerFile['mtime']
                        self.files[oldFile]['port'] = data_dic['port']
                        self.lock.release()

            # Keepalive
            else:
                self.lock.acquire()
                self.users[(self.host, data_dic['port'])] = time.perf_counter()
                self.lock.release()

            # Send directory response message
            conn.send(bytes(json.dumps(self.files), 'utf-8'))
        conn.close() # Close

if __name__ == '__main__':
    parser = optparse.OptionParser(usage="%prog ServerIP ServerPort")
    options, args = parser.parse_args()
    if len(args) < 1:
        parser.error("No ServerIP and ServerPort")
    elif len(args) < 2:
        parser.error("No  ServerIP or ServerPort")
    else:
        if validate_ip(args[0]) and validate_port(args[1]):
            server_ip = args[0]
            server_port = int(args[1])
        else:
            parser.error("Invalid ServerIP or ServerPort")
    tracker = Tracker(server_port,server_ip)
    tracker.start()
