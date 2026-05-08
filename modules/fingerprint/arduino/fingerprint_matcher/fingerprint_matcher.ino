#include <Adafruit_Fingerprint.h>
#include <SoftwareSerial.h>

// Fingerprint sensor wiring:
// Sensor TX -> Arduino pin 2
// Sensor RX -> Arduino pin 3
SoftwareSerial fingerSerial(2, 3);
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&fingerSerial);

const int MIN_CONFIDENCE = 100;
const unsigned long FINGER_TIMEOUT_MS = 15000;
const char PROTOCOL_ID[] = "COMMAND_V2";

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(200);

  finger.begin(57600);

  if (finger.verifyPassword()) {
    Serial.print("READY:");
    Serial.println(PROTOCOL_ID);
  } else {
    Serial.println("SENSOR_ERROR");
  }
}

void loop() {
  if (!Serial.available()) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();
  command.toUpperCase();

  if (command == "SCAN") {
    scanFingerprint();
    return;
  }

  if (command == "PING") {
    Serial.print("PONG:");
    Serial.println(PROTOCOL_ID);
    return;
  }

  if (command.startsWith("ENROLL:")) {
    int id = command.substring(7).toInt();
    enrollFingerprint(id);
    return;
  }

  if (command.length() > 0) {
    Serial.println("UNKNOWN_COMMAND");
  }
}

bool waitForFingerImage(unsigned long timeoutMs) {
  unsigned long startTime = millis();

  while (millis() - startTime < timeoutMs) {
    uint8_t result = finger.getImage();

    if (result == FINGERPRINT_OK) {
      return true;
    }

    if (result != FINGERPRINT_NOFINGER) {
      Serial.println("SCAN_ERROR");
      return false;
    }

    delay(100);
  }

  return false;
}

void waitForFingerRelease() {
  while (finger.getImage() != FINGERPRINT_NOFINGER) {
    delay(100);
  }
}

void scanFingerprint() {
  if (!waitForFingerImage(FINGER_TIMEOUT_MS)) {
    Serial.println("NO_MATCH");
    return;
  }

  uint8_t result = finger.image2Tz();
  if (result != FINGERPRINT_OK) {
    Serial.println("NO_MATCH");
    waitForFingerRelease();
    return;
  }

  result = finger.fingerFastSearch();

  if (result != FINGERPRINT_OK) {
    Serial.println("NO_MATCH");
    waitForFingerRelease();
    return;
  }

  if (finger.confidence < MIN_CONFIDENCE) {
    Serial.print("LOW_CONFIDENCE:");
    Serial.print(finger.fingerID);
    Serial.print(":");
    Serial.println(finger.confidence);
    waitForFingerRelease();
    return;
  }

  Serial.print("MATCH:");
  Serial.print(finger.fingerID);
  Serial.print(":");
  Serial.println(finger.confidence);

  waitForFingerRelease();
}

void enrollFingerprint(int id) {
  if (id < 1 || id > 200) {
    Serial.println("ENROLL_FAILED:BAD_ID");
    return;
  }

  Serial.println("ENROLL_PLACE_FINGER");

  if (!waitForFingerImage(FINGER_TIMEOUT_MS)) {
    Serial.println("ENROLL_FAILED:TIMEOUT_1");
    return;
  }

  uint8_t result = finger.image2Tz(1);
  if (result != FINGERPRINT_OK) {
    Serial.println("ENROLL_FAILED:IMAGE_1");
    waitForFingerRelease();
    return;
  }

  Serial.println("ENROLL_REMOVE_FINGER");
  waitForFingerRelease();
  delay(1000);

  Serial.println("ENROLL_PLACE_SAME_FINGER");

  if (!waitForFingerImage(FINGER_TIMEOUT_MS)) {
    Serial.println("ENROLL_FAILED:TIMEOUT_2");
    return;
  }

  result = finger.image2Tz(2);
  if (result != FINGERPRINT_OK) {
    Serial.println("ENROLL_FAILED:IMAGE_2");
    waitForFingerRelease();
    return;
  }

  result = finger.createModel();
  if (result != FINGERPRINT_OK) {
    Serial.println("ENROLL_FAILED:MISMATCH");
    waitForFingerRelease();
    return;
  }

  result = finger.storeModel(id);
  if (result != FINGERPRINT_OK) {
    Serial.println("ENROLL_FAILED:STORE");
    waitForFingerRelease();
    return;
  }

  Serial.print("ENROLLED:");
  Serial.println(id);

  waitForFingerRelease();
}
