import os
import cv2
import numpy as np

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
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODEL_DIR = os.path.join(BASE_DIR, "trained_model")
MODEL_PATH = os.path.join(MODEL_DIR, "face_model.yml")

CASCADE_PATH = os.path.join(
    BASE_DIR,
    "modules",
    "face_detection",
    "haarcascade_frontalface_default.xml"
)

if not os.path.exists(DATASET_DIR):
    raise FileNotFoundError(f"Dataset folder not found: {DATASET_DIR}")

os.makedirs(MODEL_DIR, exist_ok=True)

face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
if face_cascade.empty():
    raise FileNotFoundError(f"Could not load Haar Cascade from: {CASCADE_PATH}")

if not hasattr(cv2, "face"):
    raise AttributeError(
        "cv2.face is not available. Install opencv-contrib-python."
    )

recognizer = cv2.face.LBPHFaceRecognizer_create()


def extract_student_id(filename):
    name, _ = os.path.splitext(filename)
    parts = name.replace("-", "_").split("_")

    for part in parts:
        if str(part).isdigit():
            return int(part)

    return None


def preprocess_face(gray_img):
    face = cv2.resize(gray_img, (200, 200))
    face = cv2.equalizeHist(face)
    return face


faces = []
labels = []

for image_name in os.listdir(DATASET_DIR):
    if not image_name.lower().endswith((".jpg", ".jpeg", ".png")):
        continue

    student_id = extract_student_id(image_name)
    if student_id is None:
        print(f"Skipping invalid filename: {image_name}")
        continue

    image_path = os.path.join(DATASET_DIR, image_name)
    img = cv2.imread(image_path)
    if img is None:
        print(f"Skipping unreadable image: {image_name}")
        continue

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    detected_faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.2,
        minNeighbors=5,
        minSize=(80, 80)
    )

    if len(detected_faces) == 0:
        print(f"No face found in: {image_name}")
        continue

    x, y, w, h = max(detected_faces, key=lambda f: f[2] * f[3])
    face_roi = gray[y:y + h, x:x + w]
    face_roi = preprocess_face(face_roi)

    faces.append(face_roi)
    labels.append(student_id)

if len(faces) == 0:
    raise ValueError(
        "No valid training faces found. Make sure dataset contains clear face images."
    )

recognizer.train(faces, np.array(labels))
recognizer.write(MODEL_PATH)

print(f"Model trained successfully: {MODEL_PATH}")
print(f"Total training images used: {len(faces)}")
print(f"Total students detected: {len(set(labels))}")