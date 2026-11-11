#include <Arduino.h>
#include <AccelStepper.h>
#include <HX711.h>
#include <RotaryEncoder.h>

// --- PINS ---
#define STEP_PIN 2
#define DIR_PIN 5
#define EN_PIN 8
#define DATA_PIN A2
#define CLOCK_PIN A3
#define ROTARY_IN1 A0
#define ROTARY_IN2 A1
#define ROTARY_SWITCH 9
#define SWITCH_PIN 3 // The contact pin on the switch itself
const int chipSelect = 10; // SD Card

// --- HARDWARE CONFIG ---
#define STEPS_PER_MM 1280.0 // Ensure this is a float for accurate math
#define SCALE_MULT 7130
#define MAX_WEIGHT 125.0

// --- OBJECTS ---
AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);
HX711 scale;
RotaryEncoder encoder(ROTARY_IN1, ROTARY_IN2, RotaryEncoder::LatchMode::FOUR3);

// --- STATE MACHINE ---
enum MachineState { IDLE, TARE_ROUTINE, MEASURING_DOWN, MEASURING_UP, RETURN_HOME };
MachineState currentState = IDLE;

// --- VARIABLES ---
float currentWeight = 0.0;
float currentRawWeight = 0.0;
long lastLoggedPosition = -999;
bool pressed = false;
bool released = false;

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(10); // CRITICAL: Prevents string reading from blocking the motor!

  // Pins
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, LOW); // Enable driver
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  pinMode(ROTARY_SWITCH, INPUT_PULLUP);

  // Stepper Config
  stepper.setMaxSpeed(2000);
  stepper.setAcceleration(1500); // High accel for responsive UI

  // Scale Config
  scale.begin(DATA_PIN, CLOCK_PIN);
  scale.set_scale(SCALE_MULT);
  scale.tare();

  Serial.println("<STATUS:READY>");
}

// Helper to format and send data cleanly to the web backend
void sendDataPoint(char direction, long steps, float weight) {
  float mm = steps / STEPS_PER_MM;
  Serial.print("DATA:");
  Serial.print(direction);
  Serial.print(":");
  Serial.print(mm, 3);
  Serial.print(":");
  Serial.println(weight, 2);
}

void loop() {
  // 1. ALWAYS RUN THE STEPPER (Must be called as fast as possible)
  stepper.run();

  // 2. READ ROTARY ENCODER
  encoder.tick(); // Keep track of physical knob turns

  // 3. READ HARDWARE NON-BLOCKING
  // get_units(1) reads a single ti b bme without blocking heavily
  if (scale.is_ready()) {
     currentWeight = scale.get_units(1);
     currentRawWeight = scale.read();
  }

  // 4. CHECK SERIAL COMMANDS (Updated for Debugging)
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n'); // Read full command
    cmd.trim();

    if (cmd.length() > 0) {
      char action = cmd.charAt(0);

      // Control Commands
      if (action == 's') { if (currentState == IDLE) currentState = TARE_ROUTINE; }
      else if (action == 'x') { currentState = RETURN_HOME; Serial.println("<STATUS:ABORTED>"); }

      // Debug / Calibration Commands
      else if (action == 'v') { stepper.setMaxSpeed(cmd.substring(1).toFloat()); } // Set Speed (v2000)
      else if (action == 'a') { stepper.setAcceleration(cmd.substring(1).toFloat()); } // Set Accel (a1500)
      else if (action == 'j') { stepper.move(cmd.substring(1).toInt()); } // Jog relative steps (j640 or j-640)
      else if (action == 'c') { // Check switch
        Serial.print("<DEBUG:SWITCH:");
        Serial.print(digitalRead(SWITCH_PIN) == LOW ? "CLOSED (PRESSED)" : "OPEN (RELEASED)");
        Serial.println(">");
      }
      else if (action == 'w') { // Read weight (Calibrated)
        Serial.print("<DEBUG:WEIGHT:"); Serial.print(currentWeight); Serial.println(">");
      }
      else if (action == 'r') { // Read RAW uncalibrated value
        Serial.print("<DEBUG:WEIGHT_RAW:"); Serial.print(currentRawWeight); Serial.println(">");
      }

      else if (action == 'R') {
        Serial.println("<STATUS:STREAMING_RAW>");
        for(int i = 0; i < 20; i++) {
          Serial.print("<DEBUG:RAW_STREAM:");
          Serial.print(scale.read()); // Get uncalibrated hardware value
          Serial.println(">");
          delay(100); // Wait 100ms to capture the pressing motion
        }
        Serial.println("<STATUS:READY>");
      }

      else if (action == 't') { // Tare manually
        scale.tare();
        Serial.println("<STATUS:TARED>");
      }
    }
  }

  // 5. EXECUTE CURRENT STATE
  switch (currentState) {

    case IDLE:
      // In the future, update OLED menu here based on encoder position
      // Check physical encoder button to start manually
      if (digitalRead(ROTARY_SWITCH) == LOW) {
        currentState = TARE_ROUTINE;
        delay(200); // Simple debounce for the physical button
      }
      break;

    case TARE_ROUTINE:
      scale.tare();
      stepper.setCurrentPosition(0); // Set absolute 0
      pressed = false;
      released = false;
      lastLoggedPosition = -999;

      Serial.println("<STATUS:STARTING>");
      // Tell stepper to move down a large amount (it will stop based on weight)
      stepper.moveTo(3200);
      currentState = MEASURING_DOWN;
      break;

    case MEASURING_DOWN:
      // Log data if position changed
      if (stepper.currentPosition() != lastLoggedPosition) {
        sendDataPoint('d', stepper.currentPosition(), currentWeight);
        lastLoggedPosition = stepper.currentPosition();

        // Check for switch actuation
        if (!pressed && digitalRead(SWITCH_PIN) == LOW) {
           pressed = true;
           sendDataPoint('P', stepper.currentPosition(), currentWeight);
        }
      }

      // Reverse condition based on weight bottom-out
      if (currentWeight >= MAX_WEIGHT || stepper.distanceToGo() == 0) {
        stepper.moveTo(0); // Target the absolute 0 we set during TARE
        currentState = MEASURING_UP;
      }
      break;

    case MEASURING_UP:
      if (stepper.currentPosition() != lastLoggedPosition) {
        sendDataPoint('u', stepper.currentPosition(), currentWeight);
        lastLoggedPosition = stepper.currentPosition();

        // Check for switch release
        if (!released && digitalRead(SWITCH_PIN) == HIGH) {
           released = true;
           sendDataPoint('R', stepper.currentPosition(), currentWeight);
        }
      }

      // Check if we arrived safely back at 0
      if (stepper.distanceToGo() == 0) {
        currentState = IDLE;
        Serial.println("<STATUS:DONE>");
      }
      break;

    case RETURN_HOME:
      // Used for aborts
      stepper.moveTo(0);
      if (stepper.distanceToGo() == 0) {
        currentState = IDLE;
      }
      break;
  }
}