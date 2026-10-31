"""Thin ctypes wrappers around the Win32 calls RAFK needs (no external deps)."""
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
SW_RESTORE = 9

# Scan codes (set 1) — Roblox reads scan codes, not virtual keys.
SCANCODES = {
    "space": 0x39,
    "w": 0x11,
    "a": 0x1E,
    "s": 0x1F,
    "d": 0x20,
    "i": 0x17,
    "o": 0x18,
}

ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _process_name(pid: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(len(buf))
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value.rsplit("\\", 1)[-1]
        return ""
    finally:
        kernel32.CloseHandle(handle)


def find_windows(process_name: str) -> list[int]:
    """Return handles of visible top-level windows owned by `process_name`."""
    found: list[int] = []
    target = process_name.lower()

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if _process_name(pid.value).lower() == target:
            found.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return found


def foreground_window() -> int:
    return user32.GetForegroundWindow()


def focus_window(hwnd: int) -> bool:
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    # Alt tap unlocks SetForegroundWindow when we're not the foreground process.
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)
    return bool(user32.SetForegroundWindow(hwnd))


def _send_scan(scan: int, up: bool) -> None:
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0)
    inp = INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(0, scan, flags, 0, 0)))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def press_key(name: str, hold: float = 0.1) -> None:
    scan = SCANCODES[name.lower()]
    _send_scan(scan, up=False)
    time.sleep(hold)
    _send_scan(scan, up=True)
