import os
import sqlite3
import pandas as pd
from datetime import datetime

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DATABASE_DIR, "students.db")

ATTENDANCE_DIR = os.path.join(BASE_DIR, "attendance")
ATTENDANCE_CSV = os.path.join(ATTENDANCE_DIR, "attendance.csv")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
ATTENDANCE_COLUMNS = ["Student_ID", "Student_Name", "Date", "Time", "Method"]


# -------------------------------
# CONNECT DATABASE
# -------------------------------
def get_connection():
    os.makedirs(DATABASE_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def ensure_column(cursor, table_name, column_name, column_definition):
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}

    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")


def ensure_attendance_csv():
    os.makedirs(ATTENDANCE_DIR, exist_ok=True)

    if os.path.exists(ATTENDANCE_CSV):
        try:
            df = pd.read_csv(ATTENDANCE_CSV, dtype=str).fillna("")
        except Exception:
            df = pd.DataFrame(columns=ATTENDANCE_COLUMNS)
    else:
        df = pd.DataFrame(columns=ATTENDANCE_COLUMNS)

    for column in ATTENDANCE_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[ATTENDANCE_COLUMNS]
    df.to_csv(ATTENDANCE_CSV, index=False)


# -------------------------------
# INITIALIZE DATABASE
# -------------------------------
def init_database():
    os.makedirs(DATABASE_DIR, exist_ok=True)
    os.makedirs(ATTENDANCE_DIR, exist_ok=True)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            student_name TEXT NOT NULL,
            rfid_uid TEXT,
            fingerprint_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            student_name TEXT,
            date TEXT,
            time TEXT,
            method TEXT
        )
    """)

    # Add fingerprint_id column if database was created before
    ensure_column(cursor, "students", "fingerprint_id", "fingerprint_id INTEGER")
    ensure_column(cursor, "attendance", "method", "method TEXT")

    conn.commit()
    conn.close()

    ensure_attendance_csv()


# -------------------------------
# ADD STUDENT
# -------------------------------
def add_student(student_id, student_name):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO students (student_id, student_name) VALUES (?, ?)",
            (student_id, student_name)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# -------------------------------
# GET STUDENT NAME BY ID
# -------------------------------
def get_student_name(student_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT student_name FROM students WHERE student_id=?",
        (student_id,)
    )

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


# -------------------------------
# LINK RFID TO STUDENT
# -------------------------------
def link_rfid(student_id, rfid_uid):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE students SET rfid_uid=? WHERE student_id=?",
        (rfid_uid, student_id)
    )

    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()

    return changed


# -------------------------------
# REMOVE RFID FROM STUDENT
# -------------------------------
def remove_rfid(student_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE students SET rfid_uid=NULL WHERE student_id=?",
        (student_id,)
    )

    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()

    return changed


# -------------------------------
# GET STUDENT BY RFID
# -------------------------------
def get_student_by_rfid(rfid_uid):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT student_id, student_name FROM students WHERE rfid_uid=?",
        (rfid_uid,)
    )

    result = cursor.fetchone()
    conn.close()

    return result


# -------------------------------
# LINK FINGERPRINT TO STUDENT
# -------------------------------
def link_fingerprint(student_id, fingerprint_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE students SET fingerprint_id=? WHERE student_id=?",
        (fingerprint_id, student_id)
    )

    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()

    return changed


# -------------------------------
# REMOVE FINGERPRINT FROM STUDENT
# -------------------------------
def remove_fingerprint(student_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE students SET fingerprint_id=NULL WHERE student_id=?",
        (student_id,)
    )

    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()

    return changed


# -------------------------------
# GET STUDENT BY FINGERPRINT
# -------------------------------
def get_student_by_fingerprint(fingerprint_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT student_id, student_name FROM students WHERE fingerprint_id=?",
        (fingerprint_id,)
    )

    result = cursor.fetchone()
    conn.close()

    return result


# -------------------------------
# UPDATE STUDENT NAME
# -------------------------------
def update_student_name(student_id, new_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE students SET student_name=? WHERE student_id=?",
        (new_name, student_id)
    )

    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()

    return changed


# -------------------------------
# DELETE STUDENT
# -------------------------------
def delete_student(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    student_id = str(student_id).strip()

    try:
        cursor.execute(
            "SELECT student_id FROM students WHERE student_id=?",
            (student_id,)
        )
        if not cursor.fetchone():
            return False

        cursor.execute(
            "DELETE FROM attendance WHERE student_id=?",
            (student_id,)
        )

        cursor.execute(
            "DELETE FROM students WHERE student_id=?",
            (student_id,)
        )

        deleted = cursor.rowcount > 0
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if os.path.exists(ATTENDANCE_CSV):
        try:
            df = pd.read_csv(ATTENDANCE_CSV)
            if "Student_ID" in df.columns:
                df = df[df["Student_ID"].astype(str) != student_id]
                df.to_csv(ATTENDANCE_CSV, index=False)
        except Exception:
            pass

    if os.path.exists(DATASET_DIR):
        prefix = f"{student_id}_"
        for filename in os.listdir(DATASET_DIR):
            if filename.startswith(prefix):
                try:
                    os.remove(os.path.join(DATASET_DIR, filename))
                except OSError:
                    pass

    return deleted


# -------------------------------
# MARK ATTENDANCE NO DUPLICATE
# -------------------------------
def mark_attendance(student_id, student_name, method="Unknown"):
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    cursor.execute("""
        SELECT * FROM attendance
        WHERE student_id=? AND date=?
    """, (student_id, today))

    already_marked = cursor.fetchone()

    if already_marked:
        conn.close()
        return False

    cursor.execute("""
        INSERT INTO attendance (student_id, student_name, date, time, method)
        VALUES (?, ?, ?, ?, ?)
    """, (
        student_id,
        student_name,
        today,
        current_time,
        method
    ))

    conn.commit()
    conn.close()

    os.makedirs(ATTENDANCE_DIR, exist_ok=True)

    new_row = pd.DataFrame([{
        "Student_ID": student_id,
        "Student_Name": student_name,
        "Date": today,
        "Time": current_time,
        "Method": method
    }])

    if os.path.exists(ATTENDANCE_CSV):
        df = pd.read_csv(ATTENDANCE_CSV, dtype=str).fillna("")
        for column in ATTENDANCE_COLUMNS:
            if column not in df.columns:
                df[column] = ""
        df = df[ATTENDANCE_COLUMNS]
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row

    df[ATTENDANCE_COLUMNS].to_csv(ATTENDANCE_CSV, index=False)
    return True


# -------------------------------
# GET ALL STUDENTS
# -------------------------------
def get_all_students():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT student_id, student_name, rfid_uid, fingerprint_id
        FROM students
        ORDER BY student_id ASC
    """)

    data = cursor.fetchall()

    conn.close()
    return data


# -------------------------------
# GET TODAY ATTENDANCE
# -------------------------------
def get_today_attendance():
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT student_id, student_name, time, method
        FROM attendance
        WHERE date=?
        ORDER BY time ASC
    """, (today,))

    data = cursor.fetchall()

    conn.close()
    return data


# Initialize database when file runs directly
if __name__ == "__main__":
    init_database()
    print("Database initialized successfully.")
