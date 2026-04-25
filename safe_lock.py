"""
SafeLock - 安全锁屏工具
作者: Lukeclaw
方案: 全屏tkinter窗口 + 全局钩子(仅拦截系统快捷键) + Entry密码输入
"""

import ctypes
import ctypes.wintypes
import threading
import sys
import os
import hashlib
import json

import pystray
from PIL import Image, ImageDraw

# ─── 配置 ─────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_CONFIG = {
    "password_hash": hashlib.sha256("1234".encode()).hexdigest(),
    "hint": "default password: 1234",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()


# ─── 全局状态 ─────────────────────────────────────────────────
config = load_config()
is_locked = False
tray_icon = None
lock_hwnd = None


# ─── Win32 常量 ───────────────────────────────────────────────
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
LLKHF_ALTDOWN = 0x20
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_MOUSEMOVE = 0x0200

VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_TAB = 0x09
VK_F4 = 0x73
VK_ESCAPE = 0x1B

HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_int, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM
)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


kb_hook = None
mouse_hook = None


# ─── 键盘钩子：只拦截系统快捷键，其他按键全部放行 ─────────────
def kb_hook_proc(nCode, wParam, lParam):
    if nCode >= 0 and is_locked:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        vk = kb.vkCode
        flags = kb.flags

        # 只拦截系统快捷键
        if vk in {VK_LWIN, VK_RWIN}:
            return 1  # 拦截 Win 键
        if vk == VK_ESCAPE:
            return 1  # 拦截 Esc（防关闭）
        if vk == VK_F4 and (flags & LLKHF_ALTDOWN):
            return 1  # 拦截 Alt+F4
        if vk == VK_TAB and (flags & LLKHF_ALTDOWN):
            return 1  # 拦截 Alt+Tab

        # 其他所有按键（包括字母数字、Backspace、Enter等）全部放行！
        # 让 tkinter 自己处理键盘事件

    return user32.CallNextHookEx(kb_hook, nCode, wParam, lParam)


# ─── 鼠标钩子：锁屏时拦截所有鼠标事件 ────────────────────────
def mouse_hook_proc(nCode, wParam, lParam):
    if nCode >= 0 and is_locked:
        return 1  # 拦截所有鼠标
    return user32.CallNextHookEx(mouse_hook, nCode, wParam, lParam)


_kb_proc = HOOKPROC(kb_hook_proc)
_mouse_proc = HOOKPROC(mouse_hook_proc)


def install_hooks():
    global kb_hook, mouse_hook
    kb_hook = user32.SetWindowsHookExW(
        WH_KEYBOARD_LL, _kb_proc, kernel32.GetModuleHandleW(None), 0
    )
    mouse_hook = user32.SetWindowsHookExW(
        WH_MOUSE_LL, _mouse_proc, kernel32.GetModuleHandleW(None), 0
    )


def uninstall_hooks():
    global kb_hook, mouse_hook
    if kb_hook:
        user32.UnhookWindowsHookEx(kb_hook)
        kb_hook = None
    if mouse_hook:
        user32.UnhookWindowsHookEx(mouse_hook)
        mouse_hook = None


# ─── 锁屏窗口 ─────────────────────────────────────────────────
def create_lock_window():
    global is_locked, lock_hwnd

    is_locked = True

    import tkinter as tk

    root = tk.Tk()
    root.title("SafeLock")
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.configure(bg="#1A1A2E")

    # 阻止窗口被关闭
    root.protocol("WM_DELETE_WINDOW", lambda: None)

    # ── 界面布局 ──
    container = tk.Frame(root, bg="#1A1A2E")
    container.place(relx=0.5, rely=0.5, anchor="center")

    card = tk.Frame(
        container, bg="#16213E", padx=40, pady=30,
        highlightbackground="#E94560", highlightthickness=2,
    )
    card.pack()

    tk.Label(card, text="SafeLock", font=("Arial", 32, "bold"),
             fg="#E94560", bg="#16213E").pack(pady=(0, 5))
    tk.Label(card, text="Screen Locked", font=("Arial", 13),
             fg="#8888AA", bg="#16213E").pack(pady=(0, 20))
    tk.Label(card, text="Enter Password:", font=("Arial", 12),
             fg="#8888AA", bg="#16213E").pack(anchor="w", pady=(0, 5))

    # 密码输入框 - 用真正的 Entry 组件
    pwd_entry = tk.Entry(
        card, font=("Consolas", 18), fg="#FFFFFF", bg="#1A1A3E",
        insertbackground="#FFFFFF", show="\u2022",  # 圆点显示密码
        relief="solid", bd=1, highlightthickness=0,
    )
    pwd_entry.pack(fill="x", ipady=8, pady=(0, 10))
    pwd_entry.focus_set()

    # 错误提示
    err_label = tk.Label(card, text="", font=("Arial", 11),
                         fg="#E94560", bg="#16213E")
    err_label.pack(pady=(0, 5))

    tk.Label(card, text="Press Enter to unlock", font=("Arial", 11),
             fg="#8888AA", bg="#16213E").pack(pady=(10, 0))

    # ── 密码验证逻辑 ──
    def on_enter(event):
        global is_locked
        pwd = pwd_entry.get()
        if hash_password(pwd) == config.get("password_hash"):
            # 解锁
            is_locked = False
            uninstall_hooks()
            try:
                root.destroy()
            except Exception:
                pass
        else:
            err_label.config(text="Password incorrect!")
            pwd_entry.delete(0, "end")
            pwd_entry.focus_set()

    def on_key(event):
        # 清除错误提示
        if err_label.cget("text"):
            err_label.config(text="")

    pwd_entry.bind("<Return>", on_enter)
    pwd_entry.bind("<Key>", on_key)

    # ── 窗口置顶 ──
    def force_top():
        if not is_locked:
            return
        try:
            hwnd = root.winfo_id()
            if hwnd:
                # SWP_NOMOVE=0x0002 | SWP_NOSIZE=0x0001 | SWP_NOACTIVATE=0x0010
                user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0003 | 0x0010)
        except Exception:
            pass
        try:
            root.after(500, force_top)
        except Exception:
            pass

    # 安装全局钩子
    install_hooks()

    # 延迟一帧确保窗口已创建再获取HWND
    root.update_idletasks()
    root.focus_force()
    pwd_entry.focus_set()
    root.after(100, force_top)

    # 持续确保 Entry 有焦点（因为鼠标被拦截了无法点击聚焦）
    def keep_focus():
        if not is_locked:
            return
        try:
            pwd_entry.focus_set()
        except Exception:
            pass
        try:
            root.after(200, keep_focus)
        except Exception:
            pass

    root.after(300, keep_focus)

    # 运行主循环
    try:
        root.mainloop()
    except Exception:
        pass


# ─── 托盘图标 ─────────────────────────────────────────────────
def create_tray_icon_image():
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([10, 28, 54, 56], radius=6, fill=(233, 69, 96, 255))
    draw.arc([16, 8, 48, 36], start=0, end=180, fill=(233, 69, 96, 255), width=8)
    draw.ellipse([27, 36, 37, 46], fill=(26, 26, 46, 255))
    return img


def change_password():
    import tkinter as tk
    from tkinter import simpledialog, messagebox

    root = tk.Tk()
    root.withdraw()

    old = simpledialog.askstring("SafeLock", "Enter current password:", show="*", parent=root)
    if not old or hash_password(old) != config.get("password_hash"):
        if old:
            messagebox.showerror("Error", "Wrong password!", parent=root)
        root.destroy()
        return

    new = simpledialog.askstring("SafeLock", "Enter new password:", show="*", parent=root)
    if not new:
        root.destroy()
        return

    confirm = simpledialog.askstring("SafeLock", "Confirm new password:", show="*", parent=root)
    if new != confirm:
        messagebox.showerror("Error", "Passwords do not match!", parent=root)
        root.destroy()
        return

    config["password_hash"] = hash_password(new)
    config["hint"] = ""
    save_config(config)
    messagebox.showinfo("SafeLock", "Password updated!", parent=root)
    root.destroy()


def first_run_dialog():
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "SafeLock",
        "Welcome to SafeLock!\n\n"
        "Default password: 1234\n\n"
        "Right-click tray icon to lock screen.\n"
        "Please change your password ASAP!",
        parent=root,
    )
    root.destroy()


def on_lock(icon, item):
    global is_locked
    if not is_locked:
        t = threading.Thread(target=create_lock_window, daemon=True)
        t.start()


def on_change_pwd(icon, item):
    t = threading.Thread(target=change_password, daemon=True)
    t.start()


def on_quit(icon, item):
    global is_locked
    if is_locked:
        return
    icon.stop()
    sys.exit(0)


# ─── 入口 ─────────────────────────────────────────────────────
if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        threading.Timer(0.5, first_run_dialog).start()

    icon_image = create_tray_icon_image()
    menu = pystray.Menu(
        pystray.MenuItem("Lock Screen", on_lock, default=True),
        pystray.MenuItem("Change Password", on_change_pwd),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_quit),
    )
    tray_icon = pystray.Icon("SafeLock", icon_image, "SafeLock", menu)
    tray_icon.run()
