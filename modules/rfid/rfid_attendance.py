import sys
import os
import time
import serial

# Fix import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from database.db_helper import init_database, get_student_by_rfid, mark_attendance

PORT = "/dev/cu.usbmodem1101"
BAUD_RATE = 9600
TIMEOUT = 1
MAX_WAIT_SECONDS = 10


# -------------------------------
# CLEAN UID (VERY IMPORTANT FIX)
# -------------------------------
def clean_uid(raw):
    raw = raw.strip()

    if not raw:
        return ""

    # Extract UID part safely
    if "UID" in raw:
        raw = raw.split("UID")[-1]

    # Remove noise characters
    uid = raw.replace(":", "").replace(" ", "").strip().upper()

    # Accept ONLY valid full UID (8 HEX chars)
    if len(uid) == 8 and all(c in "0123456789ABCDEF" for c in uid):
        return uid

    return ""


# -------------------------------
# MAIN FUNCTION
# -------------------------------
def main():
    init_database()

    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=TIMEOUT)
        time.sleep(2)
    except Exception as e:
        print(f"Serial error: {e}", file=sys.stderr)
        sys.exit(1)

    start_time = time.time()

    try:
        while time.time() - start_time < MAX_WAIT_SECONDS:

            if ser.in_waiting > 0:
                raw = ser.readline().decode("utf-8", errors="ignore")

                uid = clean_uid(raw)

                # Ignore garbage / partial data
                if not uid:
                    continue

                # Debug (optional)
                print(f"Card Detected: {uid}")

                result = get_student_by_rfid(uid)

                if not result:
                    print("Card not registered")
                    sys.exit(0)

                student_id, name = result
                marked = mark_attendance(student_id, name, method="RFID")

                if marked:
                    print(f"{name} marked present")
                else:
                    print(f"{name} is already marked today")

                # 🔥 EXIT immediately after first valid scan
                sys.exit(0)

            time.sleep(0.05)

        # Timeout
        print("No RFID card detected", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"RFID error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        ser.close()


# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    main()
