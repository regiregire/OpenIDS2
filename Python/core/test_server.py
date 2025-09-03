import socket
from _thread import *
import cv2
from queue import Queue
import numpy as np

client_socket = None


def recvall(sock, count):
    #print("recvall1")
    buf =b''
    while count:
        #print("recvall2")
        newbuf =sock.recv(count)
        #print("recvall3")
        if not newbuf:
            #print("recvall4")
            return None
        #print("recvall5")
        buf +=newbuf
        #print("recvall6")
        count -=len(newbuf)
        #print("recvall7")
    return buf


def connect():
    global client_socket
    HOST="192.168.0.13"
    PORT=9999

    server_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    #클라이언트가 접속하면 accept함수에서 새로운 소켓을 리턴
    #새로운 쓰레드에서 해당 소켓을 사용하여 통신
    client_socket, addr =server_socket.accept()
    



def get_image():
    global client_socket
    #print("get image1")
    try:

        #데이터가 수신되면 클라이언트에 다시 전송

        #data=client_socket.recv(1024)#1024

        '''
        print(data)
        if not data:
            print('Disconnected by', addr[0], ":", addr[1])
            break
        '''
        length =recvall(client_socket,16)
        #print("get image2")
        try:
            stringData =recvall(client_socket, int(length))
            #print("get image3")
            dat =np.frombuffer(stringData, dtype ='uint8')
            #print("get image4")
            decimg=cv2.imdecode(dat,1)
            #print("get image5")

            

            return True, decimg
        except Exception as E:
            print(E)
            return False, None

            
        #print ('recieved from', addr[0], ":", addr[1], data.decode())
        #client_socket.send(data)
        
    except Exception as E:
        print(E)
    #except ConnectionResetError as e:
     #   print('Disconnected by', addr[0],":", addr[1])


