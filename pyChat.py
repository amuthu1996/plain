from tkinter import *
import threading
import socket
import random
import functools
import math

#GLOBALS
conn_array=[] #stores open sockets
secret_array=dict() #key: the open sockets in conn_array, value: integers for encryption
username_array=dict() #key: the open sockets in conn_array, value: usernames for the connection
contact_array=dict() #key: ip address as a string, value: [port, username]

username = "Self"

location=0
port=0
top=""

main_body_text= 0
#-GLOBALS-

###So,
   #  x_encode your message with the key, then pass that to
   #  refract to get a string out of it.
   # To decrypt, pass the message back to x_encode, and then back to refract


#converts the string into binary
def binWord(word):
	master=""
	for letter in word:
		temp=bin(ord(letter))[2:]
		while(len(temp)<7):
			temp='0'+temp
		master=master+temp
	return master


#encrypts the binary message by the binary key
def xcrypt(message, key):
	count=0
	master=""
	for letter in message:
		if(count==len(key)):
			count=0
		master=master+str(int(letter) ^ int(key[count]))
		count=count+1
	return master


#Encrypts the string by the number
def x_encode(string, number):
	return xcrypt(binWord(string), bin(number)[2:])


#Returns the string representation of the binary (has trouble with spaces)
def refract(binary):
	master=""
	for x in range(0, int(len(binary)/7)):
		master=master+chr(int(binary[x*7:(x+1)*7],2)+0)
	return master

#I'm not actually sure why this is here. But it's used, so for now it stays.
#Raises x to the power of y
def power(x, y):
	if(y==0):
		return 1
	if(y==1):
		return x
	final=1
	for n in range(0,y):
		final=final*x
	return final

#Ensures that number is atleast length 4 by adding extra zeros to the front
def formatNumber(number):
	temp=str(number)
	while(len(temp)<4):
		temp='0'+temp
	return temp

#Sends message through the open socket conn with the encryption key secret
#It first sends the length of the incoming message, then sends the actual message.
def netThrow(conn, secret, message):
   conn.send(formatNumber(len(x_encode(message,secret))).encode())
   conn.send(x_encode(message,secret).encode())
   
#Receive and return the message through open socket conn, decrypting using key secret.
#If the message length begins with - instead of a number, process as a flag and return 1.
def netCatch(conn, secret):
   data = conn.recv(4)
   if(data.decode()[0]=='-'):
      processFlag(data.decode(), conn)
      return 1
   data = conn.recv(int(data.decode()))
   return refract(xcrypt(data.decode(), bin(secret)[2:]))


#Checks to see if a number is prime
def isPrime(number):
	x=1
	if(number==2):
		return True
	while (x<math.sqrt(number)):
		x=x+1
		if(number%x==0):
			return False
	return True

#Process the flag corresponding to number, using open socket conn if necessary
def processFlag(number, conn=None):
   global statusConnect
   global conn_array
   global secret_array
   global username_array
   global contact_array
   t= int(number[1:])
   if(t==1): #disconnect
      if(len(conn_array)==1): #in the event of single connection being left or if we're just a client
              writeToScreen("Connection closed.","System")
              dump=secret_array.pop(conn_array[0])
              dump=conn_array.pop()
              dump.close()
              statusConnect.set("Connect")
      if(conn!=None):
              writeToScreen("Connect to " + conn.getsockname()[0] + " closed.", "System")
              dump=secret_array.pop(conn)
              conn_array.remove(conn)
              conn.close()
               
   if(t==2): #username change
           name = netCatch(conn, secret_array[conn])
           if(isUsernameFree(name)):
                   writeToScreen("User "+username_array[conn]+" has changed their username to "+name, "System")
                   username_array[conn] = name
                   contact_array[conn.getpeername()[0]]= [conn.getpeername()[1], name]
           else:
                   conn.send("-003".encode())

   if(t==3): #username already taken OR username requested is the IP of another connection, pick another one
           global username
           username = "Self"
           writeToScreen("Username is already taken, please choose another.", "System")
           for conn in conn_array:
                   conn.send("-002".encode())
                   netThrow(conn, secret_array[conn], conn.getpeername()[0])

   if(t==4): #passing a friend who this should connect to (I am assuming it will be running on the same port as the other session)
           data = conn.recv(4)
           data = conn.recv(int(data.decode()))
           Client(data, int(contact_array[conn.getpeername()[0]][0])).start()
           
           
           

#processes commands passed in via the / text input #HOLY SHIT PLEASE, ERROR CHECKING
def processUserCommands(command, param):
        global conn_array
        global secret_array
        global username
        
        if(command == "nick"): #change nickname
                writeToScreen("Username is being changed to "+param[0], "System")
                for conn in conn_array:
                        conn.send("-002".encode())
                        netThrow(conn, secret_array[conn], param[0])
                username = param[0]
        if(command == "disconnect"): #disconnects from current connection
                for conn in conn_array:
                        conn.send("-001".encode())
                processFlag("-001")
        if(command == "connect"): #connects to passed in host port
                Client(param[0], int(param[1])).start()
                
        if(command == "kick"):
                print("I need to figure out a way to make it know what conn to grab based on the username")
        if(command == "host"): #starts server on passed in port
                Server(int(param[0])).start()
                
           
#checks to see if the username name is free for use
def isUsernameFree(name):
        global username_array
        global username
        for conn in username_array:
               if(name==username_array[conn] or name==username):
                       return False
        return True


#sends conn all of the people currently in conn_array so they can connect to them
def passFriends(conn):
        global conn_array
        for connection in conn_array:
                conn.send("-004".encode())
                conn.send(formatNumber(len(connection.getpeername()[0])).encode()) #pass the ip address
                conn.send(connection.getpeername()[0].encode())
                #conn.send(formatNumber(len(connection.getpeername()[1])).encode()) #pass the port number
                #conn.send(connection.getpeername()[1].encode())

#--------------------------------------------------------------------------

#Launches client options window for getting destination hostname and port
def client_options_window(master):
   top = Toplevel(master)
   top.title("Connection options")
   Label(top, text="Server IP:").grid(row=0)
   location = Entry(top)
   location.grid(row=0, column=1)
   Label(top, text="Port:").grid(row=1)
   port = Entry(top)
   port.grid(row=1, column=1)
   go = Button(top, text="Connect", command=lambda:client_options_go(location.get(), port.get(), top ))
   go.grid(row=2, column=1)

#Processes the options entered by the user in the client options window
def client_options_go(dest, port, window):
   if(options_sanitation(port, dest)):
      window.destroy()
      Client(dest, int(port)).start()


#Checks to make sure the port and the destination ip are both valid, launches error windows if there are any issues
def options_sanitation(por, loc=""): 
   if(not por.isnumeric()):
      error_window(root,"Please input a port number.")
      return False
   if(int(por)<0 or 65555<int(por)):
      error_window(root,"Please input a port number between 0 and 65555")
      return False
   if(loc!=""):
           if(not ip_process(loc.split("."))):
                   error_window(root,"Please input a valid ip address.")
                   return False
   return True
   


#Checks to make sure every section of the ip is a valid number
def ip_process(ipArray):
        if(len(ipArray)!=4):
                return False
        for ip in ipArray:
                if(not ip.isnumeric()):
                        return False
                t=int(ip)
                if(t<0 or 255<t):
                        return False
        return True
   

#----------------------------------------------------------------------------------------

#Launches server options window for getting port
def server_options_window(master):
   top = Toplevel(master)
   top.title("Connection options")
   Label(top, text="Port:").grid(row=0)
   port = Entry(top)
   port.grid(row=0, column=1)
   go = Button(top, text="Launch", command=lambda:server_options_go(port.get(), top))
   go.grid(row=1, column=1)

#Processes the options entered by the user in the server options window
def server_options_go(port, window):
   if(options_sanitation(port)):
      window.destroy()
      Server(int(port)).start()

#----------------------------------------------------------------------------------------

#Launches a new window to display the message texty
def error_window(master, texty):
   window = Toplevel(master)
   window.title("ERROR")
   Label(window, text=texty).pack()
   go = Button(window, text="OK", command=window.destroy)
   go.pack()


#----------------------------------------------------------------------------------------
#Contacts window

#Displays the contacts window, allowing the user to select a recent connection to reuse
def contacts_window(master):
        global contact_array
        cWindow = Toplevel(master)
        cWindow.title("Contacts")
        scrollbar = Scrollbar(cWindow, orient=VERTICAL)
        listbox = Listbox(cWindow, yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        for person in contact_array:
                listbox.insert(END, contact_array[person][1]+" "+person+" "+contact_array[person][0])
        listbox.pack(side=LEFT, fill=BOTH, expand=1)
        

#Loads the recent chats out of the persistant file contacts.dat
def load_contacts():
        global contact_array
        try:
                filehandle = open("data\\contacts.dat", "r")
        except IOError:
                return
        line= filehandle.readline()
        while(len(line)!=0):
                temp = (line.rstrip('\n')).split(" ") #format: ip, port, name
                contact_array[temp[0]]=temp[1:]
                line= filehandle.readline()
        filehandle.close()

#Saves the recent chats to the persistant file contacts.dat
def dump_contacts():
        global contact_array
        try:
                filehandle = open("data\\contacts.dat", "w")
        except IOError:
                print("Can't dump contacts.")
                return
        for contact in contact_array:
                filehandle.write(contact+" "+contact_array[contact][0]+" "+contact_array[contact][1]+"\n")
        filehandle.close()


#----------------------------------------------------------------------------------------

#places the text from the text bar on to the screen and sends it to everyone this program is connected to
def placeText(text):
    global conn_array
    global secret_array
    global username
    writeToScreen(text, username)
    for person in conn_array:
            netThrow(person, secret_array[person], text)

#places text to main text body in format "username: text"
def writeToScreen(text, username=""):
        global main_body_text
        main_body_text.config(state=NORMAL)
        main_body_text.insert(END, '\n')
        if(username!=""):
                main_body_text.insert(END, username+": ")
        main_body_text.insert(END, text)
        main_body_text.yview(END)
        main_body_text.config(state=DISABLED)

#takes text from text bar input, and calls processUserCommands if it begins with /
def processUserText(event):
        data = text_input.get()
        if(data[0]!="/"): #is not a command
                placeText(data)
        else: 
                if(data.find(" ")==-1):
                        command = data[1:]
                else:
                        command = data[1:data.find(" ")]
                params = data[data.find(" ")+1:].split(" ")
                processUserCommands(command, params)
        text_input.delete(0,END)
                
                


#----------------------------------------------------------------------------------------
#Server

class Server ( threading.Thread ):
   def __init__(self, port):
           threading.Thread.__init__(self)
           self.port = port


   def run ( self ):
       global conn_array
       s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       s.bind(('', self.port))
       
       if(len(conn_array)==0):
               writeToScreen("Socket is good, waiting for connections on port: "+str(self.port), "System")
       s.listen(1)
       global conn_init
       conn_init, addr_init = s.accept()
       serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       serv.bind(('', 0)) #get a random empty port
       serv.listen(1)
       
       portVal = str(serv.getsockname()[1])
       if(len(portVal)==5):
               conn_init.send(portVal.encode())
       else:
               conn_init.send(("0"+portVal).encode())

       conn_init.close() 
       conn, addr = serv.accept()
       conn_array.append(conn) #add an array entry for this connection
       writeToScreen("Connected by " + str(addr[0]), "System")
       
       global statusConnect
       statusConnect.set("Disconnect")
       
       

       #create the numbers for my encryption
       prime= random.randint(1000,9000)
       while(not isPrime(prime)):
               prime = random.randint(1000,9000)
       print(prime, isPrime(prime)) 
       base= random.randint(20,100)
       a= random.randint(20,100)

       #send the numbers (base, prime, A)
       conn.send(formatNumber(len(str(base))).encode())
       conn.send(str(base).encode())

       conn.send(formatNumber(len(str(prime))).encode())
       conn.send(str(prime).encode())

       conn.send(formatNumber(len(str(power(base,a)%prime))).encode())
       conn.send(str(power(base,a)%prime).encode())

       #get B
       data = conn.recv(4)
       data = conn.recv(int(data.decode()))
       b= int(data.decode())

       #calculate the encryption key
       global secret_array
       secret = power(b, a) % prime
       secret_array[conn]=secret #store the encryption key by the connection
       username_array[conn] = addr[0]
       contact_array[str(addr[0])]=[str(self.port), "No nick"]
       passFriends(conn)
       threading.Thread(target=Runner, args=(conn, secret)).start()
       Server(self.port).start()


class Client (threading.Thread):

    def __init__(self, host, port):
            threading.Thread.__init__(self)
            self.port = port
            self.host = host

    def run(self):
        global conn_array
        global secret_array
        conn_init = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn_init.settimeout(5.0)
        try:
                conn_init.connect((self.host, self.port))
        except socket.timeout:
                writeToScreen("Timeout issue. Host possible not there.", "System")
                raise SystemExit(0)
        except socket.error:
                writeToScreen("Connection issue. Host actively refused connection.", "System")
                raise SystemExit(0)
        porta = conn_init.recv(5)
        porte = int(porta.decode())
        conn_init.close()
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((self.host,porte))
        
        writeToScreen("Connected to: " + self.host +" on port: "+ str(porte), "System")
        
        global statusConnect
        statusConnect.set("Disconnect")
        
        conn_array.append(conn)
        #get my base, prime, and A values
        data = conn.recv(4)
        data = conn.recv(int(data.decode()))
        base = int(data.decode())
        data = conn.recv(4)
        data = conn.recv(int(data.decode()))
        prime = int(data.decode())
        data = conn.recv(4)
        data = conn.recv(int(data.decode()))
        a = int(data.decode())
        b = random.randint(20,100)
        #send the B value
        conn.send(formatNumber(len(str(power(base,b)%prime))).encode())
        conn.send(str(power(base,b)%prime).encode())
        secret = power(a,b)%prime
        secret_array[conn]=secret
        username_array[conn] = self.host
        contact_array[conn.getpeername()[0]]=[str(self.port), "No nick"]
        threading.Thread(target=Runner, args=(conn, secret)).start()


def Runner (conn, secret):
        global username_array
        while(1):
                data = netCatch(conn,secret)
                if(data!=1):
                        writeToScreen(data, username_array[conn])

#----------------------------------------------------------------------------------------
#Menu helpers
                        
def QuickClient():
        window = Toplevel(root)
        window.title("Connection options")
        Label(window, text="Server IP:").grid(row=0)
        destination = Entry(window)
        destination.grid(row=0, column=1)
        go = Button(window, text="Connect", command=lambda: client_options_go(destination.get(), "9999", window))
        go.grid(row=1, column=1)
        

def QuickServer():
        Server(9999).start()

def connects (clientType):
    global conn_array
    if(len(conn_array)==0):
        if(clientType==0):
           client_options_window(root)
        if(clientType==1):
            server_options_window(root)
    else:
       for connection in conn_array: 
               connection.send("-001".encode())
       processFlag("-001")

#----------------------------------------------------------------------------------------

root = Tk()
root.title("Chat")

def dummy():
        print("Write this function")

def dummer(push):
        print("Nooo!")

menubar = Menu(root)

file_menu= Menu(menubar, tearoff=0)
file_menu.add_command(label="Save chat", command=lambda: dummer(1)) #####
file_menu.add_command(label="Change username", command=lambda: dummer(2)) #####
file_menu.add_command(label="Exit", command=lambda: dummer(3)) #####
menubar.add_cascade(label="File", menu=file_menu)

connection_menu = Menu(menubar, tearoff=0)
connection_menu.add_command(label="Quick Connect", command=QuickClient)
connection_menu.add_command(label="Connect on port", command=lambda:client_options_window(root) )
connection_menu.add_command(label="Disconnect", command=lambda: processFlag("-001"))
menubar.add_cascade(label="Connect", menu=connection_menu)

server_menu = Menu(menubar, tearoff=0)
server_menu.add_command(label="Launch server", command=QuickServer)
server_menu.add_command(label="Listen on port", command=lambda: server_options_window(root))
server_menu.add_command(label="Kick user", command=dummy) #####
menubar.add_cascade(label="Server", menu=server_menu)

menubar.add_command(label="Contacts", command=lambda:contacts_window(root))

root.config(menu=menubar)

main_body = Frame(root, height=20, width=50)

main_body_text = Text(main_body)
body_text_scroll = Scrollbar(main_body)
main_body_text.focus_set()
body_text_scroll.pack(side=RIGHT, fill=Y)
main_body_text.pack(side=LEFT, fill=Y)
body_text_scroll.config(command=main_body_text.yview)
main_body_text.config(yscrollcommand=body_text_scroll.set)
main_body.pack()

main_body_text.insert(END, "Welcome to the chat program!")
main_body_text.config(state=DISABLED)

text_input = Entry(root, width=60 )
text_input.bind("<Return>",processUserText)
text_input.pack()

statusConnect= StringVar()
statusConnect.set("Connect")
clientType= 1
Radiobutton(root, text="Client", variable= clientType, value=0).pack(anchor=E)
Radiobutton(root, text="Server", variable= clientType, value=1).pack(anchor=E)
connecter = Button(root, textvariable=statusConnect, command=lambda: connects(clientType))
connecter.pack()

load_contacts()

#------------------------------------------------------------#

root.mainloop()

dump_contacts()
