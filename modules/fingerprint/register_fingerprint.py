import os
import re
import sys
import time

import serial
from serial.tools import list_ports

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

BAUD_RATE = int(os.environ.get("FINGERPRINT_BAUD_RATE", "9600"))
TIMEOUT = 0.2
MAX_WAIT_SECONDS = 30
SKETCH_HANDSHAKE_SECONDS = 18
MIN_CONFIDENCE = int(os.environ.get("FINGERPRINT_MIN_CONFIDENCE", "100"))
PROTOCOL_ID = "COMMAND_V2"


def get_requested_fingerprint_id():
    if len(sys.argv) < 2:
        return None

    try:
        fingerprint_id = int(sys.argv[1])
    except ValueError:
        return None

    if fingerprint_id < 1 or fingerprint_id > 200:
        return None

    return fingerprint_id


def get_available_ports():
    return list(list_ports.comports())


def format_available_ports(ports):
    if not ports:
        return "No serial ports found."

    return "\n".join(f"- {port.device} ({port.description})" for port in ports)


def get_fingerprint_port():
    configured_port = os.environ.get("FINGERPRINT_PORT")
    if configured_port:
        return configured_port

    ports = get_available_ports()
    preferred_keywords = (
        "usbmodem",
        "usbserial",
        "wchusbserial",
        "arduino",
        "ch340",
        "cp210",
    )

    for port in ports:
        haystack = f"{port.device} {port.description} {port.hwid}".lower()
        if any(keyword in haystack for keyword in preferred_keywords):
            return port.device

    return None


def clear_serial_buffers(ser):
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception:
        pass


def send_command(ser, command):
    ser.write(f"{command}\n".encode("utf-8"))
    ser.flush()


def require_command_sketch(ser):
    start_time = time.time()
    last_ping = 0
    messages = []

    while time.time() - start_time < SKETCH_HANDSHAKE_SECONDS:
        now = time.time()
        if now - last_ping >= 1:
            send_command(ser, "PING")
            last_ping = now

        raw = ser.readline().decode("utf-8", errors="ignore")
        message = raw.strip()

        if not message:
            continue

        messages.append(message)

        if message == f"PONG:{PROTOCOL_ID}" or message == f"READY:{PROTOCOL_ID}":
            return True, messages

    return False, messages


def is_unregistered_message(raw):
    lower = raw.lower()
    return any(
        text in lower
        for text in (
            "no match",
            "not found",
            "not registered",
            "unknown fingerprint",
            "did not find",
            "not find a match",
            "fingerprint not found",
            "no_match",
        )
    )


def extract_fingerprint_id(raw):
    match = extract_fingerprint_match(raw)
    return match[0] if match else None


def extract_confidence(raw):
    machine_match = re.search(r"^(?:match|low_confidence)[:=](\d+):(\d+)$", raw.lower())
    if machine_match:
        return int(machine_match.group(2))

    patterns = [
        r"confidence\s*(?:of|is|:|=)?\s*(\d+)",
        r"score\s*(?:of|is|:|=)?\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw.lower())
        if match:
            return int(match.group(1))

    return None


def extract_fingerprint_match(raw):
    raw = raw.strip()
    if not raw:
        return None

    lower = raw.lower()
    if is_unregistered_message(raw) or "failed" in lower:
        return None

    confidence = extract_confidence(raw)

    machine_match = re.search(r"^(?:match|low_confidence)[:=](\d+)(?::\d+)?$", lower)
    if machine_match:
        return int(machine_match.group(1)), confidence

    if raw.isdigit():
        return int(raw), confidence

    patterns = [
        r"(?:finger(?:print)?\s*)?id\s*[:=#-]?\s*(\d+)",
        r"found\s+(?:id|finger(?:print)?)\s*#?\s*(\d+)",
        r"stored\s+(?:at\s+)?(?:id|position|slot)\s*#?\s*(\d+)",
        r"enrolled\s+(?:id\s*)?#?\s*(\d+)",
        r"enrolled[:=#-]?\s*(\d+)",
        r"template\s*#?\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            return int(match.group(1)), confidence

    numbers = re.findall(r"\d+", raw)
    if len(numbers) == 1 and any(
        text in lower for text in ("finger", "template", "position", "slot")
    ):
        return int(numbers[0]), confidence

    return None


def wait_for_fingerprint_result(ser):
    start_time = time.time()
    last_messages = []

    while time.time() - start_time < MAX_WAIT_SECONDS:
        raw = ser.readline().decode("utf-8", errors="ignore")
        message = raw.strip()

        if not message:
            continue

        last_messages.append(message)
        last_messages = last_messages[-5:]

        if message.lower().startswith("enrolled"):
            fingerprint_match = extract_fingerprint_match(message)
            return fingerprint_match, "enrolled", last_messages

        if message.lower().startswith("enroll_failed"):
            return None, "enroll_failed", last_messages

        if message.lower().startswith("enroll_") or message.lower().startswith("ready"):
            continue

        if is_unregistered_message(message):
            return None, "not_registered", last_messages

        normalized_message = message.lower()

        if normalized_message.startswith("low_confidence"):
            fingerprint_match = extract_fingerprint_match(message)
            if fingerprint_match is not None:
                fingerprint_id, confidence = fingerprint_match
                if confidence is not None and confidence >= MIN_CONFIDENCE:
                    return (fingerprint_id, confidence), "matched", last_messages
            return fingerprint_match, "low_confidence", last_messages

        fingerprint_match = extract_fingerprint_match(message)
        if fingerprint_match is not None:
            fingerprint_id, confidence = fingerprint_match
            if confidence is not None and confidence < MIN_CONFIDENCE:
                return (fingerprint_id, confidence), "low_confidence", last_messages
            return fingerprint_match, "matched", last_messages

    return None, "timeout", last_messages


def main():
    requested_fingerprint_id = get_requested_fingerprint_id()
    if requested_fingerprint_id is None:
        print("Missing or invalid fingerprint ID for enrollment.", file=sys.stderr)
        sys.exit(1)

    try:
        port = get_fingerprint_port()
        if not port:
            print(
                "No Arduino/fingerprint serial port found.\n\n"
                "Plug in the Arduino and make sure it appears as /dev/cu.usbmodem* "
                "or /dev/cu.usbserial*.\n\n"
                f"Available ports:\n{format_available_ports(get_available_ports())}",
                file=sys.stderr,
            )
            sys.exit(1)

        ser = serial.Serial(port, BAUD_RATE, timeout=TIMEOUT)
        time.sleep(2)
        clear_serial_buffers(ser)
        sketch_ok, sketch_messages = require_command_sketch(ser)
        if not sketch_ok:
            details = " | ".join(sketch_messages) if sketch_messages else "No PONG response"
            print(
                "Arduino is not running the command-based fingerprint sketch.\n\n"
                "Upload this sketch:\n"
                "modules/fingerprint/arduino/fingerprint_matcher/fingerprint_matcher.ino\n\n"
                f"Expected PONG:{PROTOCOL_ID}. Received: {details}",
                file=sys.stderr,
            )
            sys.exit(1)

        send_command(ser, f"ENROLL:{requested_fingerprint_id}")

    except Exception as e:
        print(f"Error opening serial port: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        fingerprint_match, status, last_messages = wait_for_fingerprint_result(ser)

        if status == "enrolled":
            fingerprint_id, confidence = fingerprint_match
            print(fingerprint_id)
            sys.stdout.flush()
            sys.exit(0)

        if status == "enroll_failed":
            details = " | ".join(last_messages)
            print(f"Fingerprint enrollment failed. Last scanner messages: {details}", file=sys.stderr)
            sys.exit(1)

        if status == "matched":
            print(
                "Scanner returned a match during enrollment. Upload the command-based Arduino sketch.",
                file=sys.stderr,
            )
            sys.exit(1)

        if status == "not_registered":
            print(
                "Fingerprint not found on sensor. Enroll it on the fingerprint module first.",
                file=sys.stderr,
            )
            sys.exit(1)

        if status == "low_confidence":
            if fingerprint_match is None:
                print(
                    "Fingerprint match confidence is too low. Try again with the same finger flat on the sensor.",
                    file=sys.stderr,
                )
            else:
                fingerprint_id, confidence = fingerprint_match
                print(
                    "Fingerprint match confidence is too low. "
                    f"Sensor returned ID {fingerprint_id} with confidence {confidence}.",
                    file=sys.stderr,
                )
            sys.exit(1)

        if last_messages:
            details = " | ".join(last_messages)
            print(
                "No fingerprint ID received within timeout. "
                f"Last scanner messages: {details}",
                file=sys.stderr,
            )
        else:
            print(f"No serial data received from fingerprint scanner on {port}.", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"Unexpected fingerprint error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        ser.close()


if __name__ == "__main__":
    main()
