import os
import sys
import subprocess
import time
import pandas as pd
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QProcess
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from database.db_helper import (
    init_database,
    add_student,
    get_student_name,
    link_rfid,
    link_fingerprint,
    get_all_students,
    get_today_attendance,
    delete_student,
    remove_rfid,
    remove_fingerprint,
)

IMAGE_DIR = os.path.join(BASE_DIR, "image")
ATTENDANCE_DIR = os.path.join(BASE_DIR, "attendance")
ATTENDANCE_FILE = os.path.join(ATTENDANCE_DIR, "attendance.csv")

UI_ASSETS = {
    "logo": "logo_graduation_cap.png",
    "admin_avatar": "admin_avatar.png",
    "top_calendar": "top_calendar.png",
    "top_bell": "top_bell.png",
    "status_shield": "status_shield.png",
    "nav_dashboard": "nav_dashboard.png",
    "nav_register": "nav_register_student.png",
    "nav_manage": "nav_manage_students.png",
    "nav_attendance": "nav_view_attendance.png",
    "nav_exit": "nav_exit.png",
    "metric_students": "metric_total_students.png",
    "metric_present": "metric_present.png",
    "metric_absent": "metric_absent.png",
    "metric_rate": "metric_attendance_rate.png",
    "sparkline_students": "sparkline_students.png",
    "sparkline_present": "sparkline_present.png",
    "sparkline_absent": "sparkline_absent.png",
    "sparkline_rate": "sparkline_rate.png",
    "card_register": "card_register_student.png",
    "card_face": "card_face_id.png",
    "card_fingerprint": "card_fingerprint.png",
    "card_rfid": "card_rfid.png",
    "card_report": "card_view_reports.png",
    "illustration_report": "illustration_reports.png",
    "card_exit": "card_exit_power.png",
    "illustration_exit": "illustration_exit_door.png",
}


def asset_path(asset_key):
    return os.path.join(IMAGE_DIR, UI_ASSETS[asset_key])

CAPTURE_SCRIPT = os.path.join(BASE_DIR, "modules", "face_registration", "capture_faces.py")
TRAIN_SCRIPT = os.path.join(BASE_DIR, "modules", "face_training", "train_model.py")
RECOGNIZE_SCRIPT = os.path.join(BASE_DIR, "modules", "attendance", "recognize_attendance.py")

FINGERPRINT_SCRIPT = os.path.join(BASE_DIR, "modules", "fingerprint", "fingerprint_attendance.py")
FINGERPRINT_REGISTER_SCRIPT = os.path.join(BASE_DIR, "modules", "fingerprint", "register_fingerprint.py")

RFID_SCRIPT = os.path.join(BASE_DIR, "modules", "rfid", "rfid_attendance.py")
RFID_REGISTER_SCRIPT = os.path.join(BASE_DIR, "modules", "rfid", "register_rfid.py")

os.makedirs(ATTENDANCE_DIR, exist_ok=True)

if not os.path.exists(ATTENDANCE_FILE):
    pd.DataFrame(columns=["Student_ID", "Student_Name", "Date", "Time", "Method"]).to_csv(
        ATTENDANCE_FILE, index=False
    )


def add_shadow(widget, blur=24, x=0, y=6, color=QColor(30, 50, 100, 55)):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(x, y)
    shadow.setColor(color)
    widget.setGraphicsEffect(shadow)


MESSAGE_BOX_STYLE = """
    QMessageBox {
        background:#f7fbff;
    }
    QMessageBox QLabel {
        color:#0d1b3f;
        font-size:14px;
        font-weight:700;
    }
    QMessageBox QPushButton {
        background:#1367f2;
        color:white;
        min-width:96px;
        min-height:36px;
        border:none;
        border-radius:9px;
        padding:7px 16px;
        font-weight:900;
    }
    QMessageBox QPushButton:hover {
        background:#0f53c5;
    }
"""


def show_app_message(parent, title, message, icon=QMessageBox.Information):
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setIcon(icon)
    box.setText(message)
    box.setStyleSheet(MESSAGE_BOX_STYLE)
    box.exec()


class RegisterStudentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Register Student")
        self.setFixedSize(500, 320)
        self.setModal(True)

        self.setStyleSheet("""
            QDialog {
                background:#f7fbff;
            }
            QLabel {
                color:#12346d;
                font-size: 14px;
                font-weight: 800;
            }
            QLineEdit {
                background:white;
                color:#0d1b3f;
                border:1px solid #d8e2f2;
                border-radius:10px;
                padding:12px 14px;
                font-size: 14px;
                font-weight:600;
            }
            QLineEdit:focus {
                border:1px solid #1367f2;
            }
            QPushButton {
                min-width: 112px;
                min-height: 42px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 900;
                padding:8px 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(18)

        title = QLabel("Student Details")
        title.setStyleSheet("font-size:24px; font-weight:900; color:#0d1b3f;")
        layout.addWidget(title)

        subtitle = QLabel("Enter the student ID and full name exactly as you want them stored.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size:13px; font-weight:700; color:#5f6f92;")
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignLeft)

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Enter Student ID")
        self.id_input.setFixedHeight(46)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter Student Name")
        self.name_input.setFixedHeight(46)

        form.addRow("Student ID:", self.id_input)
        form.addRow("Student Name:", self.name_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")

        self.save_btn.setStyleSheet("""
            QPushButton {
                background:#1367f2;
                color:white;
                border:none;
            }
            QPushButton:hover {
                background:#0f53c5;
            }
        """)

        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background:#e7edf7;
                color:#24385f;
                border:none;
            }
            QPushButton:hover {
                background:#d9e3f1;
            }
        """)

        buttons.addButton(self.save_btn, QDialogButtonBox.AcceptRole)
        buttons.addButton(self.cancel_btn, QDialogButtonBox.RejectRole)

        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        layout.addStretch()
        layout.addWidget(buttons)

    def get_data(self):
        return self.id_input.text().strip(), self.name_input.text().strip()


class RegisterOptionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Register Student")
        self.setFixedSize(460, 390)
        self.setModal(True)

        self.selected_option = None

        self.setStyleSheet("""
            QDialog {
                background:#f7fbff;
            }
            QLabel {
                color:#0d1b3f;
                font-size: 22px;
                font-weight: 900;
            }
            QPushButton {
                min-height: 52px;
                border: none;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 900;
                color: white;
                padding:8px 18px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Choose Registration Type")
        layout.addWidget(title)

        subtitle = QLabel("Select which student identity method you want to add.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size:13px; font-weight:700; color:#5f6f92;")
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        self.face_btn = QPushButton("Register Face")
        self.face_btn.setStyleSheet("""
            QPushButton {
                background:qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1367f2, stop:1 #4f86ff);
                color:white;
            }
            QPushButton:hover {
                background:#0f53c5;
            }
        """)
        self.face_btn.clicked.connect(lambda: self.select_option("face"))

        self.rfid_btn = QPushButton("Register RFID")
        self.rfid_btn.setStyleSheet("""
            QPushButton {
                background:qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #a855f7);
                color:white;
            }
            QPushButton:hover {
                background:#682cc8;
            }
        """)
        self.rfid_btn.clicked.connect(lambda: self.select_option("rfid"))

        self.fingerprint_btn = QPushButton("Register Fingerprint")
        self.fingerprint_btn.setStyleSheet("""
            QPushButton {
                background:qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0795e8, stop:1 #38bdf8);
                color:white;
            }
            QPushButton:hover {
                background:#0878bf;
            }
        """)
        self.fingerprint_btn.clicked.connect(lambda: self.select_option("fingerprint"))

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background:#e7edf7;
                color:#24385f;
            }
            QPushButton:hover {
                background:#d9e3f1;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        layout.addWidget(self.face_btn)
        layout.addWidget(self.rfid_btn)
        layout.addWidget(self.fingerprint_btn)
        layout.addStretch()
        layout.addWidget(self.cancel_btn)

    def select_option(self, option):
        self.selected_option = option
        self.accept()


class LoadingDialog(QDialog):
    def __init__(self, title, message, parent=None, animated=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(480, 180)
        self.setModal(True)
        self.base_message = message.rstrip(".")
        self.animation_step = 0

        self.setStyleSheet("""
            QDialog {
                background:#f7fbff;
            }
            QLabel {
                color:#0d1b3f;
                font-size: 15px;
                font-weight: 800;
            }
            QProgressBar {
                border:1px solid #d8e2f2;
                border-radius:6px;
                background:white;
                height:12px;
                text-align: center;
            }
            QProgressBar::chunk {
                background:qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1367f2, stop:1 #38bdf8);
                border-radius:6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(18)

        self.label = QLabel(message)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)

        layout.addStretch()
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addStretch()

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)

        if animated:
            self.start_animation()

    def set_message(self, message):
        self.stop_animation()
        self.base_message = message.rstrip(".")
        self.label.setText(message)

    def start_animation(self, message=None):
        if message:
            self.base_message = message.rstrip(".")
        self.animation_step = 0
        self.update_animation()
        self.animation_timer.start(350)

    def stop_animation(self):
        self.animation_timer.stop()

    def update_animation(self):
        dots = "." * ((self.animation_step % 3) + 1)
        self.label.setText(f"{self.base_message}{dots}")
        self.animation_step += 1


class ConfirmActionDialog(QDialog):
    def __init__(self, title, message, confirm_text="Confirm", danger=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(520, 270)
        self.setModal(True)

        confirm_color = "#ef4444" if danger else "#1367f2"
        confirm_hover = "#dc2626" if danger else "#0f53c5"

        self.setStyleSheet(f"""
            QDialog {{
                background:#f7fbff;
            }}
            QLabel {{
                color:#0d1b3f;
                background: transparent;
            }}
            QPushButton {{
                min-width: 116px;
                min-height: 42px;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 800;
                padding: 8px 16px;
            }}
            QPushButton#cancelButton {{
                background:#e7edf7;
                color:#24385f;
            }}
            QPushButton#cancelButton:hover {{
                background:#d9e3f1;
            }}
            QPushButton#confirmButton {{
                background: {confirm_color};
                color: white;
            }}
            QPushButton#confirmButton:hover {{
                background: {confirm_hover};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 26)
        layout.setSpacing(16)

        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size:22px; font-weight:900;")

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size:14px; font-weight:700; color:#5f6f92;")

        layout.addWidget(title_label)
        layout.addWidget(message_label)
        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelButton")
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setObjectName("confirmButton")
        confirm_btn.clicked.connect(self.accept)

        buttons.addWidget(cancel_btn)
        buttons.addWidget(confirm_btn)
        layout.addLayout(buttons)


class ManageStudentsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Students")
        self.resize(980, 580)
        self.setModal(True)

        self.setStyleSheet("""
            QDialog {
                background:#f7fbff;
            }
            QLabel {
                color:#0d1b3f;
                font-size:18px;
                font-weight:900;
            }
            QTableWidget {
                background:white;
                alternate-background-color:#f8fbff;
                color:#0d1b3f;
                border:1px solid #d8e2f2;
                border-radius:10px;
                gridline-color:#e3eaf5;
                font-size:13px;
                selection-background-color:#e8f1ff;
                selection-color:#0d1b3f;
            }
            QHeaderView::section {
                background:#edf4ff;
                color:#12346d;
                padding:10px;
                border:none;
                border-bottom:1px solid #d8e2f2;
                font-weight:900;
            }
            QPushButton {
                min-height:40px;
                border:none;
                border-radius:9px;
                font-size:13px;
                font-weight:900;
                color:white;
                padding:8px 14px;
            }
            QPushButton:disabled {
                background:#cbd5e1;
                color:#f8fafc;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)

        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(4)

        title = QLabel("Manage Students")
        title.setStyleSheet("font-size:22px; font-weight:900; color:#0d1b3f;")
        subtitle = QLabel("Review students and remove linked RFID or fingerprint records.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size:13px; font-weight:700; color:#5f6f92;")
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)
        header.addLayout(title_wrap, 1)

        self.summary_label = QLabel("")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setStyleSheet("""
            QLabel {
                background:#edf4ff;
                color:#155ee8;
                border:1px solid #c7d9ff;
                border-radius:10px;
                padding:10px 16px;
                font-size:13px;
                font-weight:900;
            }
        """)
        header.addWidget(self.summary_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Student ID", "Student Name", "RFID UID", "Fingerprint ID"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet("background:#1367f2;")

        self.delete_btn = QPushButton("Delete Student")
        self.delete_btn.setStyleSheet("background:#ef4444;")

        self.remove_rfid_btn = QPushButton("Remove RFID")
        self.remove_rfid_btn.setStyleSheet("background:#7c3aed;")

        self.remove_fingerprint_btn = QPushButton("Remove Fingerprint")
        self.remove_fingerprint_btn.setStyleSheet("background:#0795e8;")

        self.close_btn = QPushButton("Close")
        self.close_btn.setStyleSheet("background:#6b7280;")

        self.delete_btn.setEnabled(False)
        self.remove_rfid_btn.setEnabled(False)
        self.remove_fingerprint_btn.setEnabled(False)

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.remove_rfid_btn)
        btn_layout.addWidget(self.remove_fingerprint_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

        self.refresh_btn.clicked.connect(self.load_students)
        self.delete_btn.clicked.connect(self.delete_selected_student)
        self.remove_rfid_btn.clicked.connect(self.remove_selected_rfid)
        self.remove_fingerprint_btn.clicked.connect(self.remove_selected_fingerprint)
        self.close_btn.clicked.connect(self.close)
        self.table.itemSelectionChanged.connect(self.update_action_buttons)

        self.load_students()

    def load_students(self):
        students = get_all_students()
        self.table.clearSelection()
        self.table.setRowCount(len(students))

        for row, (student_id, student_name, rfid_uid, fingerprint_id) in enumerate(students):
            values = [
                str(student_id),
                student_name,
                rfid_uid if rfid_uid else "",
                str(fingerprint_id) if fingerprint_id is not None else "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter if column != 1 else Qt.AlignVCenter)
                self.table.setItem(row, column, item)

        self.summary_label.setText(f"{len(students)} Student(s)")
        self.update_action_buttons()

    def update_action_buttons(self):
        has_selection = self.get_selected_student_id() is not None
        self.delete_btn.setEnabled(has_selection)
        self.remove_rfid_btn.setEnabled(has_selection)
        self.remove_fingerprint_btn.setEnabled(has_selection)

    def get_selected_row(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            return selected_rows[0].row()

        row = self.table.currentRow()
        if row < 0:
            return None
        return row

    def get_selected_student_id(self):
        row = self.get_selected_row()
        if row is None:
            return None

        item = self.table.item(row, 0)
        return item.text() if item else None

    def get_selected_student_name(self):
        row = self.get_selected_row()
        if row is None:
            return ""

        item = self.table.item(row, 1)
        return item.text() if item else ""

    def delete_selected_student(self):
        student_id = self.get_selected_student_id()
        student_name = self.get_selected_student_name()

        if not student_id:
            show_app_message(self, "No Selection", "Please select a student first.", QMessageBox.Warning)
            return

        display_name = f"{student_name} (ID {student_id})" if student_name else f"ID {student_id}"

        confirm = ConfirmActionDialog(
            f"Delete {display_name}?",
            "This will remove the student, attendance records, and saved face images.",
            confirm_text="Delete",
            danger=True,
            parent=self,
        )

        if confirm.exec() == QDialog.Accepted:
            try:
                deleted = delete_student(student_id)
                if deleted:
                    show_app_message(self, "Deleted", "Student deleted successfully.")
                else:
                    show_app_message(
                        self,
                        "Not Found",
                        "Student could not be deleted.",
                        QMessageBox.Warning,
                    )
                self.load_students()
            except Exception as e:
                show_app_message(
                    self,
                    "Delete Error",
                    f"Could not delete student.\n\n{e}",
                    QMessageBox.Critical,
                )

    def remove_selected_rfid(self):
        student_id = self.get_selected_student_id()

        if not student_id:
            show_app_message(self, "No Selection", "Please select a student first.", QMessageBox.Warning)
            return

        confirm = ConfirmActionDialog(
            "Remove RFID?",
            f"Remove RFID from student ID {student_id}?",
            confirm_text="Remove",
            parent=self,
        )

        if confirm.exec() == QDialog.Accepted:
            remove_rfid(student_id)
            show_app_message(self, "Success", "RFID removed successfully.")
            self.load_students()

    def remove_selected_fingerprint(self):
        student_id = self.get_selected_student_id()

        if not student_id:
            show_app_message(self, "No Selection", "Please select a student first.", QMessageBox.Warning)
            return

        confirm = ConfirmActionDialog(
            "Remove Fingerprint?",
            f"Remove fingerprint from student ID {student_id}?",
            confirm_text="Remove",
            parent=self,
        )

        if confirm.exec() == QDialog.Accepted:
            remove_fingerprint(student_id)
            show_app_message(self, "Success", "Fingerprint removed successfully.")
            self.load_students()


class AttendanceReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("View Attendance")
        self.resize(1040, 620)
        self.setModal(True)

        self.setStyleSheet("""
            QDialog {
                background:#f7fbff;
            }
            QLabel {
                background:transparent;
                border:none;
            }
            QTableWidget {
                background:white;
                alternate-background-color:#f8fbff;
                color:#0d1b3f;
                border:1px solid #d8e2f2;
                border-radius:10px;
                gridline-color:#e3eaf5;
                font-size:13px;
                selection-background-color:#e8f1ff;
                selection-color:#0d1b3f;
            }
            QHeaderView::section {
                background:#edf4ff;
                color:#12346d;
                padding:9px;
                border:none;
                border-bottom:1px solid #d8e2f2;
                font-weight:900;
            }
            QPushButton {
                min-height:40px;
                border:none;
                border-radius:9px;
                font-size:13px;
                font-weight:800;
                color:white;
                padding:8px 16px;
            }
            QPushButton:disabled {
                background:#cbd5e1;
                color:#f8fafc;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)

        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(4)

        title = QLabel("Attendance Records")
        title.setStyleSheet("""
            color:#0d1b3f;
            font-size:22px;
            font-weight:900;
        """)

        subtitle = QLabel("All attendance entries are shown here inside the software.")
        subtitle.setStyleSheet("""
            color:#5f6f92;
            font-size:14px;
            font-weight:600;
        """)

        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)
        header.addLayout(title_wrap, 1)

        self.summary_label = QLabel("")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setStyleSheet("""
            QLabel {
                background:#edf4ff;
                color:#155ee8;
                border:1px solid #c7d9ff;
                border-radius:10px;
                padding:10px 16px;
                font-size:13px;
                font-weight:900;
            }
        """)
        header.addWidget(self.summary_label, 0, Qt.AlignRight | Qt.AlignVCenter)

        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Student ID", "Student Name", "Date", "Time", "Method"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        layout.addWidget(self.table, 1)

        footer = QHBoxLayout()
        footer.setSpacing(12)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            color:#5f6f92;
            font-size:13px;
            font-weight:700;
        """)
        footer.addWidget(self.status_label, 1)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background:#1367f2;
            }
            QPushButton:hover {
                background:#0f53c5;
            }
        """)

        self.close_btn = QPushButton("Close")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background:#6b7280;
            }
            QPushButton:hover {
                background:#4b5563;
            }
        """)

        footer.addWidget(self.refresh_btn)
        footer.addWidget(self.close_btn)
        layout.addLayout(footer)

        self.refresh_btn.clicked.connect(self.load_attendance)
        self.close_btn.clicked.connect(self.close)
        self.load_attendance()

    def load_attendance(self):
        columns = ["Student_ID", "Student_Name", "Date", "Time", "Method"]

        if not os.path.exists(ATTENDANCE_FILE):
            df = pd.DataFrame(columns=columns)
        else:
            try:
                df = pd.read_csv(ATTENDANCE_FILE, dtype=str).fillna("")
            except Exception as e:
                show_app_message(
                    self,
                    "Attendance Error",
                    f"Could not load attendance file.\n\n{e}",
                    QMessageBox.Critical,
                )
                return

        for column in columns:
            if column not in df.columns:
                df[column] = ""

        df = df[columns].copy()
        if not df.empty:
            df = df.sort_values(by=["Date", "Time"], ascending=[False, False])

        self.table.setRowCount(len(df))
        for row, record in enumerate(df.itertuples(index=False)):
            values = [
                record.Student_ID,
                record.Student_Name,
                record.Date,
                record.Time,
                record.Method,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter if column in (0, 2, 3, 4) else Qt.AlignVCenter)
                self.table.setItem(row, column, item)

        today = datetime.now().strftime("%Y-%m-%d")
        today_count = 0
        if not df.empty:
            today_count = len(df[df["Date"].astype(str) == today])

        self.summary_label.setText(f"{len(df)} Total Records")
        self.status_label.setText(f"{today_count} attendance record(s) for today")


class ImageIconWidget(QWidget):
    def __init__(self, image_path, max_size=100, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.max_size = max_size

        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background: transparent; border: none;")
        self.label.setFixedSize(max_size + 8, max_size + 8)

        layout.addWidget(self.label)
        self.load_pixmap()

    def load_pixmap(self):
        if self.image_path and os.path.exists(self.image_path):
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.max_size,
                    self.max_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.label.setPixmap(scaled)
                return

        self.label.setText("")
        self.label.setStyleSheet("""
            color:#15357d;
            font-size:14px;
            font-weight:700;
            background: transparent;
            border: none;
        """)


class ActionButton(QPushButton):
    def __init__(self, text, bg, hover, fg="white", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(42)
        self.setStyleSheet(f"""
            QPushButton {{
                background:{bg};
                color:{fg};
                border:none;
                border-radius:10px;
                font-size:14px;
                font-weight:800;
                padding:8px 16px;
            }}
            QPushButton:hover {{
                background:{hover};
            }}
            QPushButton:pressed {{
                padding-top:9px;
            }}
        """)


class IconBox(QFrame):
    def __init__(self, image_path, tint, size=74, icon_size=48, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setObjectName("iconBox")
        self.setStyleSheet(f"""
            QFrame#iconBox {{
                background:{tint};
                border:none;
                border-radius:14px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setAlignment(Qt.AlignCenter)

        icon = ImageIconWidget(image_path, max_size=icon_size)
        layout.addWidget(icon, 0, Qt.AlignCenter)


class MetricCard(QFrame):
    def __init__(
        self,
        title,
        value,
        detail,
        image_path,
        accent,
        tint,
        sparkline_path=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setMinimumHeight(150)
        self.setMaximumHeight(156)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(f"""
            QFrame#metricCard {{
                background:white;
                border:1px solid {accent};
                border-radius:12px;
            }}
            QLabel {{
                background:transparent;
                border:none;
            }}
        """)
        add_shadow(self, blur=22, x=0, y=8, color=QColor(25, 52, 110, 28))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 15, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(IconBox(image_path, tint, size=60, icon_size=36), 0, Qt.AlignTop)

        text = QVBoxLayout()
        text.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.title_label.setStyleSheet("""
            color:#27365d;
            font-size:12px;
            font-weight:800;
        """)

        self.value_label = QLabel(value)
        self.value_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.value_label.setStyleSheet(f"""
            color:{accent};
            font-size:25px;
            font-weight:900;
        """)

        self.detail_label = QLabel(detail)
        self.detail_label.setWordWrap(True)
        self.detail_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.detail_label.setStyleSheet("""
            color:#16a063;
            font-size:11px;
            font-weight:800;
        """)

        text.addWidget(self.title_label)
        text.addWidget(self.value_label)
        text.addWidget(self.detail_label)
        text.addStretch()

        layout.addLayout(text, 1)

        if sparkline_path:
            chart = ImageIconWidget(sparkline_path, max_size=58)
            chart.setFixedWidth(62)
            layout.addWidget(chart, 0, Qt.AlignRight | Qt.AlignBottom)

    def set_values(self, value, detail):
        self.value_label.setText(value)
        self.detail_label.setText(detail)


class TopCard(QFrame):
    def __init__(
        self,
        title,
        subtitle,
        image_path,
        button_text,
        accent1,
        accent2,
        button_bg,
        button_hover,
        bottom_tint,
        icon_size=100,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("actionCard")
        self.setMinimumHeight(280)
        self.setMaximumHeight(292)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame#actionCard {
                background:white;
                border:1px solid #d8e2f2;
                border-radius:12px;
            }
            QLabel {
                background:transparent;
                border:none;
            }
        """)
        add_shadow(self, blur=24, x=0, y=9, color=QColor(24, 46, 95, 32))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(IconBox(image_path, bottom_tint, size=82, icon_size=icon_size))
        top.addStretch()

        self.arrow_button = QPushButton("->")
        self.arrow_button.setCursor(Qt.PointingHandCursor)
        self.arrow_button.setFixedSize(34, 34)
        self.arrow_button.setStyleSheet(f"""
            QPushButton {{
                background:{bottom_tint};
                color:{button_bg};
                border:none;
                border-radius:10px;
                font-size:16px;
                font-weight:900;
            }}
            QPushButton:hover {{
                background:#eaf1ff;
            }}
        """)
        top.addWidget(self.arrow_button, 0, Qt.AlignTop)
        layout.addLayout(top)

        title_label = QLabel(title.replace("\n", " "))
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"""
            color:{button_bg};
            font-size:17px;
            font-weight:900;
        """)

        subtitle_label = QLabel(subtitle.replace("\n", " "))
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("""
            color:#65728f;
            font-size:13px;
            font-weight:600;
            line-height:1.35;
        """)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addStretch()

        self.button = ActionButton(
            f"{button_text}   ->",
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {button_bg}, stop:1 {accent2})",
            button_hover,
        )
        self.button.setMinimumHeight(48)
        layout.addWidget(self.button)
        self.arrow_button.clicked.connect(self.button.click)


class ReportCard(QFrame):
    def __init__(self, image_path, illustration_path):
        super().__init__()
        self.setObjectName("reportCard")
        self.setMinimumHeight(198)
        self.setMaximumHeight(210)
        self.setStyleSheet("""
            QFrame#reportCard {
                background:#f6faff;
                border:1px solid #bed7ff;
                border-radius:12px;
            }
            QLabel {
                background:transparent;
                border:none;
            }
        """)
        add_shadow(self, blur=22, x=0, y=8, color=QColor(28, 64, 130, 26))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        layout.addWidget(IconBox(image_path, "#e9f1ff", size=78, icon_size=50))

        text = QVBoxLayout()
        text.setSpacing(8)

        title = QLabel("View Attendance")
        title.setStyleSheet("""
            color:#0d3a8f;
            font-size:19px;
            font-weight:900;
        """)

        sub = QLabel("Check attendance records and generate detailed reports.")
        sub.setWordWrap(True)
        sub.setStyleSheet("""
            color:#5f6f92;
            font-size:13px;
            font-weight:600;
        """)

        self.button = ActionButton(
            "View Reports   ->",
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3165f4, stop:1 #1266df)",
            "#1551c8",
        )
        self.button.setFixedWidth(176)

        text.addStretch()
        text.addWidget(title)
        text.addWidget(sub)
        text.addSpacing(12)
        text.addWidget(self.button, 0, Qt.AlignLeft)
        text.addStretch()

        layout.addLayout(text, 1)

        side_art = ImageIconWidget(illustration_path, max_size=126)
        side_art.setFixedWidth(140)
        layout.addWidget(side_art, 0, Qt.AlignRight | Qt.AlignVCenter)


class ExitCard(QFrame):
    def __init__(self, image_path, illustration_path):
        super().__init__()
        self.setObjectName("exitCard")
        self.setMinimumHeight(198)
        self.setMaximumHeight(210)
        self.setStyleSheet("""
            QFrame#exitCard {
                background:#fff7f7;
                border:1px solid #ffc7cd;
                border-radius:12px;
            }
            QLabel {
                background:transparent;
                border:none;
            }
        """)
        add_shadow(self, blur=22, x=0, y=8, color=QColor(130, 26, 39, 20))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        layout.addWidget(IconBox(image_path, "#ffe4e8", size=78, icon_size=50))

        text = QVBoxLayout()
        text.setSpacing(8)

        title = QLabel("Exit System")
        title.setStyleSheet("""
            color:#df252f;
            font-size:19px;
            font-weight:900;
        """)

        sub = QLabel("Close the application safely.")
        sub.setWordWrap(True)
        sub.setStyleSheet("""
            color:#5f6f92;
            font-size:13px;
            font-weight:600;
        """)

        self.button = ActionButton(
            "Exit Application   ->",
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #f43f5e)",
            "#d9283a",
        )
        self.button.setFixedWidth(190)

        text.addStretch()
        text.addWidget(title)
        text.addWidget(sub)
        text.addSpacing(12)
        text.addWidget(self.button, 0, Qt.AlignLeft)
        text.addStretch()

        layout.addLayout(text, 1)

        side_art = ImageIconWidget(illustration_path, max_size=128)
        side_art.setFixedWidth(140)
        layout.addWidget(side_art, 0, Qt.AlignRight | Qt.AlignVCenter)


class SidebarButton(QPushButton):
    def __init__(self, text, icon_path=None, active=False, parent=None):
        super().__init__(parent)
        self.btn_text = text
        self.icon_path = icon_path
        self.active = active

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 18, 0)
        layout.setSpacing(14)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setAlignment(Qt.AlignCenter)

        if self.icon_path and os.path.exists(self.icon_path):
            pixmap = QPixmap(self.icon_path)
            if not pixmap.isNull():
                self.icon_label.setPixmap(
                    pixmap.scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )

        self.text_label = QLabel(self.btn_text)
        self.text_label.setStyleSheet("""
            color:white;
            font-size:16px;
            font-weight:800;
            background:transparent;
            border:none;
        """)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()

        self.update_style()

    def set_active(self, value: bool):
        self.active = value
        self.update_style()

    def update_style(self):
        if self.active:
            self.setStyleSheet("""
                QPushButton {
                    background:qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #0f62fe,
                        stop:1 #0756d8
                    );
                    border:1px solid #2b83ff;
                    border-radius:12px;
                }
            """)
            self.icon_label.setStyleSheet("""
                QLabel {
                    background:#2b88ff;
                    border:none;
                    border-radius:10px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background:transparent;
                    border:1px solid transparent;
                    border-radius:12px;
                }
                QPushButton:hover {
                    background:rgba(255,255,255,0.07);
                }
            """)
            self.icon_label.setStyleSheet("""
                QLabel {
                    background:rgba(255,255,255,0.11);
                    border:none;
                    border-radius:10px;
                }
            """)


class TopBar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("topBar")
        self.setFixedHeight(100)
        self.setStyleSheet("""
            QFrame#topBar {
                background:white;
                border:none;
                border-bottom:1px solid #dfe7f3;
            }
            QLabel {
                background:transparent;
                border:none;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 14, 32, 14)
        layout.setSpacing(20)

        self.menu_button = QPushButton("☰")
        self.menu_button.setCursor(Qt.PointingHandCursor)
        self.menu_button.setFixedSize(52, 52)
        self.menu_button.setStyleSheet("""
            QPushButton {
                background:#edf4ff;
                color:#1266e3;
                border:none;
                border-radius:12px;
                font-size:24px;
                font-weight:900;
            }
            QPushButton:hover {
                background:#e1edff;
            }
        """)

        title = QLabel("Dashboard")
        title.setStyleSheet("""
            color:#0d1b3f;
            font-size:22px;
            font-weight:900;
        """)

        layout.addWidget(self.menu_button)
        layout.addWidget(title)
        layout.addStretch()

        calendar_icon = ImageIconWidget(asset_path("top_calendar"), max_size=22)
        calendar_icon.setFixedWidth(28)
        layout.addWidget(calendar_icon)

        self.date_label = QLabel("")
        self.date_label.setStyleSheet("""
            color:#24385f;
            font-size:14px;
            font-weight:700;
        """)
        layout.addWidget(self.date_label)

        divider = QFrame()
        divider.setFixedSize(1, 36)
        divider.setStyleSheet("background:#d8e0ed; border:none;")
        layout.addWidget(divider)

        bell = ImageIconWidget(asset_path("top_bell"), max_size=32)
        bell.setFixedSize(38, 38)
        layout.addWidget(bell)

        avatar = QLabel()
        avatar.setFixedSize(54, 54)
        avatar.setStyleSheet("""
            background:#eaf7ef;
            border:2px solid #16b76b;
            border-radius:27px;
        """)

        avatar_path = asset_path("admin_avatar")
        if os.path.exists(avatar_path):
            pixmap = QPixmap(avatar_path)
            if not pixmap.isNull():
                avatar.setPixmap(
                    pixmap.scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                avatar.setAlignment(Qt.AlignCenter)
        layout.addWidget(avatar)

        admin_text = QVBoxLayout()
        admin_text.setSpacing(1)
        admin_name = QLabel("Admin")
        admin_name.setStyleSheet("""
            color:#0d1b3f;
            font-size:14px;
            font-weight:900;
        """)
        role = QLabel("Administrator")
        role.setStyleSheet("""
            color:#73809d;
            font-size:12px;
            font-weight:700;
        """)
        admin_text.addWidget(admin_name)
        admin_text.addWidget(role)
        layout.addLayout(admin_text)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_datetime)
        self.timer.start(60000)
        self.update_datetime()

    def update_datetime(self):
        self.date_label.setText(datetime.now().strftime("%A, %B %d, %Y"))


class StatusCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("statusCard")
        self.setFixedHeight(138)
        self.setStyleSheet("""
            QFrame#statusCard {
                background:rgba(15, 84, 185, 0.30);
                border:1px solid rgba(87, 151, 255, 0.38);
                border-radius:14px;
            }
            QLabel {
                background:transparent;
                border:none;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 18, 20, 18)
        layout.setSpacing(14)

        text = QVBoxLayout()
        text.setSpacing(4)

        line = QLabel("●  System Status")
        line.setStyleSheet("""
            color:#dfeaff;
            font-size:13px;
            font-weight:700;
        """)
        online = QLabel("All Systems Online")
        online.setStyleSheet("""
            color:#20e083;
            font-size:18px;
            font-weight:900;
        """)
        sub = QLabel("Everything is working perfectly.")
        sub.setWordWrap(True)
        sub.setStyleSheet("""
            color:#d6e2ff;
            font-size:12px;
            font-weight:600;
        """)

        text.addStretch()
        text.addWidget(line)
        text.addWidget(online)
        text.addWidget(sub)
        text.addStretch()

        layout.addLayout(text, 1)

        shield = ImageIconWidget(asset_path("status_shield"), max_size=58)
        shield.setFixedSize(64, 64)
        layout.addWidget(shield)


class Sidebar(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(300)
        self.setObjectName("sidebar")
        self.setStyleSheet("""
            QFrame#sidebar {
                background:qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #061d4b,
                    stop:0.48 #05245c,
                    stop:1 #031539
                );
                border:none;
            }
            QLabel {
                background:transparent;
                color:white;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 26, 22, 24)
        layout.setSpacing(18)

        header = QWidget()
        header.setStyleSheet("background:transparent; border:none;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(14)

        logo = QLabel()
        logo.setFixedSize(72, 64)
        logo.setStyleSheet("background:transparent; border:none;")
        hat_logo = asset_path("logo")
        if os.path.exists(hat_logo):
            pixmap = QPixmap(hat_logo)
            if not pixmap.isNull():
                logo.setPixmap(
                    pixmap.scaled(66, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )

        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(4)
        title = QLabel("Student Attendance")
        title.setStyleSheet("""
            font-size:17px;
            font-weight:900;
            color:white;
        """)
        subtitle = QLabel("System")
        subtitle.setStyleSheet("""
            font-size:14px;
            font-weight:600;
            color:#d8e6ff;
        """)
        title_wrap.addStretch()
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)
        title_wrap.addStretch()

        header_layout.addWidget(logo)
        header_layout.addLayout(title_wrap, 1)
        layout.addWidget(header)
        layout.addSpacing(28)

        home_icon = asset_path("nav_dashboard")
        man_icon = asset_path("nav_register")
        settings_icon = asset_path("nav_manage")
        copy_icon = asset_path("nav_attendance")
        exit_icon = asset_path("nav_exit")

        self.btn_dashboard = SidebarButton("Dashboard", home_icon, active=True)
        self.btn_register = SidebarButton("Register Student", man_icon)
        self.btn_manage = SidebarButton("Manage Students", settings_icon)
        self.btn_view = SidebarButton("View Attendance", copy_icon)
        self.btn_exit = SidebarButton("Exit", exit_icon)

        for button in (
            self.btn_dashboard,
            self.btn_register,
            self.btn_manage,
            self.btn_view,
            self.btn_exit,
        ):
            layout.addWidget(button)

        layout.addStretch()
        layout.addWidget(StatusCard())

        self.all_buttons = [
            self.btn_dashboard,
            self.btn_register,
            self.btn_manage,
            self.btn_view,
            self.btn_exit,
        ]

    def set_active(self, button):
        for btn in self.all_buttons:
            btn.set_active(btn is button)


class MainDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        init_database()

        self.capture_process = None
        self.train_process = None
        self.loading_dialog = None
        self.current_student_id = None
        self.current_student_name = None
        self.sidebar_expanded = True

        self.setWindowTitle("Student Attendance System")
        self.resize(1536, 960)
        self.setMinimumSize(1280, 820)

        register_logo = asset_path("card_register")
        face_logo = asset_path("card_face")
        fingerprint_logo = asset_path("card_fingerprint")
        rfid_logo = asset_path("card_rfid")
        report_logo = asset_path("card_report")
        report_illustration = asset_path("illustration_report")
        exit_logo = asset_path("card_exit")
        exit_illustration = asset_path("illustration_exit")
        student_logo = asset_path("metric_students")
        present_logo = asset_path("metric_present")
        absent_logo = asset_path("metric_absent")
        rate_logo = asset_path("metric_rate")

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        self.topbar = TopBar()
        right.addWidget(self.topbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background:#f7fbff;
                border:none;
            }
            QScrollArea > QWidget > QWidget {
                background:#f7fbff;
            }
            QScrollBar:vertical {
                background:#eef4fb;
                width:10px;
                margin:0px;
            }
            QScrollBar::handle:vertical {
                background:#c4d3e8;
                border-radius:5px;
                min-height:40px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height:0px;
            }
        """)

        content_bg = QWidget()
        content_bg.setStyleSheet("""
            QWidget {
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fbfdff,
                    stop:0.55 #f6faff,
                    stop:1 #f9fbff
                );
            }
        """)

        outer = QVBoxLayout(content_bg)
        outer.setContentsMargins(24, 28, 24, 32)
        outer.setSpacing(24)

        welcome_row = QHBoxLayout()
        welcome_row.setSpacing(18)

        welcome_text = QVBoxLayout()
        welcome_text.setSpacing(6)

        title = QLabel("Welcome back, Admin!")
        title.setStyleSheet("""
            color:#0d1b3f;
            font-size:24px;
            font-weight:900;
            background:transparent;
        """)

        sub = QLabel("Here's what's happening with your attendance system today.")
        sub.setStyleSheet("""
            color:#5f6f92;
            font-size:15px;
            font-weight:600;
            background:transparent;
        """)

        welcome_text.addWidget(title)
        welcome_text.addWidget(sub)
        welcome_row.addLayout(welcome_text, 1)

        academic_year = QLabel("Academic Year: 2025-2026")
        academic_year.setAlignment(Qt.AlignCenter)
        academic_year.setStyleSheet("""
            QLabel {
                background:#f7fbff;
                color:#155ee8;
                border:1px solid #c7d9ff;
                border-radius:12px;
                padding:12px 20px;
                font-size:14px;
                font-weight:900;
            }
        """)
        welcome_row.addWidget(academic_year, 0, Qt.AlignRight | Qt.AlignVCenter)
        outer.addLayout(welcome_row)

        total_students, today_present, today_absent, attendance_rate = self.get_dashboard_metrics()

        metrics_grid = QGridLayout()
        metrics_grid.setHorizontalSpacing(14)
        metrics_grid.setVerticalSpacing(14)

        self.total_metric = MetricCard(
            "Total Students",
            f"{total_students:,}",
            "Registered students",
            student_logo,
            "#2563eb",
            "#eaf2ff",
            sparkline_path=asset_path("sparkline_students"),
        )
        self.present_metric = MetricCard(
            "Today's Present",
            f"{today_present:,}",
            "Marked attendance",
            present_logo,
            "#059669",
            "#e8f8ef",
            sparkline_path=asset_path("sparkline_present"),
        )
        self.absent_metric = MetricCard(
            "Today's Absent",
            f"{today_absent:,}",
            "Pending attendance",
            absent_logo,
            "#f97316",
            "#fff1e7",
            sparkline_path=asset_path("sparkline_absent"),
        )
        self.rate_metric = MetricCard(
            "Attendance Rate",
            f"{attendance_rate:.2f}%",
            "Present today",
            rate_logo,
            "#7c3aed",
            "#f3e8ff",
            sparkline_path=asset_path("sparkline_rate"),
        )

        for index, card in enumerate(
            (
                self.total_metric,
                self.present_metric,
                self.absent_metric,
                self.rate_metric,
            )
        ):
            metrics_grid.addWidget(card, 0, index)
            metrics_grid.setColumnStretch(index, 1)

        outer.addLayout(metrics_grid)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        self.register_card = TopCard(
            "Register Student",
            "Add new students to the attendance system.",
            register_logo,
            "+ Register Student",
            "#0fba72",
            "#18c964",
            "#05a857",
            "#078846",
            "#e9f8ef",
            icon_size=54,
        )

        self.face_card = TopCard(
            "Face ID Attendance",
            "Mark attendance using facial recognition.",
            face_logo,
            "Scan Face",
            "#2563eb",
            "#4f86ff",
            "#1367f2",
            "#0f53c5",
            "#edf4ff",
            icon_size=54,
        )

        self.fingerprint_card = TopCard(
            "Fingerprint Attendance",
            "Record attendance via fingerprint scan.",
            fingerprint_logo,
            "Scan Fingerprint",
            "#0ea5e9",
            "#38bdf8",
            "#0795e8",
            "#0878bf",
            "#e8f8ff",
            icon_size=54,
        )

        self.rfid_card = TopCard(
            "RFID Attendance",
            "Use RFID cards to mark attendance.",
            rfid_logo,
            "Scan RFID Card",
            "#7c3aed",
            "#a855f7",
            "#7c3aed",
            "#682cc8",
            "#f3eafe",
            icon_size=54,
        )

        grid.addWidget(self.register_card, 0, 0)
        grid.addWidget(self.face_card, 0, 1)
        grid.addWidget(self.fingerprint_card, 0, 2)
        grid.addWidget(self.rfid_card, 0, 3)

        for column in range(4):
            grid.setColumnStretch(column, 1)

        outer.addLayout(grid)

        bottom = QGridLayout()
        bottom.setHorizontalSpacing(16)
        bottom.setVerticalSpacing(16)

        self.report_card = ReportCard(report_logo, report_illustration)
        self.exit_card = ExitCard(exit_logo, exit_illustration)

        bottom.addWidget(self.report_card, 0, 0)
        bottom.addWidget(self.exit_card, 0, 1)
        bottom.setColumnStretch(0, 1)
        bottom.setColumnStretch(1, 1)

        outer.addLayout(bottom)
        outer.addStretch()

        scroll.setWidget(content_bg)
        right.addWidget(scroll, 1)
        root.addLayout(right, 1)

        self.sidebar.btn_dashboard.clicked.connect(
            lambda: self.sidebar.set_active(self.sidebar.btn_dashboard)
        )
        self.topbar.menu_button.clicked.connect(self.toggle_sidebar)
        self.sidebar.btn_register.clicked.connect(self.register_student)
        self.sidebar.btn_manage.clicked.connect(self.open_manage_students)
        self.sidebar.btn_view.clicked.connect(self.view_reports)
        self.sidebar.btn_exit.clicked.connect(self.close_app)

        self.register_card.button.clicked.connect(self.register_student)
        self.face_card.button.clicked.connect(self.face_attendance)
        self.fingerprint_card.button.clicked.connect(self.fingerprint_attendance)
        self.rfid_card.button.clicked.connect(self.rfid_attendance)
        self.report_card.button.clicked.connect(self.view_reports)
        self.exit_card.button.clicked.connect(self.close_app)

    def toggle_sidebar(self):
        self.sidebar_expanded = not self.sidebar_expanded
        self.sidebar.setVisible(self.sidebar_expanded)

    def get_dashboard_metrics(self):
        try:
            total_students = len(get_all_students())
        except Exception:
            total_students = 0

        try:
            today_rows = get_today_attendance()
            today_present = len({str(row[0]) for row in today_rows})
        except Exception:
            today_present = 0

        today_absent = max(total_students - today_present, 0)
        attendance_rate = (today_present / total_students * 100) if total_students else 0

        return total_students, today_present, today_absent, attendance_rate

    def refresh_dashboard_metrics(self):
        if not hasattr(self, "total_metric"):
            return

        total_students, today_present, today_absent, attendance_rate = self.get_dashboard_metrics()
        self.total_metric.set_values(f"{total_students:,}", "Registered students")
        self.present_metric.set_values(f"{today_present:,}", "Marked attendance")
        self.absent_metric.set_values(f"{today_absent:,}", "Pending attendance")
        self.rate_metric.set_values(f"{attendance_rate:.2f}%", "Present today")

    def show_error(self, title, message):
        show_app_message(self, title, message, QMessageBox.Critical)

    def show_info(self, title, message):
        show_app_message(self, title, message, QMessageBox.Information)

    def run_python_script(self, script_path, args=None):
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found:\n{script_path}")

        command = [sys.executable, os.path.abspath(script_path)]
        if args:
            command.extend(args)

        subprocess.run(command, check=True, cwd=BASE_DIR)

    def run_python_script_with_loading(self, script_path, loading, args=None, timeout=30):
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found:\n{script_path}")

        command = [sys.executable, os.path.abspath(script_path)]
        if args:
            command.extend(args)

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=BASE_DIR,
        )

        start_time = time.time()

        while process.poll() is None:
            QApplication.processEvents()

            if time.time() - start_time > timeout:
                process.kill()
                stdout_msg, stderr_msg = process.communicate()
                raise subprocess.TimeoutExpired(
                    command,
                    timeout,
                    output=stdout_msg,
                    stderr=stderr_msg,
                )

            time.sleep(0.05)

        stdout_msg, stderr_msg = process.communicate()

        return subprocess.CompletedProcess(
            command,
            process.returncode,
            stdout=stdout_msg,
            stderr=stderr_msg,
        )

    def open_manage_students(self):
        self.sidebar.set_active(self.sidebar.btn_manage)
        dialog = ManageStudentsDialog(self)
        dialog.exec()
        self.refresh_dashboard_metrics()

    def register_student(self):
        self.sidebar.set_active(self.sidebar.btn_register)

        option_dialog = RegisterOptionDialog(self)
        result = option_dialog.exec()

        if result != QDialog.Accepted:
            return

        if option_dialog.selected_option == "face":
            self.register_face_student()
        elif option_dialog.selected_option == "rfid":
            self.register_rfid_student()
        elif option_dialog.selected_option == "fingerprint":
            self.register_fingerprint_student()

    def register_face_student(self):
        dialog = RegisterStudentDialog(self)
        result = dialog.exec()

        if result != QDialog.Accepted:
            return

        student_id, student_name = dialog.get_data()

        if not student_id or not student_name:
            self.show_error("Missing Data", "Please enter both Student ID and Student Name.")
            return

        if not student_id.isdigit():
            self.show_error("Invalid ID", "Student ID must contain only numbers.")
            return

        existing_name = get_student_name(student_id)
        if existing_name:
            if existing_name.strip().lower() != student_name.strip().lower():
                self.show_error(
                    "Name Mismatch",
                    f"Student ID {student_id} belongs to '{existing_name}', not '{student_name}'.",
                )
                return
            display_name = existing_name
        else:
            saved = add_student(student_id, student_name)
            if not saved:
                self.show_error("Registration Error", f"Could not create student ID {student_id}.")
                return
            display_name = student_name

        self.current_student_id = student_id
        self.current_student_name = display_name

        self.loading_dialog = LoadingDialog(
            "Please Wait",
            f"Capturing faces for {display_name} ({student_id})...\nCamera will open now.",
        )
        self.loading_dialog.show()
        QApplication.processEvents()

        self.start_capture_process(student_id, display_name)

    def register_rfid_student(self):
        dialog = RegisterStudentDialog(self)
        result = dialog.exec()

        if result != QDialog.Accepted:
            return

        student_id, student_name = dialog.get_data()

        if not student_id or not student_name:
            self.show_error("Missing Data", "Please enter both Student ID and Student Name.")
            return

        if not student_id.isdigit():
            self.show_error("Invalid ID", "Student ID must contain only numbers.")
            return

        existing_name = get_student_name(student_id)
        is_new_student = existing_name is None
        display_name = existing_name or student_name

        if existing_name and existing_name.strip().lower() != student_name.strip().lower():
            self.show_error(
                "Name Mismatch",
                f"Student ID {student_id} belongs to '{existing_name}', not '{student_name}'.",
            )
            return

        if not os.path.exists(RFID_REGISTER_SCRIPT):
            self.show_error("Missing File", f"register_rfid.py not found:\n{RFID_REGISTER_SCRIPT}")
            return

        loading = LoadingDialog(
            "RFID Registration",
            f"Scan RFID card for {display_name} ({student_id})...",
        )
        loading.show()
        QApplication.processEvents()

        try:
            result = subprocess.run(
                [sys.executable, os.path.abspath(RFID_REGISTER_SCRIPT)],
                capture_output=True,
                text=True,
                cwd=BASE_DIR,
                timeout=20,
            )

            loading.close()

            stdout_msg = result.stdout.strip()
            stderr_msg = result.stderr.strip()

            if result.returncode != 0:
                self.show_error("RFID Error", stderr_msg if stderr_msg else "RFID registration failed.")
                return

            rfid_uid = stdout_msg

            if not rfid_uid:
                self.show_error("RFID Error", "No RFID UID was received from scanner.")
                return

            if len(rfid_uid) != 8 or any(c not in "0123456789ABCDEF" for c in rfid_uid.upper()):
                self.show_error(
                    "RFID Error",
                    f"Invalid RFID UID received: {rfid_uid}\n\nPlease scan the card again.",
                )
                return

            rfid_uid = rfid_uid.upper()

            if is_new_student:
                saved = add_student(student_id, student_name)
                if not saved:
                    latest_name = get_student_name(student_id)
                    if not latest_name or latest_name.strip().lower() != student_name.strip().lower():
                        self.show_error(
                            "Registration Error",
                            f"RFID was scanned, but student ID {student_id} could not be created.",
                        )
                        return
                    display_name = latest_name

            if not link_rfid(student_id, rfid_uid):
                self.show_error("RFID Error", f"Could not link RFID to student ID {student_id}.")
                return

            self.refresh_dashboard_metrics()

            success_title = "Student Created" if is_new_student else "RFID Linked"
            success_message = (
                "Student created and RFID card linked successfully."
                if is_new_student
                else "RFID card linked successfully."
            )
            self.show_info(
                success_title,
                f"{success_message}\n\n"
                f"Name: {display_name}\n"
                f"ID: {student_id}\n"
                f"RFID UID: {rfid_uid}",
            )

        except subprocess.TimeoutExpired:
            loading.close()
            self.show_error("RFID Timeout", "No RFID card was scanned in time.")
        except Exception as e:
            loading.close()
            self.show_error("Error", str(e))

    def register_fingerprint_student(self):
        dialog = RegisterStudentDialog(self)
        result = dialog.exec()

        if result != QDialog.Accepted:
            return

        student_id, student_name = dialog.get_data()

        if not student_id or not student_name:
            self.show_error("Missing Data", "Please enter both Student ID and Student Name.")
            return

        if not student_id.isdigit():
            self.show_error("Invalid ID", "Student ID must contain only numbers.")
            return

        existing_name = get_student_name(student_id)
        is_new_student = existing_name is None
        display_name = existing_name or student_name

        if existing_name and existing_name.strip().lower() != student_name.strip().lower():
            self.show_error(
                "Name Mismatch",
                f"Student ID {student_id} belongs to '{existing_name}', not '{student_name}'.",
            )
            return

        if not os.path.exists(FINGERPRINT_REGISTER_SCRIPT):
            self.show_error(
                "Missing File",
                f"register_fingerprint.py not found:\n{FINGERPRINT_REGISTER_SCRIPT}",
            )
            return

        loading = LoadingDialog(
            "Fingerprint Registration",
            f"Scanning fingerprint for {display_name} ({student_id})",
            animated=True,
        )
        loading.show()
        QApplication.processEvents()

        try:
            result = self.run_python_script_with_loading(
                FINGERPRINT_REGISTER_SCRIPT,
                loading,
                args=[student_id],
                timeout=35,
            )

            loading.close()

            stdout_msg = result.stdout.strip()
            stderr_msg = result.stderr.strip()

            if result.returncode != 0:
                self.show_error(
                    "Fingerprint Error",
                    stderr_msg if stderr_msg else "Fingerprint registration failed.",
                )
                return

            if not stdout_msg:
                self.show_error("Fingerprint Error", "No fingerprint ID was received from scanner.")
                return

            try:
                fingerprint_id = int(stdout_msg)
            except ValueError:
                self.show_error("Fingerprint Error", f"Invalid fingerprint ID received: {stdout_msg}")
                return

            if is_new_student:
                saved = add_student(student_id, student_name)
                if not saved:
                    latest_name = get_student_name(student_id)
                    if not latest_name or latest_name.strip().lower() != student_name.strip().lower():
                        self.show_error(
                            "Registration Error",
                            f"Fingerprint was scanned, but student ID {student_id} could not be created.",
                        )
                        return
                    display_name = latest_name

            if not link_fingerprint(student_id, fingerprint_id):
                self.show_error("Fingerprint Error", f"Could not link fingerprint to student ID {student_id}.")
                return

            self.refresh_dashboard_metrics()

            success_title = "Student Created" if is_new_student else "Fingerprint Linked"
            success_message = (
                "Student created and fingerprint linked successfully."
                if is_new_student
                else "Fingerprint linked successfully."
            )
            self.show_info(
                success_title,
                f"{success_message}\n\n"
                f"Name: {display_name}\n"
                f"ID: {student_id}\n"
                f"Fingerprint ID: {fingerprint_id}",
            )

        except subprocess.TimeoutExpired as e:
            loading.close()
            error_message = e.stderr or "No fingerprint was scanned in time."
            self.show_error("Fingerprint Timeout", error_message)
        except Exception as e:
            loading.close()
            self.show_error("Error", str(e))

    def start_capture_process(self, student_id, student_name):
        if not os.path.exists(CAPTURE_SCRIPT):
            if self.loading_dialog:
                self.loading_dialog.close()
            self.show_error("Missing File", f"capture_faces.py not found:\n{CAPTURE_SCRIPT}")
            return

        self.capture_process = QProcess(self)
        self.capture_process.setWorkingDirectory(BASE_DIR)

        self.capture_process.finished.connect(self.on_capture_finished)
        self.capture_process.errorOccurred.connect(self.on_capture_error)

        self.capture_process.readyReadStandardError.connect(
            lambda: print(bytes(self.capture_process.readAllStandardError()).decode(errors="ignore"))
        )
        self.capture_process.readyReadStandardOutput.connect(
            lambda: print(bytes(self.capture_process.readAllStandardOutput()).decode(errors="ignore"))
        )

        self.capture_process.start(
            sys.executable,
            [os.path.abspath(CAPTURE_SCRIPT), student_id, student_name],
        )

    def on_capture_finished(self, exit_code, exit_status):
        if exit_code != 0:
            if self.loading_dialog:
                self.loading_dialog.close()
            self.show_error("Capture Error", "Face capture failed or was closed unexpectedly.")
            return

        if self.loading_dialog:
            self.loading_dialog.set_message(
                f"Training face model for {self.current_student_name} ({self.current_student_id})..."
            )
            QApplication.processEvents()

        self.start_training_process()

    def on_capture_error(self, error):
        if self.loading_dialog:
            self.loading_dialog.close()
        self.show_error("Capture Error", "Could not start face capture process.")

    def start_training_process(self):
        if not os.path.exists(TRAIN_SCRIPT):
            if self.loading_dialog:
                self.loading_dialog.close()
            self.show_error("Missing File", f"train_model.py not found:\n{TRAIN_SCRIPT}")
            return

        self.train_process = QProcess(self)
        self.train_process.setWorkingDirectory(BASE_DIR)

        self.train_process.finished.connect(self.on_training_finished)
        self.train_process.errorOccurred.connect(self.on_training_error)

        self.train_process.readyReadStandardError.connect(
            lambda: print(bytes(self.train_process.readAllStandardError()).decode(errors="ignore"))
        )
        self.train_process.readyReadStandardOutput.connect(
            lambda: print(bytes(self.train_process.readAllStandardOutput()).decode(errors="ignore"))
        )

        self.train_process.start(sys.executable, [os.path.abspath(TRAIN_SCRIPT)])

    def on_training_finished(self, exit_code, exit_status):
        if self.loading_dialog:
            self.loading_dialog.close()

        if exit_code != 0:
            self.show_error("Training Error", "Face model training failed.")
            return

        self.show_info(
            "Success",
            f"Student registered successfully.\n\n"
            f"Name: {self.current_student_name}\n"
            f"ID: {self.current_student_id}\n\n"
            f"Face capture and training completed.",
        )
        self.refresh_dashboard_metrics()

    def on_training_error(self, error):
        if self.loading_dialog:
            self.loading_dialog.close()
        self.show_error("Training Error", "Could not start training process.")

    def face_attendance(self):
        self.sidebar.set_active(self.sidebar.btn_dashboard)

        try:
            self.run_python_script(RECOGNIZE_SCRIPT)
            self.refresh_dashboard_metrics()
        except subprocess.CalledProcessError as e:
            self.show_error("Face Attendance Error", f"Could not start face attendance.\n\n{e}")
        except Exception as e:
            self.show_error("Error", str(e))

    def fingerprint_attendance(self):
        self.sidebar.set_active(self.sidebar.btn_dashboard)

        if not os.path.exists(FINGERPRINT_SCRIPT):
            self.show_error("Missing File", f"fingerprint_attendance.py not found:\n{FINGERPRINT_SCRIPT}")
            return

        loading = LoadingDialog("Fingerprint Attendance", "Scanning fingerprint", animated=True)
        loading.show()
        QApplication.processEvents()

        try:
            result = self.run_python_script_with_loading(
                FINGERPRINT_SCRIPT,
                loading,
                timeout=35,
            )

            loading.close()

            stdout_msg = result.stdout.strip()
            stderr_msg = result.stderr.strip()

            if result.returncode != 0:
                self.show_error(
                    "Fingerprint Attendance Error",
                    stderr_msg if stderr_msg else "Fingerprint attendance failed.",
                )
                return

            message_lower = stdout_msg.lower()

            if not stdout_msg:
                self.show_info("Fingerprint Attendance", "Fingerprint attendance completed.")
            elif "marked present" in message_lower:
                self.show_info("Attendance Marked", stdout_msg)
            elif "already marked" in message_lower:
                self.show_info("Already Marked", stdout_msg)
            elif "low confidence" in message_lower:
                self.show_error("Low Confidence", stdout_msg)
            elif "not registered" in message_lower:
                self.show_error("Fingerprint Not Registered", stdout_msg)
            else:
                self.show_info("Fingerprint Attendance", stdout_msg)
            self.refresh_dashboard_metrics()

        except subprocess.TimeoutExpired as e:
            loading.close()
            error_message = e.stderr or "No fingerprint was scanned in time."
            self.show_error("Fingerprint Timeout", error_message)
        except Exception as e:
            loading.close()
            self.show_error("Error", str(e))

    def rfid_attendance(self):
        self.sidebar.set_active(self.sidebar.btn_dashboard)

        if not os.path.exists(RFID_SCRIPT):
            self.show_error("Missing File", f"rfid_attendance.py not found:\n{RFID_SCRIPT}")
            return

        loading = LoadingDialog("RFID Attendance", "Scan RFID card...")
        loading.show()
        QApplication.processEvents()

        try:
            result = subprocess.run(
                [sys.executable, os.path.abspath(RFID_SCRIPT)],
                capture_output=True,
                text=True,
                cwd=BASE_DIR,
                timeout=20,
            )

            loading.close()

            stdout_msg = result.stdout.strip()
            stderr_msg = result.stderr.strip()

            if result.returncode != 0:
                self.show_error(
                    "RFID Attendance Error",
                    stderr_msg if stderr_msg else "RFID attendance failed.",
                )
                return

            if stdout_msg:
                self.show_info("RFID Attendance", stdout_msg)
            else:
                self.show_info("RFID Attendance", "RFID attendance completed.")
            self.refresh_dashboard_metrics()

        except subprocess.TimeoutExpired:
            loading.close()
            self.show_error("RFID Timeout", "No RFID card was scanned in time.")
        except Exception as e:
            loading.close()
            self.show_error("Error", str(e))

    def view_reports(self):
        self.sidebar.set_active(self.sidebar.btn_view)

        dialog = AttendanceReportDialog(self)
        dialog.exec()
        self.refresh_dashboard_metrics()

    def close_app(self):
        confirm = ConfirmActionDialog(
            "Exit System?",
            "Are you sure you want to close the attendance system?",
            confirm_text="Exit",
            danger=True,
            parent=self,
        )

        if confirm.exec() == QDialog.Accepted:
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    if sys.platform == "darwin":
        app.setFont(QFont("Helvetica"))
    elif sys.platform == "win32":
        app.setFont(QFont("Segoe UI"))
    else:
        app.setFont(QFont("Arial"))

    window = MainDashboard()
    window.show()

    sys.exit(app.exec())
