import sys
import os
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtCore import QTimer, QTime
from PyQt5.QtGui import QIcon
from shutdown_timer_ui import Ui_ShutdownTimer  # pyuic5로 생성한 코드 임포트


class ShutdownApp(QWidget, Ui_ShutdownTimer):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Shutdown Timer")  # 창 제목 변경
        icon_path = os.path.join(os.path.dirname(__file__), "SD.ico")
        self.setWindowIcon(QIcon(icon_path))

        # 타이머 관련 초기화
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_lcd)
        self.remaining_seconds = 0

        # 프리셋 버튼 → QTimeEdit에 설정
        self.pushButton_8.clicked.connect(lambda: self.set_timeedit(minutes=15))  # 15m
        self.pushButton_7.clicked.connect(lambda: self.set_timeedit(minutes=30))  # 30m
        self.pushButton.clicked.connect(lambda: self.set_timeedit(hours=1))  # 1h
        self.pushButton_4.clicked.connect(lambda: self.set_timeedit(hours=2))  # 2h
        self.pushButton_3.clicked.connect(lambda: self.set_timeedit(hours=3))  # 3h
        self.pushButton_6.clicked.connect(lambda: self.set_timeedit(minutes=45))  # 45m

        # Start / Stop 버튼
        self.pushButton_9.clicked.connect(self.start_timer)  # Start
        self.pushButton_10.clicked.connect(self.stop_timer)  # Stop

        self.pushButton_2.clicked.connect(self.reset_timeedit)  # reset

    def reset_timeedit(self):
        self.timeEdit.setTime(QTime(0, 0))

    def set_timeedit(self, hours: int = None, minutes: int = None):
        """
        QTimeEdit에 시/분을 설정하되, 인자가 없으면 기존 값을 유지
        """
        current_time = self.timeEdit.time()
        h = current_time.hour() if hours is None else hours
        m = current_time.minute() if minutes is None else minutes
        self.timeEdit.setTime(QTime(h, m))

    def start_timer(self):
        """Start 버튼: shutdown 예약 + 타이머 시작"""
        time = self.timeEdit.time()
        self.remaining_seconds = time.hour() * 3600 + time.minute() * 60

        if self.remaining_seconds == 0:
            QMessageBox.warning(self, "알림", "0보다 큰 시간을 설정해주세요.")
            return

        # 시스템 종료 예약
        subprocess.run(f"shutdown -s -t {self.remaining_seconds}", shell=True)

        # LCD 표시 시작
        self.update_lcd()
        self.timer.start(1000)

    def stop_timer(self):
        """Stop 버튼: shutdown 취소 + 타이머 중지"""
        subprocess.run("shutdown -a", shell=True)
        self.timer.stop()
        self.remaining_seconds = 0
        self.lcdNumber.display("00:00:00")

    def update_lcd(self):
        """1초마다 LCD에 남은 시간 표시"""
        if self.remaining_seconds <= 0:
            self.timer.stop()
            self.lcdNumber.display("00:00:00")
            return

        hours, remainder = divmod(self.remaining_seconds, 3600)
        mins, secs = divmod(remainder, 60)
        display_time = f"{hours:02}:{mins:02}:{secs:02}"
        self.lcdNumber.display(display_time)
        self.remaining_seconds -= 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ShutdownApp()
    win.show()
    sys.exit(app.exec_())
