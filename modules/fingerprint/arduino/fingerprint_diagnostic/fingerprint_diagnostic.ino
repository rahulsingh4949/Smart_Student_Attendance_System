#include <Adafruit_Fingerprint.h>
#include <SoftwareSerial.h>

// Diagnostic sketch only.
// It tests common fingerprint sensor wiring directions and baud rates.
//
// Common wiring:
// Sensor VCC -> Arduino 5V
// Sensor GND -> Arduino GND
// Sensor TX  -> Arduino pin 2
// Sensor RX  -> Arduino pin 3

SoftwareSerial serialA(2, 3);
SoftwareSerial serialB(3, 2);
Adafruit_Fingerprint fingerA(&serialA);
Adafruit_Fingerprint fingerB(&serialB);

const long BAUDS[] = {57600, 9600, 19200, 38400, 115200};

bool testSensor(Adafruit_Fingerprint &finger, SoftwareSerial &port, long baud, const char *label) {
  port.listen();
  delay(200);
  finger.begin(baud);
  delay(300);

  Serial.print("Testing ");
  Serial.print(label);
  Serial.print(" at ");
  Serial.print(baud);
  Serial.print(" baud ... ");

  if (finger.verifyPassword()) {
    Serial.println("FOUND");
    Serial.print("Template count: ");
    if (finger.getTemplateCount() == FINGERPRINT_OK) {
      Serial.println(finger.templateCount);
    } else {
      Serial.println("could not read");
    }
    return true;
  }

  Serial.println("not found");
  return false;
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(500);
  delay(1000);

  Serial.println();
  Serial.println("Fingerprint sensor diagnostic");
  Serial.println("Close other apps using the Arduino port.");
  Serial.println("If all tests say not found, check VCC, GND, TX, RX, or sensor damage.");
  Serial.println();

  bool found = false;

  for (int i = 0; i < 5; i++) {
    found = testSensor(fingerA, serialA, BAUDS[i], "Sensor TX->pin2, Sensor RX->pin3") || found;
    delay(300);
    found = testSensor(fingerB, serialB, BAUDS[i], "Sensor TX->pin3, Sensor RX->pin2") || found;
    delay(300);
  }

  Serial.println();
  if (found) {
    Serial.println("RESULT: Sensor detected. Use the wiring/baud that printed FOUND.");
  } else {
    Serial.println("RESULT: Sensor not detected on any tested wiring/baud.");
    Serial.println("Check power, ground, jumper wires, and sensor connector.");
  }
}

void loop() {
}
