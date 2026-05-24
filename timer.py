class PomodoroTimer:
    def __init__(self):
        self.work_time = 25 * 60
        self.short_break = 5 * 60
        self.long_break = 15 * 60
        self.time_left = self.work_time
        self.running = False
        self.completed_sessions = 0
        self._on_complete = None  # callback set by UI

    def set_on_complete(self, callback):
        self._on_complete = callback

    def start(self):
        self.running = True

    def pause(self):
        self.running = False

    def reset(self):
        self.running = False
        self.time_left = self.work_time

    def tick(self):
        if self.running and self.time_left > 0:
            self.time_left -= 1
        elif self.time_left == 0 and self.running:
            self.running = False
            self.completed_sessions += 1
            if self._on_complete:
                self._on_complete()

    def set_work_time(self, minutes):
        self.work_time = int(minutes) * 60
        self.time_left = self.work_time

    def set_short_break(self, minutes):
        self.short_break = int(minutes) * 60

    def set_long_break(self, minutes):
        self.long_break = int(minutes) * 60

    def use_short_break(self):
        self.time_left = self.short_break

    def use_long_break(self):
        self.time_left = self.long_break

    def get_time(self):
        mins = self.time_left // 60
        secs = self.time_left % 60
        return f"{mins:02}:{secs:02}"