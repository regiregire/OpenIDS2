#include <Wire.h>
#include <AccelStepper.h>
#include <TMCStepper.h>
#include <SoftwareSerial.h>
#include <TimerOne.h>

String command;
bool is_init;
#define limit1 A1
#define limit2 A0

#define limit_1_position 0
#define limit_2_position 3200
#define max_position 10000
#define Airpressure_arduino 1
#define OXI_pulse 2
#define wash_pulse 3
#define DET_pulse 4
#define linear_pulse 5
#define waste_pulse 6
#define DIR 7
#define OXI_E 8
#define wash_E 9
#define DET_E 10
#define linear_E 11
#define waste_E 12
#define valve 13
#define waste_TX 14   // Arduino TX → TMC2209 RX
#define waste_RX 15   // Arduino RX → TMC2209 TX
#define linear_TX 16     // Arduino TX → TMC2209 RX
#define linear_RX 17   // Arduino RX → TMC2209 TX
#define bulk_TX 18   // Arduino TX → TMC2209 RX
#define bulk_RX 19   // Arduino RX → TMC2209 TX

#define R_SENSE 0.11f      // 측정저항 값 (기본 0.11Ω)
int accel = 10000;
int TMCmaxSpeed = 4000;
#define TMC2209_ADDR 0b00  // 기본 주소 (A1, A2 핀 둘 다 GND일 경우)

SoftwareSerial bulk_TMCSerial(bulk_RX, bulk_TX);
SoftwareSerial linear_TMCSerial(linear_RX, linear_TX);
SoftwareSerial waste_TMCSerial(waste_RX, waste_TX);

TMC2209Stepper bulk_TMCdriver(&bulk_TMCSerial, R_SENSE, TMC2209_ADDR);
TMC2209Stepper linear_TMCdriver(&linear_TMCSerial, R_SENSE, TMC2209_ADDR);
TMC2209Stepper waste_TMCdriver(&waste_TMCSerial, R_SENSE, TMC2209_ADDR);

AccelStepper OXI_stepper(AccelStepper::DRIVER, OXI_pulse, DIR);
AccelStepper wash_stepper(AccelStepper::DRIVER, wash_pulse, DIR);
AccelStepper DET_stepper(AccelStepper::DRIVER, DET_pulse, DIR);
AccelStepper linear_stepper(AccelStepper::DRIVER, linear_pulse, DIR);
AccelStepper waste_stepper1(AccelStepper::DRIVER, waste_pulse, DIR);
AccelStepper waste_stepper2(AccelStepper::DRIVER, 22, DIR);


void waste_stepper2_run(){
  //waste_stepper2.runSpeed();
  digitalWrite(22,HIGH);
  digitalWrite(22,LOW);

}


void x_init(){

  digitalWrite(linear_E, LOW);
  linear_stepper.setCurrentPosition(0);
  linear_stepper.setMaxSpeed(1000);
  linear_stepper.moveTo(-max_position);

  while(analogRead(limit1)<800&&analogRead(limit2)<800){
    linear_stepper.run();
  }
  linear_stepper.setCurrentPosition(0);
  linear_stepper.moveTo(100);
  linear_stepper.runToPosition();
  linear_stepper.setMaxSpeed(100);
  linear_stepper.moveTo(-1000);
  while(analogRead(limit1)<800&&analogRead(limit2)<800){ 
    linear_stepper.run();
  }

  if (analogRead(limit1)>800){
    linear_stepper.setCurrentPosition(limit_1_position);

  }

  if (analogRead(limit2)>800){
    linear_stepper.setCurrentPosition(limit_2_position);

  }
  linear_stepper.setMaxSpeed(2000);
  digitalWrite(linear_E, HIGH);
  is_init = true;

}


void setup() {
  
  for (int i=2; i<25; i++){
    pinMode(i,OUTPUT);  
  }
  
  OXI_stepper.setAcceleration(15000);
  wash_stepper.setAcceleration(15000);
  DET_stepper.setAcceleration(15000);
  linear_stepper.setAcceleration(15000);
  waste_stepper1.setAcceleration(15000);
  waste_stepper2.setAcceleration(15000);

  OXI_stepper.setMaxSpeed(1000);
  wash_stepper.setMaxSpeed(1000);
  DET_stepper.setMaxSpeed(1000);
  linear_stepper.setMaxSpeed(4000);
  waste_stepper1.setMaxSpeed(1000);
  waste_stepper2.setMaxSpeed(4000);
  waste_stepper2.setSpeed(1000);

  Wire.begin(1);
  Serial.begin(9600);
  bulk_TMCSerial.begin(115200);
  linear_TMCSerial.begin(115200);
  waste_TMCSerial.begin(115200);

  bulk_TMCdriver.begin();                                                                                                                                                                                                                                                                                                                            // UART: Init SW UART (if selected) with default 115200 baudrate
  bulk_TMCdriver.toff(5);                 // Enables driver in software
  //bulk_TMCdriver.pwm_autoscale(true);  // 전류 자동조정
  bulk_TMCdriver.en_spreadCycle(true); // StealthChop 비활성화
  bulk_TMCdriver.microsteps(0);         // Set microsteps

  linear_TMCdriver.begin();                                                                                                                                                                                                                                                                                                                            // UART: Init SW UART (if selected) with default 115200 baudrate
  linear_TMCdriver.toff(5);                 // Enables driver in software
  //linear_TMCdriver.pwm_autoscale(true);  // 전류 자동조정
  linear_TMCdriver.en_spreadCycle(true); // StealthChop 비활성화
  linear_TMCdriver.microsteps(0);         // Set microsteps

  waste_TMCdriver.begin();                                                                                                                                                                                                                                                                                                                            // UART: Init SW UART (if selected) with default 115200 baudrate
  waste_TMCdriver.toff(5);                 // Enables driver in software
  //waste_TMCdriver.pwm_autoscale(true);  // 전류 자동조정
  waste_TMCdriver.en_spreadCycle(true); // StealthChop 비활성화
  waste_TMCdriver.microsteps(0);         // Set microsteps
  
Serial.println(bulk_TMCdriver.microsteps());  // 확인용

  bulk_TMCdriver.rms_current(3000);  
  
  linear_TMCdriver.rms_current(2000);  
  
  waste_TMCdriver.rms_current(3000);  
  delay(100);  // 살짝 시간 주기
  //TMCdriver.pwm_autoscale(true);     // Needed for stealthChop

  Timer1.initialize(2000);
  Timer1.attachInterrupt(waste_stepper2_run);

  digitalWrite(linear_E, HIGH);
  digitalWrite(wash_E, HIGH);
  digitalWrite(waste_E, HIGH);
  digitalWrite(DET_E, HIGH);
  digitalWrite(OXI_E, HIGH);

   
}

void loop() {

  /*
  linear_stepper.setCurrentPosition(0);
  linear_stepper.moveTo(-1000);  // 200스텝 이동
  linear_stepper.runToPosition();
  delay(1000);
  linear_stepper.setCurrentPosition(0);
  linear_stepper.moveTo(1000);  // 200스텝 이동
  linear_stepper.runToPosition();
  delay(1000);
  */

 if(Serial.available()){

    command = Serial.readStringUntil(';');

    if (command == "x_init"){
    x_init();
    Serial.print("done");
    }

    
    if (command == "4"){
      digitalWrite(linear_E,LOW);
      linear_stepper.setMaxSpeed(2000);
      linear_stepper.moveTo(3720);
      linear_stepper.runToPosition();
      digitalWrite(linear_E,HIGH);


      digitalWrite(valve,HIGH);
      digitalWrite(waste_E,LOW);
      waste_stepper1.setMaxSpeed(1000);
      waste_stepper1.move(25000);
      waste_stepper1.runToPosition();
      


      digitalWrite(linear_E,LOW);
      linear_stepper.setMaxSpeed(2000);
      linear_stepper.moveTo(3600);
      linear_stepper.runToPosition();
      digitalWrite(linear_E,HIGH);

      waste_stepper1.move(25000);
      waste_stepper1.runToPosition();
      
      digitalWrite(valve,LOW);
      digitalWrite(waste_E,HIGH);
      Serial.print("done");
    }

    if (command == "6"){
      digitalWrite(linear_E,LOW);
      linear_stepper.setMaxSpeed(2000);
      linear_stepper.moveTo(3740);
      linear_stepper.runToPosition();
      digitalWrite(linear_E,HIGH);

      digitalWrite(DET_E,LOW);
      digitalWrite(waste_E,LOW);
      DET_stepper.setCurrentPosition(0);
      DET_stepper.setMaxSpeed(600);
      DET_stepper.moveTo(600);
      DET_stepper.runToPosition();

      
      for (int i=0; i<4; i++){
      
        DET_stepper.setCurrentPosition(0);
        DET_stepper.setMaxSpeed(600);
        DET_stepper.moveTo(300);
        DET_stepper.runToPosition();
  
        waste_stepper1.setCurrentPosition(0);
        waste_stepper1.moveTo(2000);
        waste_stepper1.runToPosition();
      }
      
      DET_stepper.setCurrentPosition(0);
      DET_stepper.setMaxSpeed(600);
      DET_stepper.moveTo(200);
      DET_stepper.runToPosition();

      DET_stepper.setCurrentPosition(0);
      DET_stepper.setMaxSpeed(1000);
      DET_stepper.moveTo(-600);
      DET_stepper.runToPosition();

      digitalWrite(DET_E,HIGH);
      digitalWrite(waste_E,HIGH);
      Serial.print("done");
    }

    if (command == "8"){
      digitalWrite(linear_E,LOW);
      linear_stepper.setMaxSpeed(2000);
      linear_stepper.moveTo(3740);
      linear_stepper.runToPosition();
      digitalWrite(linear_E,HIGH);

      digitalWrite(wash_E,LOW);
      digitalWrite(waste_E,LOW);
      wash_stepper.setCurrentPosition(0);
      wash_stepper.setMaxSpeed(600);
      wash_stepper.moveTo(1000);
      wash_stepper.runToPosition();

      
      for (int i=0; i<10; i++){
      
      wash_stepper.setCurrentPosition(0);
      wash_stepper.setMaxSpeed(600);
      wash_stepper.moveTo(300);
      wash_stepper.runToPosition();
 
      waste_stepper1.setCurrentPosition(0);
      waste_stepper1.moveTo(2000);
      waste_stepper1.runToPosition();
      }
      waste_stepper1.setCurrentPosition(0);
      waste_stepper1.moveTo(2000);
      waste_stepper1.runToPosition();
      wash_stepper.setCurrentPosition(0);
      wash_stepper.setMaxSpeed(400);
      wash_stepper.moveTo(-1000);
      wash_stepper.runToPosition();
      
      digitalWrite(wash_E,HIGH);
      digitalWrite(waste_E,HIGH);
      Serial.print("done");
    }

    if (command == "12"){
      digitalWrite(linear_E,LOW);
      linear_stepper.setMaxSpeed(2000);
      linear_stepper.moveTo(3740);
      linear_stepper.runToPosition();
      digitalWrite(linear_E,HIGH);

      digitalWrite(OXI_E,LOW);
      digitalWrite(waste_E,LOW);
      OXI_stepper.setCurrentPosition(0);
      OXI_stepper.setMaxSpeed(600);
      OXI_stepper.moveTo(800);
      OXI_stepper.runToPosition();

      
      for (int i=0; i<4; i++){
      
      OXI_stepper.setCurrentPosition(0);
      OXI_stepper.setMaxSpeed(600);
      OXI_stepper.moveTo(200);
      OXI_stepper.runToPosition();

      waste_stepper1.setCurrentPosition(0);
      waste_stepper1.moveTo(2000);
      waste_stepper1.runToPosition();
      }
      
      OXI_stepper.setCurrentPosition(0);
      OXI_stepper.setMaxSpeed(600);
      OXI_stepper.moveTo(200);
      OXI_stepper.runToPosition();

      OXI_stepper.setCurrentPosition(0);
      OXI_stepper.setMaxSpeed(400);
      OXI_stepper.moveTo(-800);
      OXI_stepper.runToPosition();

      digitalWrite(OXI_E,HIGH);
      digitalWrite(waste_E,HIGH);
      Serial.print("done");
    }


  else if(command =="waste"){//waste만 빨아들이기
      digitalWrite(waste_E,LOW);
      waste_stepper1.setCurrentPosition(0);
      waste_stepper1.moveTo(3000);
      waste_stepper1.runToPosition();
      digitalWrite(waste_E,HIGH);
      Serial.print("done");
  }
    
  else if(command == "act+"){
    I2C(Airpressure_arduino, command);
    I2C_wait();
    Serial.print("done");
  }

  else if(command == "act-"){
    I2C(Airpressure_arduino, command);
    I2C_wait();
    Serial.print("done");
  }


  else if(command == "A+"){
    I2C(Airpressure_arduino, command);
    I2C_wait();
    Serial.print("done");
  }

  else if(command == "A-"){
    I2C(Airpressure_arduino, command);
    I2C_wait();
    Serial.print("done");
  }

  else if(command == "T+"){
    I2C(Airpressure_arduino, command);
    I2C_wait();
    Serial.print("done");
  }

  else if(command == "T-"){
    I2C(Airpressure_arduino, command);
    I2C_wait();
    Serial.print("done");
  }

  else if(command == "G+"){
    I2C(Airpressure_arduino, command);
    I2C_wait();
    Serial.print("done");
  }

  else if(command == "G-"){
    I2C(Airpressure_arduino, command);
    I2C_wait();
    Serial.print("done");
  }

  else if(command == "C+"){
    I2C(Airpressure_arduino, command);
    I2C_wait();
    Serial.print("done");
  }

  else if(command == "C-"){
    I2C(Airpressure_arduino, command);
    I2C_wait();
    Serial.print("done");
  }
  else if(command == "ink_x"){
    I2C(Airpressure_arduino, command);
    I2C_wait();
    Serial.print("done");
  }

  else if(command.indexOf("x_move") == 0){
    digitalWrite(linear_E, LOW);
    command = command.substring(6);

    linear_stepper.setMaxSpeed(2000);
    linear_stepper.moveTo(command.toInt());
    linear_stepper.runToPosition(); 

    digitalWrite(linear_E, HIGH);
    Serial.print("done");
      
  }

  else if(command.indexOf("p_move") == 0){
    digitalWrite(linear_E, LOW);
    command = command.substring(6);

    linear_stepper.setMaxSpeed(2000);
    linear_stepper.moveTo(command.toInt());
    linear_stepper.runToPosition(); 

    digitalWrite(linear_E, HIGH);
    Serial.print("done");
      
  }
  else if(command == "P"){
    digitalWrite(linear_E,LOW);
    linear_stepper.setMaxSpeed(500);
    linear_stepper.moveTo(0);
    linear_stepper.runToPosition(); 
    digitalWrite(linear_E,HIGH);
    
    Serial.print("done");
  }
 
  }
}
void I2C(int arduino, String command){
  char data[100]; 
  Wire.beginTransmission(1);  // n번 슬레이브와 통신 시작
  command.toCharArray(data, command.length()+1);
  Wire.write(data); // data 전송
  Wire.endTransmission(); // 전송 종료
}



bool I2C_receive(int arduino, int byte_length){
  Wire.requestFrom(arduino, byte_length); //n번 슬레이브에 byte_length길이 데이터 요청

  while (Wire.available()) { //보내온 데이터가 있을 시 데이터 읽기
    int c = Wire.read(); 
    return c;      
  }  

}


void I2C_wait(){
  delay(500);
  while(!I2C_receive(Airpressure_arduino, 1)){
    delay(100);
  }
}
