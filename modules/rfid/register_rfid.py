import sys
import os
import time
import re
import serial

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

PORT = "/dev/cu.usbmodem1101"
BAUD_RATE = 9600
TIMEOUT = 1
MAX_WAIT_SECONDS = 15
VALID_UID_LENGTH = 8
HEX_CHARS = "0123456789ABCDEF"
UID_PATTERN = re.compile(r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{2}[\s:-]?){4}(?![0-9A-Fa-f])")


def clean_uid(raw):
    raw = raw.strip().upper()

    if not raw:
        return ""

    # Prefer text after UID when the Arduino prints lines like "UID: C3 B7 DE 00".
    search_text = raw.split("UID", 1)[-1] if "UID" in raw else raw

    # Accept only real 4-byte RFID UIDs, not prompt/status lines such as "Scan RFID card...".
    for candidate in UID_PATTERN.findall(search_text):
        uid = re.sub(r"[^0-9A-F]", "", candidate.upper())
        if len(uid) == VALID_UID_LENGTH and all(c in HEX_CHARS for c in uid):
            return uid

    uid = re.sub(r"[^0-9A-F]", "", search_text)
    if (
        len(uid) == VALID_UID_LENGTH
        and all(c in HEX_CHARS for c in uid)
        and all(c in f"{HEX_CHARS} :-" for c in search_text)
    ):
        return uid

    return ""


def main():
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=TIMEOUT)
        time.sleep(2)
    except Exception as e:
        print(f"Error opening serial port: {e}", file=sys.stderr)
        sys.exit(1)

    start_time = time.time()

    try:
        while time.time() - start_time < MAX_WAIT_SECONDS:
            if ser.in_waiting > 0:
                raw = ser.readline().decode("utf-8", errors="ignore")
                uid = clean_uid(raw)

                if not uid:
                    continue

                print(uid)
                sys.stdout.flush()
                sys.exit(0)

            time.sleep(0.1)

        print("No RFID card detected within timeout.", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"Unexpected RFID error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        ser.close()


if __name__ == "__main__":
    main()
