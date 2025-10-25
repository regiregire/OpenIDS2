#include <Wire.h>
#include <AccelStepper.h>

// --- 튜닝 가능한 상수들 ---
const long ACCELERATION = 1000;         // 모터 가속도
const long DAMPER_MAX_SPEED = 200;       // 감압 시 모터 속도
const long FORWARD_MAX_SPEED = 3000;     // 증압 시 모터 속도
const long DAMPER_MOVE_DISTANCE = 3000;  // 초기 감압 시 이동 거리
const long FORWARD_MOVE_DISTANCE = 4500; // 최초 증압 시 이동 거리

// *** 핵심 튜닝 값 ***
// 압력 조절을 위해 한 번에 움직일 스텝 거리 (이 값을 조절하여 민감도 튜닝)
const long CORRECTION_STEP = 1000;

const int MAX_COMMAND_LENGTH = 10;       // I2C로 받을 최대 명령어 길이

// --- 모터 및 핀 설정 ---
enum MotorIndex {
  MOTOR_ACT = 0,
  MOTOR_DA = 1,
  MOTOR_DT = 2,
  MOTOR_DG = 3,
  MOTOR_DC = 4,
  MOTOR_COUNT = 5 // 전체 모터 개수
};
const int enablePins[MOTOR_COUNT] = {0, 1, 2, 3, 4};
const int pulsePins[MOTOR_COUNT] = {5, 6, 7, 8, 9};
const int sensorPins[MOTOR_COUNT] = {A0, A1, A2, A3, 11};
const int DIRECTION_PIN = 10;

// AccelStepper 객체 배열
AccelStepper motors[MOTOR_COUNT] = {
  AccelStepper(AccelStepper::DRIVER, pulsePins[MOTOR_ACT], DIRECTION_PIN),
  AccelStepper(AccelStepper::DRIVER, pulsePins[MOTOR_DA], DIRECTION_PIN),
  AccelStepper(AccelStepper::DRIVER, pulsePins[MOTOR_DT], DIRECTION_PIN),
  AccelStepper(AccelStepper::DRIVER, pulsePins[MOTOR_DG], DIRECTION_PIN),
  AccelStepper(AccelStepper::DRIVER, pulsePins[MOTOR_DC], DIRECTION_PIN)
};

// --- 전역 변수 ---
char command[MAX_COMMAND_LENGTH];
volatile bool newCommandReceived = false;
bool damper_flags[MOTOR_COUNT] = {false};
bool is_ready = true;

// --- 기본 설정 함수 ---
void setup() {
  Wire.begin(0x12); // I2C 슬레이브 주소 0x12로 초기화
  Wire.onReceive(receiveEvent);
  Wire.onRequest(requestEvent);

  for (int i = 0; i < MOTOR_COUNT; i++) {
    pinMode(enablePins[i], OUTPUT);
    pinMode(pulsePins[i], OUTPUT);
    pinMode(sensorPins[i], INPUT);
    digitalWrite(enablePins[i], HIGH); // 모터 드라이버 비활성화로 시작
    
    motors[i].setAcceleration(ACCELERATION);
    motors[i].setCurrentPosition(0);
  }
  pinMode(DIRECTION_PIN, OUTPUT);
}

// --- I2C 이벤트 핸들러 ---
void receiveEvent(int bytes) {
  int i = 0;
  while (Wire.available() && i < MAX_COMMAND_LENGTH - 1) {
    command[i++] = Wire.read();
  }
  command[i] = '\0';
  newCommandReceived = true;
}

void requestEvent() {
  Wire.write(is_ready);
}

// --- 모터 제어 함수 ---

// 초기 압력 설정을 위한 함수
void runDamper(int motorIndex) {
  
  digitalWrite(enablePins[motorIndex], LOW);
  AccelStepper &motor = motors[motorIndex];
  int sensorPin = sensorPins[motorIndex];
  motor.setCurrentPosition(0);
  motor.setAcceleration(ACCELERATION);
  motor.setMaxSpeed(DAMPER_MAX_SPEED);

  // 센서가 HIGH(과압)이면 LOW가 될 때까지 역회전
  if (digitalRead(sensorPin)) {
    motor.moveTo(-DAMPER_MOVE_DISTANCE);
    while (digitalRead(sensorPin) && motor.run()) {}
  }
  
  motor.stop(); // 혹시 모를 움직임 정지
  motor.setCurrentPosition(0);

  // 센서가 LOW(압력 부족)이면 HIGH가 될 때까지 정회전
  if (!digitalRead(sensorPin)) {
    motor.moveTo(DAMPER_MOVE_DISTANCE);
    while (!digitalRead(sensorPin) && motor.run()) {}
  }
  
  motor.setCurrentPosition(0);
  digitalWrite(enablePins[motorIndex], HIGH);
}

// 일반 전진 함수 (압력 유지와 무관)
void moveForward(int motorIndex) {
  digitalWrite(enablePins[motorIndex], LOW);
  AccelStepper &motor = motors[motorIndex];
  motor.setMaxSpeed(FORWARD_MAX_SPEED);
  motor.move(FORWARD_MOVE_DISTANCE);
  motor.runToPosition();
  digitalWrite(enablePins[motorIndex], HIGH);
}

// --- 명령어 처리 ---
void handleCommand() {
  is_ready = false;
  if (command[0] != '_') {
    is_ready = true;
    command[0] = '\0';
    return;
  }
  
  char* cmd_body = command + 1;
  if (strcmp(cmd_body, "stop") == 0) {
    for (int i = 0; i < MOTOR_COUNT; i++) {
      damper_flags[i] = false;
    }
    is_ready = true;
    command[0] = '\0'; 
    return;
  }

  int motorIndex = -1;
  char action = 0;

  if (strncmp(cmd_body, "act", 3) == 0) motorIndex = MOTOR_ACT, action = cmd_body[3];
  else if (strncmp(cmd_body, "A", 1) == 0) motorIndex = MOTOR_DA, action = cmd_body[1];
  else if (strncmp(cmd_body, "T", 1) == 0) motorIndex = MOTOR_DT, action = cmd_body[1];
  else if (strncmp(cmd_body, "G", 1) == 0) motorIndex = MOTOR_DG, action = cmd_body[1];
  else if (strncmp(cmd_body, "C", 1) == 0) motorIndex = MOTOR_DC, action = cmd_body[1];

  if (motorIndex != -1) {
    if (action == '+') {
      damper_flags[motorIndex] = false;
      moveForward(motorIndex);
    } else if (action == '-') {
      runDamper(motorIndex); // 압력유지 모드 시작 시 최초 압력 설정
      damper_flags[motorIndex] = true;
    }
  }

  command[0] = '\0';
  is_ready = true;
}


// +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
// +++ 아래부터가 핵심 수정 부분입니다. +++
// +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

/**
 * @brief 압력이 낮을 때, 센서 상태가 HIGH로 바뀔 때까지 압력을 높이는 함수
 * @param motorIndex 타겟 모터 인덱스
 */
void correctPressureUntilFlip(int motorIndex) {
  is_ready = false;
  digitalWrite(enablePins[motorIndex], LOW);
  AccelStepper &motor = motors[motorIndex];
  
  // 보정 시에는 너무 빠르지 않은 속도로 설정
  motor.setAcceleration(ACCELERATION);
  motor.setMaxSpeed(DAMPER_MAX_SPEED);

  // 센서가 LOW인 동안 계속 1스텝씩 전진
  motor.move(CORRECTION_STEP);
  while (digitalRead(sensorPins[motorIndex]) == LOW && motor.run()) {
  }
  motor.setCurrentPosition(0);
  digitalWrite(enablePins[motorIndex], HIGH);
  is_ready = true;
}

/**
 * @brief 압력이 높을 때, 센서 상태가 LOW로 바뀔 때까지 압력을 낮추는 함수
 * @param motorIndex 타겟 모터 인덱스
 */
void releasePressureUntilFlip(int motorIndex) {
  is_ready = false;
  digitalWrite(enablePins[motorIndex], LOW);
  AccelStepper &motor = motors[motorIndex];

  motor.setAcceleration(ACCELERATION);
  motor.setMaxSpeed(DAMPER_MAX_SPEED);

  // 센서가 HIGH인 동안 계속 1스텝씩 후진
  motor.move(-CORRECTION_STEP);
  while (digitalRead(sensorPins[motorIndex]) == HIGH && motor.run()) {
  }
  motor.setCurrentPosition(0);
  digitalWrite(enablePins[motorIndex], HIGH);
  is_ready = true;
}


// --- 메인 루프 ---
void loop() {
  // 1. I2C로부터 새 명령 수신 시 처리
  if (newCommandReceived) {
    newCommandReceived = false;
    handleCommand();
  }

  // 2. [수정된] 실시간 압력 감지 및 미세 조정
  for (int i = 0; i < MOTOR_COUNT; i++) {
    // 해당 모터가 압력 유지 모드일 때만 실행
    if (damper_flags[i] == true) {
      int sensorState = digitalRead(sensorPins[i]);

      // 센서가 LOW (압력 부족) -> 정상 압력이 될 때까지 '계속' 높임
      if (sensorState == LOW) {
        correctPressureUntilFlip(i);
        delay(500); //★★ 안정화를 위한 대기 시간 (진동 방지) ★★
      } 
      // 센서가 HIGH (압력 과잉) -> 정상 압력이 될 때까지 '계속' 낮춤
      else if (sensorState == HIGH) {
        releasePressureUntilFlip(i);
        delay(500); //★★ 안정화를 위한 대기 시간 (진동 방지) ★★
      }
    }
  }
}
