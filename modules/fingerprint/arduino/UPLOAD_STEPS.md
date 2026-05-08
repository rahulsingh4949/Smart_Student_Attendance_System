# Fingerprint Arduino Upload Steps

Upload this sketch:

`modules/fingerprint/arduino/fingerprint_matcher/fingerprint_matcher.ino`

1. Open `fingerprint_matcher.ino` in Arduino IDE.
2. Install the **Adafruit Fingerprint Sensor Library** from **Sketch > Include Library > Manage Libraries** if Arduino IDE says `Adafruit_Fingerprint.h` is missing.
3. Select your board from **Tools > Board**.
4. Select the USB port from **Tools > Port**.
5. Upload the sketch.
6. Open Serial Monitor at `9600` baud.
7. Type `PING` and press send.
8. Type `SCAN` and press send, then scan a finger.

Expected safe output:

```text
PONG:COMMAND_V2
MATCH:1:180
NO_MATCH
LOW_CONFIDENCE:1:60
```

The app accepts matches at confidence `100` or higher. If your Arduino still prints
`LOW_CONFIDENCE:1:104`, the updated Python code will accept it, but uploading the
latest sketch keeps the Arduino message names consistent too.

If Serial Monitor prints only a bare number like:

```text
1
```

the old Arduino sketch is still running. Attendance will reject that output because it is unsafe.

If Serial Monitor prints `NO_MATCH` after `PING`, the Arduino is not running this command sketch yet, or it is still finishing an older scan. Upload again, close Serial Monitor, reopen it at `9600` baud, and test `PING` first.

For enrollment testing, type:

```text
ENROLL:1
```

Then follow the sensor prompts. Successful enrollment prints:

```text
ENROLLED:1
```
