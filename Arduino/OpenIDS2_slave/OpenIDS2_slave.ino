#include <SPI.h>
#include <Wire.h>

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

// !!! IMPORTANT: Set a unique address for each slave board !!!
// Act = 0x13, A = 0x14, T = 0x15, G = 0x16, C = 0x17.
const uint8_t I2C_ADDR = 0x17 ;

// --- I2C Command Definitions ---
const byte CMD_RESET_LOW   = 0x00;
const byte CMD_RESET_HIGH  = 0x01;
const byte CMD_POWER_UP    = 0x02;
const byte CMD_POWER_DOWN  = 0x03;

// Buffer to hold data received via I2C
volatile byte i2c_receive_buffer[20];
volatile int i2c_data_len = 0;
volatile bool i2c_data_received = false;
volatile int8_t received_command = -1; // -1 means no command received

// Flag to indicate that a job is done and the slave is ready to signal
volatile bool isJobDone = false;


char serial_buffer[150]; // Buffer to hold serial data
bool serial_data_ready = false;

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Wire.begin(I2C_ADDR);
  Wire.onReceive(onReceiveISR);
  Wire.onRequest(onRequestISR);

  pinMode(nSS1, OUTPUT);
  pinMode(nSS2, OUTPUT);
  digitalWrite(nSS1, HIGH);
  digitalWrite(nSS2, HIGH);
  SPI.begin();

  pinMode(Ready, INPUT_PULLUP);
  pinMode(VPPH, OUTPUT);
  pinMode(VPPL, OUTPUT);
  pinMode(Fault, INPUT_PULLUP);
  pinMode(Fire, OUTPUT);
  pinMode(Reset, OUTPUT);
  pinMode(CLK, OUTPUT);

  digitalWrite(Reset, HIGH);  // Default state for nRESET is HIGH
  digitalWrite(Fire, HIGH);   // Default state for Fire is HIGH
  
  // Set up a 1MHz square wave for Xaar state machine CLK.
  TCCR1A = _BV(COM1A0);              // toggle OC1A on compare match
  OCR1A = 7;                         // top value for counter
  TCCR1B = _BV(WGM12) | _BV(CS10);   // CTC mode, prescaler clock/1
}

void loop() {
  readSerialData();
  if (serial_data_ready) {
    test(serial_buffer);
    serial_data_ready = false; // Reset flag after processing
  }
  
  // --- Process single-byte commands from I2C ---
  if (received_command != -1) {
    switch(received_command) {
      case CMD_RESET_LOW:   reset_low();    break;
      case CMD_RESET_HIGH:  reset_high();   break;
      case CMD_POWER_UP:    power_up();     break;
      case CMD_POWER_DOWN:  power_down();   break;
    }
    isJobDone = true;
    received_command = -1;
  }

  // --- Process multi-byte printhead data from I2C ---
  if (i2c_data_received) {
    if (i2c_data_len == 17) {
      int injectionAmount = i2c_receive_buffer[0];
      byte local_data_bytes[16];
      memcpy(local_data_bytes, (const void*)(i2c_receive_buffer + 1), 16);
      
      Serial.println("\n--- I2C Data Processing ---");
      Serial.print("  Parsed Amount: ");
      Serial.println(injectionAmount);

      sendSPIData(local_data_bytes);
      fire(injectionAmount);
    } else {
      Serial.print("  Error: Invalid data format received. Expected 17 bytes, got ");
      Serial.println(i2c_data_len);
    }
    
    isJobDone = true; 
    i2c_data_received = false;
    Serial.println("--------------------------");
  }
}

/**
 * @brief I2C receive ISR.
 */
void onReceiveISR(int len) {
  if (len == 1) {
    if (Wire.available()) {
      received_command = Wire.read();
    }
  } else if (len > 1) {
    i2c_data_len = len;
    int i = 0;
    while (Wire.available() && i < 20) {
      i2c_receive_buffer[i] = Wire.read();
      i++;
    }
    i2c_data_received = true;
  }
}

/**
 * @brief I2C request ISR.
 */
void onRequestISR() {
  if (isJobDone) {
    Wire.write("Ready");
    isJobDone = false;
    Serial.println("  --> Sent 'Ready' signal to master.");
  }
}

void sendSPIData(byte* data_bytes) {
  SPI.beginTransaction(SPISettings(250000, MSBFIRST, SPI_MODE0));

  digitalWrite(nSS1, LOW);
  delayMicroseconds(50);
  for (int i = 0; i < 8; i++) {
    SPI.transfer(data_bytes[i]);
  }
  digitalWrite(nSS1, HIGH);

  delayMicroseconds(50);
  
  digitalWrite(nSS2, LOW);
  delayMicroseconds(50);
  for (int i = 8; i < 16; i++) {
    SPI.transfer(data_bytes[i]);
  }
  digitalWrite(nSS2, HIGH);
  SPI.endTransaction();

  Serial.println("  --> SPI data sent to printhead.");

  Serial.print("  Sent (Binary): ");
  for (int i = 0; i < 16; i++) {
    for (int j = 7; j >= 0; j--) {
      Serial.print(bitRead(data_bytes[i], j));
    }
  }
  Serial.println();

  Serial.println("  SPI Job done. Waiting for fire command to complete.");
}


void fire(int injectionAmount) {
  // --- Start of Fire Diagnostics ---


  digitalWrite(Fire, LOW);

  long delay_ms = 10 * injectionAmount;

  delay(delay_ms);
  digitalWrite(Fire, HIGH);

  delayMicroseconds(50); 

}

void reset_low() {
  digitalWrite(Reset, LOW);
  Serial.println("--> Command: reset_low() executed.");
  delay(2);
}

void reset_high() {
  digitalWrite(Reset, HIGH);
  Serial.println("--> Command: reset_high() executed.");
  delay(2);
}

void power_up() {
  digitalWrite(VPPH, HIGH);
  delayMicroseconds(500);
  digitalWrite(VPPL, HIGH);
  Serial.println("--> Command: power_up() executed.");
  delay(2);
}

void power_down() {
  digitalWrite(VPPL, LOW);
  delayMicroseconds(500);
  digitalWrite(VPPH, LOW);
  Serial.println("--> Command: power_down() executed.");
  delay(2);
}


void readSerialData() {
  static byte buffer_index = 0;
  while (Serial.available() > 0) {
    char incoming_char = Serial.read();

    if (incoming_char == '\n' || incoming_char == '\r') {
      if (buffer_index > 0) { // If we have received some data
        serial_buffer[buffer_index] = '\0'; // Null-terminate the string
        serial_data_ready = true;
        buffer_index = 0; // Reset for next message
      }
    } else {
      if (buffer_index < (sizeof(serial_buffer) - 1)) {
        serial_buffer[buffer_index++] = incoming_char;
      }
    }
  }
}

void test(char* serial_input) {
  Serial.println("\n--- Serial Test Mode ---");
  Serial.print("Received: ");
  Serial.println(serial_input);
  reset_low();

  Serial.println("  [ACTION] Powering up printhead for test...");

  power_up();
  Serial.println("  [ACTION] Toggling reset pin for test...");

  reset_high();
  Serial.println("  [INFO] Printhead setup for test complete.");


  char* underscore_ptr = strchr(serial_input, '_');
  if (underscore_ptr == NULL) {
    Serial.println("  Error: Invalid test format. Use 'amount_binary_data'.");
    return;
  }
  
  *underscore_ptr = '\0';
  char* amount_str = serial_input;
  char* data_str = underscore_ptr + 1;

  int injectionAmount = atoi(amount_str);

  if (strlen(data_str) != 128) {
    Serial.print("  Error: Binary data must be 128 characters long, but got ");
    Serial.println(strlen(data_str));
    return;
  }

  byte data_bytes[16];
  for (int i = 0; i < 16; i++) {
    byte current_byte = 0;
    for (int j = 0; j < 8; j++) {
      current_byte <<= 1;
      if (data_str[i * 8 + j] == '1') {
        current_byte |= 1;
      }
    }
    data_bytes[i] = current_byte;
  }
  
  Serial.print("  Parsed Amount: ");
  Serial.println(injectionAmount);
  
  sendSPIData(data_bytes);
  fire(injectionAmount);
  

  power_down(); 
  
  Serial.println("--- End of Test ---");
  reset_low();
}
