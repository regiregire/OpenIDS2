import serial
import os
import time
import threading
import cv2
import numpy as np


ink_pump1,ink_pump2, dT,xp,ACN,Oxidizer,Deblock,arduino,linear,amidite_T = None,None,None,None,None,None,None,None,None,None
command = None
try:
    synthesis_log_path = os.getcwd() + '\\x64\\Release\\synthesis_log\\' +time.strftime("%y_%m_%d_%H시%M")
    synthesis_log_txt = open(synthesis_log_path+'.txt','w')

    
except Exception as E:
    print(E)



class System():
    def connection(self):
        try:
            dT = serial.Serial("COM6", 9600, write_timeout=1, timeout=0.1)
            print("dT connect")


        except Exception as e:
            print(e)
            connection_Fluidics[3] = False

    def ink_manual_move(self, command):
        state = open("state.txt","w")
        state.write(command)
        state.close()


    def printing_both(self,cycle,print_num):
        threading.Thread(target=self.check_point,args = (cycle-1,"coupling",)).start()

        
        
        
        state = open("state.txt", "w")
        state.write("Print"+'C'+str(cycle)+'P'+str(print_num))
        state.close()
        self.linear_wait()


    def x_init(self):
        print("x_init")
        state = open("state.txt","w")
        state.write("x_init")
        state.close()
        self.linear_wait()

    
    def moving(self,distance):
        if distance == "x_init":
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

    def waste(self):
        state = open("state.txt","w")
        state.write("Waste")
        state.close()
        self.linear_wait()
    
    def linear_wait(self):

        while(1):
            self.wait(0.01)
            state = open("state.txt","r")
            if state.readline() == "Done":
                break
            state.close()

    
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

        except Exception as e:
            print('e ', e)
            print("log error")
