#include <Arduino.h>
#include <RotaryEncoder.h>
#include "BasicStepperDriver.h"
#include "HX711.h"


// Pins
// Stepper Motor (Digital)
#define STEP 2
#define DIR 5
#define EN 8

// Load cell (Digital)
#define DATA A2
#define CLOCK A3

// Oled Display
// Defined in library A4(SDA), A5(SCL)

// Sd card
// Defined in SPI lib 11(MOSI), 12(MISO), 13(SCK)
const int chipSelect = 10;

// Rotary Encoder
#define ROTARY_IN1 A0
#define ROTARY_IN2 A1
#define ROTARY_SWITCH 9

RotaryEncoder encoder(ROTARY_IN1, ROTARY_IN2, RotaryEncoder::LatchMode::FOUR3);

// Switch
#define SWITCH_PIN 3

//SD card variables
// File myFile;

// Motor configs
#define MOTOR_STEPS 40
#define RPM 300
#define STEPS_PER_MM 640
// Must match what is set on jumpers
#define MICROSTEPS 64

BasicStepperDriver stepper(MOTOR_STEPS, DIR, STEP);

// Load cell configs and variables
#define SCALE_MULT 7130
HX711 scale;
uint8_t dataPin = DATA;
uint8_t clockPin = CLOCK;
uint32_t start, stop;
volatile float f;

// Switch variables
bool pressed = 0;
bool released = 0;
int test = 0;


void setup() {
  // Begin serial
  Serial.begin(115200);

  // Setup scale
  scale.begin(dataPin, clockPin);
  scale.set_scale(SCALE_MULT);
  scale.tare(); // reset the scale to zero = 0

  // Setup pins
  pinMode(ROTARY_SWITCH, INPUT);
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  pinMode(DIR, OUTPUT);
  pinMode(STEP, OUTPUT);
  pinMode(EN, OUTPUT);

  // Setup stepper motor
  digitalWrite(EN, LOW);
  stepper.begin(RPM, MICROSTEPS);

  // Setup file on SD
  // Only one file can be open at a time, so you have to close this one before opening another.
  // mkdir("/switchData")
  // myFile = SD.open("/switchData/00000000.txt", FILE_WRITE);
  // if (myFile) {
  //  Serial.print("Writing to test.txt...");
  //  myFile.println("testing 1, 2, 3.");
  //  // close the file:
  //  myFile.close();
  //} else {
    // if the file didn't open, print an error:
  //  Serial.println("error opening test.txt");
  //}
}

void loop() {
  static int pos = 0;
  encoder.tick();
  int newPos = encoder.getPosition();
  if (pos != newPos) {
    Serial.print("pos:");
    Serial.print(newPos);
    Serial.print(" dir:");
    Serial.println((int)(encoder.getDirection()));
    pos = newPos;
  }
  if (Serial.available())
  {
    char c = Serial.read();
    switch (c)
    {
      case 't': // tare
        scale.tare();
        break;
      case 'z':
        scale.tare();
        f = 0.0;
        while (f < 1.0)
        {
          stepper.move(80);
          f = scale.get_units(1);
        }
        while (f > 0.1)
        {
          stepper.move(-8);
          delay(100);
          f = scale.get_units(4);
        }
        break;
      case 'w': // weigh
        f = scale.get_units(1);
        Serial.println(f);
        break;
      case 'm': // move
        test = Serial.parseInt();
        Serial.println(test);
        stepper.move(test);
        break;
      case 'd': // disable motor
        stepper.disable();
        break;
      case 'p': // plot
        {
          int z = 0;
          f = 0;
          pressed = 0;
          released = 0;
          bool aborted = false;

          while (f < 110 && !aborted)
          {
            z += 8;
            stepper.move(8);
            delay(10); // Lower delay, check serial more often

            // Check for emergency stop
            if (Serial.available() && Serial.read() == 's') {
              aborted = true;
              Serial.println("ABORTED");
              break;
            }

            f = scale.get_units(4);
            Serial.print('d'); Serial.print(z); Serial.print(':'); Serial.println(f);

            if (!pressed && !digitalRead(SWITCH_PIN))
            {
              pressed = 1;
              Serial.print('P'); Serial.print(z); Serial.print(':'); Serial.println(f);
            }
          }

          delay(500);

          while (f > 0.5 && !aborted) // Upward stroke
          {
            z -= 8;
            stepper.move(-8);
            delay(10);

            if (Serial.available() && Serial.read() == 's') {
              aborted = true;
              Serial.println("ABORTED");
              break;
            }

            f = scale.get_units(4);
            Serial.print('u'); Serial.print(z); Serial.print(':'); Serial.println(f);

            if (!released && digitalRead(SWITCH_PIN))
            {
              released = 1;
              Serial.print('R'); Serial.print(z); Serial.print(':'); Serial.println(f);
            }
          }
          Serial.println("DONE");
        }
        break;
      default:
        Serial.println("Unknown cmd");
        break;
    }
    Serial.println(c);
  }



  //  f = scale.get_units(1);
  //  Serial.println(f);
  //
  //  if (f > 110)
  //  {
  //    stepper.move(-3200);
  //  }
  //  else stepper.move(8);
}
