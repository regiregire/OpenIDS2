#include <Wire.h>
#include <AccelStepper.h>
#include <MultiStepper.h>


///////pin map////////
int Act_enable = 0;
int dA_enable = 1;
int dT_enable = 2;
int dG_enable = 3;
int dC_enable = 4;
int Act_pulse = 5;
int dA_pulse = 6;
int dT_pulse = 7;
int dG_pulse = 8;
int dC_pulse = 9;
int Direction = 10;

int Act_sensor = A0;
int dA_sensor = A1;
int dT_sensor = A2;
int dG_sensor = A3;
int dC_sensor = 11;
///////pin map////////

String command;
int Speed;
int Distance;

bool Act_flag = false;
bool dA_flag = false;
bool dT_flag = false;
bool dG_flag = false;
bool dC_flag = false;
bool is_ready = true;
int last_run = 0;
int now_time = 0;

AccelStepper Act_motor(AccelStepper::DRIVER, Act_pulse, Direction);
AccelStepper dA_motor(AccelStepper::DRIVER, dA_pulse, Direction);
AccelStepper dT_motor(AccelStepper::DRIVER, dT_pulse, Direction);
AccelStepper dG_motor(AccelStepper::DRIVER, dG_pulse, Direction);
AccelStepper dC_motor(AccelStepper::DRIVER, dC_pulse, Direction);

void setup() {
  Wire.begin(1);
  Wire.onReceive(receiveEvent);
  Wire.onRequest(requestEvent);
  Act_motor.setAcceleration(15000);
  Act_motor.setCurrentPosition(0);
  
  dA_motor.setAcceleration(15000);
  dA_motor.setCurrentPosition(0);
  
  dT_motor.setAcceleration(15000);
  dT_motor.setCurrentPosition(0);
  
  dG_motor.setAcceleration(15000);
  dG_motor.setCurrentPosition(0);

  dC_motor.setAcceleration(15000);
  dC_motor.setCurrentPosition(0);

  for(int i=0; i<11; i++){
    pinMode(i,OUTPUT);
  } 

  pinMode(Act_sensor,INPUT);
  pinMode(dA_sensor,INPUT);
  pinMode(dT_sensor,INPUT);
  pinMode(dG_sensor,INPUT);
  pinMode(dC_sensor,INPUT);
  
  digitalWrite(Act_enable,HIGH);
  digitalWrite(dA_enable,HIGH);
  digitalWrite(dT_enable,HIGH);
  digitalWrite(dG_enable,HIGH);
  digitalWrite(dC_enable,HIGH);
}


void receiveEvent(int bytes) {
  Serial.println("receiving");
  command = "";
  while(Wire.available()){
  char c = Wire.read();
  command += String(c);

  }
}

void requestEvent() { //요청 시 수행 함수
  Wire.write(is_ready);
}

int damper(AccelStepper motor, int sensor){
  motor.setAcceleration(2000);
  motor.setMaxSpeed(500);  
  motor.setCurrentPosition(0); 
  motor.moveTo(-3000); 

  while(analogRead(sensor)>800&&motor.run()){
  }

  motor.setMaxSpeed(100);  
  motor.setCurrentPosition(0); 
  motor.moveTo(3000); 

  while(analogRead(sensor)<800&&motor.run()){
  }
  motor.setCurrentPosition(0);

 
}

AccelStepper MOVE(AccelStepper motor, int Speed, int Distance){
    motor.setMaxSpeed(Speed);
    motor.moveTo(Distance);
    motor.runToPosition();

    return motor;
}


void loop() {
      
    if(command =="act-"){
      is_ready = false;
      Act_flag = true;
      digitalWrite(Act_enable,LOW);
      damper(Act_motor, Act_sensor);
      digitalWrite(Act_enable,HIGH);
      command = "";
      is_ready = true;
    }

    if(command =="act+"){
      Serial.print(command);
      Serial.print("  ");
      Serial.println("act");
      is_ready = false;
      Act_flag = false;
      digitalWrite(Act_enable,LOW);
      Act_motor.setMaxSpeed(3000);
      Act_motor.move(4500);
      Act_motor.runToPosition();
      digitalWrite(Act_enable,HIGH);
      command = "";
      is_ready = true;
    }

    if(command =="A-"){
      is_ready = false;
      dA_flag = true;
      digitalWrite(dA_enable,LOW);
      damper(dA_motor, dA_sensor);
      digitalWrite(dA_enable,HIGH);
      command = "";
      is_ready = true;
    }

    if(command =="A+"){
      is_ready = false;
      dA_flag = false;
      digitalWrite(dA_enable,LOW);
      dA_motor.setCurrentPosition(0);
      MOVE(dA_motor, 3000, 4500);
      digitalWrite(dA_enable,HIGH);
      command = "";
      is_ready = true;
    }


    if(command =="T-"){
      is_ready = false;
      dT_flag = true;
      digitalWrite(dT_enable,LOW);
      damper(dT_motor, dT_sensor);
      digitalWrite(dT_enable,HIGH);
      command = "";
      is_ready = true;
    }
    
    if(command =="T+"){
      is_ready = false;
      dT_flag = false;
      digitalWrite(dT_enable,LOW);
      dT_motor.setMaxSpeed(3000);
      dT_motor.move(4500);
      dT_motor.runToPosition();
      digitalWrite(dT_enable,HIGH);
      command = "";
      is_ready = true;
    }

    
    if(command =="G-"){
      is_ready = false;
      dG_flag = true;
      digitalWrite(dG_enable,LOW);
      damper(dG_motor, dG_sensor);
      digitalWrite(dG_enable,HIGH);
      command = "";
      is_ready = true;
    }

    if(command =="G+"){
      is_ready = false;
      dG_flag = false;
      digitalWrite(dG_enable,LOW);
      dG_motor.setCurrentPosition(0);
      MOVE(dG_motor, 3000, 4500);
      digitalWrite(dG_enable,HIGH);
      command = "";
      is_ready = true;
    }


    if(command =="C-"){
      is_ready = false;
      dC_flag = true;
      digitalWrite(dC_enable,LOW);
      damper(dC_motor, dC_sensor);
      digitalWrite(dC_enable,HIGH);
      command = "";
      is_ready = true;
    }

    if(command =="C+"){
      is_ready = false;
      dC_flag = false;
      digitalWrite(dC_enable,LOW);
      dC_motor.setCurrentPosition(0);
      MOVE(dC_motor, 4000, 6000);
      digitalWrite(dC_enable,HIGH);
      command = "";
      is_ready = true;
    }
    if(command =="ink_stop"){
      is_ready = false;
      Act_flag = false;
      dA_flag = false;
      dG_flag = false;
      dT_flag = false;
      dC_flag = false;
      is_ready = true;
    }

   now_time = millis();
   if(now_time-last_run>3000){
     if (Act_flag==true){
       is_ready = false;
       digitalWrite(Act_enable,LOW);
       damper(Act_motor, Act_sensor);
       digitalWrite(Act_enable,HIGH);
       is_ready = true;
     }
     
     if (dA_flag==true){
       is_ready = false;
       digitalWrite(dA_enable,LOW);
       damper(dA_motor, dA_sensor);
       digitalWrite(dA_enable,HIGH);
       is_ready = true;
     }
  
     if (dT_flag==true){
       is_ready = false;
       digitalWrite(dT_enable,LOW);
       damper(dT_motor, dT_sensor);
       digitalWrite(dT_enable,HIGH);
       is_ready = true;
     }
  
      if (dG_flag==true){
       is_ready = false;
       digitalWrite(dG_enable,LOW);
       damper(dG_motor, dG_sensor);
       digitalWrite(dG_enable,HIGH);
       is_ready = true;
     }

      if (dC_flag==true){
       is_ready = false;
       digitalWrite(dC_enable,LOW);
       damper(dC_motor, dC_sensor);
       digitalWrite(dC_enable,HIGH);
       is_ready = true;
     }

     last_run = millis();
   }
}
