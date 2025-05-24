    def stop_timer(self):
        # 종료 예약 취소
        subprocess.run("shutdown -a", shell=True)

        # QThread 안전 종료
        if self.timer_thread:
            self.timer_thread.stop()
            self.timer_thread.wait()
            self.timer_thread = None  # 참조 해제

        # 상태 초기화
        self.blinking = False
        self.blink_count = 0
        self.remaining_seconds = 0

        # LCD 즉시 클리어
        self.lcdNumber.display("00:00:00")
        self._set_lcd_color(QColor(0, 0, 0))
        self.reset_timeedit()