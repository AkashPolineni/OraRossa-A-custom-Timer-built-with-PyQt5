import sys
import os
import io

import cv2

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QLineEdit, QTextEdit, QVBoxLayout, QHBoxLayout,
    QMessageBox, QSizePolicy, QSystemTrayIcon
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QImage, QPen, QBrush, QPainterPath
)
from PyQt5.QtCore import Qt, QTimer, QRectF

from PIL import Image, ImageDraw, ImageFont

from timer import PomodoroTimer
from tasks import TaskManager


# ==========================================
# COLORS
# ==========================================
ACCENT      = "#102C57"
SOFT_GREEN  = "#7C9D96"
SOFT_ORANGE = "#E6A57E"
SOFT_RED    = "#D97B66"


# ==========================================
# GLASS PANEL
# ==========================================
class GlassPanel(QWidget):

    def __init__(self, parent=None, radius=20, color=(255, 255, 255, 40)):
        super().__init__(parent)
        self.radius = radius
        self.color  = color
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r, g, b, a = self.color
        painter.setBrush(QBrush(QColor(r, g, b, a)))
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.radius, self.radius)
        painter.drawPath(path)


# ==========================================
# STYLED BUTTON
# ==========================================
class GlassButton(QPushButton):

    def __init__(self, text, color, hover_color, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 25px;
                font-family: 'Helvetica Neue';
                font-size: 15px;
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)


# ==========================================
# STYLED ENTRY
# ==========================================
class GlassEntry(QLineEdit):

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 40);
                color: white;
                border: 1px solid rgba(255, 255, 255, 150);
                border-radius: 25px;
                font-family: 'Helvetica Neue';
                font-size: 15px;
                padding: 8px 18px;
            }
        """)
        self.setFixedHeight(50)


# ==========================================
# VIDEO BACKGROUND LABEL
# ==========================================
class VideoBackground(QLabel):
    """
    Reads an mp4 with OpenCV, pumps frames into a QLabel via QTimer.
    Loops automatically. Sits behind the UI as the window background.
    """

    WIN_W = 1450
    WIN_H = 860

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.WIN_W, self.WIN_H)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._cap      = None
        self._path     = None

        # ~30 fps frame pump
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._next_frame)

    def load(self, path: str):
        """Load a new video file and start playing immediately."""
        if not os.path.exists(path):
            return
        if self._cap:
            self._cap.release()
        self._path = path
        self._cap  = cv2.VideoCapture(path)
        fps        = self._cap.get(cv2.CAP_PROP_FPS) or 30
        self._frame_timer.start(int(1000 / fps))

    def pause(self):
        self._frame_timer.stop()

    def resume(self):
        if self._cap:
            self._frame_timer.start()

    def _next_frame(self):
        if not self._cap:
            return
        ok, frame = self._cap.read()
        if not ok:
            # Loop: rewind
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
            if not ok:
                return

        # Convert BGR → RGB, scale to window size
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        qimg = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.WIN_W, self.WIN_H,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        self.setPixmap(pixmap)


# ==========================================
# MAIN WINDOW
# ==========================================
class OraRossa(QMainWindow):

    VIDEO_IDLE    = "assets/idle.mp4"
    VIDEO_RUNNING = "assets/running.mp4"
    VIDEO_END     = "assets/end.mp4"

    WIN_W = 1450
    WIN_H = 860

    def __init__(self):
        super().__init__()

        self.setWindowTitle("OraRossa")
        self.setFixedSize(self.WIN_W, self.WIN_H)

        # TIMER + TASKS
        self.timer = PomodoroTimer()
        self.timer.set_on_complete(self.on_session_complete)
        self.task_manager = TaskManager()

        # SYSTEM TRAY
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        self.tray.show()

        # ── Central widget (plain, opaque) ──────────────────────────────
        self._central = QWidget(self)
        self._central.setFixedSize(self.WIN_W, self.WIN_H)
        self.setCentralWidget(self._central)

        # ── Video background ─────────────────────────────────────────────
        self.video_bg = VideoBackground(self._central)
        self.video_bg.move(0, 0)
        self.video_bg.lower()           # push behind everything

        # ── Transparent UI overlay ───────────────────────────────────────
        self._ui_layer = QWidget(self._central)
        self._ui_layer.setAttribute(Qt.WA_TranslucentBackground)
        self._ui_layer.setFixedSize(self.WIN_W, self.WIN_H)
        self._ui_layer.move(0, 0)
        self._ui_layer.raise_()         # pull above video

        # Start idle video
        self._current_video = None
        self.play_video(self.VIDEO_IDLE)

        # BUILD UI
        self.create_ui()

        # TIMER LOOP
        self.qt_timer = QTimer()
        self.qt_timer.timeout.connect(self.update_timer)
        self.qt_timer.start(1000)

        self.update_tomato()

    # ==========================================
    # VIDEO CONTROL
    # ==========================================
    def play_video(self, path: str):
        if self._current_video == path:
            return
        self._current_video = path
        self.video_bg.load(os.path.abspath(path))

    # ==========================================
    # BUILD UI  (layout lives in self._ui_layer)
    # ==========================================
    def create_ui(self):

        root_layout = QHBoxLayout(self._ui_layer)
        root_layout.setContentsMargins(25, 25, 25, 25)
        root_layout.setSpacing(20)

        # ── SIDEBAR ──────────────────────────────────────────────────────
        self.sidebar = GlassPanel(color=(15, 30, 20, 160), radius=22)
        self.sidebar.setFixedWidth(370)
        self.sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(25, 30, 25, 30)
        sidebar_layout.setSpacing(10)

        logo = QLabel("OraRossa")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"""
            color: {ACCENT};
            font-family: 'Helvetica Neue';
            font-size: 36px;
            font-weight: bold;
            background: transparent;
        """)
        sidebar_layout.addWidget(logo)
        sidebar_layout.addSpacing(10)

        self.task_entry = GlassEntry("Add a task...")
        sidebar_layout.addWidget(self.task_entry)

        add_btn = GlassButton("Add Task", SOFT_ORANGE, "#D98F65")
        add_btn.setFixedHeight(50)
        add_btn.clicked.connect(self.add_task)
        sidebar_layout.addWidget(add_btn)

        sidebar_layout.addSpacing(5)

        self.task_box = QTextEdit()
        self.task_box.setReadOnly(True)
        self.task_box.setStyleSheet("""
            QTextEdit {
                background-color: rgba(10, 30, 20, 140);
                color: white;
                border: none;
                border-radius: 16px;
                font-family: 'Helvetica Neue';
                font-size: 15px;
                padding: 12px;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,80);
                border-radius: 3px;
            }
        """)
        self.task_box.setMinimumHeight(200)
        sidebar_layout.addWidget(self.task_box, stretch=1)

        sidebar_layout.addSpacing(5)

        self.index_entry = GlassEntry("Task Number")
        sidebar_layout.addWidget(self.index_entry)

        complete_btn = GlassButton("Complete Task", SOFT_GREEN, "#66867F")
        complete_btn.setFixedHeight(50)
        complete_btn.clicked.connect(self.complete_task)
        sidebar_layout.addWidget(complete_btn)

        delete_btn = GlassButton("Delete Task", SOFT_RED, "#C56755")
        delete_btn.setFixedHeight(50)
        delete_btn.clicked.connect(self.delete_task)
        sidebar_layout.addWidget(delete_btn)

        root_layout.addWidget(self.sidebar)

        # ── MAIN AREA ─────────────────────────────────────────────────────
        main_widget = QWidget()
        main_widget.setAttribute(Qt.WA_TranslucentBackground)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 30, 20, 20)
        main_layout.setSpacing(8)
        main_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        self.mode_label = QLabel("FOCUS ZEN MODE")
        self.mode_label.setAlignment(Qt.AlignCenter)
        self.mode_label.setStyleSheet("""
            color: #5E8673;
            font-family: 'Helvetica Neue';
            font-size: 28px;
            font-weight: bold;
            background: transparent;
        """)
        main_layout.addWidget(self.mode_label)

        self.tomato_label = QLabel()
        self.tomato_label.setAlignment(Qt.AlignCenter)
        self.tomato_label.setFixedSize(260, 260)
        self.tomato_label.setStyleSheet("background: transparent;")
        main_layout.addWidget(self.tomato_label, alignment=Qt.AlignHCenter)

        self.quote_label = QLabel("Stay focused. Stay calm.")
        self.quote_label.setAlignment(Qt.AlignCenter)
        self.quote_label.setStyleSheet("""
            color: rgba(255,255,255,200);
            font-family: 'Helvetica Neue';
            font-size: 18px;
            font-style: italic;
            background: transparent;
        """)
        main_layout.addWidget(self.quote_label)

        self.session_label = QLabel("Completed Sessions: 0")
        self.session_label.setAlignment(Qt.AlignCenter)
        self.session_label.setStyleSheet("""
            color: white;
            font-family: 'Helvetica Neue';
            font-size: 17px;
            background: transparent;
        """)
        main_layout.addWidget(self.session_label)

        main_layout.addSpacing(10)

        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(12)
        btn_row1.setAlignment(Qt.AlignHCenter)

        self.start_btn = GlassButton("Start", SOFT_GREEN, "#6A8A82")
        self.start_btn.setFixedSize(145, 54)
        self.start_btn.clicked.connect(self.start_timer)

        self.pause_btn = GlassButton("Pause", SOFT_ORANGE, "#D38C63")
        self.pause_btn.setFixedSize(145, 54)
        self.pause_btn.clicked.connect(self.pause_timer)

        self.reset_btn = GlassButton("Reset", SOFT_RED, "#C26454")
        self.reset_btn.setFixedSize(145, 54)
        self.reset_btn.clicked.connect(self.reset_timer)

        btn_row1.addWidget(self.start_btn)
        btn_row1.addWidget(self.pause_btn)
        btn_row1.addWidget(self.reset_btn)
        main_layout.addLayout(btn_row1)

        main_layout.addSpacing(8)

        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(12)
        btn_row2.setAlignment(Qt.AlignHCenter)

        work_btn = GlassButton("Work", "#5E8673", "#4C7060")
        work_btn.setFixedSize(160, 50)
        work_btn.clicked.connect(self.work_mode)

        short_btn = GlassButton("Short Break", "#DCA271", "#C88C59")
        short_btn.setFixedSize(160, 50)
        short_btn.clicked.connect(self.short_break)

        long_btn = GlassButton("Long Break", "#B97756", "#9E6044")
        long_btn.setFixedSize(160, 50)
        long_btn.clicked.connect(self.long_break)

        btn_row2.addWidget(work_btn)
        btn_row2.addWidget(short_btn)
        btn_row2.addWidget(long_btn)
        main_layout.addLayout(btn_row2)

        main_layout.addSpacing(20)

        custom_title = QLabel("Custom Timer Settings")
        custom_title.setAlignment(Qt.AlignCenter)
        custom_title.setStyleSheet("""
            color: white;
            font-family: 'Helvetica Neue';
            font-size: 22px;
            font-weight: bold;
            background: transparent;
        """)
        main_layout.addWidget(custom_title)

        main_layout.addSpacing(8)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(15)
        custom_row.setAlignment(Qt.AlignHCenter)

        self.work_entry  = GlassEntry("Work (mins)")
        self.short_entry = GlassEntry("Short (mins)")
        self.long_entry  = GlassEntry("Long (mins)")

        for entry in [self.work_entry, self.short_entry, self.long_entry]:
            entry.setFixedWidth(145)
            custom_row.addWidget(entry)

        main_layout.addLayout(custom_row)
        main_layout.addSpacing(10)

        apply_btn = GlassButton("Apply Custom Timer", ACCENT, "#0B2245")
        apply_btn.setFixedSize(270, 52)
        apply_btn.clicked.connect(self.apply_custom_times)
        main_layout.addWidget(apply_btn, alignment=Qt.AlignHCenter)

        main_layout.addStretch()

        root_layout.addWidget(main_widget, stretch=1)

        self.refresh_tasks()

    # ==========================================
    # TOMATO
    # ==========================================
    def update_tomato(self):
        progress = max(0.0, min(1.0, self.timer.time_left / self.timer.work_time))
        red      = max(0, min(255, int((1 - progress) * 255)))
        green    = max(0, min(255, int(progress * 255)))

        image = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
        draw  = ImageDraw.Draw(image)

        draw.ellipse((55, 65, 215, 225), fill=(40, 50, 45, 70))
        draw.polygon([(120, 55), (160, 55), (140, 20)], fill="#3A7D44")
        draw.ellipse((50, 50, 210, 210), fill=f"#{red:02x}{green:02x}00")

        try:
            font = ImageFont.truetype("Helvetica.ttc", 38)
        except OSError:
            font = ImageFont.load_default()

        timer_text = self.timer.get_time()
        text_box   = draw.textbbox((0, 0), timer_text, font=font)
        tw = text_box[2] - text_box[0]
        th = text_box[3] - text_box[1]
        draw.text(
            ((260 - tw) / 2, (260 - th) / 2 - 4),
            timer_text, fill="white", font=font
        )

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        qimg   = QImage.fromData(buf.read())
        pixmap = QPixmap.fromImage(qimg).scaled(
            260, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.tomato_label.setPixmap(pixmap)

    # ==========================================
    # TIMER LOOP
    # ==========================================
    def update_timer(self):
        self.timer.tick()
        self.session_label.setText(
            f"Completed Sessions: {self.timer.completed_sessions}"
        )
        self.update_tomato()

    # ==========================================
    # TIMER CONTROLS
    # ==========================================
    def on_session_complete(self):
        self._current_video = None
        self.play_video(self.VIDEO_END)
        self._play_sound("assets/end.mp3")
        self.tray.showMessage(
            "Il pomodoro è maturo",
            "Session complete! Time for a break.",
            QSystemTrayIcon.Information,
            5000
        )

    def _play_sound(self, path: str):
        """Play a sound file non-blocking using macOS afplay."""
        import subprocess
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            subprocess.Popen(["afplay", abs_path])


    def start_timer(self):
        self.timer.start()
        self._current_video = None
        self.play_video(self.VIDEO_RUNNING)

    def pause_timer(self):
        self.timer.pause()
        self.video_bg.pause()

    def reset_timer(self):
        self.timer.reset()
        self._current_video = None
        self.play_video(self.VIDEO_IDLE)

    def work_mode(self):
        self.timer.time_left = self.timer.work_time
        self.mode_label.setText("FOCUS ZEN MODE")
        self.mode_label.setStyleSheet("""
            color: #5E8673;
            font-family: 'Helvetica Neue';
            font-size: 28px; font-weight: bold; background: transparent;
        """)

    def short_break(self):
        self.timer.use_short_break()
        self.mode_label.setText("SHORT BREAK")
        self.mode_label.setStyleSheet("""
            color: #DCA271;
            font-family: 'Helvetica Neue';
            font-size: 28px; font-weight: bold; background: transparent;
        """)

    def long_break(self):
        self.timer.use_long_break()
        self.mode_label.setText("LONG BREAK")
        self.mode_label.setStyleSheet("""
            color: #B97756;
            font-family: 'Helvetica Neue';
            font-size: 28px; font-weight: bold; background: transparent;
        """)

    def apply_custom_times(self):
        try:
            work  = self.work_entry.text()
            short = self.short_entry.text()
            long  = self.long_entry.text()

            if work:  self.timer.set_work_time(work)
            if short: self.timer.set_short_break(short)
            if long:  self.timer.set_long_break(long)

            QMessageBox.information(self, "Success", "Custom timers updated!")
        except Exception:
            QMessageBox.critical(self, "Error", "Please enter valid numbers.")

    # ==========================================
    # TASKS
    # ==========================================
    def refresh_tasks(self):
        self.task_box.clear()
        tasks     = self.task_manager.get_tasks()
        pending   = [t for t in tasks if not t["completed"]]
        completed = [t for t in tasks if t["completed"]]

        self.task_box.append("TO-DO TASKS\n")
        for t in pending:
            self.task_box.append(f"○  {t['title']}")
        self.task_box.append("\nCOMPLETED\n")
        for t in completed:
            self.task_box.append(f"✓  {t['title']}")

    def add_task(self):
        task = self.task_entry.text().strip()
        if not task:
            return
        self.task_manager.add_task(task)
        self.task_entry.clear()
        self.refresh_tasks()

    def complete_task(self):
        try:
            index = int(self.index_entry.text()) - 1
            self.task_manager.complete_task(index)
            self.refresh_tasks()
        except Exception:
            QMessageBox.critical(self, "Error", "Invalid task number.")

    def delete_task(self):
        try:
            index = int(self.index_entry.text()) - 1
            self.task_manager.delete_task(index)
            self.refresh_tasks()
        except Exception:
            QMessageBox.critical(self, "Error", "Invalid task number.")


# ==========================================
# ENTRY POINT
# ==========================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = OraRossa()
    win.show()
    sys.exit(app.exec_())