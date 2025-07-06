import sys
import os
import glob
import subprocess
import time
import json
from pathlib import Path
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtCore import QTimer, QTime, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPalette, QColor, QFontDatabase


class PresetConfigManager:
    def __init__(self, app_name="ShutdownTimer"):
        local_appdata = os.getenv(
            "LOCALAPPDATA", str(Path.home() / "AppData" / "Local")
        )
        self.config_path = Path(local_appdata) / app_name / "preset_config.json"
        self.presets = self._load_or_create_presets()

    def _load_or_create_presets(self):
        default_presets = {
            "timer": {
                "preset_1": {"label": "15m", "time": "00:15:00"},
                "preset_2": {"label": "30m", "time": "00:30:00"},
                "preset_3": {"label": "45m", "time": "00:45:00"},
                "preset_4": {"label": "1h", "time": "01:00:00"},
                "preset_5": {"label": "2h", "time": "02:00:00"},
                "preset_6": {"label": "3h", "time": "03:00:00"},
            },
            "stopwatch": {
                "preset_1": {"label": "1m", "time": "00:01:00"},
                "preset_2": {"label": "2m", "time": "00:02:00"},
                "preset_3": {"label": "3m", "time": "00:03:00"},
                "preset_4": {"label": "5m", "time": "00:05:00"},
                "preset_5": {"label": "15m", "time": "00:15:00"},
                "preset_6": {"label": "30m", "time": "00:30:00"},
            },
        }

        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default_presets, f, indent=4, ensure_ascii=False)

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_preset(self, mode: str, key: str) -> dict:
        return self.presets.get(mode, {}).get(key, {"label": "N/A", "time": "00:00:00"})

    def save_presets(self, mode: str, new_presets: dict):
        self.presets[mode] = new_presets
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.presets, f, indent=4, ensure_ascii=False)


class TimerThread(QThread):
    tick = pyqtSignal(int)

    def __init__(self, total_seconds):
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


class StopwatchThread(QThread):
    tick = pyqtSignal(int)

    def __init__(self, base_seconds=0):
        super().__init__()
        self._running = True
        self.base = base_seconds

    def run(self):
        start_time = time.time()
        while self._running:
            elapsed = int(time.time() - start_time)
            self.tick.emit(self.base + elapsed)
            time.sleep(1)

    def stop(self):
        self._running = False


class ShutdownManager:
    def execute_shutdown(self):
        subprocess.run("shutdown -s -t 0", shell=True)

    def cancel_shutdown(self):
        subprocess.run("shutdown -a", shell=True)


class ShutdownApp(QWidget):
    def __init__(self):
        super().__init__()

        self.shutdown_manager = ShutdownManager()
        self.config_manager = PresetConfigManager()

        self.timer_thread = None
        self.stopwatch_thread = None

        self.blinking = False
        self.blink_count = 0
        self.color_change_time = 20
        self.timer_active = False

        if getattr(sys, "frozen", False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(__file__)

        fonts_dir = os.path.join(base_dir, "fonts")
        ttf_files = glob.glob(os.path.join(fonts_dir, "*.ttf"))
        if ttf_files:
            loaded_families = []
            for font_path in ttf_files:
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id >= 0:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    loaded_families.extend(families)
            if loaded_families:
                self.setStyleSheet(
                    f"QWidget {{ font-family: '{loaded_families[0]}'; }}"
                )

        uic.loadUi(os.path.join(base_dir, "st.ui"), self)
        self.setWindowTitle("Shutdown Timer")
        self.setWindowIcon(QIcon(os.path.join(base_dir, "SD.ico")))
        self.lcdNumber.display("00:00:00")

        # Default mode: stopwatch
        self.timer_mode = False
        self.stopwatch_mode = True
        self.pushButton_5.setChecked(False)
        self.pushButton_11.setChecked(True)
        self.label.setText("🟢")
        self.label_2.setText("🔴")
        self.apply_preset_labels()
        self.checkBox.setEnabled(False)

        # mode flags initialized after UI loaded

        self.pushButton_5.setCheckable(True)
        self.pushButton_11.setCheckable(True)
        self.pushButton_5.clicked.connect(self.timer_mode_clicked)
        self.pushButton_11.clicked.connect(self.stopwatch_mode_clicked)

        self.pushButton_9.clicked.connect(self.start_action)
        self.pushButton_10.clicked.connect(self.stop_action)

        self.pushButton.clicked.connect(lambda: self.apply_preset("preset_1"))
        self.pushButton_4.clicked.connect(lambda: self.apply_preset("preset_2"))
        self.pushButton_3.clicked.connect(lambda: self.apply_preset("preset_3"))
        self.pushButton_8.clicked.connect(lambda: self.apply_preset("preset_4"))
        self.pushButton_7.clicked.connect(lambda: self.apply_preset("preset_5"))
        self.pushButton_6.clicked.connect(lambda: self.apply_preset("preset_6"))
        self.pushButton_2.clicked.connect(self.reset_timeedit)

        # self.pushButton_12.clicked.connect(self.open_config_file)
        self.timeEdit.timeChanged.connect(self.on_timeedit_changed)

    def on_timeedit_changed(self, qtime):
        self.lcdNumber.display(qtime.toString("HH:mm:ss"))

    def open_config_file(self):
        config_path = self.config_manager.config_path
        if not config_path.exists():
            QMessageBox.warning(
                self,
                "No configuration file",
                f"Configuration file does not exist:\n{config_path}",
            )
            return
        try:
            os.startfile(str(config_path))  # 윈도우 전용, 기본 연결 앱으로 파일 열기
        except Exception as e:
            QMessageBox.critical(
                self, "error", f"Unable to open configuration file:\n{e}"
            )

    def timer_mode_clicked(self):
        if self.timer_mode:
            return
        self.timer_mode = True
        self.stopwatch_mode = False
        self.pushButton_5.setChecked(True)
        self.pushButton_11.setChecked(False)
        self.label.setText("🔴")
        self.label_2.setText("🟢")
        self.apply_preset_labels()
        self.checkBox.setEnabled(True)

    def stopwatch_mode_clicked(self):
        if self.stopwatch_mode:
            return
        self.timer_mode = False
        self.stopwatch_mode = True
        self.pushButton_5.setChecked(False)
        self.pushButton_11.setChecked(True)
        self.label.setText("🟢")
        self.label_2.setText("🔴")
        self.apply_preset_labels()
        self.checkBox.setEnabled(False)

    def apply_preset_labels(self):
        mode = "timer" if self.timer_mode else "stopwatch"
        buttons = [
            (self.pushButton, "preset_1"),
            (self.pushButton_4, "preset_2"),
            (self.pushButton_3, "preset_3"),
            (self.pushButton_8, "preset_4"),
            (self.pushButton_7, "preset_5"),
            (self.pushButton_6, "preset_6"),
        ]
        for btn, key in buttons:
            preset = self.config_manager.get_preset(mode, key)
            btn.setText(preset["label"])

    def apply_preset(self, key):
        mode = "timer" if self.timer_mode else "stopwatch"
        preset = self.config_manager.get_preset(mode, key)
        h, m, s = map(int, preset["time"].split(":"))
        self.timeEdit.setTime(QTime(h, m, s))
        self.lcdNumber.display(preset["time"])

    def start_action(self):
        if self.timer_mode:
            self.start_timer()
        elif self.stopwatch_mode:
            self.start_stopwatch()
        else:
            QMessageBox.warning(self, "Notice", "Please select a mode.")

    def stop_action(self):
        if self.timer_mode:
            self.stop_timer()
        if self.stopwatch_mode:
            self.stop_stopwatch()

    def start_timer(self):
        if self.timer_thread and self.timer_thread.isRunning():
            return
        total = self.get_total_seconds_from_timeedit()
        if total <= 0:
            QMessageBox.warning(self, "Notice", "Please set a time.")
            return
        self.timer_active = True
        self.timer_thread = TimerThread(total)
        self.timer_thread.tick.connect(self.update_lcd_timer)
        self.timer_thread.start()
        self.lcdNumber.display(self._format_time(total))
        self._set_lcd_color(QColor(0, 0, 0))

    def stop_timer(self):
        self.timer_active = False
        self.shutdown_manager.cancel_shutdown()
        if self.timer_thread:
            self.timer_thread.stop()
            self.timer_thread.wait()
            self.timer_thread = None
        self.lcdNumber.display("00:00:00")
        self._set_lcd_color(QColor(0, 0, 0))
        self.blinking = False
        self.blink_count = 0

    def update_lcd_timer(self, remaining):
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
            if self.checkBox.isChecked():
                self.shutdown_manager.execute_shutdown()
            self._start_blinking()

    def start_stopwatch(self):
        if self.stopwatch_thread and self.stopwatch_thread.isRunning():
            return
        base_seconds = self.get_total_seconds_from_timeedit()
        self.stopwatch_thread = StopwatchThread(base_seconds=base_seconds)
        self.stopwatch_thread.tick.connect(self.update_lcd_stopwatch)
        self.stopwatch_thread.start()
        self._set_lcd_color(QColor(0, 0, 0))

    def stop_stopwatch(self):
        if self.stopwatch_thread:
            self.stopwatch_thread.stop()
            self.stopwatch_thread.wait()
            self.stopwatch_thread = None
        self.lcdNumber.display("00:00:00")
        self._set_lcd_color(QColor(0, 0, 0))

    def update_lcd_stopwatch(self, elapsed):
        self.lcdNumber.display(self._format_time(elapsed))

    def get_total_seconds_from_timeedit(self):
        t = self.timeEdit.time()
        return t.hour() * 3600 + t.minute() * 60 + t.second()

    def reset_timeedit(self):
        self.timeEdit.setTime(QTime(0, 0))

    def _format_time(self, seconds):
        h, r = divmod(seconds, 3600)
        m, s = divmod(r, 60)
        return f"{h:02}:{m:02}:{s:02}"

    def _set_lcd_color(self, color):
        p = self.lcdNumber.palette()
        p.setColor(QPalette.WindowText, color)
        self.lcdNumber.setPalette(p)

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ShutdownApp()
    win.show()
    sys.exit(app.exec_())
