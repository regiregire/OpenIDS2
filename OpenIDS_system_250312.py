from typing import Any, Tuple, Union

import serial
import os
import time
import threading
import winsound
import paramiko
import sys
import cv2
import numpy as np
import math
import socketreceive
import test_server
from PIL import Image
from PyQt5.QtGui import QPixmap, QImage
import PyQt5
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


ink_pump1,ink_pump2, dT,xp,ACN,Oxidizer,Deblock,arduino,linear,amidite_T = None,None,None,None,None,None,None,None,None,None
command = None
try:
    sound_path = os.getcwd()+'\\x64\\Release\\alram'
    synthesis_log_path = os.getcwd() + '\\x64\\Release\\synthesis_log\\' +time.strftime("%y_%m_%d_%H시%M")
    synthesis_log_txt = open(synthesis_log_path+'.txt','w')
    sequence_path = os.getcwd() + '\\x64\\Release\\sequence.txt'

    
except Exception as E:
    print("log폴더 생성햇")
            


class System():
    def connection(self):
        
        connection_Fluidics = [0, 0, 0,0]
        Current_position=0
        
        global ink_pump1,ink_pump2,dT,ACN,Oxidizer,Deblock,arduino,linear
        '''
        print("connection")
        try:
            ACN = serial.Serial("COM4", 9600, write_timeout=1, timeout=0.1)
            connection_Fluidics[0] = True
            print("ACN connect")
            
        except Exception as e:
            print(e)
            connection_Fluidics[0] = False

        try:
            Oxidizer = serial.Serial("COM100", 9600, write_timeout=1, timeout=0.1)

            connection_Fluidics[1] = True
            print("oxidizer connect")
            
        except Exception as e:
            print(e)
            connection_Fluidics[1] = False

        try:
            Deblock = serial.Serial("COM8", 9600, write_timeout=1, timeout=0.1)

            connection_Fluidics[2] = True
            print("deblock connect")
            
        except Exception as e:
            print(e)
            connection_Fluidics[2] = False
        '''
        try:
            dT = serial.Serial("COM6", 9600, write_timeout=1, timeout=0.1)
            connection_Fluidics[3] = True
            print("dT connect")

            
        except Exception as e:
            print(e)
            connection_Fluidics[3] = False
        '''
        try:
            
            ink_pump1 = serial.Serial("COM7", 9600)
            print("ink pump1 connect")

        except Exception as e:
            print(e)
            
        try:
            
            ink_pump2 = serial.Serial("COM5", 9600)
            print("ink pump2 connect")

        except Exception as e:
            print(e)

        '''
    def ink_manual_move(self, command):
        state = open("state.txt","w")
        state.write(command)
        state.close()

            

    def set_current_position(self,step_gap):
        state = open("state.txt","w")
        state.write("C"+str(step_gap))
        state.close()
        self.linear_wait()
        time.sleep(3)

    def syringe_init(self):
        global dT,ACN,Oxidizer,Deblock

        print("Syringe init")
        '''
        ACN.write(b'init;')
        Oxidizer.write(b'init;')
        Deblock.write(b'init;')
        '''
        try:
            
            state = open("state.txt","w")
            state.write("Syringe_Oxidation_init")
            
            state.close()
            
            self.linear_wait()
            print('oxidizer init')
            Oxidizer.write(b'/1ZR\r\n')
            self.syringe_wait(Oxidizer)
            

        except Exception as E:
            print(E)

        try:
            
            state = open("state.txt","w")
            state.write("Syringe_dT_init")
            state.close()
            self.linear_wait()
            print('dT init')
            dT.write(b'/1ZR\r\n')
            self.syringe_wait(dT)


        except Exception as E:
            print(E)

        try:
            state = open("state.txt","w")
            state.write("Syringe_ACN_init")
            state.close()
            self.linear_wait()
            print('ACN init')
            ACN.write(b'/1ZR\r\n')
            self.syringe_wait(ACN)
        except Exception as E:
            print(E)

            

            
        try:
            
            state = open("state.txt","w")
            state.write("Syringe_Deblock_init")
            state.close()
            self.linear_wait()
            print('deblock init')
            Deblock.write(b'/1ZR\r\n')
            self.syringe_wait(Deblock)
        except Exception as E:
            print(E)
            
            '''
            Deblock.write(b'/1V1000I5A3000R\r\n')
            self.syringe_wait(Deblock)
            Deblock.write(b'/1I6A0R\r\n')
            self.syringe_wait(Deblock)
            '''

            

        except Exception as e:
            print(e)

    
    def syringe_flush(self):
        ACN.write(b'/1V6000I3A6000R\r\n')

        self.linear_wait()
        self.syringe_wait(ACN)
        ACN.write(b'/1V1000I6A0R\r\n')
        self.syringe_wait(ACN)

        ACN.write(b'/1V6000I3A6000R\r\n')

        self.linear_wait()
        self.syringe_wait(ACN)
        ACN.write(b'/1V1000I6A0R\r\n')
        self.syringe_wait(ACN)

        ACN.write(b'/1V6000I3A6000R\r\n')

        self.linear_wait()
        self.syringe_wait(ACN)
        ACN.write(b'/1V1000I6A0R\r\n')
        self.syringe_wait(ACN)

        Oxidizer.write(b'/1V3000I4A6000R\r\n')
        
        self.linear_wait()
        self.syringe_wait(Oxidizer)

        Oxidizer.write(b'/1V500I7A0R\r\n')
        self.syringe_wait(Oxidizer)
        Oxidizer.write(b'/1V3000I4A6000R\r\n')
        
        self.linear_wait()
        self.syringe_wait(Oxidizer)

        Oxidizer.write(b'/1V500I7A0R\r\n')
        self.syringe_wait(Oxidizer)
        Oxidizer.write(b'/1V3000I4A6000R\r\n')
        
        self.linear_wait()
        self.syringe_wait(Oxidizer)

        Oxidizer.write(b'/1V500I7A0R\r\n')
        self.syringe_wait(Oxidizer)

                   
        Deblock.write(b'/1V3000I3A6000R\r\n')

        self.linear_wait()

        self.syringe_wait(Deblock)
            
        Deblock.write(b'/1V500I6A0R\r\n')
        self.syringe_wait(Deblock)
        Deblock.write(b'/1V3000I3A6000R\r\n')

        self.linear_wait()

        self.syringe_wait(Deblock)
            
        Deblock.write(b'/1V500I6A0R\r\n')
        self.syringe_wait(Deblock)
        Deblock.write(b'/1V3000I3A6000R\r\n')

        self.linear_wait()

        self.syringe_wait(Deblock)
            
        Deblock.write(b'/1V500I6A0R\r\n')
        self.syringe_wait(Deblock)
        

    def line(self,img):
        # 이진화
        ret, img=cv2.threshold(img, 100, 255, cv2.THRESH_BINARY_INV)

        # 에지 검출
        edges = cv2.Canny(img, 50, 50)

        # 직선 성분 검출
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180., 110, minLineLength=300, maxLineGap=600)

        if lines is not None:

            x1 = int(lines[0][0][0])
            y1 = int(lines[0][0][1])  # 시작점 좌표 x,y
            x2 = int(lines[0][0][2])
            y2 = int(lines[0][0][3])  # 끝점 좌표, 가운데는 무조건 0

            if (x2 != x1):
                angle = (y2 - y1) / (x2 - x1)
                if angle != 0:
                    x = x1 - y1 / angle
                else:
                    x = x1

            else:
                x = x1

            return x, x1, y1, x2, y2


        else:
            return -1 ,-1, -1, -1, -1





        
    def printing_both(self,cycle,print_num):
        threading.Thread(target=self.check_point,args = (cycle-1,"coupling",)).start()

        
        
        
        state = open("state.txt", "w")
        state.write("Print"+'C'+str(cycle)+'P'+str(print_num))
        state.close()
        self.linear_wait()

    

    def flush(self, mode):
        state = open("state.txt", "w")
        state.write(mode)
        state.close()

    def pre_wet(self, cycle):

        threading.Thread(target=self.check_point,args = (cycle, "pre wet",)).start()
        print("액티베이터로 미리적셔")
        #global ACN_used
        #ACN_used += volume
        state = open("state.txt","w")
        state.write("Bulk_dT")
        state.close()
        
        
        retraction = 150
        
        ##############충전##############       

        self.syringe_wait(dT)
        dT.write(b'/1I5R\r\n')
        self.syringe_wait(dT)
        #dT.write(b'/1V4000I5A1300R\r\n')
        #self.syringe_wait(dT)
        dT.write(b'/1I6R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V4000I6A2150R\r\n')#2330#113차 2000이었
        self.syringe_wait(dT)
        ################################
        

        ##########밸브 포트 설정##########
        self.syringe_wait(dT)
        dT.write(b'/1I7R\r\n')
        ##################################

        ###############분사###############
        self.linear_wait() # linear가 분사위치에 도착할 때까지 기달
        start = time.time() 
        

            
        self.syringe_wait(dT)
        dT.write(b'/1I7V1500A0R\r\n')
        ###################################
            

        #다시 살짝 빨아들임
        self.syringe_wait(dT)
        dT.write(b'/1V300I7A'+str(int(retraction)).encode()+b'R\r\n')
        time.sleep(5)
        self.blow(1, 1, 1)
        self.blow(1, 1, 1)
        
        end = time.time()

        

    def printing_Test(self,cycle):
        threading.Thread(target=self.check_point,args = (cycle,"coupling",)).start()
        self.x_init()

        state = open("state.txt", "w")
        state.write("Print")
        state.close()
        time.sleep(18)


        
        



    def x_init(self):
        print("x_init")
        state = open("state.txt","w")
        state.write("x_init")
        state.close()
        self.linear_wait()

    
    def moving(self,distance):
        if distance == "x_init":
            print("이니시에이션")
            self.x_init()
        else:
            state = open("state.txt", "w")
            state.write("x_move"+str(distance))
            state.close()


    
    def wait(self,n):
        time.sleep(n)
        

    
    def blow(self,valve_open_time, incubation, cycle):
        threading.Thread(target=self.check_point,args = (cycle, "blow",)).start()
        
        state = open("state.txt","w")
        state.write("Blow")
        state.close()
        self.linear_wait()

        

    def Sblow(self,valve_open_time, incubation, cycle):
        threading.Thread(target=self.check_point,args = (cycle, "Sblow",)).start()
        state = open("state.txt","w")
        state.write("SBlow")
        state.close()
        print("Sblow")
        self.linear_wait()
        

        
        




    ######bulk soultion syringe 사용하여 control######

    def Bulk_dT(self, cycle):
        threading.Thread(target=self.check_point,args = (cycle, "dT",)).start()
   
        #global ACN_used
        #ACN_used += volume
        state = open("state.txt","w")
        state.write("Bulk_dT")
        state.close()
        self.linear_wait()
        
        retraction = 150
        
        ##############충전##############       

        self.syringe_wait(dT)
        dT.write(b'/1V3000I3A50R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I4A100R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I3A150R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I4A200R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I3A250R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I4A300R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I3A350R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I4A400R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I3A450R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I4A500R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I3A550R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I4A600R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I2A3000R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I1A2000R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I1A3000R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I1A2000R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I1A3000R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I1A2000R\r\n')
        self.syringe_wait(dT)
        dT.write(b'/1V3000I2A3000R\r\n')
        self.syringe_wait(dT)
        ################################
        

        ##########밸브 포트 설정##########
        self.syringe_wait(dT)
        dT.write(b'/1I1R\r\n')
        ##################################

        ###############분사###############
        self.linear_wait() # linear가 분사위치에 도착할 때까지 기달
        start = time.time() 
        

            
        self.syringe_wait(dT)
        dT.write(b'/1I1V1000A0R\r\n')
        self.syringe_wait(dT)

        ###################################
            

        end = time.time()



    def waste(self):
        state = open("state.txt","w")
        state.write("Waste")
        state.close()
        self.linear_wait()
        

    
    def wash(self, volume, incubation, cycle):
        threading.Thread(target=self.check_point,args = (cycle, "wash",)).start()
        state = open("state.txt","w")
        state.write("Wash")
        state.close()
        self.linear_wait()
        if incubation < 2:
            time.sleep(2)
        else:
            self.wait(incubation)

    def oxidation(self, volume, incubation, cycle):
        threading.Thread(target=self.check_point,args = (cycle, "oxidation",)).start()
        state = open("state.txt","w")
        state.write("Oxidation")
        state.close()
        self.linear_wait()
        if incubation < 2:
            time.sleep(2)
        else:
            self.wait(incubation)


    def detritylation(self, volume, incubation, cycle):
        threading.Thread(target=self.check_point,args = (cycle, "detritylation",)).start()
        state = open("state.txt","w")
        state.write("Detritylation")
        state.close()
        self.linear_wait()
        if incubation < 2:
            time.sleep(2)
        else:
            self.wait(incubation)
    
    def wash_no_use(self, volume,incubation, cycle):
        threading.Thread(target=self.check_point,args = (cycle, "wash",)).start()

        #global ACN_used
        #ACN_used += volume
        
        

        retraction = 0

        ##############충전##############       
        step = int(volume*600) + retraction

        #최대 6000 step
        if step > 6000:
            step = 6000

        self.syringe_wait(ACN)
        ACN.write(b'/1I2R\r\n')
        self.syringe_wait(ACN)
        ACN.write(b'/1V4000I2A'+str(step).encode()+b'R\r\n') ###### 7월 29일. 4를 5로 바꾸세요
        ################################

        state = open("state.txt","w")
        state.write("Wash")
        state.close()
        
        #wash는 항상 1000
        speed = 1000
        
        time.sleep(1.5)
        ##########밸브 포트 설정##########
        self.syringe_wait(ACN)
        ACN.write(b'/1I6R\r\n')
        
        ##################################

        ###############분사###############
        self.linear_wait() # linear가 분사위치에 도착할 때까지 기달
        self.syringe_wait(ACN)

        ACN.write(b'/1V2000I6A0R\r\n')

        '''
        ACN.write(b'/1V500I6A800R\r\n')
        self.syringe_wait(ACN)
        self.waste(6000, 10)

        
        ACN.write(b'/1V500I6A0R\r\n')

        '''
        
        #다시 살짝 빨아들임
        self.syringe_wait(ACN)
        ACN.write(b'/1V500I6A'+str(int(retraction)).encode()+b'R\r\n')
        

        #self.waste(6000, 10)
        #self.waste(6000, 10)
        #self.waste(6000, 10)

        try:
            self.wait(1)
            pass
        except:
            pass


    
    def oxidation_no_use(self, volume,incubation, cycle):
        threading.Thread(target=self.check_point,args = (cycle, "oxidation",)).start()

        #global oxidation_used
        #oxidation_used += volume
        
        state = open("state.txt","w")
        state.write("Oxidation")
        state.close()

        retraction = 600


        
        for i in range(0,5):
            ##############충전##############       
            step = int(volume*600) + retraction

            #최대 6000 step
            if step > 6000:
                step = 3000

            step = 3000
            self.syringe_wait(Oxidizer)
            Oxidizer.write(b'/1I1R\r\n')
            self.syringe_wait(Oxidizer)
            Oxidizer.write(b'/1V3000I1A'+str(3000).encode()+b'R\r\n') ###### 7월 29일. 5를 6으로 바꾸세요
            ################################


            #incubation 시간에 맞게 속도 조절. 너무 빠르면 안되니 최대 속도는 1000
            speed = int(step/incubation)*2
            if speed > 1000:
                speed = 1000

            

            ##########밸브 포트 설정##########
            self.syringe_wait(Oxidizer)
            Oxidizer.write(b'/1I3R\r\n')
            ##################################


            ###############분사###############
            self.linear_wait() # linear가 분사위치에 도착할 때까지 기달
            start = time.time()
            
            #1000 step은 일단 빠르게 뿌림
            if step >= 1000:



                self.syringe_wait(Oxidizer)
                Oxidizer.write(b'/1I3V1000A0R\r\n')
                


            else:
                
                self.syringe_wait(Oxidizer)
                Oxidizer.write(b'/1I3V1000A0R\r\n')

            ###################################

            #self.waste(1000, 4)
            
            
            #state = open("state.txt","w")
            #state.write("Oxidation_move")
            #state.close()

        

        #다시 살짝 빨아들임
        self.syringe_wait(Oxidizer)
        Oxidizer.write(b'/1V1000I3A'+str(int(retraction)).encode()+b'R\r\n')

        
        end = time.time()
        try:
            self.wait(incubation-(end-start))
        except:
            pass

        #self.waste(6000, 10)

        


    def detritylation_no_use(self, volume,incubation, cycle):
        threading.Thread(target=self.check_point, args = (cycle, "detritylation",)).start()
        
        #global deblock_used
        #deblock_used += volume
        
        state = open("state.txt","w")
        state.write("Detritylation")
        state.close()

        retraction = 300

        
        ##############충전##############       
        step = int(volume*600) + retraction

        #최대 6000 step
        if step > 6000:
                
            step = 3000


        self.syringe_wait(Deblock)
        Deblock.write(b'/1I3R\r\n')
        self.syringe_wait(Deblock)
        Deblock.write(b'/1V5000I3A'+str(6000).encode()+b'R\r\n')
        self.wait(1)
        ################################


        #incubation 시간에 맞게 속도 조절. 너무 빠르면 안되니 최대 속도는 1000
        speed = int(step/incubation*2.5)
        if speed > 1000:
            speed = 1000

        time.sleep(1)
        ##########밸브 포트 설정##########
        self.syringe_wait(Deblock)
        Deblock.write(b'/1I4R\r\n')
        ##################################

        ###############분사###############
        self.linear_wait() # linear가 분사위치에 도착할 때까지 기달
        start = time.time()

        Deblock.write(b'/1I7V100A0R\r\n')
        '''
        self.syringe_wait(ACN)
        ACN.write(b'/1I4V1000A600R\r\n')

        self.syringe_wait(ACN)        
        self.waste(500, 5)
        ACN.write(b'/1I4V1000A300R\r\n')
        self.syringe_wait(ACN)        
        self.waste(500, 10)

        ACN.write(b'/1I4V1000A0R\r\n')
        self.syringe_wait(ACN)
        '''
        
        #다시 살짝 빨아들임
        self.syringe_wait(Deblock)
        Deblock.write(b'/1V1000I7A'+str(int(600)).encode()+b'R\r\n')
        self.syringe_wait(Deblock)
        Deblock.write(b'/1I3R\r\n')
       

        
        end = time.time()
        try:
            self.wait(incubation-(end-start))
        except:
            pass
        #self.Sblow(0,0)
        #self.linear_wait()
        #self.moving(2500)
        #self.linear_wait()
        #self.waste(6000, 10)


    ###################################################

    def syringe_wait(self, syringe):

        msg = syringe.readline()
        while (msg.find(b'`') == -1):

            syringe.write(b'/1Q\r\n')
            time.sleep(0.1)
            msg = syringe.readline()

    
    def linear_wait(self):

        while(1):
            self.wait(0.01)
            state = open("state.txt","r")
            if state.readline() == "Done":
                break
            state.close()

    
            
    def load_sequence(self,path):
        file_sequence = open(path,'r')
        _5to3_lines = file_sequence.readlines()
        _3to5_lines = _5to3_lines[1][::-1]
        return _3to5_lines
        
    
    def load_protocol(self,path):
        is_error = 0
        file_protocol = open(path,'r')
        lines = file_protocol.readlines()
        list_protocol = []
        for line in lines:
            step = line.split('\t')
            list_protocol.append(step)
            
        step_num = 0
        for step in list_protocol:
            step_num += 1
            if step[0] != 'oxidation':
                if step[0] != 'coupling':
                
                    if step[0] != 'wash':
                         if step[0] != 'blow':
                             if step[0] != 'detritylation':
                                  is_error = 1
                                  print("LOAD ERROR 1")
        
            try:
                int(step[1])
                
            except:
                is_error = 2
                print("LOAD ERROR 2")
    
            try:
                int(step[2])
                
            except:
                is_error = 3
                print("LOAD ERROR 3")
                
        return list_protocol,is_error
    
    
    
    def save_protocol(self,path,list_protocol):
        print(path)
        print(list_protocol)
        file_protocol = open(path+'.protocol','w')
    
        for step in list_protocol:
            for i in step:
                file_protocol.write(str(i)+'\t')
            file_protocol.write('\n')
    
        file_protocol.close()

    
    
    def check_point(self,cycle, step):
        global progress_step 
        progress_step = step
        print(time.strftime('%y-%m-%d\t%H:%M:%S',time.localtime(time.time())) +'\t'+ str(cycle+1) +"\t"+step)
        try:
            synthesis_log_txt = open(synthesis_log_path+'.txt','a')
            synthesis_log_txt.write(time.strftime('%y-%m-%d\t%H:%M:%S',time.localtime(time.time()))+"\t"+str(cycle+1)+'\t'+step+"\n")

            try:
                winsound.PlaySound(sound_path+'\\'+step+'.wav',winsound.SND_ALIAS)

            except Exception as e:
                print('e ', e)
                print("sound error")
                synthesis_log+txt.write("ERROR: sound error\n")
        except Exception as e:
            print('e ', e)
            print("log error")

    def get_humidity(self):
        state = open("state.txt","r")
        humidity = state.read()
        state.close()

        return humidity
        

