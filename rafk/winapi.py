"""Thin ctypes wrappers around the Win32 calls RAFK needs (no external deps)."""
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
VK_MENU = 0x12

SW_MINIMIZE = 6
SW_RESTORE = 9

MOD_NOREPEAT = 0x4000
WM_QUIT = 0x0012
WM_HOTKEY = 0x0312

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

# Scan codes (set 1) — Roblox reads scan codes, not virtual keys.
# Value is (scan code, extended flag).
SCANCODES: dict[str, tuple[int, bool]] = {
    "space": (0x39, False),
    "w": (0x11, False),
    "a": (0x1E, False),
    "s": (0x1F, False),
    "d": (0x20, False),
    "i": (0x17, False),
    "o": (0x18, False),
    "left": (0x4B, True),
    "right": (0x4D, True),
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


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ULONG_PTR),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.GetForegroundWindow.restype = wintypes.HWND
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.OpenProcess.restype = wintypes.HANDLE


# --- Windows -----------------------------------------------------------------


def enum_windows() -> list[int]:
    handles: list[int] = []

    def callback(hwnd, _lparam):
        handles.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return handles


def window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def window_title(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, len(buf))
    return buf.value


def window_class(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, len(buf))
    return buf.value


def is_visible(hwnd: int) -> bool:
    return bool(user32.IsWindowVisible(hwnd))


def is_minimized(hwnd: int) -> bool:
    return bool(user32.IsIconic(hwnd))


def is_hung(hwnd: int) -> bool:
    return bool(user32.IsHungAppWindow(hwnd))


def is_window(hwnd: int) -> bool:
    return bool(user32.IsWindow(hwnd))


def foreground_window() -> int:
    return user32.GetForegroundWindow() or 0


def focus_window(hwnd: int, attempts: int = 5) -> bool:
    if is_minimized(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    for _ in range(attempts):
        if foreground_window() == hwnd:
            return True
        # Windows only lets the foreground thread change focus: borrow its input
        # state, and tap Alt, which also lifts the foreground lock.
        fg_thread = user32.GetWindowThreadProcessId(foreground_window(), None)
        own_thread = kernel32.GetCurrentThreadId()
        attached = fg_thread and fg_thread != own_thread and user32.AttachThreadInput(own_thread, fg_thread, True)
        try:
            user32.keybd_event(VK_MENU, 0, 0, 0)
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        finally:
            if attached:
                user32.AttachThreadInput(own_thread, fg_thread, False)
        time.sleep(0.1)
    return foreground_window() == hwnd


def minimize_window(hwnd: int) -> None:
    user32.ShowWindow(hwnd, SW_MINIMIZE)


# --- Processes ---------------------------------------------------------------


def list_processes() -> list[tuple[int, str]]:
    """Return (pid, exe name) for every running process."""
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == INVALID_HANDLE_VALUE:
        return []
    result: list[tuple[int, str]] = []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            result.append((entry.th32ProcessID, entry.szExeFile))
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    return result


def terminate_process(pid: int) -> bool:
    handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not handle:
        return False
    try:
        return bool(kernel32.TerminateProcess(handle, 1))
    finally:
        kernel32.CloseHandle(handle)


# --- Input -------------------------------------------------------------------


def _send_scan(scan: int, extended: bool, up: bool) -> None:
    flags = KEYEVENTF_SCANCODE
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    if up:
        flags |= KEYEVENTF_KEYUP
    inp = INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(0, scan, flags, 0, 0)))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def press_key(name: str, hold: float = 0.1) -> None:
    scan, extended = SCANCODES[name.lower()]
    _send_scan(scan, extended, up=False)
    try:
        time.sleep(hold)
    finally:
        _send_scan(scan, extended, up=True)


def tick_ms() -> int:
    return kernel32.GetTickCount() & 0xFFFFFFFF


def last_input_tick() -> int:
    """Tick (ms, 32-bit) of the last keyboard/mouse input, ours included."""
    info = LASTINPUTINFO(cbSize=ctypes.sizeof(LASTINPUTINFO))
    user32.GetLastInputInfo(ctypes.byref(info))
    return info.dwTime & 0xFFFFFFFF


def tick_diff(later: int, earlier: int) -> int:
    """Milliseconds from `earlier` to `later`, wrap-around safe."""
    return (later - earlier) & 0xFFFFFFFF


# --- Power -------------------------------------------------------------------


def prevent_sleep(enabled: bool) -> None:
    flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if enabled else 0)
    kernel32.SetThreadExecutionState(flags)


# --- Hotkeys -----------------------------------------------------------------


def vk_from_name(name: str) -> int:
    """Map 'F1'..'F24' to a virtual-key code."""
    upper = name.strip().upper()
    if upper.startswith("F") and upper[1:].isdigit() and 1 <= int(upper[1:]) <= 24:
        return 0x70 + int(upper[1:]) - 1
    raise ValueError(f"Unsupported hotkey {name!r} (use F1..F24)")


def current_thread_id() -> int:
    return kernel32.GetCurrentThreadId()


def register_hotkey(hotkey_id: int, vk: int) -> bool:
    return bool(user32.RegisterHotKey(None, hotkey_id, MOD_NOREPEAT, vk))


def unregister_hotkey(hotkey_id: int) -> None:
    user32.UnregisterHotKey(None, hotkey_id)


def wait_hotkey() -> int | None:
    """Block until a WM_HOTKEY arrives on this thread; None on WM_QUIT."""
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_HOTKEY:
            return msg.wParam
    return None


def post_quit(thread_id: int) -> None:
    user32.PostThreadMessageW(thread_id, WM_QUIT, 0, 0)
