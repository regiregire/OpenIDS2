#include <Wire.h>
#include <AccelStepper.h>
#include <TMCStepper.h>
#include <SoftwareSerial.h>
#include <TimerOne.h>

// --- Pin map ---
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

#define bulk_TMC_ADDR 0b00
#define linear_TMC_ADDR 0b01
#define R_SENSE 0.11f

// --- Object Declaration ---
SoftwareSerial TMC_serial(TMC_TX,TMC_TX);
TMC2209Stepper bulk_TMCdriver(&TMC_serial, R_SENSE, bulk_TMC_ADDR);
TMC2209Stepper linear_TMCdriver(&TMC_serial, R_SENSE, linear_TMC_ADDR);

AccelStepper bulk_step_motor(AccelStepper::DRIVER, nano_step, DIR);
AccelStepper linear_step_motor(AccelStepper::DRIVER, nano_step, DIR);
AccelStepper waste_step_motor(AccelStepper::DRIVER, nano_step, DIR);

// --- Global Variables ---
volatile bool limit_L_Flag = false;
volatile bool limit_R_Flag = false;
volatile bool is_init = false;
int max_position = 10000;
int limit_1_position = 0;
int limit_2_position = 3200;
uint8_t Airpressure_arduino = 0x12;

// --- I2C Slave Related ---
uint8_t allSlaveAddresses[] = {0x13, 0x14, 0x15, 0x16, 0x17};
uint8_t activeSlaveAddresses[5];
int activeSlaveCount = 0;

// --- I2C Command Codes ---
const byte CMD_RESET_LOW   = 0x00;
const byte CMD_RESET_HIGH  = 0x01;
const byte CMD_POWER_UP    = 0x02;
const byte CMD_POWER_DOWN  = 0x03;



// Enum defining the states of the FSM (Finite State Machine)
enum MachineState {
  IDLE,                 // Waiting for a new command
  START_MOTOR_MOVE,   // 'head_' command received, start motor movement
  WAITING_FOR_MOTOR,  // Motor is moving to the target position
  SEND_DATA_TO_SLAVE, // Motor arrived, send data to slave
  WAITING_FOR_SLAVE,  // Waiting for 'Ready' response from slave
  HANDLE_OTHER_CMD    // Handle other blocking commands (not 'head_')
};

MachineState currentState = IDLE; // Current state of the machine

// Struct to store parameters of the 'head_' command currently being processed
struct HeadCommand {
  long motorPosition;
  uint8_t headAddress;
  int injectionAmount;
  char data[129]; // 128-bit data + NULL terminator
};

HeadCommand currentCommand; // Information of the command currently being executed
unsigned long state_enter_time; // Time when the current state was entered (for timeout management)

// Buffer for serial communication (replaces String object)
#define CMD_BUFFER_SIZE 150
char serial_cmd_buffer[CMD_BUFFER_SIZE];


void setup() {
  Serial.begin(115200);
  Wire.begin();
  // Set I2C communication speed to fast mode (400kHz) to reduce communication time
  Wire.setClock(400000L);

  // I2C slave scan
  for (uint8_t addr : allSlaveAddresses) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      if (activeSlaveCount < 5) {
        activeSlaveAddresses[activeSlaveCount++] = addr;
      }
    }
  }

  // Pin mode and interrupt settings
  pinMode(limit_L_S, INPUT_PULLUP);
  pinMode(limit_R_S, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(limit_L_S), [](){ limit_L_Flag = true; }, RISING);
  attachInterrupt(digitalPinToInterrupt(limit_R_S), [](){ limit_R_Flag = true; }, RISING);
  
  for(int i=4; i<16; i++) pinMode(i,OUTPUT);
  pinMode(limit_L_S,INPUT);
  pinMode(limit_R_S,INPUT);

  digitalWrite(wash_E, HIGH);
  digitalWrite(OXI_E, HIGH);
  digitalWrite(DET_E, HIGH);
  digitalWrite(linear_E,HIGH);
  digitalWrite(waste_E,HIGH);

  // Motor settings
  linear_step_motor.setMaxSpeed(2000);
  linear_step_motor.setAcceleration(15000);
  bulk_step_motor.setMaxSpeed(500);
  bulk_step_motor.setAcceleration(5000);
  waste_step_motor.setMaxSpeed(2000);
  waste_step_motor.setAcceleration(15000);
  
  // TMC driver settings
  TMC_serial.begin(115200);
  linear_TMCdriver.begin();
  linear_TMCdriver.toff(5);
  linear_TMCdriver.en_spreadCycle(true);
  linear_TMCdriver.microsteps(0);
  linear_TMCdriver.rms_current(2000);
  bulk_TMCdriver.begin();
  bulk_TMCdriver.toff(5);
  bulk_TMCdriver.en_spreadCycle(true);
  bulk_TMCdriver.microsteps(0);
  bulk_TMCdriver.rms_current(2000);

  Timer1.initialize(2000);
  Timer1.attachInterrupt(waste_auto);
}

void loop() {
  // 1. Always check for new commands from the serial port (start of pipelining)
  //    Can receive the next command regardless of the current state (even while the motor is moving).
  if (currentState == IDLE && Serial.available() > 0) {
    int bytesRead = Serial.readBytesUntil(';', serial_cmd_buffer, CMD_BUFFER_SIZE - 1);
    serial_cmd_buffer[bytesRead] = '\0'; // Null-terminate the string

    // If the received command starts with 'head_', start the asynchronous state machine
    if (strncmp(serial_cmd_buffer, "head_", 5) == 0) {
      currentState = START_MOTOR_MOVE;
    }  
    // Other commands are processed immediately (blocking method)
    else {
      currentState = HANDLE_OTHER_CMD;
    }
  }

  // 2. Perform appropriate actions according to the current state
  switch (currentState) {
    case IDLE:
      // Nothing to do. Waiting for a new command.
      break;

    case START_MOTOR_MOVE:
      // Parse 'head_' command and start motor movement
      if (parseAndSetupHeadCommand(serial_cmd_buffer)) {
        digitalWrite(linear_E, LOW);
        linear_step_motor.moveTo(currentCommand.motorPosition);
        
        state_enter_time = millis();
        currentState = WAITING_FOR_MOTOR;
      } else {
        // If parsing fails, send an error message and return to IDLE state
        Serial.print("ERROR: Invalid head command format;");
        currentState = IDLE;
      }
      break;

    case WAITING_FOR_MOTOR:
      // Keep calling run() until the motor reaches the target position (non-blocking)
      linear_step_motor.run();

      // Check motor movement completion
      if (linear_step_motor.distanceToGo() == 0) {
        currentState = SEND_DATA_TO_SLAVE;
      }
      
      // Check motor movement timeout
      if (millis() - state_enter_time > 10000) { // 10-second timeout
        Serial.print("ERROR: Motor movement timed out;");
        linear_step_motor.stop();
        digitalWrite(linear_E, HIGH);
        currentState = IDLE;
      }
      break;

    case SEND_DATA_TO_SLAVE:
      // Send injection data to slave
      sendDataToSlave(currentCommand.headAddress, currentCommand.injectionAmount, currentCommand.data);
      state_enter_time = millis();
      currentState = WAITING_FOR_SLAVE;
      break;

    case WAITING_FOR_SLAVE:
      {
        bool isReady = false;
        char responseBuffer[6]; // "Ready" + NULL
        
        Wire.requestFrom(currentCommand.headAddress, (uint8_t)5);
        if (Wire.available() >= 5) {
          Wire.readBytes(responseBuffer, 5);
          responseBuffer[5] = '\0';
          if (strcmp(responseBuffer, "Ready") == 0) {
            isReady = true;
          }
        }

        if (isReady) {
          Serial.print("K;");
          currentState = IDLE; // All tasks completed, return to waiting state
        }

        if (millis() - state_enter_time > 15000) {  
          Serial.print("ERROR: Slave not ready in time;");
          currentState = IDLE;
        }
      }
      break;

    case HANDLE_OTHER_CMD:
      // Handle commands other than 'head_'
      handleBlockingCommands(serial_cmd_buffer);
      currentState = IDLE; // Return to IDLE state immediately after processing
      break;
  }
}

/**
 * @brief Parses the 'head_' command string and stores it in the currentCommand struct.
 * @param cmd The entire command string starting with 'head_'
 * @return true if parsing is successful, false otherwise
 */
bool parseAndSetupHeadCommand(char* cmd) {
  // Skip the "head_" part and set the pointer
  char* params = cmd + 5;

  char* pos_str = strtok(params, "_");
  char* addr_str = strtok(NULL, "_");
  char* amount_str = strtok(NULL, "_");
  char* data_str = strtok(NULL, "_");

  // Parameter validation
  if (!pos_str || !addr_str || !amount_str || !data_str || strlen(data_str) != 128) {
    return false;
  }

  currentCommand.motorPosition = atol(pos_str);
  currentCommand.headAddress = strtol(addr_str, NULL, 16);
  currentCommand.injectionAmount = atoi(amount_str);
  strcpy(currentCommand.data, data_str);

  // Motor position validation (optional)
  if (currentCommand.motorPosition < 0 || currentCommand.motorPosition > max_position) {
    return false;
  }
  
  return true;
}

/**
 * @brief Handles blocking commands other than 'head_'.
 * @param cmd The entire command string with the semicolon removed
 */
void handleBlockingCommands(char* cmd) {
  if (strcmp(cmd, "ph_power_up") == 0) {
    power_up_sequence();
  }  
  else if (strcmp(cmd, "ph_power_down") == 0) {
    power_down_sequence();
  }  
  else if (strcmp(cmd, "linear_init") == 0) {
    linear_init();
    is_init = true;
  }  
  else if (strcmp(cmd, "blow") == 0) {
    digitalWrite(linear_E,LOW);
    if(!is_init){
    linear_init();
    }
    linear_step_motor.setMaxSpeed(2000);
    linear_step_motor.moveTo(3900);
    linear_step_motor.runToPosition();
    linear_TMCdriver.microsteps(16);
    digitalWrite(valve,HIGH);
    digitalWrite(waste_E,LOW);
    linear_step_motor.setMaxSpeed(1000);
    int sweap_distance = 2000*4;
    linear_step_motor.move(-sweap_distance);
    linear_step_motor.runToPosition();
    linear_step_motor.setCurrentPosition(3900-sweap_distance/16);
    digitalWrite(valve,LOW);
    digitalWrite(waste_E,HIGH);
    digitalWrite(linear_E,HIGH);
    linear_TMCdriver.microsteps(0);
  }  
  else if (strncmp(cmd, "bulk_", 5) == 0) { //1000 steps = 1.4ml
    if(!is_init){
        linear_init();
      }
    // Handle strings using C functions instead of String objects
    char* body = cmd + 5;
    char* last_underscore = strrchr(body, '_');
    if (last_underscore) {
      *last_underscore = '\0'; // Replace '_' with NULL to split the string into two
      char* step_name = body;
      int volume = atoi(last_underscore + 1);
      bulk_step_motor.setMaxSpeed(1000);
      
      int retraction = 1100;
      digitalWrite(wash_E, HIGH);
      digitalWrite(OXI_E, HIGH);
      digitalWrite(DET_E, HIGH);
      digitalWrite(linear_E,HIGH);
      digitalWrite(waste_E,HIGH);
      digitalWrite(linear_E,LOW);

      linear_step_motor.setMaxSpeed(2000);
      linear_step_motor.runToNewPosition(3770);
      digitalWrite(linear_E,HIGH);

      int now_E;
      if (strcmp(step_name, "wash") == 0) now_E = wash_E;
      if (strcmp(step_name, "oxidation") == 0) now_E = OXI_E;
      if (strcmp(step_name, "detritylation") == 0) now_E = DET_E;
      if (strcmp(step_name, "linear") == 0) now_E = linear_E;

      digitalWrite(now_E,LOW);
      digitalWrite(waste_E,LOW);
      bulk_step_motor.move(retraction+volume);
      bulk_step_motor.runToPosition();
      digitalWrite(waste_E,HIGH);

      for(int i =0; i<5; i++){
        digitalWrite(now_E,LOW);
        bulk_step_motor.move(volume);
        bulk_step_motor.runToPosition();
        digitalWrite(now_E,HIGH);  
        delay(500);
        digitalWrite(waste_E,LOW);
        bulk_step_motor.move(1000);
        bulk_step_motor.runToPosition();  
        digitalWrite(waste_E,HIGH);
      }

      digitalWrite(now_E,LOW);
      bulk_step_motor.move(volume);
      bulk_step_motor.runToPosition();
      
      
      //if (strcmp(step_name, "wash") != 0){
      //  digitalWrite(waste_E,HIGH);
      //}
      bulk_step_motor.setMaxSpeed(1000);
      bulk_step_motor.move(-retraction);
      bulk_step_motor.runToPosition();
      digitalWrite(waste_E,HIGH);
      digitalWrite(OXI_E, HIGH);
      digitalWrite(DET_E, HIGH);
      digitalWrite(linear_E,HIGH);
      digitalWrite(wash_E,HIGH);
    } else {
      Serial.print("ERROR: Invalid bulk command;");
    }
  }  
  else if (strcmp(cmd, "Lwaste") == 0) {
    digitalWrite(wash_E, HIGH);
    digitalWrite(OXI_E, HIGH);
    digitalWrite(DET_E, HIGH);
    digitalWrite(linear_E,HIGH);
    digitalWrite(waste_E,LOW);
    bulk_step_motor.setMaxSpeed(2000);
    bulk_step_motor.setCurrentPosition(0);
    bulk_step_motor.moveTo(6000);
    bulk_step_motor.runToPosition();
    digitalWrite(waste_E,HIGH);
  }  

  else if (strcmp(cmd, "Swaste") == 0) {
    digitalWrite(wash_E, HIGH);
    digitalWrite(OXI_E, HIGH);
    digitalWrite(DET_E, HIGH);
    digitalWrite(linear_E,HIGH);
    digitalWrite(waste_E,LOW);
    bulk_step_motor.setMaxSpeed(1000);
    bulk_step_motor.setCurrentPosition(0);
    bulk_step_motor.moveTo(1000);
    bulk_step_motor.runToPosition();
    digitalWrite(waste_E,HIGH);
  }  
  else if (strncmp(cmd, "linear_move", 11) == 0) {
    digitalWrite(wash_E, HIGH);
    digitalWrite(OXI_E, HIGH);
    digitalWrite(DET_E, HIGH);
    digitalWrite(waste_E, HIGH);
    digitalWrite(linear_E,LOW);
    linear_step_motor.setMaxSpeed(2000);
    linear_step_motor.runToNewPosition(atoi(cmd + 12));
  }  
  else if(strncmp(cmd, "ink", 3) == 0) {
    Wire.beginTransmission(Airpressure_arduino);
    Wire.write(cmd + 3);
    Wire.endTransmission();
  }  
  else if(strcmp(cmd, "is_ready") == 0) {
    Serial.print("OK;");
  }  
  else if (strcmp(cmd, "WHOAMI") == 0) {
    Serial.print("openIDS;");
  }
}

/**
 * @brief Converts a 128-bit binary string into a 16-byte array and sends it to the slave.
 */
void sendDataToSlave(uint8_t slaveAddress, int amount, const char* data) {
  byte data_bytes[16];
  char byte_segment[9];
  byte_segment[8] = '\0';

  for (int i = 0; i < 16; i++) {
    strncpy(byte_segment, data + (i * 8), 8);
    data_bytes[i] = (byte)strtol(byte_segment, NULL, 2);
  }

  Wire.beginTransmission(slaveAddress);
  Wire.write((uint8_t)amount);
  Wire.write(data_bytes, 16);
  Wire.endTransmission();
}

/**
 * @brief Initializes (Homing) the linear stage.
 */
void linear_init(){
  limit_L_Flag = false;
  limit_R_Flag = false;
  linear_step_motor.setMaxSpeed(1000);  
  digitalWrite(linear_E, LOW);
  if (digitalRead(limit_L_S)|| digitalRead(limit_R_S) == HIGH) {
    linear_step_motor.setMaxSpeed(1000);
    linear_step_motor.move(200);
    linear_step_motor.runToPosition();
     delay(200);  
    }
  linear_step_motor.move(-max_position);
  while(!limit_L_Flag && !limit_R_Flag){
    linear_step_motor.run();
  }
  linear_step_motor.stop();
  delay(200);
  limit_L_Flag = false;
  limit_R_Flag = false;
  linear_step_motor.setCurrentPosition(0);
  linear_step_motor.move(200);
  linear_step_motor.runToPosition();
  linear_step_motor.setMaxSpeed(100);
  linear_step_motor.move(-500);
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
  is_init = true;
}


/**
 * @brief Sends a specific command to all active slaves and waits for a 'Ready' response.
 * @param command The I2C command to send (e.g., CMD_RESET_LOW)
 */
void sendCommandAndWait(uint8_t command) {
  if (activeSlaveCount == 0) return;

  for (int i = 0; i < activeSlaveCount; i++) {
    Wire.beginTransmission(activeSlaveAddresses[i]);
    Wire.write(command);
    Wire.endTransmission();
  }

  bool allReady = false;
  bool readyFlags[activeSlaveCount] = {false};
  unsigned long startTime = millis();

  while (!allReady && (millis() - startTime < 2000)) { // 2-second timeout
    allReady = true;
    for (int i = 0; i < activeSlaveCount; i++) {
      if (!readyFlags[i]) {
        Wire.requestFrom(activeSlaveAddresses[i], (uint8_t)5);
        char responseBuffer[6] = {0};
        if (Wire.readBytes(responseBuffer, 5) == 5) {
            if (strcmp(responseBuffer, "Ready") == 0) {
              readyFlags[i] = true;
            }
        }
      }
      if (!readyFlags[i]) allReady = false;
    }
    if (!allReady) delay(10); // Short delay to reduce CPU load
  }
}

void waste_auto(){
  digitalWrite(auto_step,HIGH);
  digitalWrite(auto_step,LOW);
}

/**
 * @brief Print head power-up sequence.
 */
void power_up_sequence() {
  sendCommandAndWait(CMD_RESET_LOW);
  digitalWrite(PH_VDD, HIGH);
  delay(10); // VDD stabilization time
  sendCommandAndWait(CMD_POWER_UP);
  sendCommandAndWait(CMD_RESET_HIGH);
}

/**
 * @brief Print head power-down sequence.
 */
void power_down_sequence() {
  sendCommandAndWait(CMD_RESET_HIGH);
  sendCommandAndWait(CMD_RESET_LOW);
  sendCommandAndWait(CMD_POWER_DOWN);
  digitalWrite(PH_VDD, LOW);
}
