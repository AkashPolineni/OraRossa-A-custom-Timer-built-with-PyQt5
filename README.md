# 🍅 OraRossa

> *"Ora Rossa" — Italian for "Red Hour". A Pomodoro timer that actually feels like something.*

OraRossa is a desktop productivity app for macOS built with Python and PyQt5. It uses the Pomodoro technique to help you work in focused intervals, with animated video backgrounds that respond to your timer state, a built-in task manager, and a glassmorphic UI layered over live video.

---

## 📸 Preview
1. App Interface.
<img width="800" height="505" alt="Screenshot1-ezgif com-video-to-gif-converter" src="https://github.com/user-attachments/assets/521a67fe-5012-458b-a6d5-0f776ea1be41" />
2. Running the Timer:
<img width="800" height="514" alt="Screenshot2-ezgif com-video-to-gif-converter" src="https://github.com/user-attachments/assets/bcb9e0e7-5427-4d61-8dca-23cf050ebd91" />
3. Timer Complete:
<img width="800" height="514" alt="ScreenRecording2026-05-24at11 13 32pm-ezgif com-video-to-gif-converter" src="https://github.com/user-attachments/assets/b2a2e193-9218-4176-be37-456ac973aa38" />



## ✨ Features

- **State-aware video backgrounds** — three separate looping `.mp4` files play for idle, running, and session-complete states, rendered directly inside the window (no external player)
- **Animated tomato timer** — the tomato shifts from green to red in real time as your session counts down
- **Sidebar task manager** — add, complete, and delete tasks without leaving the app
- **Custom durations** — set your own work, short break, and long break lengths on the fly
- **System tray notifications** — session-complete alerts appear even when the window is in the background
- **Completion sound** — an audio cue fires via macOS `afplay` when a session ends
- **Glassmorphic UI** — frosted-glass panels float transparently over the live video background

---

## 🗂 File Structure

```
pomodoro-app/
├── main.py              # Entry point — boots the QApplication
├── ui.py                # Main window: all UI, video background, timer controls
├── timer.py             # PomodoroTimer — tick, start, pause, reset, sessions
├── tasks.py             # TaskManager — add, complete, delete
├── assets/
│   ├── idle.mp4         # Background video — timer waiting
│   ├── running.mp4      # Background video — session active
│   ├── end.mp4          # Background video — session complete
│   └── end.mp3          # Audio cue on session complete
└── requirements.txt
```

---

## 🛠 Requirements

- macOS (audio uses the built-in `afplay` command)
- Python 3.10+

---

## ⚙️ Installation

**1. Clone the repo**
```bash
git clone https://github.com/AkashPolineni/pomodoro-app.git
cd pomodoro-app
```

**2. Create and activate a virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

Dependencies: `PyQt5`, `Pillow`, `opencv-python`

**4. Add your assets**

Drop your files into the `assets/` folder:
| File | When it plays |
|---|---|
| `idle.mp4` | App launch and after reset |
| `running.mp4` | Active session |
| `end.mp4` | Session complete |
| `end.mp3` | Sound on session complete |

**5. Run**
```bash
python3 main.py
```

---

## 🎮 Usage

| Action | How |
|---|---|
| Start a session | Click **Start** |
| Pause | Click **Pause** — video freezes too |
| Reset to idle | Click **Reset** |
| Switch modes | **Work / Short Break / Long Break** |
| Custom durations | Enter minutes → **Apply Custom Timer** |
| Add a task | Type in the sidebar → **Add Task** |
| Complete / delete a task | Enter task number → **Complete Task** or **Delete Task** |

---

## 🏗 How It Works

### Timer
`PomodoroTimer` stores durations for work (25 min), short break (5 min), and long break (15 min) as seconds internally. Each second, the main window calls `tick()` via a `QTimer`. Inside `tick()`, if the timer is running and `time_left > 0` it decrements by one. When `time_left` hits zero, `running` is set to `False`, `completed_sessions` increments, and a callback registered via `set_on_complete` is fired — this is how the UI knows to switch the video, play the sound, and show the tray notification without the timer needing to know anything about the UI.

Custom durations are supported: `set_work_time()`, `set_short_break()`, and `set_long_break()` each take a minute value, convert it to seconds, and update the internal state. `get_time()` returns the current `time_left` formatted as `MM:SS`.

### Tomato Visual
On every tick, Pillow draws a fresh tomato image. The fill color of the ellipse is calculated from `time_left / work_time` — fully green at the start, fully red at zero. The formatted time string from `get_time()` is measured and centered over the tomato, then the whole image is converted to a `QPixmap` and set on a `QLabel`.

### Video Background
The background is a `VideoBackground` class — a `QLabel` at the bottom of the widget stack. OpenCV reads the video frame by frame, a `QTimer` fires at the clip's native FPS, and each frame is painted as a `QPixmap`. When the clip ends it rewinds to frame 0 and loops. The UI floats above on a transparent overlay widget. When the timer state changes — start, pause, reset, or complete — the corresponding clip loads automatically.

### Tasks
`TaskManager` loads and saves tasks via a `storage.py` module, so your list persists between sessions. Each task is a dict with a `title` and a `completed` boolean. `add_task()` appends and saves, `complete_task()` flips the boolean and saves, `delete_task()` pops the entry and saves. The sidebar displays pending and completed tasks in two separate sections, refreshing after every change.

---

## 💭 Reflection

OraRossa started as a standard Pomodoro timer but I wanted it to feel more intentional than a plain clock on a screen. The idea was that the app should *feel* different depending on what state you're in — focused, on a break, or done — rather than just showing a number ticking down.

The most interesting part to build was tying the timer state to the rest of the UI. Every second the tomato redraws itself with a new color, the session counter updates, and the video background stays in sync — it all runs off a single `QTimer` loop which keeps the logic clean and predictable.

The glassmorphic sidebar was a deliberate design choice to keep tasks visible without pulling attention away from the timer. Layering a transparent `QWidget` over a live video background required careful z-ordering, but the result is a UI that feels grounded in the environment rather than sitting on top of it.

---

## 📝 Credits

Built by [Akash](https://github.com/AkashPolineni) · Python · PyQt5 · OpenCV · Pillow
