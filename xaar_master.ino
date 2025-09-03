#include <Wire.h>
#include <AccelStepper.h>
#include <TMCStepper.h>
#include <SoftwareSerial.h>
#include <TimerOne.h>

String command;
bool is_init;

// --------- I2C protocol ----------
const uint8_t PH_SLAVE_ADDR[6]      = {0x12, 0x13, 0x14, 0x15, 0x16, 0x17}; //Air pressure, Act, A, T, G, C
const uint8_t CMD_QUEUE_LINE = 0x01;  // 16B 라인 적재
const uint8_t CMD_FIRE_NEXT  = 0x02;  // 큐에서 한 줄 꺼내 분사

const uint8_t STAT_OK        = 0x06;  // 처리 OK
const uint8_t STAT_BUSY      = 0x15;  // 큐 풀/바쁨
const uint8_t STAT_FIRED     = 0xF1;  // 분사 완료(READY까지 끝)

// --------- Pin map ----------
constexpr uint8_t RX = 0;
constexpr uint8_t TX = 1;
constexpr uint8_t limit_L_S = 2;
constexpr uint8_t limit_R_S  = 3;
constexpr uint8_t nano_step  = 4;
constexpr uint8_t auto_step  = 5;
constexpr uint8_t DIR  = 6;
constexpr uint8_t TMC_TX  = 7;
constexpr uint8_t linear_E   = 8;
constexpr uint8_t wash_E   = 9;
constexpr uint8_t OXI_E   = 10;
constexpr uint8_t waste_E   = 11;
constexpr uint8_t DET_E   = 12;
constexpr uint8_t valve   = A0;
constexpr uint8_t PH_VDD   = A1;
//SDA  = A4, SCL  = A5

//--------- stepper ----------

#define bulk_TMC_ADDR 0b00 //(MS2: LOW, MS1: LOW)
#define linear_TMC_ADDR 0b01 //(MS2: GND, MS1: HIGH)
#define R_SENSE 0.11f      // 측정저항 값 (기본 0.11Ω)

SoftwareSerial TMC_serial(TMC_TX,TMC_TX);
TMC2209Stepper bulk_TMCdriver(&TMC_serial, R_SENSE, bulk_TMC_ADDR);
TMC2209Stepper linear_TMCdriver(&TMC_serial, R_SENSE, linear_TMC_ADDR);

AccelStepper bulk_step_motor(AccelStepper::DRIVER, nano_step, DIR);
AccelStepper linear_step_motor(AccelStepper::DRIVER, nano_step, DIR);


volatile bool limit_L_Flag = false;
volatile bool limit_R_Flag = false;

int max_position = 10000;
int limit_1_position = 0;
int limit_2_position = 3000;
int lineIdx = 0;
uint8_t Airpressure_arduino = 0x20;


// ... (기존 setup 및 다른 함수들은 그대로 유지)
void I2C(uint8_t addr, String cmd) { /* 함수 내용 필요 */ }
void I2C_wait() { /* 함수 내용 필요 */ }
// -----------------------------------------


void waste_stepper2_auto_run(){
  digitalWrite(auto_step,HIGH);
  digitalWrite(auto_step,LOW);
}

void limit_L_home() {
  limit_L_Flag = true;
}

void limit_R_home() {
  limit_R_Flag = true;
}

void linear_init(){
  limit_L_Flag = false;
  limit_R_Flag = false;
  
  digitalWrite(linear_E, LOW);
  linear_step_motor.setMaxSpeed(1000);
  linear_step_motor.move(-max_position);

  while(!limit_L_Flag && !limit_R_Flag){
    linear_step_motor.run();
  }
  linear_step_motor.stop();
  while (linear_step_motor.isRunning()) {
    linear_step_motor.run();
  }

  linear_step_motor.move(200);
  linear_step_motor.runToPosition();
  linear_step_motor.setMaxSpeed(100);
  linear_step_motor.move(-1000);
  
  while(!limit_L_Flag && !limit_R_Flag){
    linear_step_motor.run();
  }
  linear_step_motor.stop();
  while (linear_step_motor.isRunning()) {
    linear_step_motor.run();
  }

  if (limit_L_Flag) {
    linear_step_motor.setCurrentPosition(limit_1_position);
  }

  if (limit_R_Flag) {
    linear_step_motor.setCurrentPosition(limit_2_position);
  }
  linear_step_motor.setMaxSpeed(2000);
  digitalWrite(linear_E, HIGH);
}



void setup() {
  for (int i=4; i<16; i++){
    pinMode(i,OUTPUT);  
  }
  
  pinMode(limit_L_S, INPUT_PULLUP);
  pinMode(limit_R_S, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(limit_L_S), limit_L_home, RISING);
  attachInterrupt(digitalPinToInterrupt(limit_R_S), limit_R_home, RISING);
  
  Wire.begin();           // 마스터
  Wire.setClock(400000);    // 400kHz I2C (배선 길면 100k)
  Serial.begin(115200);


  // 스테퍼 파라미터
  bulk_step_motor.setMaxSpeed(1000);      // [steps/s]
  bulk_step_motor.setAcceleration(5000);// [steps/s^2]
  bulk_step_motor.setCurrentPosition(0);

  linear_step_motor.setMaxSpeed(1000);      // [steps/s]
  linear_step_motor.setAcceleration(5000);// [steps/s^2]
  linear_step_motor.setCurrentPosition(0);

  bulk_TMCdriver.begin();                                                                                                                                                                                                                                                                                                                                         // UART: Init SW UART (if selected) with default 115200 baudrate
  bulk_TMCdriver.toff(5);             // Enables driver in software
  //bulk_TMCdriver.pwm_autoscale(true);  // 전류 자동조정
  bulk_TMCdriver.en_spreadCycle(true); // StealthChop 비활성화
  bulk_TMCdriver.microsteps(0);       // Set microsteps
  bulk_TMCdriver.rms_current(3000);  

  linear_TMCdriver.begin();                                                                                                                                                                                                                                                                                                                                         // UART: Init SW UART (if selected) with default 115200 baudrate
  linear_TMCdriver.toff(5);             // Enables driver in software
  linear_TMCdriver.pwm_autoscale(true);  // 전류 자동조정
  linear_TMCdriver.en_spreadCycle(true); // StealthChop 비활성화
  linear_TMCdriver.microsteps(0);       // Set microsteps


  Timer1.initialize(2000);
  Timer1.attachInterrupt(waste_stepper2_auto_run);

  digitalWrite(linear_E, HIGH);
  digitalWrite(wash_E, HIGH);
  digitalWrite(waste_E, HIGH);
  digitalWrite(DET_E, HIGH);
  digitalWrite(OXI_E, HIGH);


}


// 16바이트(=128bit) 라인 하나 전송 (슬레이브 주소를 인자로 받도록 수정)
bool sendLine16(uint8_t slave_addr, const uint8_t* payload16) {
  Wire.beginTransmission(slave_addr);
  Wire.write(CMD_QUEUE_LINE);
  Wire.write(payload16, 16);
  uint8_t err = Wire.endTransmission();   // 0=성공(버스 에러 없음)
  if (err != 0) {
    Serial.print("ERR:I2C_TX_FAIL,ADDR:0x");
    Serial.println(slave_addr, HEX);
    return false;
  }

  // 상태 1바이트 읽기(슬레이브 onRequest에서 직전 결과 제공)
  Wire.requestFrom(slave_addr, (uint8_t)1);
  if (Wire.available()) {
    uint8_t st = Wire.read();
    if (st == STAT_OK) {
      return true;
    } else {
      // 슬레이브가 바쁜 경우 로그 출력
      Serial.print("ERR:SLAVE_BUSY,ADDR:0x");
      Serial.println(slave_addr, HEX);
      return false;
    }
  }
  Serial.print("ERR:I2C_RX_FAIL,ADDR:0x");
  Serial.println(slave_addr, HEX);
  return false;
}

// ... (fireAndWait, printing 함수 등은 그대로 유지)
// FIRE 요청 후 "분사 완료"를 기다림 (타임아웃 포함)
bool fireAndWait(uint8_t slave_addr) {
  // 명령 전송
  Wire.beginTransmission(slave_addr);
  Wire.write(CMD_FIRE_NEXT);
  if (Wire.endTransmission() != 0) return false;

  // 폴링로 "분사 완료" 확인
  uint32_t t0 = millis();
  while (millis() - t0 < 100) {
    delayMicroseconds(200);                 // 슬레이브 처리시간 소량 양보
    Wire.requestFrom(slave_addr, (uint8_t)1);
    if (Wire.available()) {
      uint8_t st = Wire.read();
      if (st == STAT_FIRED) return true;  // READY까지 끝난 상태로 가정
      if (st == STAT_BUSY)  ;               // 필요 시 재시도 정책
    }
  }
  return false; // 타임아웃
}

void printing(uint8_t slave_addr, const uint8_t* line){

  // 1) 라인 전송(큐에 적재)
  if (!sendLine16(slave_addr, line)) {
    // 큐가 가득/BUSY면 잠깐 쉰 뒤 재시도
    delayMicroseconds(200);
    return;
  }

  // 2) FIRE 요청 & 완료 대기
  if (!fireAndWait(slave_addr)) {
    Serial.println(F("FIRE timeout or error"));
    return;
  }

  // 3) 분사 완료 → 100스텝 이동
  linear_step_motor.runToNewPosition(100);

  lineIdx++;
}

// Hex 문자(0-F)를 4비트 값으로 변환하는 유틸리티 함수
byte hexCharToNibble(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return 0;
}

void loop() {
  if(Serial.available()){
    command = Serial.readStringUntil(';');
  }


  // --- 'line' 명령어 처리 로직 추가 ---
  if (command.startsWith("line,")) {
    // 형식: "line,주소,16바이트hex데이터"
    // 예: "line,19,0102...3132" (19는 0x13의 10진수)
    
    int firstComma = command.indexOf(',');
    int secondComma = command.indexOf(',', firstComma + 1);

    if (firstComma > 0 && secondComma > firstComma) {
      String addrStr = command.substring(firstComma + 1, secondComma);
      uint8_t slaveAddress = (uint8_t)addrStr.toInt();

      String hexDataStr = command.substring(secondComma + 1);
      uint8_t payload[16];

      if (hexDataStr.length() == 32) { // 16바이트 = 32개 hex 문자
        for (int i = 0; i < 16; i++) {
          char hi = hexDataStr.charAt(i * 2);
          char lo = hexDataStr.charAt(i * 2 + 1);
          payload[i] = (hexCharToNibble(hi) << 4) | hexCharToNibble(lo);
        }

        if (sendLine16(slaveAddress, payload)) {
          Serial.println("OK"); // 성공 응답
        } else {
          Serial.println("FAIL"); // 실패 응답
        }
      } else {
        Serial.println("ERR:Invalid hex length");
      }
    } else {
      Serial.println("ERR:Invalid line format");
    }
    
    command = ""; // 명령어 처리 후 초기화
    return; // 다른 명령어와 중복 실행 방지
  }
  
  // ... (기존의 다른 if/else if 명령어 처리 로직)
  if (command == "x_init"){
    // x_init();
    }

 if (command == "blow"){
    digitalWrite(linear_E,LOW);
    linear_step_motor.setMaxSpeed(2000);
    linear_step_motor.moveTo(3720);
    linear_step_motor.runToPosition();

    linear_TMCdriver.microsteps(4);       // Set microsteps

    digitalWrite(valve,HIGH);
    digitalWrite(waste_E,LOW);
    bulk_step_motor.setMaxSpeed(1000);
    bulk_step_motor.runToNewPosition(5000);
    
    digitalWrite(valve,LOW);
    digitalWrite(waste_E,HIGH);
    digitalWrite(linear_E,HIGH);
    linear_TMCdriver.microsteps(0);       // Set microsteps
  }

  if (command.startsWith("bulk_") == 1){
    String temp_cmd = command.substring(5);
    int retraction = 1600;
    int lastUnderscoreIndex = temp_cmd.lastIndexOf('_');
    String step_name = temp_cmd.substring(0, lastUnderscoreIndex);
    int volume = temp_cmd.substring(lastUnderscoreIndex + 1).toInt();

    digitalWrite(linear_E,LOW);
    linear_step_motor.setMaxSpeed(2000);
    linear_step_motor.runToNewPosition(3740);
    digitalWrite(linear_E,HIGH);

    digitalWrite(wash_E, HIGH);
    digitalWrite(OXI_E, HIGH);
    digitalWrite(DET_E, HIGH);
    digitalWrite(linear_E,HIGH);
    digitalWrite(waste_E,HIGH);
    
    if (step_name == "wash") digitalWrite(wash_E,LOW);
    if (step_name == "oxidation") digitalWrite(OXI_E,LOW);
    if (step_name == "detritylation") digitalWrite(DET_E,LOW);
    if (step_name == "linear") digitalWrite(linear_E,LOW);
    digitalWrite(waste_E,LOW);
    bulk_step_motor.setMaxSpeed(600);
    bulk_step_motor.runToNewPosition(retraction+volume);
    digitalWrite(waste_E,HIGH);
    bulk_step_motor.runToNewPosition(-retraction);
    digitalWrite(wash_E, HIGH);
    digitalWrite(OXI_E, HIGH);
    digitalWrite(DET_E, HIGH);
    digitalWrite(linear_E,HIGH);
  }
  
    


  else if(command =="waste"){//waste만 빨아들이기
      digitalWrite(waste_E,LOW);
      bulk_step_motor.setCurrentPosition(0);
      bulk_step_motor.moveTo(3000);
      bulk_step_motor.runToPosition();
      digitalWrite(waste_E,HIGH);
  }
    
  else if(command.startsWith("ink") == 1){
    command = command.substring(3);
    I2C(Airpressure_arduino, command);
    I2C_wait();
  }

  else if(command =="is_ready"){
      Serial.print("ready");
  }

  else if (command == "WHOAMI"){
    Serial.print("openIDS");
  }

  if (command != "") {
    command = "";
  }
}
