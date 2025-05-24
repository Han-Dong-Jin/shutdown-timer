import sys
import os
import subprocess
import time
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtCore import QTimer, QTime, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPalette, QColor


class TimerThread(QThread):
    tick = pyqtSignal(int)

    def __init__(self, total_seconds: int):
        super().__init__()
        self.total = total_seconds
        self._running = True

    def run(self):
        start_time = time.time()
        while self._running:
            elapsed = int(time.time() - start_time)
            remaining = self.total - elapsed

            if remaining <= 0:
                self.tick.emit(0)
                break

            self.tick.emit(remaining)
            time.sleep(1)

    def stop(self):
        self._running = False


class ShutdownApp(QWidget):
    def __init__(self):
        super().__init__()

        self.blink_count = 0
        self.blinking = False
        self.color_change_time = 20
        self.timer_status = False
        self.timer_thread = None
        self.timer_active = False

        base_dir = os.path.dirname(__file__)
        uic.loadUi(os.path.join(base_dir, "st.ui"), self)
        self.setWindowTitle("Shutdown Timer")
        self.setWindowIcon(QIcon(os.path.join(base_dir, "SD.ico")))
        self.lcdNumber.display("00:00:00")

        # 버튼 연결
        self.pushButton.clicked.connect(lambda: self.set_timeedit(hours=1))
        self.pushButton_4.clicked.connect(lambda: self.set_timeedit(hours=2))
        self.pushButton_3.clicked.connect(lambda: self.set_timeedit(hours=3))
        self.pushButton_8.clicked.connect(lambda: self.set_timeedit(minutes=15))
        self.pushButton_7.clicked.connect(lambda: self.set_timeedit(minutes=30))
        self.pushButton_6.clicked.connect(lambda: self.set_timeedit(minutes=45))
        self.pushButton_9.clicked.connect(self.start_timer)
        self.pushButton_10.clicked.connect(self.stop_timer)
        self.pushButton_2.clicked.connect(self.reset_timeedit)
        self.pushButton_5.toggled.connect(self.set_shutdown_toggle)

    def set_shutdown_toggle(self, status: bool):
        self.timer_status = status
        self.label.setText("🟢" if status else "🔴")

    def reset_timeedit(self):
        self.timeEdit.setTime(QTime(0, 0))

    def set_timeedit(self, hours: int = None, minutes: int = None):
        time = self.timeEdit.time()
        h = hours if hours is not None else time.hour()
        m = minutes if minutes is not None else time.minute()
        self.timeEdit.setTime(QTime(h, m))

    def start_timer(self):
        if self.timer_thread and self.timer_thread.isRunning():
            return

        time_val = self.timeEdit.time()
        total_seconds = (
            time_val.hour() * 3600 + time_val.minute() * 60 + time_val.second()
        )

        if total_seconds == 0:
            QMessageBox.warning(self, "Notice", "Please set a time greater than 0.")
            return

        if not self.timer_status:
            subprocess.run(f"shutdown -s -t {total_seconds}", shell=True)

        self.timer_active = True
        self._start_thread_timer(total_seconds)
        self.lcdNumber.display(self._format_time(total_seconds))
        self._set_lcd_color(QColor(0, 0, 0))

    def stop_timer(self):
        self.timer_active = False
        subprocess.run("shutdown -a", shell=True)

        self.lcdNumber.display("00:00:00")
        self._set_lcd_color(QColor(0, 0, 0))
        self.reset_timeedit()

        if hasattr(self, "blink_timer") and self.blink_timer.isActive():
            self.blink_timer.stop()

        if self.timer_thread:
            try:
                self.timer_thread.tick.disconnect()
            except Exception:
                pass
            self.timer_thread.stop()
            self.timer_thread.wait()
            self.timer_thread = None

        self.blinking = False
        self.blink_count = 0

    def _start_thread_timer(self, total_seconds: int):
        self.timer_thread = TimerThread(total_seconds)
        self.timer_thread.tick.connect(self.update_lcd_from_thread)
        self.timer_thread.start()

    def update_lcd_from_thread(self, remaining):
        if not self.timer_active:
            return

        if remaining > 0:
            self.lcdNumber.display(self._format_time(remaining))

            if remaining <= self.color_change_time:
                ratio = (self.color_change_time - remaining) / self.color_change_time
                red = int(255 * ratio)
                self._set_lcd_color(QColor(red, 0, 0))
            else:
                self._set_lcd_color(QColor(0, 0, 0))
        else:
            self._start_blinking()

    def _start_blinking(self):
        if self.blinking:
            return

        self.blinking = True
        self.blink_count = 0

        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.blink_lcd)
        self.blink_timer.start(200)

    def blink_lcd(self):
        if self.blink_count >= 10:
            self.blink_timer.stop()
            self.blinking = False
            self._set_lcd_color(QColor(0, 0, 0))
            return

        self.blink_count += 1
        color = QColor(255, 0, 0) if self.blink_count % 2 == 0 else QColor(0, 0, 0)
        self.lcdNumber.display("00:00:00")
        self._set_lcd_color(color)

    def _format_time(self, seconds: int):
        h, r = divmod(seconds, 3600)
        m, s = divmod(r, 60)
        return f"{h:02}:{m:02}:{s:02}"

    def _set_lcd_color(self, color: QColor):
        palette = self.lcdNumber.palette()
        palette.setColor(QPalette.WindowText, color)
        self.lcdNumber.setPalette(palette)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ShutdownApp()
    win.show()
    sys.exit(app.exec_())
