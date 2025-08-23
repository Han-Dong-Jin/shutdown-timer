import sys
import os
import glob
import subprocess
import json
from pathlib import Path
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QLCDNumber,
)
from PyQt5.QtCore import QTimer, QTime, Qt
from PyQt5.QtGui import QIcon, QPalette, QColor, QFontDatabase


class LcdPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        if getattr(sys, "frozen", False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(__file__)
        uic.loadUi(os.path.join(base_dir, "lcd_popup.ui"), self)
        self.setWindowTitle("LCD Popup")
        self.setFixedSize(self.size())
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

    def set_value(self, value: str):
        self.lcdNumber_popup.display(value)

    def set_theme(self, palette: QPalette):
        self.lcdNumber_popup.setPalette(palette)
        self.lcdNumber_popup.setAutoFillBackground(True)


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


class ShutdownManager:
    def execute_shutdown(self):
        subprocess.run("shutdown -s -t 0", shell=True)

    def cancel_shutdown(self):
        subprocess.run("shutdown -a", shell=True)


class ShutdownApp(QWidget):
    def __init__(self):
        super().__init__()

        self.lcd_popup = None

        self.shutdown_manager = ShutdownManager()
        self.config_manager = PresetConfigManager()

        self.timer_qtimer = QTimer(self)
        self.timer_qtimer.timeout.connect(self.update_lcd_timer)
        self.timer_remaining = 0
        self.timer_active = False

        self.stopwatch_qtimer = QTimer(self)
        self.stopwatch_qtimer.timeout.connect(self.update_lcd_stopwatch)
        self.stopwatch_elapsed = 0
        self.stopwatch_active = False

        self.blinking = False
        self.blink_count = 0
        self.color_change_time = 20

        self.timer_time = QTime(0, 0, 0)
        self.stopwatch_time = QTime(0, 0, 0)

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

        self.timer_mode = False
        self.stopwatch_mode = True
        self.pushButton_5.setChecked(False)
        self.pushButton_11.setChecked(True)
        self.apply_preset_labels()
        self.checkBox.setEnabled(False)

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

        self.timeEdit.timeChanged.connect(self.on_timeedit_changed)

        self.radioButton.toggled.connect(self.update_lcd_theme)
        self.radioButton_2.toggled.connect(self.update_lcd_theme)
        self.update_lcd_theme()

        self._last_lcd_text = "00:00:00"

        self.pushButton_popup.clicked.connect(self.show_lcd_popup)

    def show_lcd_popup(self):
        if self.lcd_popup is None or not self.lcd_popup.isVisible():
            self.lcd_popup = LcdPopup(self)
            self.lcd_popup.set_value(self._last_lcd_text)
            self.lcd_popup.set_theme(self.lcdNumber.palette())
            self.lcd_popup.show()
        else:
            self.lcd_popup.activateWindow()

    def sync_lcd_popup(self):
        if self.lcd_popup and self.lcd_popup.isVisible():
            self.lcd_popup.set_value(self._last_lcd_text)
            self.lcd_popup.set_theme(self.lcdNumber.palette())

    def lcdNumber_display(self, value):
        self._last_lcd_text = str(value)
        self.lcdNumber.display(value)
        self.sync_lcd_popup()

    def update_lcd_timer(self):
        if not self.timer_active or not self.timer_mode:
            return
        self.timer_remaining -= 1
        if self.timer_remaining > 0:
            self.lcdNumber_display(self._format_time(self.timer_remaining))
            if self.timer_remaining <= 10:
                self._set_lcd_color(QColor(255, 0, 0))
                # 팝업도 색상 동기화
                if self.lcd_popup and self.lcd_popup.isVisible():
                    self.lcd_popup.set_theme(self.lcdNumber.palette())
                    self.lcd_popup.set_value(self._format_time(self.timer_remaining))
            else:
                if self.radioButton_2.isChecked():
                    self._set_lcd_color(QColor(255, 255, 255))
                else:
                    self._set_lcd_color(QColor(0, 0, 0))
                # 팝업도 색상 동기화
                if self.lcd_popup and self.lcd_popup.isVisible():
                    self.lcd_popup.set_theme(self.lcdNumber.palette())
                    self.lcd_popup.set_value(self._format_time(self.timer_remaining))
        else:
            self.lcdNumber_display("00:00:00")
            self.timer_qtimer.stop()
            self.timer_active = False
            if self.checkBox.isChecked():
                self.shutdown_manager.execute_shutdown()
            self._start_blinking()

    def update_lcd_stopwatch(self):
        if not self.stopwatch_active:
            return

        self.stopwatch_elapsed += 1

        if self.stopwatch_mode:
            self.lcdNumber_display(self._format_time(self.stopwatch_elapsed))

    def on_timeedit_changed(self, qtime):
        if self.timer_mode:
            self.timer_time = qtime
        elif self.stopwatch_mode:
            self.stopwatch_time = qtime
        if (self.timer_mode and self.timer_active) or (
            self.stopwatch_mode and self.stopwatch_active
        ):
            return
        self.lcdNumber_display(qtime.toString("HH:mm:ss"))

    def reset_timeedit(self):
        if self.timer_mode:
            self.timer_time = QTime(0, 0, 0)
        elif self.stopwatch_mode:
            self.stopwatch_time = QTime(0, 0, 0)
        self.timeEdit.setTime(QTime(0, 0, 0))
        if (self.timer_mode and self.timer_active) or (
            self.stopwatch_mode and self.stopwatch_active
        ):
            return
        self.lcdNumber_display("00:00:00")

    def apply_preset(self, key):
        mode = "timer" if self.timer_mode else "stopwatch"
        preset = self.config_manager.get_preset(mode, key)
        h, m, s = map(int, preset["time"].split(":"))
        qtime = QTime(h, m, s)
        if self.timer_mode:
            self.timer_time = qtime
        elif self.stopwatch_mode:
            self.stopwatch_time = qtime
        self.timeEdit.setTime(qtime)
        if (self.timer_mode and self.timer_active) or (
            self.stopwatch_mode and self.stopwatch_active
        ):
            return
        self.lcdNumber_display(preset["time"])

    def timer_mode_clicked(self):
        if self.timer_mode:
            return

        self.timer_mode = True
        self.stopwatch_mode = False
        self.pushButton_5.setChecked(True)
        self.pushButton_11.setChecked(False)
        self.apply_preset_labels()
        self.checkBox.setEnabled(True)

        if self.timer_active:
            self.lcdNumber_display(self._format_time(self.timer_remaining))
        else:
            self.timeEdit.setTime(self.timer_time)
            self.lcdNumber_display(self.timer_time.toString("HH:mm:ss"))

        self._set_lcd_color(
            QColor(255, 255, 255) if self.radioButton_2.isChecked() else QColor(0, 0, 0)
        )

    def stopwatch_mode_clicked(self):
        if self.stopwatch_mode:
            return

        self.timer_mode = False
        self.stopwatch_mode = True
        self.pushButton_5.setChecked(False)
        self.pushButton_11.setChecked(True)
        self.apply_preset_labels()
        self.checkBox.setEnabled(False)

        if self.stopwatch_active:
            display_value = self._format_time(self.stopwatch_elapsed)
        else:
            display_value = self.stopwatch_time.toString("HH:mm:ss")
            self.timeEdit.setTime(self.stopwatch_time)

        self.lcdNumber_display(display_value)
        self._set_lcd_color(
            QColor(255, 255, 255) if self.radioButton_2.isChecked() else QColor(0, 0, 0)
        )

        # 팝업도 동기화
        if self.lcd_popup and self.lcd_popup.isVisible():
            self.lcd_popup.set_value(display_value)
            self.lcd_popup.set_theme(self.lcdNumber.palette())

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
        elif self.stopwatch_mode:
            self.stop_stopwatch()

    def start_timer(self):
        if self.timer_active:
            return
        total = self.get_total_seconds_from_timeedit()
        if total <= 0:
            QMessageBox.warning(self, "Notice", "Please set a time.")
            return
        self.timer_remaining = total
        self.timer_active = True
        self.timer_qtimer.start(1000)
        if self.timer_mode:
            self.lcdNumber_display(self._format_time(self.timer_remaining))
            self._set_lcd_color(
                QColor(255, 255, 255)
                if self.radioButton_2.isChecked()
                else QColor(0, 0, 0)
            )

    def stop_timer(self):
        self.timer_qtimer.stop()
        self.timer_active = False
        self.shutdown_manager.cancel_shutdown()
        if self.timer_mode:
            self.lcdNumber_display(self.timer_time.toString("HH:mm:ss"))
            self._set_lcd_color(
                QColor(255, 255, 255)
                if self.radioButton_2.isChecked()
                else QColor(0, 0, 0)
            )
        self.blinking = False
        self.blink_count = 0

    def start_stopwatch(self):
        if self.stopwatch_active:
            return
        self.stopwatch_elapsed = self.get_total_seconds_from_timeedit()
        self.stopwatch_active = True
        self.stopwatch_qtimer.start(1000)
        if self.stopwatch_mode:
            self.lcdNumber_display(self._format_time(self.stopwatch_elapsed))
            self._set_lcd_color(
                QColor(255, 255, 255)
                if self.radioButton_2.isChecked()
                else QColor(0, 0, 0)
            )

    def stop_stopwatch(self):
        self.stopwatch_qtimer.stop()
        self.stopwatch_active = False
        if self.stopwatch_mode:
            self.lcdNumber_display(self.stopwatch_time.toString("HH:mm:ss"))
            self._set_lcd_color(
                QColor(255, 255, 255)
                if self.radioButton_2.isChecked()
                else QColor(0, 0, 0)
            )

    def get_total_seconds_from_timeedit(self):
        t = self.timeEdit.time()
        return t.hour() * 3600 + t.minute() * 60 + t.second()

    def _format_time(self, seconds):
        h, r = divmod(seconds, 3600)
        m, s = divmod(r, 60)
        return f"{h:02}:{m:02}:{s:02}"

    def update_lcd_theme(self):
        palette = self.lcdNumber.palette()
        if self.radioButton.isChecked():
            palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
            palette.setColor(QPalette.Background, QColor(255, 255, 255))
            palette.setColor(QPalette.Window, QColor(255, 255, 255))
        elif self.radioButton_2.isChecked():
            palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
            palette.setColor(QPalette.Background, QColor(0, 0, 0))
            palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.lcdNumber.setAutoFillBackground(True)
        self.lcdNumber.setPalette(palette)
        if self.lcd_popup and self.lcd_popup.isVisible():
            self.lcd_popup.set_theme(palette)

    def _set_lcd_color(self, color):
        palette = self.lcdNumber.palette()
        if self.radioButton_2.isChecked() and color == QColor(0, 0, 0):
            color = QColor(255, 255, 255)
        palette.setColor(QPalette.WindowText, color)
        self.lcdNumber.setPalette(palette)

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
            self._set_lcd_color(
                QColor(255, 255, 255)
                if self.radioButton_2.isChecked()
                else QColor(0, 0, 0)
            )
            # 팝업도 색상 및 값 동기화
            if self.lcd_popup and self.lcd_popup.isVisible():
                self.lcd_popup.set_theme(self.lcdNumber.palette())
                self.lcd_popup.set_value("00:00:00")
            return

        self.blink_count += 1
        if self.radioButton_2.isChecked():
            color = (
                QColor(255, 0, 0)
                if self.blink_count % 2 == 0
                else QColor(255, 255, 255)
            )
        else:
            color = QColor(255, 0, 0) if self.blink_count % 2 == 0 else QColor(0, 0, 0)

        self.lcdNumber_display("00:00:00")
        self._set_lcd_color(color)
        # 팝업에도 값과 색상 동기화
        if self.lcd_popup and self.lcd_popup.isVisible():
            self.lcd_popup.set_value("00:00:00")
            self.lcd_popup.set_theme(self.lcdNumber.palette())


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    win = ShutdownApp()
    win.show()
    sys.exit(app.exec_())
