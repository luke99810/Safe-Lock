# SafeLock - Screen Lock Tool

> Lock your screen and input devices while background programs keep running. Unlock with password.

---

## Features

| Feature | Description |
|---------|-------------|
| Fullscreen Overlay | Covers the entire screen without switching user sessions, background tasks run normally |
| Input Blocking | Global low-level hooks block all mouse input and system keyboard shortcuts |
| Shortcut Shield | Blocks Win key, Alt+F4, Alt+Tab, Esc and other system shortcuts |
| Password Unlock | Only correct password can dismiss the lock screen |
| System Tray | Runs in system tray, right-click to lock screen, change password, or exit |
| Password Persistence | SHA-256 hashed storage, password survives restarts |

---

## Quick Start

### Option 1: Run as Python script (for developers)

```bash
# Install dependencies
pip install pystray Pillow

# Run
python safe_lock.py
```

### Option 2: Run as EXE (recommended for daily use)

1. Right-click `dist/SafeLock.exe` > **Run as administrator**
2. The program starts in the system tray (bottom-right corner)

### Option 3: Package your own EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name SafeLock safe_lock.py
# Output: dist/SafeLock.exe
```

> **Note:** Use Python 3.11+ for packaging. Python 3.10.0 has a known `dis` module bug that breaks PyInstaller.

---

## Usage

1. Launch the program (run as **administrator**)
2. A lock icon appears in the **system tray** (bottom-right)
3. **First run:** default password is `1234`, change it immediately
4. Right-click tray icon > **Lock Screen**
5. Lock screen activates:
   - Fullscreen dark blue overlay covers the screen
   - Keyboard input is captured for password entry
   - Mouse clicks are completely blocked
   - Background programs (training, rendering, etc.) **continue running**
6. Type your password and press **Enter** to unlock

### Change Password

- Right-click tray icon > **Change Password**
- Enter current password, then new password, then confirm

### Manual Password Reset

If you forget your password, delete `config.json` next to the EXE/script. The default password `1234` will be restored on next launch.

---

## File Structure

```
SafeLock/
├── safe_lock.py      # Main program
├── requirements.txt  # Python dependencies
├── run.bat           # One-click launch script
├── build_exe.bat     # Package as EXE
├── dist/             # Built EXE (after packaging)
├── config.json       # Password config (auto-generated)
└── README.md
```

---

## Important Notes

- **Administrator privileges required** - global keyboard hooks need elevated permissions
- **Ctrl+Alt+Del** cannot be intercepted (Windows kernel-level security sequence)
- For emergency exit, use Task Manager to kill `SafeLock.exe`
- Recommended to use with a "prevent sleep" tool (like `caffeine`) to stop Windows from sleeping

---

## Tech Stack

| Category | Technology | Role |
|----------|-----------|------|
| Language | Python 3.11+ | Core runtime |
| GUI | tkinter | Fullscreen lock screen UI (Entry widget, Frame layout) |
| System Hook | ctypes + Win32 API (`SetWindowsHookEx`) | Global low-level keyboard & mouse interception |
| System Tray | pystray | System tray icon with context menu |
| Image | Pillow (PIL) | Generate tray icon programmatically |
| Security | hashlib (SHA-256) | Password hashing, plaintext never stored |
| Packaging | PyInstaller | Bundle into standalone `.exe` |
| Platform | Windows 10/11 | Win32 API dependent |

### Architecture

```
Main Thread: pystray icon event loop
     |
     v  (user clicks "Lock Screen")
Dedicated Thread: create tkinter Tk() root
     |
     |-- Entry widget (receives keyboard events directly)
     |-- SetWindowPos (HWND_TOPMOST) + periodic re-raise
     |-- force_focus timer (keeps Entry focused)
     |
     v
Global Hooks (installed on lock, removed on unlock):
  - WH_KEYBOARD_LL (id=13): blocks Win/Alt+F4/Alt+Tab/Esc, passes others through
  - WH_MOUSE_LL  (id=14): blocks all mouse events
```

---

## Technical Details

```
User triggers lock
     |
     v
Create fullscreen tkinter window (TOPMOST, dedicated thread)
     |
     v
SetWindowsHookEx installs global hooks:
  - Keyboard: blocks Win/Alt+F4/Alt+Tab/Esc, passes other keys to Entry widget
  - Mouse: blocks all mouse events
     |
     v
User types password in Entry widget (tkinter handles keyboard events)
     |
     v
Enter pressed -> SHA-256 comparison
     |
     v
Password correct -> UnhookWindowsHookEx -> destroy window -> normal
```

---

*Made by Lukeclaw*
