#include <SPI.h>
#include <Wire.h>
String command;

// !!! 중요: 이 주소를 각 슬레이브 보드마다 다르게 설정하고 업로드해야 합니다. !!!
// ACT: 0x13, A: 0x14, T: 0x15, G: 0x16, C: 0x17
const uint8_t I2C_ADDR = 0x13; 

// ... (기존 핀 정의)
#define Ready A0
#define nSS2 A1
#define VPPH A2
#define VPPL A3
#define SDA A4
#define SCL A5
#define Fault 4
#define Fire 5
#define Reset 7
#define CLK 9
#define nSS1 10
#define MOSI 11
#define MISO 12
#define SCK 13

// I2C 상태 코드
const uint8_t STAT_OK   = 0x06;
const uint8_t STAT_BUSY = 0x15;

volatile uint8_t ackByte = STAT_OK; // onRequest에서 돌려줄 상태 바이트

// 2라인 큐
volatile uint8_t q[2][16];
volatile uint8_t q_head = 0, q_tail = 0, q_count = 0;

void setup() {
  Wire.begin(I2C_ADDR);
  Wire.onReceive(onReceiveISR);
  Wire.onRequest(onRequestISR);
  Serial.begin(9600); // 디버깅용 시리얼 통신 시작
  while(!Serial);
  Serial.print("Slave Addr: 0x");
  Serial.println(I2C_ADDR, HEX);
    
  // ... (기존 pinMode 및 SPI, Timer 설정)
}

void loop() {
  // 슬레이브는 주로 인터럽트로 동작하므로 loop는 비워둘 수 있습니다.
  // 또는 큐에 데이터가 있을 때 처리하는 로직을 여기에 넣을 수 있습니다.

  if(Serial.available()){
    command = Serial.readStringUntil(';');
  }

} 

// I2C 데이터 수신 인터럽트
void onReceiveISR(int len) {
  if (len < 1) return;
  uint8_t cmd = Wire.read();

  // CMD_QUEUE_LINE (0x01) 이고, 데이터 길이가 16바이트일 때
  if (cmd == 0x01 && len >= 17) {
    if (q_count < 2) { // 큐에 공간이 있으면
      for (uint8_t i=0; i<16; ++i) {
        q[q_head][i] = Wire.read();
      }
      q_head = (q_head + 1) % 2; 
      q_count++;
      ackByte = STAT_OK; // 성공 상태로 변경
      
      // --- 확인용 로그 출력 ---
      Serial.print("Line received. Queue count: ");
      Serial.println(q_count);

    } else { // 큐가 가득 찼으면
      ackByte = STAT_BUSY; // 바쁨 상태로 변경
      Serial.println("Queue full!");
    }
  } else {
    // 잘못된 명령어 또는 데이터 길이
    ackByte = STAT_BUSY;
  }
  
  // 남은 바이트 비우기
  while (Wire.available()) {
    Wire.read();
  }
}

// I2C 데이터 요청 인터럽트
void onRequestISR() {
  Wire.write(ackByte); // 마스터에게 현재 상태 전송
}
