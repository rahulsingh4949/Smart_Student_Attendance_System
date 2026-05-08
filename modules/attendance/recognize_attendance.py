import os
import sys
import cv2

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from database.db_helper import get_student_name, mark_attendance, init_database


def get_base_dir():
    current_file = os.path.abspath(__file__)
    candidates = [
        os.path.dirname(os.path.dirname(os.path.dirname(current_file))),
        os.path.dirname(os.path.dirname(current_file)),
        os.path.dirname(current_file),
        os.getcwd(),
    ]

    for candidate in candidates:
        if os.path.exists(os.path.join(candidate, "modules")):
            return candidate

    return os.path.dirname(os.path.dirname(os.path.dirname(current_file)))


BASE_DIR = get_base_dir()

CASCADE_PATH = os.path.join(
    BASE_DIR,
    "modules",
    "face_detection",
    "haarcascade_frontalface_default.xml"
)

MODEL_PATH = os.path.join(BASE_DIR, "trained_model", "face_model.yml")

init_database()

if not os.path.exists(CASCADE_PATH):
    raise FileNotFoundError(f"Cascade not found: {CASCADE_PATH}")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
if face_cascade.empty():
    raise FileNotFoundError(f"Could not load Haar cascade: {CASCADE_PATH}")

if not hasattr(cv2, "face"):
    raise AttributeError("cv2.face is not available. Install opencv-contrib-python.")

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_PATH)

CONFIDENCE_THRESHOLD = 80
exit_clicked = False


def preprocess_face(gray_face):
    face = cv2.resize(gray_face, (200, 200))
    face = cv2.equalizeHist(face)
    return face


def draw_exit_button(frame):
    h, w = frame.shape[:2]
    x1 = max(20, w - 170)
    y1 = 10
    x2 = w - 20
    y2 = 50

    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), -1)
    cv2.putText(
        frame,
        "EXIT",
        (x1 + 35, y1 + 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )
    return (x1, y1, x2, y2)


exit_button_rect = (0, 0, 0, 0)


def mouse_callback(event, x, y, flags, param):
    global exit_clicked, exit_button_rect

    if event == cv2.EVENT_LBUTTONDOWN:
        x1, y1, x2, y2 = exit_button_rect
        if x1 <= x <= x2 and y1 <= y <= y2:
            exit_clicked = True


def main():
    global exit_button_rect

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    cv2.namedWindow("Face Attendance System")
    cv2.setMouseCallback("Face Attendance System", mouse_callback)

    status_message = "Waiting for face..."
    status_color = (255, 255, 0)
    cooldown_counter = 0
    last_student_id = None

    print("Starting face recognition attendance...")
    print("Press 'q' or click EXIT to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read from camera.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=6,
            minSize=(100, 100)
        )

        if len(faces) == 0 and cooldown_counter <= 0:
            status_message = "Waiting for face..."
            status_color = (255, 255, 0)

        for (x, y, w, h) in faces:
            margin_x = int(w * 0.12)
            margin_y = int(h * 0.12)

            x1 = max(0, x - margin_x)
            y1 = max(0, y - margin_y)
            x2 = min(gray.shape[1], x + w + margin_x)
            y2 = min(gray.shape[0], y + h + margin_y)

            face_roi = gray[y1:y2, x1:x2]
            processed_face = preprocess_face(face_roi)

            try:
                predicted_id, confidence = recognizer.predict(processed_face)
            except Exception:
                predicted_id, confidence = -1, 999.0

            student_id = str(predicted_id).strip()
            recognized = False
            label = "Unknown"
            info = f"Confidence: {confidence:.1f}"

            if confidence <= CONFIDENCE_THRESHOLD:
                student_name = get_student_name(student_id)

                if student_name:
                    recognized = True
                    label = f"{student_name} ({student_id})"

                    if student_id != last_student_id or cooldown_counter <= 0:
                        marked = mark_attendance(student_id, student_name, method="Face")

                        if marked:
                            status_message = f"Attendance Marked: {student_name} ({student_id})"
                            status_color = (0, 255, 0)
                        else:
                            status_message = f"Already Marked Today: {student_name} ({student_id})"
                            status_color = (0, 165, 255)

                        last_student_id = student_id
                        cooldown_counter = 20
                else:
                    status_message = "Face detected but ID not found in database"
                    status_color = (0, 0, 255)
            else:
                status_message = "Unknown Face"
                status_color = (0, 0, 255)

            color = (0, 255, 0) if recognized else (0, 0, 255)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                color,
                2
            )
            cv2.putText(
                frame,
                info,
                (x1, y2 + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

        if cooldown_counter > 0:
            cooldown_counter -= 1

        cv2.rectangle(frame, (10, 10), (900, 55), (40, 40, 40), -1)
        cv2.putText(
            frame,
            status_message,
            (20, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            status_color,
            2
        )

        exit_button_rect = draw_exit_button(frame)
        cv2.imshow("Face Attendance System", frame)

        if cv2.waitKey(1) & 0xFF == ord("q") or exit_clicked:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
