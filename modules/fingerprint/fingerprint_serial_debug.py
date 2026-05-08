import os
import sys
import time

import serial

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from modules.fingerprint.fingerprint_attendance import (
    BAUD_RATE,
    PROTOCOL_ID,
    TIMEOUT,
    clear_serial_buffers,
    format_available_ports,
    get_available_ports,
    get_fingerprint_port,
    require_command_sketch,
    send_command,
)

MAX_SECONDS = 20


def main():
    port = get_fingerprint_port()

    if not port:
        print("No Arduino/fingerprint serial port found.")
        print()
        print("Available ports:")
        print(format_available_ports(get_available_ports()))
        sys.exit(1)

    print(f"Opening {port} at {BAUD_RATE} baud...")

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=TIMEOUT)
        time.sleep(2)
        clear_serial_buffers(ser)
        sketch_ok, messages = require_command_sketch(ser)
        if not sketch_ok:
            details = " | ".join(messages) if messages else "No PONG response"
            print(
                "Wrong Arduino sketch detected.\n"
                f"Expected PONG:{PROTOCOL_ID}. Received: {details}",
                file=sys.stderr,
            )
            sys.exit(1)
        send_command(ser, "SCAN")
    except Exception as e:
        print(f"Serial error: {e}", file=sys.stderr)
        sys.exit(1)

    print("Sent SCAN. Place a finger on the sensor. Raw Arduino output:")

    start_time = time.time()
    try:
        while time.time() - start_time < MAX_SECONDS:
            raw = ser.readline().decode("utf-8", errors="ignore").strip()
            if raw:
                print(raw)
                sys.stdout.flush()
    finally:
        ser.close()


if __name__ == "__main__":
    main()
