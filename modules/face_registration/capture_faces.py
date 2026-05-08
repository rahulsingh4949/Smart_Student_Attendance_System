import cv2
import os
import sys


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


def preprocess_face(gray_face):
    face = cv2.resize(gray_face, (200, 200))
    face = cv2.equalizeHist(face)
    return face


def draw_exit_button(frame):
    cv2.rectangle(frame, (1050, 10), (1200, 50), (0, 0, 255), -1)
    cv2.putText(
        frame,
        "EXIT",
        (1080, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )


exit_clicked = False


def mouse_callback(event, x, y, flags, param):
    global exit_clicked
    if event == cv2.EVENT_LBUTTONDOWN:
        if 1050 <= x <= 1200 and 10 <= y <= 50:
            exit_clicked = True


if len(sys.argv) < 3:
    print("Usage: python capture_faces.py <ID> <Name>")
    sys.exit(1)

student_id = sys.argv[1].strip()
student_name = sys.argv[2].strip()

if not student_id or not student_name:
    print("Error: Missing ID or Name")
    sys.exit(1)

BASE_DIR = get_base_dir()
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
CASCADE_PATH = os.path.join(
    BASE_DIR,
    "modules",
    "face_detection",
    "haarcascade_frontalface_default.xml"
)

os.makedirs(DATASET_DIR, exist_ok=True)

face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
if face_cascade.empty():
    print(f"Error: Cannot load Haar cascade: {CASCADE_PATH}")
    sys.exit(1)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Cannot open webcam")
    sys.exit(1)

cv2.namedWindow("Capture Faces")
cv2.setMouseCallback("Capture Faces", mouse_callback)

count = 0
MAX_IMAGES = 80
saved_this_frame = False

print("Capturing faces...")
print("Tips: look straight, left, right, slightly up, slightly down.")
print("Press 'q' or click EXIT to stop.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to read frame from camera")
        break

    display_frame = frame.copy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=6,
        minSize=(100, 100)
    )

    saved_this_frame = False

    if len(faces) > 0:
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

        margin_x = int(w * 0.12)
        margin_y = int(h * 0.12)

        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(gray.shape[1], x + w + margin_x)
        y2 = min(gray.shape[0], y + h + margin_y)

        face = gray[y1:y2, x1:x2]
        face = preprocess_face(face)

        if count < MAX_IMAGES:
            count += 1
            filename = os.path.join(DATASET_DIR, f"{student_id}_{count}.jpg")
            cv2.imwrite(filename, face)
            saved_this_frame = True

        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    status_text = f"{student_name} ({student_id})  Saved: {count}/{MAX_IMAGES}"
    status_color = (0, 255, 0) if saved_this_frame else (0, 255, 255)

    cv2.rectangle(display_frame, (10, 10), (930, 55), (40, 40, 40), -1)
    cv2.putText(
        display_frame,
        status_text,
        (20, 42),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        status_color,
        2
    )

    draw_exit_button(display_frame)
    cv2.imshow("Capture Faces", display_frame)

    key = cv2.waitKey(80) & 0xFF
    if key == ord("q") or exit_clicked:
        break

    if count >= MAX_IMAGES:
        break

cap.release()
cv2.destroyAllWindows()
print(f"Face dataset captured successfully for {student_name} ({student_id}).")