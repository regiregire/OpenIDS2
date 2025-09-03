import socket 
import numpy as np
import cv2
import time

client_socket = None

def recvall(sock, count):

    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf: return None
        buf += newbuf
        count -= len(newbuf)
    return buf




def connect():
    global client_socket
    HOST = '192.168.0.11'
    PORT = 9999

    client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM) 


    client_socket.connect((HOST, PORT)) 


def disconnect():
    global client_socket
    client_socket.close()
    

def get_img():
    try:
        global client_socket

        message = '1'
        client_socket.send(message.encode()) 
                  
        length = recvall(client_socket,16)
        stringData = recvall(client_socket, int(length))
        data = np.frombuffer(stringData, dtype='uint8') 

        decimg=cv2.imdecode(data,1)
        return True, decimg 
    except:
        return False, None

       

