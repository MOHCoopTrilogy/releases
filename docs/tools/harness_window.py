#!/usr/bin/env python3
"""harness_window.py - the shared BACKGROUND TEST WINDOW policy for every harness that launches a private game client.

Policy + evidence: docs/proposals/test_window_policy_2026-09-27/README.md. The user plays on DISPLAY1; test clients live
on DISPLAY2 and must never take focus, grab the mouse, make a sound or paint on DISPLAY1.

What it does, and why each piece is needed (measured 2026-09-27, Windows 11 26200, SDL 2.32.8):
  1. env SDL_WINDOW_NO_ACTIVATION_WHEN_SHOWN=1 -> SDL's WIN_ShowWindow uses SW_SHOWNA (never activates). This is the
     ONLY thing that stops activation: STARTUPINFO.wShowWindow does NOT override a first ShowWindow(SW_SHOWNA)
     (both SW_HIDE and SW_SHOWMINNOACTIVE were ignored). STARTF_USESHOWWINDOW=SW_SHOWNOACTIVATE is still passed as a
     fallback for a build whose SDL would call plain SW_SHOW.
  2. the exe is CONSOLE-subsystem: CREATE_NO_WINDOW, or a parent without a console gets a new console window.
  3. created SUSPENDED, a pid-filtered WinEvent hook is installed, THEN resumed - so window creation cannot be missed.
     The engine has no window-position cvar (sdl_glimp.c: x = y = SDL_WINDOWPOS_UNDEFINED = centred on display 0,
     the PRIMARY). The hook moves the still-HIDDEN window with SetWindowPos(... SWP_NOSENDCHANGING): that lands
     immediately even while the engine thread is busy in pixel-format/driver setup; without NOSENDCHANGING the call
     waits for the engine to pump and the window is first shown on DISPLAY1; SWP_ASYNCWINDOWPOS likewise lands late.
     The mover runs on its own thread because the call still blocks until the engine pumps WM_WINDOWPOSCHANGED.
  4. a watchdog polls every few ms for the whole run: foreground (plus an EVENT_SYSTEM_FOREGROUND hook), window on any
     display other than the test display (re-placed), mouse capture (GetGUIThreadInfo) and ClipCursor changes, and
     optionally the process's audio-session peak meter. Every violation is logged and kept in .report(), and it is
     ENFORCED (bug-3147): the client's job is terminated at once and, for a foreground theft, the foreground is
     handed back to the window that had it.
  0. THE GUARD (bug-3147): an out-of-process watcher can only react. A foreground theft happened anyway (a lost
     placement race + an activation Windows granted the test window - no engine or SDL code asks for one), so the
     launcher now puts harness_cbt/hzm_cbt.dll on the client's main thread as a WH_CBT hook: HCBT_CREATEWND creates
     every top-level window ON the test display (no race), HCBT_ACTIVATE is refused (the window can never become
     active, whoever asks). Launch is REFUSED when the guard cannot be built/installed, unless the SDL hint is proven
     (sdl_preflight) AND the engine placement patch is in. The client also runs in a job object (killed with the
     harness; no display-mode / system-parameter / desktop changes).
  5. command-line policy (apply_policy): r_fullscreen 0, r_mode -1 + a size that fits the test display, r_noborder 1,
     in_mouse 0, s_volume 0 are forced as +set (they must be set before the window/IN_Init/sound init);
     in_nograb 1, s_musicvolume 0 (and com_maxfpsUnfocused 60 unless the harness set it) are added while the 31 '+'
     budget lasts (bug-2996) and are otherwise returned as cfg lines for the harness's boot cfg. The process runs at
     BELOW_NORMAL priority. Both keep a background test from taking GPU/CPU time from the user's game. s_volume 0 alone already zeroes the OpenAL listener
     gain (snd_openal_new.cpp: listener gain = s_volume^2, music = s_volume * s_musicvolume).

Never: SetForegroundWindow / BringWindowToTop / SwitchToThisWindow / AttachThreadInput, SendInput / keybd_event /
mouse_event / SetCursorPos / ClipCursor, desktop screen grabs (bug-3053). Keys and clicks go to the test HWND only
(post_key / post_click below); captures are PrintWindow of the test HWND or the engine's own `screenshot`.

Library:
    import harness_window as hw
    args, cfg_lines = hw.apply_policy([exe, "+set", ...])          # or let launch_background do it
    with hw.launch_background(exe, args_without_exe, cwd, env=None, log=print) as c:
        c.pid, c.hwnd(), c.post_key(vk), c.capture_png(path) ...
        c.report()                                                # violations so far
    # A game client is ONLY ever started by launch_background (suspended start -> guard + job -> resume). There is
    # no attach-after-launch path any more: hold() was removed (bug-3147) because a guard installed after the fact
    # cannot cover the first window. popen_kwargs() is for console servers (omohaaded), never for a client.
CLI:
    python harness_window.py displays      monitors, the chosen test display and the current foreground window
"""
import ctypes, ctypes.wintypes as wt, os, subprocess, sys, threading, time

__all__ = ["apply_policy", "popen_kwargs", "launch_background", "test_display", "monitors", "PolicyError",
           "NoTestDisplay", "BackgroundClient", "Watcher", "audio_sessions", "PLUS_LIMIT", "sdl_preflight",
           "ensure_cbt_dll", "ENFORCE_KINDS"]

PLUS_LIMIT = 31                       # Com_ParseCommandLine keeps MAX_CONSOLE_LINES 32 lines = 31 '+' commands
SDL_ENV = {"SDL_WINDOW_NO_ACTIVATION_WHEN_SHOWN": "1"}
CREATE_SUSPENDED, CREATE_NEW_PROCESS_GROUP, CREATE_NO_WINDOW = 0x4, 0x200, 0x08000000
BELOW_NORMAL_PRIORITY_CLASS = 0x4000
UNFOCUSED_FPS = 60    # the test window is never focused: com_maxfpsUnfocused caps it so it does not eat the GPU the
#                       user's game is using. Pass unfocused_fps=0 for a perf run (and do not run perf while they play).
SW_SHOWNOACTIVATE = 4
IGNORE_CLASSES = {"IME", "MSCTFIME UI"}
# HIDDEN windows are pre-placed only for these classes (the SDL game window + SDL's 10x10 GL probe windows); the
# driver's own hidden helpers (NVOpenGLPbuffer, ...) are left alone. VISIBLE windows of any class are held.
PRESHOW_CLASSES = ("SDL_app",)
# violations that end the run at once (bug-3147: the watchdog used to log a 100 s foreground theft and carry on)
ENFORCE_KINDS = {"foreground", "off_test_display", "mouse_capture", "cursor_clip", "audible", "guard_missing"}
HERE = os.path.dirname(os.path.abspath(__file__))
CBT_SRC = os.path.join(HERE, "harness_cbt", "hzm_cbt.c")
CACHE = os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Users\Public"), "hzm_harness")
SDL_HINT_MIN = (2, 0, 22, 0)      # the no-activation hint is in SDL_hints.h from 2.0.22 on (checked: 2.0.22 .. 2.32.8)

u32 = ctypes.WinDLL("user32", use_last_error=True)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll")
try:
    dwm = ctypes.WinDLL("dwmapi")
except OSError:
    dwm = None

WINEVENTPROC = ctypes.WINFUNCTYPE(None, wt.HANDLE, wt.DWORD, wt.HWND, wt.LONG, wt.LONG, wt.DWORD, wt.DWORD)
ENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
MONENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HMONITOR, wt.HDC, ctypes.POINTER(wt.RECT), wt.LPARAM)
u32.SetWinEventHook.restype = wt.HANDLE
u32.SetWinEventHook.argtypes = [wt.DWORD, wt.DWORD, wt.HMODULE, WINEVENTPROC, wt.DWORD, wt.DWORD, wt.DWORD]
u32.UnhookWinEvent.argtypes = [wt.HANDLE]
u32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
u32.GetForegroundWindow.restype = wt.HWND
u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
u32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
u32.MsgWaitForMultipleObjects.argtypes = [wt.DWORD, ctypes.c_void_p, wt.BOOL, wt.DWORD, wt.DWORD]
u32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
u32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
k32.OpenProcess.restype = wt.HANDLE
k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
k32.CloseHandle.argtypes = [wt.HANDLE]
u32.IsWindow.argtypes = [wt.HWND]
u32.IsWindowVisible.argtypes = [wt.HWND]
u32.IsIconic.argtypes = [wt.HWND]
u32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
u32.GetAncestor.restype = wt.HWND
u32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
u32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
ntdll.NtResumeProcess.argtypes = [wt.HANDLE]
k32.LoadLibraryW.restype = wt.HMODULE
k32.LoadLibraryW.argtypes = [wt.LPCWSTR]
k32.GetProcAddress.restype = ctypes.c_void_p
k32.GetProcAddress.argtypes = [wt.HMODULE, ctypes.c_char_p]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.CreateJobObjectW.restype = wt.HANDLE
k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wt.LPCWSTR]
k32.SetInformationJobObject.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD]
k32.AssignProcessToJobObject.argtypes = [wt.HANDLE, wt.HANDLE]
k32.TerminateJobObject.argtypes = [wt.HANDLE, wt.UINT]
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
u32.SetWindowsHookExW.restype = wt.HANDLE
u32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, wt.HMODULE, wt.DWORD]
u32.UnhookWindowsHookEx.argtypes = [wt.HANDLE]
u32.SetForegroundWindow.argtypes = [wt.HWND]

EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_CAPTURESTART = 0x0003, 0x0008
EVENT_OBJECT_CREATE, EVENT_OBJECT_SHOW = 0x8000, 0x8002
WINEVENT_OUTOFCONTEXT = 0x0
SWP_NOSIZE, SWP_NOZORDER, SWP_NOACTIVATE, SWP_NOOWNERZORDER, SWP_NOSENDCHANGING = 0x1, 0x4, 0x10, 0x200, 0x400
PLACE_FLAGS = SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOOWNERZORDER | SWP_NOSENDCHANGING
DPI_PER_MONITOR_V2 = ctypes.c_void_p(-4)


class PolicyError(Exception):
    pass


class NoTestDisplay(Exception):
    pass


class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("flags", wt.DWORD), ("hwndActive", wt.HWND), ("hwndFocus", wt.HWND),
                ("hwndCapture", wt.HWND), ("hwndMenuOwner", wt.HWND), ("hwndMoveSize", wt.HWND),
                ("hwndCaret", wt.HWND), ("rcCaret", wt.RECT)]


class _MONITORINFOEX(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD),
                ("szDevice", wt.WCHAR * 32)]


class _TE32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ThreadID", wt.DWORD),
                ("th32OwnerProcessID", wt.DWORD), ("tpBasePri", ctypes.c_long), ("tpDeltaPri", ctypes.c_long),
                ("dwFlags", wt.DWORD)]


def _threads(pid):
    """thread ids of `pid` in Toolhelp order (creation order: [0] is the main thread)"""
    snap = k32.CreateToolhelp32Snapshot(0x4, 0)
    te = _TE32()
    te.dwSize = ctypes.sizeof(te)
    res = []
    ok = k32.Thread32First(snap, ctypes.byref(te))
    while ok:
        if te.th32OwnerProcessID == pid:
            res.append(te.th32ThreadID)
        ok = k32.Thread32Next(snap, ctypes.byref(te))
    k32.CloseHandle(snap)
    return res


def ensure_cbt_dll():
    """build (once per source version) and return the in-process guard DLL; raises if MSVC is unavailable"""
    import hashlib
    src = open(CBT_SRC, "rb").read()
    out = os.path.join(CACHE, "hzm_cbt_%s.dll" % hashlib.sha1(src).hexdigest()[:8])
    if os.path.exists(out):
        return out
    os.makedirs(CACHE, exist_ok=True)
    vswhere = os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                           r"Microsoft Visual Studio\Installer\vswhere.exe")
    vs = subprocess.run([vswhere, "-latest", "-products", "*", "-property", "installationPath"], capture_output=True,
                        text=True, creationflags=CREATE_NO_WINDOW).stdout.strip() if os.path.exists(vswhere) else ""
    vc = os.path.join(vs, r"VC\Auxiliary\Build\vcvars64.bat")
    if not vs or not os.path.exists(vc):
        raise RuntimeError("no MSVC (vcvars64.bat) to build " + CBT_SRC)
    tmp = out + ".obj.d"
    os.makedirs(tmp, exist_ok=True)
    cmd = 'call "%s" >nul && cl /nologo /O2 /W3 /LD /MT "%s" user32.lib kernel32.lib /Fe:"%s" /Fo:"%s\\\\" /link /NOLOGO' % (
        vc, CBT_SRC, out, tmp)
    r = subprocess.run('cmd /s /c "' + cmd + '"', capture_output=True, text=True, cwd=tmp,
                       creationflags=CREATE_NO_WINDOW)
    if r.returncode != 0 or not os.path.exists(out):
        raise RuntimeError("hzm_cbt build failed: " + (r.stdout + r.stderr)[-600:])
    return out


def _file_version(path):
    ver = ctypes.WinDLL("version")
    n = ver.GetFileVersionInfoSizeW(path, None)
    if not n:
        return None
    buf = ctypes.create_string_buffer(n)
    if not ver.GetFileVersionInfoW(path, 0, n, buf):
        return None
    ptr, ln = ctypes.c_void_p(), wt.UINT()
    if not ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(ln)):
        return None
    ms, ls = ctypes.cast(ptr, ctypes.POINTER(wt.DWORD * 4)).contents[2:4]
    return (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)


def sdl_preflight(exe):
    """Which SDL does `exe` really run, and can it be shown to honour SDL_WINDOW_NO_ACTIVATION_WHEN_SHOWN?
    An exe importing SDL2.dll loads the one next to it (the exe's directory is searched first); otherwise SDL is
    static and the exe itself must carry the hint. ok = the hint string is in the SDL code and its version >= 2.0.22."""
    import hashlib
    data = open(exe, "rb").read()
    imports = b"sdl2.dll" in data.lower()
    sdl = os.path.join(os.path.dirname(os.path.abspath(exe)), "SDL2.dll") if imports else exe
    res = {"exe": exe, "sdl": sdl, "static": not imports}
    if not os.path.exists(sdl):
        res.update(ok=False, reason="SDL2.dll is not next to the exe")
        return res
    blob = open(sdl, "rb").read() if imports else data
    res["sdl_sha1"] = hashlib.sha1(blob).hexdigest()[:8]
    res["hint_in_code"] = b"SDL_WINDOW_NO_ACTIVATION_WHEN_SHOWN" in blob
    res["version"] = _file_version(sdl) if imports else None
    res["ok"] = res["hint_in_code"] and (res["version"] is None or tuple(res["version"]) >= SDL_HINT_MIN)
    if not res["ok"]:
        res["reason"] = "SDL %s does not reference the no-activation hint" % (res["version"],)
    return res


class _JOBBASIC(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wt.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wt.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wt.DWORD), ("SchedulingClass", wt.DWORD)]


class _JOBEXT(ctypes.Structure):
    _fields_ = [("Basic", _JOBBASIC), ("Io", ctypes.c_uint64 * 6), ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t)]


def _make_job(kill_on_close=True, ui_limits=True):
    """a job for the client tree: TerminateJobObject kills it in one call; KILL_ON_JOB_CLOSE ends it with the harness;
    UI limits: no display-mode change (the user's monitor), no system parameters, no desktop switch, no logoff"""
    job = k32.CreateJobObjectW(None, None)
    if not job:
        return None
    if kill_on_close:
        info = _JOBEXT()
        info.Basic.LimitFlags = 0x2000                   # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
    if ui_limits:   # untested against the real engine yet (bug-3147) - pass job_ui_limits=False if a run breaks
        ui = wt.DWORD(0x08 | 0x10 | 0x40 | 0x80)        # SYSTEMPARAMETERS | DISPLAYSETTINGS | DESKTOP | EXITWINDOWS
        k32.SetInformationJobObject(job, 4, ctypes.byref(ui), 4)
    return job


def _dpi_aware():
    """per-thread: physical pixels, so rects match the monitor layout whatever the scaling"""
    try:
        return u32.SetThreadDpiAwarenessContext(DPI_PER_MONITOR_V2)
    except (AttributeError, OSError):
        return None


def _r(rc):
    return (rc.left, rc.top, rc.right, rc.bottom)


def monitors():
    old = _dpi_aware()
    res = []

    def cb(h, dc, rc, lp):
        mi = _MONITORINFOEX()
        mi.cbSize = ctypes.sizeof(mi)
        u32.GetMonitorInfoW(h, ctypes.byref(mi))
        res.append({"device": mi.szDevice, "rect": _r(mi.rcMonitor), "work": _r(mi.rcWork),
                    "primary": bool(mi.dwFlags & 1)})
        return True
    u32.EnumDisplayMonitors(None, None, MONENUMPROC(cb), 0)
    if old:
        u32.SetThreadDpiAwarenessContext(old)
    return res


def test_display(name=None):
    """the monitor test windows live on: $HZM_TEST_DISPLAY (e.g. \\\\.\\DISPLAY2), else the first non-primary one.
    Refuses (NoTestDisplay) rather than fall back to the primary - that is the user's screen."""
    name = name or os.environ.get("HZM_TEST_DISPLAY")
    mons = monitors()
    for m in mons:
        if name and m["device"].lower() == name.lower():
            if m["primary"]:
                raise NoTestDisplay("%s is the PRIMARY display - test windows never go there" % name)
            return m
    if name:
        raise NoTestDisplay("no display named %s (have %s)" % (name, [m["device"] for m in mons]))
    for m in mons:
        if not m["primary"]:
            return m
    raise NoTestDisplay("only one display connected - no background display for a test window")


def _size(rect):
    return rect[2] - rect[0], rect[3] - rect[1]


def _overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


# ------------------------------------------------------------------------------------------------ command line policy
def _plus_count(args):
    return sum(1 for a in args if isinstance(a, str) and a.startswith("+"))


def _set_index(args):
    idx = {}
    for i, a in enumerate(args):
        if a.lower() == "+set" and i + 2 < len(args):
            idx[args[i + 1].lower()] = i + 2
    return idx


def sdl_display_index(display):
    """SDL2's display index for a monitor: WIN_InitModes adds the primary first, then the rest in adapter order"""
    mons = sorted(monitors(), key=lambda m: (not m["primary"], m["device"]))
    return next(i for i, m in enumerate(mons) if m["device"] == display["device"])


def supports_window_cvars(gamedir):
    """True once the proposed engine patch (engine_window_placement.patch: r_windowDisplay / vid_xpos / vid_ypos,
    compiled into the renderer DLLs via sdl_glimp.c) is in the renderer DLLs next to the exe"""
    try:
        dlls = [f for f in os.listdir(gamedir) if f.lower().startswith("renderer_") and f.lower().endswith(".dll")]
        return bool(dlls) and all(b"r_windowDisplay" in open(os.path.join(gamedir, f), "rb").read() for f in dlls)
    except OSError:
        return False


def apply_policy(args, width=None, height=None, display=None, noborder=True, window_display=None,
                 unfocused_fps=UNFOCUSED_FPS):
    """args = the full argv (exe first). Returns (new_args, cfg_lines): cfg_lines are the soft policy cvars that did
    not fit the 31 '+' budget - put them in the harness's boot cfg. Raises PolicyError if the hard ones do not fit."""
    d = display or test_display()
    dw, dh = _size(d["rect"])
    args = list(args)
    idx = _set_index(args)
    if width is None:
        width = int(args[idx["r_customwidth"]]) if "r_customwidth" in idx else dw
    if height is None:
        height = int(args[idx["r_customheight"]]) if "r_customheight" in idx else dh
    if width > dw or height > dh:
        width, height = min(width, dw), min(height, dh)
    hard = [("r_fullscreen", "0"), ("r_mode", "-1"), ("r_customwidth", str(width)), ("r_customheight", str(height)),
            ("in_mouse", "0"), ("s_volume", "0"),
            # a FRESH homepath otherwise triggers the engine's first-launch auto-detect (sdl_glimp.c, bug-753
            # addendum): it overrides r_mode/r_custom* with the PRIMARY display's desktop size (3440x1440 here)
            ("r_resAutoDetected", "1")]
    if noborder:
        hard.append(("r_noborder", "1"))
    soft = [("in_nograb", "1"), ("s_musicvolume", "0")]
    # defaults: added only when the harness did not set them itself (an explicit value wins)
    defaults = [("com_maxfpsUnfocused", str(unfocused_fps))]
    if window_display is not None:   # patched engine: created on the test display, no pre-show race at all
        soft.insert(0, ("r_windowDisplay", str(window_display)))

    def first_cmd():   # new +sets go before the first non-set '+' command, so a trailing +exec still reads last
        return next((i for i, a in enumerate(args) if a.startswith("+") and a.lower() != "+set"), len(args))

    for k, v in hard:
        if k.lower() in idx:
            args[idx[k.lower()]] = v
        else:
            i = first_cmd()
            args[i:i] = ["+set", k, v]
            idx = _set_index(args)
    if _plus_count(args) > PLUS_LIMIT:
        raise PolicyError("%d '+' commands after the background policy; the engine keeps only %d (bug-2996) - move "
                          "runtime-only cvars into the boot cfg" % (_plus_count(args), PLUS_LIMIT))
    cfg_lines = []
    idx = _set_index(args)
    for k, v in soft:
        if k.lower() in idx:
            args[idx[k.lower()]] = v
        elif _plus_count(args) + 1 <= PLUS_LIMIT:
            i = first_cmd()
            args[i:i] = ["+set", k, v]
            idx = _set_index(args)
        else:
            cfg_lines.append("set %s %s" % (k, v))
    for k, v in defaults:
        if k.lower() in idx:
            continue
        if _plus_count(args) + 1 <= PLUS_LIMIT:
            i = first_cmd()
            args[i:i] = ["+set", k, v]
            idx = _set_index(args)
        else:
            cfg_lines.append("set %s %s" % (k, v))
    return args, cfg_lines


def popen_kwargs(env=None, below_normal=True):
    """kwargs for launching a CONSOLE SERVER (omohaaded) or other helper exe: no console window, below-normal
    priority, stdio closed. NOT for a game client - clients go through launch_background (guard + job + watchdog)."""
    e = dict(os.environ)
    e.update(env or {})
    e.update(SDL_ENV)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = SW_SHOWNOACTIVATE
    flags = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP | (BELOW_NORMAL_PRIORITY_CLASS if below_normal else 0)
    return {"env": e, "startupinfo": si, "creationflags": flags,
            "close_fds": True, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL}


# ------------------------------------------------------------------------------------------------ window helpers
def _pid_of(hwnd):
    p = wt.DWORD()
    tid = u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
    return p.value, tid


def _cls(hwnd):
    b = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, b, 256)
    return b.value


def _title(hwnd):
    b = ctypes.create_unicode_buffer(512)
    u32.GetWindowTextW(hwnd, b, 512)
    return b.value


def _wrect(hwnd):
    rc = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(rc))
    return _r(rc)


def _frame(hwnd):
    """the VISIBLE frame (DWM extended frame bounds), falling back to the window rect"""
    if dwm is not None:
        rc = wt.RECT()
        if dwm.DwmGetWindowAttribute(wt.HWND(hwnd), 9, ctypes.byref(rc), ctypes.sizeof(rc)) == 0 and rc.right > rc.left:
            return _r(rc)
    return _wrect(hwnd)


def windows_of(pid, visible_only=False):
    res = []

    def cb(h, lp):
        if _pid_of(h)[0] == pid and _cls(h) not in IGNORE_CLASSES:
            if not visible_only or u32.IsWindowVisible(h):
                res.append(h)
        return True
    u32.EnumWindows(ENUMPROC(cb), 0)
    return res


def audio_sessions(pid):
    """[(state, peak)] for every audio session of `pid` on every active render endpoint. state 1 = active.
    Pure ctypes COM (no pycaw). Must run on a thread that may call CoInitializeEx."""
    ole = ctypes.OleDLL("ole32")
    ole.CoInitializeEx(None, 0)   # COINIT_MULTITHREADED; S_FALSE/RPC_E_CHANGED_MODE are fine
    GUID = ctypes.c_byte * 16

    def guid(s):
        g = GUID()
        ole.CLSIDFromString(ctypes.c_wchar_p(s), ctypes.byref(g))
        return g

    VP, U32, I32, HR = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int32, ctypes.HRESULT

    def call(obj, index, types, *args, restype=HR):
        vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(restype, VP, *types)(vtbl[index])(obj, *args)

    def release(obj):
        if obj is not None and obj.value:
            call(obj, 2, (), restype=ctypes.c_ulong)

    out = []
    enum = ctypes.c_void_p()
    ole.CoCreateInstance(ctypes.byref(guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")), None, 23,
                         ctypes.byref(guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")), ctypes.byref(enum))
    coll = ctypes.c_void_p()
    call(enum, 3, (I32, U32, VP), 0, 1, ctypes.byref(coll))
    n = wt.UINT()
    call(coll, 3, (VP,), ctypes.byref(n))
    iid_mgr2 = guid("{77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F}")
    iid_ctl2 = guid("{BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D}")
    iid_meter = guid("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")
    for i in range(n.value):
        dev = ctypes.c_void_p()
        call(coll, 4, (U32, VP), i, ctypes.byref(dev))
        mgr = ctypes.c_void_p()
        try:
            call(dev, 3, (VP, U32, VP, VP), ctypes.byref(iid_mgr2), 23, None, ctypes.byref(mgr))
            senum = ctypes.c_void_p()
            call(mgr, 5, (VP,), ctypes.byref(senum))
            cnt = ctypes.c_int()
            call(senum, 3, (VP,), ctypes.byref(cnt))
            for j in range(cnt.value):
                ctl = ctypes.c_void_p()
                call(senum, 4, (I32, VP), j, ctypes.byref(ctl))
                ctl2, meter = ctypes.c_void_p(), ctypes.c_void_p()
                try:
                    call(ctl, 0, (VP, VP), ctypes.byref(iid_ctl2), ctypes.byref(ctl2))
                    spid = wt.DWORD()
                    call(ctl2, 14, (VP,), ctypes.byref(spid))
                    if spid.value == pid:
                        st = ctypes.c_int()
                        call(ctl2, 3, (VP,), ctypes.byref(st))
                        call(ctl, 0, (VP, VP), ctypes.byref(iid_meter), ctypes.byref(meter))
                        pk = ctypes.c_float()
                        call(meter, 3, (VP,), ctypes.byref(pk))
                        out.append((st.value, pk.value))
                except OSError:
                    pass
                finally:
                    release(meter)
                    release(ctl2)
                    release(ctl)
            release(senum)
        except OSError:
            pass
        finally:
            release(mgr)
            release(dev)
    release(coll)
    release(enum)
    return out


# ------------------------------------------------------------------------------------------------ the watchdog
class Watcher(threading.Thread):
    """Places every top-level window of `pid` on the test display, keeps it there, and records violations."""

    def __init__(self, pid, display=None, log=None, poll_ms=4, watch_audio=False, audio_every=0.25,
                 preshow_classes=PRESHOW_CLASSES, enforce=True, killer=None, cbt_dll=None, cbt_log=None,
                 cbt_required=False, others=None):
        super().__init__(daemon=True, name="harness_window-%d" % pid)
        self.pid = pid
        self.display = display or test_display()
        self.others = others if others is not None else \
            [m["rect"] for m in monitors() if m["rect"] != self.display["rect"]]
        self.primary = next((m["rect"] for m in monitors() if m["primary"]), None)
        self.logf = log or (lambda *a: print("[harness_window]", *a, file=sys.stderr, flush=True))
        self.poll = poll_ms
        self.watch_audio, self.audio_every = watch_audio, audio_every
        self.preshow = preshow_classes      # None = pre-place hidden windows of every class
        self.ready, self.stopping = threading.Event(), threading.Event()
        self.t0 = time.perf_counter()
        self.lock = threading.Lock()
        self.inflight = set()
        self.seen = {}                  # hwnd -> {"cls", "created", "first_visible", ...}
        self.violations = []            # {"kind", "t", "until", ...}
        self._open = {}                 # kind+hwnd -> violation dict still open
        self.placements = []
        self.fg_events = []
        self.audio = {"samples": 0, "sessions_seen": 0, "max_peak": 0.0, "active_samples": 0}
        vx, vy = u32.GetSystemMetrics(76), u32.GetSystemMetrics(77)
        self.virtual = (vx, vy, vx + u32.GetSystemMetrics(78), vy + u32.GetSystemMetrics(79))
        self.polls = 0
        self._last_enum = 0.0
        self._known = set()
        self.enforce, self.killer = enforce, killer
        self.killed = None              # the enforcement record, once it fired
        self.prev_fg = u32.GetForegroundWindow()   # the last foreground window that was NOT ours (restore target)
        self.fg_history = []            # (t, hwnd, pid, class) for EVERY foreground change - incident evidence
        self.cbt_dll, self.cbt_log, self.cbt_required = cbt_dll, cbt_log, cbt_required
        self.cbt = {"wanted": bool(cbt_dll), "installed": False}
        self._cbt_hook = None

    # ---- helpers
    def now(self):
        return round(time.perf_counter() - self.t0, 4)

    def log(self, *a):
        self.logf("t=%.3f" % self.now(), *a)

    @staticmethod
    def _clip():
        rc = wt.RECT()
        u32.GetClipCursor(ctypes.byref(rc))
        return _r(rc)

    def target_for(self, hwnd):
        """top-left so the window sits centred on the test display; if it is bigger than the display it hangs off the
        side AWAY from the primary, never onto it"""
        dl, dt, dr, db = self.display["rect"]
        wl, wtp, wr, wb = _wrect(hwnd)
        fl, ft, fr, fb = _frame(hwnd) if u32.IsWindowVisible(hwnd) else (wl, wtp, wr, wb)
        w, h = fr - fl, fb - ft
        pl, pt, pr, pb = self.primary or (0, 0, 0, 0)
        if w <= dr - dl:
            x = dl + (dr - dl - w) // 2
        else:
            x = dl if dl >= pr else dr - w
        if h <= db - dt:
            y = dt + (db - dt - h) // 2
        else:
            y = dt if dt >= pb else db - h
        return x - (fl - wl), y - (ft - wtp)   # convert visible-frame origin back to window-rect origin

    def place(self, hwnd, why):
        with self.lock:
            if hwnd in self.inflight:
                return
            self.inflight.add(hwnd)
        x, y = self.target_for(hwnd)
        before = _wrect(hwnd)
        rec = {"t": self.now(), "hwnd": hwnd, "why": why, "from": before, "to": (x, y),
               "visible": bool(u32.IsWindowVisible(hwnd))}
        self.placements.append(rec)

        def mv():
            rec["visible_at_call"] = bool(u32.IsWindowVisible(hwnd))   # False = placed before the first show
            a = time.perf_counter()
            ok = u32.SetWindowPos(hwnd, None, x, y, 0, 0, PLACE_FLAGS)
            rec.update({"ok": bool(ok), "returned_ms": round((time.perf_counter() - a) * 1000, 1),
                        "rect_after": _wrect(hwnd)})
            with self.lock:
                self.inflight.discard(hwnd)
        # SWP_NOSENDCHANGING applies the rect at once; the thread then only waits for WM_WINDOWPOSCHANGED delivery
        threading.Thread(target=mv, daemon=True).start()
        self.log("place", hex(hwnd), _cls(hwnd), why, before, "->", (x, y), "visible" if rec["visible"] else "hidden")

    def _on_other_display(self, hwnd):
        fr = _frame(hwnd)
        return any(_overlap(fr, o) > 0 for o in self.others)

    def _open_v(self, kind, key, **info):
        k = (kind, key)
        if k not in self._open:
            v = {"kind": kind, "t": self.now(), "until": None}
            v.update(info)
            self._open[k] = v
            self.violations.append(v)
            self.log("VIOLATION", kind, info)
            if self.enforce and kind in ENFORCE_KINDS and self.killed is None:
                self._enforce(v)

    def _kill(self):
        if self.killer is not None:
            self.killer()
            return
        h = k32.OpenProcess(0x0001, False, self.pid)       # PROCESS_TERMINATE
        if h:
            k32.TerminateProcess(h, 1)
            k32.CloseHandle(h)

    def _enforce(self, v):
        """end the run NOW: terminate the client (its job), wait for it to be gone, and after a foreground theft hand
        the foreground back to the window that had it (the only SetForegroundWindow the policy allows)"""
        t0 = time.perf_counter()
        rec = {"kind": v["kind"], "t": self.now()}
        self.killed = rec
        try:
            self._kill()
        except Exception as e:
            rec["kill_error"] = repr(e)
        h = k32.OpenProcess(0x00100000, False, self.pid)    # SYNCHRONIZE
        rec["dead"] = (k32.WaitForSingleObject(h, 3000) == 0) if h else True
        if h:
            k32.CloseHandle(h)
        rec["kill_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        if v["kind"] == "foreground":
            saved = self.prev_fg
            rest = {"saved": hex(saved or 0), "saved_class": _cls(saved) if saved else None, "attempts": 0,
                    "restored": False}
            end = time.perf_counter() + 1.0
            while time.perf_counter() < end:
                fg = u32.GetForegroundWindow()
                if saved and fg == saved:
                    rest["restored"] = True
                    break
                if saved and u32.IsWindow(saved) and (not fg or _pid_of(fg)[0] == self.pid):
                    rest["attempts"] += 1
                    u32.SetForegroundWindow(saved)
                time.sleep(0.005)
            fg = u32.GetForegroundWindow()
            rest.update({"final_fg": hex(fg or 0), "final_fg_class": _cls(fg) if fg else None,
                         "ms": round((time.perf_counter() - t0) * 1000, 1)})
            rec["restore"] = rest
        self.log("ENFORCED:", rec)

    def _close_v(self, kind, key):
        v = self._open.pop((kind, key), None)
        if v:
            v["until"] = self.now()
            self.log("violation ended", kind, "after %.3fs" % (v["until"] - v["t"]))

    # ---- hooks
    def _event(self, hook, event, hwnd, idobj, idchild, tid, ms):
        try:
            if event == EVENT_SYSTEM_FOREGROUND:
                pid = _pid_of(hwnd)[0] if hwnd else 0
                self.fg_events.append((self.now(), hwnd, pid))
                if len(self.fg_history) < 2000:
                    self.fg_history.append((self.now(), hex(hwnd or 0), pid, _cls(hwnd) if hwnd else None))
                if pid == self.pid:
                    self._open_v("foreground", 0, hwnd=hwnd, via="hook")
                else:
                    if hwnd:
                        self.prev_fg = hwnd
                    self._close_v("foreground", 0)
                return
            if idobj != 0 or idchild != 0 or not hwnd or u32.GetAncestor(hwnd, 2) != hwnd:
                return
            cls = _cls(hwnd)
            if cls in IGNORE_CLASSES:
                return
            if event == EVENT_SYSTEM_CAPTURESTART:
                self._open_v("mouse_capture", hwnd, hwnd=hwnd, via="hook")
                return
            s = self.seen.setdefault(hwnd, {"cls": cls, "created": self.now(), "first_visible": None})
            if event == EVENT_OBJECT_CREATE:
                if self.cbt_required and not self.cbt["installed"]:
                    self._open_v("guard_missing", hwnd, hwnd=hwnd, cls=cls,
                                 why="a top-level window was created before the in-process guard was installed")
                if self.preshow is None or cls in self.preshow:
                    self.place(hwnd, "created")
            elif event == EVENT_OBJECT_SHOW and s["first_visible"] is None:
                s["first_visible"] = {"t": self.now(), "frame": _frame(hwnd), "on_other_display":
                                      self._on_other_display(hwnd)}
        except Exception as e:  # a hook callback must never raise into ctypes
            self.log("hook error", repr(e))

    # ---- poll
    def _poll(self):
        self.polls += 1
        fg = u32.GetForegroundWindow()
        if fg and _pid_of(fg)[0] == self.pid:
            self._open_v("foreground", 0, hwnd=fg, via="poll")
        else:
            if fg:
                self.prev_fg = fg
            if ("foreground", 0) in self._open:
                self._close_v("foreground", 0)
        tids = set()
        now = time.perf_counter()
        any_visible = any(s.get("first_visible") for s in self.seen.values())
        if now - self._last_enum >= (0.25 if any_visible else 0.02):
            self._last_enum = now
            self._known = set(windows_of(self.pid))
        self._known = {h for h in self._known | set(self.seen) if u32.IsWindow(h) and _pid_of(h)[0] == self.pid
                       and _cls(h) not in IGNORE_CLASSES}
        for h in list(self._known):
            s = self.seen.setdefault(h, {"cls": _cls(h), "created": self.now(), "first_visible": None,
                                     "found_by": "poll"})
            tids.add(_pid_of(h)[1])
            vis = u32.IsWindowVisible(h) and not u32.IsIconic(h)
            if not vis:
                s["rect_hidden_last"] = _wrect(h)
                if (self.preshow is None or s["cls"] in self.preshow) and \
                        not any(p["hwnd"] == h for p in self.placements):
                    self.place(h, "hidden-found-by-poll")
                continue
            if s["first_visible"] is None:
                s["first_visible"] = {"t": self.now(), "frame": _frame(h), "on_other_display":
                                      self._on_other_display(h), "via": "poll"}
            if self._on_other_display(h):
                self._open_v("off_test_display", h, hwnd=h, frame=_frame(h))
                self.place(h, "off-test-display")
            else:
                self._close_v("off_test_display", h)
        for tid in tids:
            gi = _GUITHREADINFO()
            gi.cbSize = ctypes.sizeof(gi)
            if u32.GetGUIThreadInfo(tid, ctypes.byref(gi)) and gi.hwndCapture:
                self._open_v("mouse_capture", tid, hwnd=gi.hwndCapture, via="poll")
            else:
                self._close_v("mouse_capture", tid)
        # a clip is ours only if it is not the whole desktop and lies inside one of our windows; the user's own game
        # clipping the cursor on DISPLAY1 is not a violation
        clip = self._clip()
        mine = clip != self.virtual and any(_overlap(clip, _wrect(h)) >= _overlap(clip, clip) > 0
                                            for h in self._known if u32.IsWindowVisible(h))
        if mine:
            self._open_v("cursor_clip", 0, rect=clip)
        else:
            self._close_v("cursor_clip", 0)

    def _audio_loop(self):
        while not self.stopping.is_set():
            try:
                ss = audio_sessions(self.pid)
                self.audio["samples"] += 1
                self.audio["sessions_seen"] = max(self.audio["sessions_seen"], len(ss))
                for st, pk in ss:
                    self.audio["active_samples"] += 1 if st == 1 else 0
                    self.audio["max_peak"] = max(self.audio["max_peak"], pk)
                    if pk > 1e-4:
                        self._open_v("audible", 0, peak=pk)
            except Exception as e:
                self.audio["error"] = repr(e)
            self.stopping.wait(self.audio_every)

    def run(self):
        _dpi_aware()
        vx, vy = u32.GetSystemMetrics(76), u32.GetSystemMetrics(77)   # again, in this (DPI-aware) thread
        self.virtual = (vx, vy, vx + u32.GetSystemMetrics(78), vy + u32.GetSystemMetrics(79))
        cb = WINEVENTPROC(self._event)
        hooks = [u32.SetWinEventHook(EVENT_OBJECT_CREATE, EVENT_OBJECT_SHOW, None, cb, self.pid, 0,
                                     WINEVENT_OUTOFCONTEXT),
                 u32.SetWinEventHook(EVENT_SYSTEM_CAPTURESTART, EVENT_SYSTEM_CAPTURESTART, None, cb, self.pid, 0,
                                     WINEVENT_OUTOFCONTEXT),
                 u32.SetWinEventHook(EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND, None, cb, 0, 0,
                                     WINEVENT_OUTOFCONTEXT)]
        if not all(hooks):
            self.log("WARNING: a WinEvent hook failed to install (%s) - polling only" % hooks)
        if self.watch_audio:
            threading.Thread(target=self._audio_loop, daemon=True).start()
        cbt_mod = cbt_proc = cbt_tid = None
        if self.cbt_dll:
            # the hook is owned by THIS thread (hooks die with the thread that set them) and targets ONLY the
            # client's main thread. It cannot be set on a suspended, not-yet-GUI thread (ERROR_INVALID_PARAMETER):
            # the launcher resumes after ready, and this loop retries every ~1 ms until it takes (measured ~30 ms).
            cbt_mod = k32.LoadLibraryW(self.cbt_dll)
            cbt_proc = k32.GetProcAddress(cbt_mod, b"HzmCbtProc") if cbt_mod else None
            tids = _threads(self.pid)
            cbt_tid = tids[0] if tids else None
            self.cbt.update({"dll": self.cbt_dll, "tid": cbt_tid, "loaded": bool(cbt_proc)})
        t_ready = time.perf_counter()
        self.ready.set()
        msg = wt.MSG()
        hproc = k32.OpenProcess(0x00100000, False, self.pid)   # SYNCHRONIZE
        try:
            while not self.stopping.is_set():
                if cbt_proc and cbt_tid and not self.cbt["installed"]:
                    hk = u32.SetWindowsHookExW(5, cbt_proc, cbt_mod, cbt_tid)      # WH_CBT, this client thread only
                    if hk:
                        self._cbt_hook = hk
                        self.cbt.update({"installed": True, "t": self.now(),
                                         "after_ready_ms": round((time.perf_counter() - t_ready) * 1000, 2)})
                        self.log("in-process guard installed on thread %d" % cbt_tid)
                    elif time.perf_counter() - t_ready > 10:
                        self.cbt["error"] = ctypes.get_last_error()
                        cbt_proc = None
                        if self.cbt_required:
                            self._open_v("guard_missing", 0, why="WH_CBT could not be installed (err %s)" %
                                         self.cbt["error"])
                wait = 1 if (cbt_proc and not self.cbt["installed"]) else self.poll
                u32.MsgWaitForMultipleObjects(0, None, False, wait, 0x04FF)
                while u32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    u32.TranslateMessage(ctypes.byref(msg))
                    u32.DispatchMessageW(ctypes.byref(msg))
                self._poll()
                if hproc and k32.WaitForSingleObject(hproc, 0) == 0:
                    self.log("process exited")
                    break
        finally:
            for h in hooks:
                if h:
                    u32.UnhookWinEvent(h)
            if self._cbt_hook:
                u32.UnhookWindowsHookEx(self._cbt_hook)
            if hproc:
                k32.CloseHandle(hproc)
            for k in list(self._open):
                self._close_v(*k)
            self.stopping.set()

    def stop(self, timeout=5):
        self.stopping.set()
        self.join(timeout)

    def cbt_decisions(self):
        """the guard's own log: windows it re-homed at creation, activations it refused"""
        out = {"created": [], "blocked_activations": 0}
        try:
            for ln in open(self.cbt_log, encoding="latin-1").read().splitlines():
                if " BLOCK_ACTIVATE " in ln:
                    out["blocked_activations"] += 1
                elif " CREATE " in ln:
                    out["created"].append(ln.split(" ", 1)[1])
        except (OSError, TypeError):
            return None
        return out

    def report(self):
        first = {hex(h): s for h, s in self.seen.items() if s.get("first_visible")}
        return {"pid": self.pid, "test_display": self.display["device"], "rect": self.display["rect"],
                "windows": {hex(h): s for h, s in self.seen.items()}, "first_visible": first,
                "placements": self.placements, "violations": self.violations, "polls": self.polls,
                "foreground_events_ours": [e for e in self.fg_events if e[2] == self.pid],
                "foreground_history": self.fg_history[-200:],
                "enforced": self.killed, "guard": dict(self.cbt, decisions=self.cbt_decisions()),
                "audio": self.audio if self.watch_audio else None,
                "clean": not self.violations and self.killed is None and
                all(not s["first_visible"]["on_other_display"] for s in first.values())}

    def __enter__(self):
        if not self.is_alive():
            self.start()
        self.ready.wait(5)
        return self

    def __exit__(self, *exc):
        self.stop()
        return False


def hold(*a, **k):
    """REMOVED (bug-3147): attaching to an already-running client cannot guarantee the in-process guard is in before
    its first window. Launch the client with launch_background() instead."""
    raise PolicyError("harness_window.hold() was removed (bug-3147): launch game clients with launch_background()")


# ------------------------------------------------------------------------------------------------ launcher + handle
class BackgroundClient:
    def __init__(self, popen, watcher, args, cfg_lines, job=None, preflight=None):
        self.proc, self.watcher, self.args, self.cfg_lines = popen, watcher, args, cfg_lines
        self.pid = popen.pid
        self.job, self.preflight = job, preflight

    def alive(self):
        return self.proc.poll() is None

    def hwnd(self):
        """the visible game window (largest visible top-level window of the process), or None"""
        hs = windows_of(self.pid, visible_only=True)
        if not hs:
            return None
        return max(hs, key=lambda h: (lambda r: (r[2] - r[0]) * (r[3] - r[1]))(_wrect(h)))

    def post_key(self, vk, down_ms=60, scan=None):
        """key to OUR window only (PostMessage) - never SendInput. SDL maps it from the scancode in lParam."""
        h = self.hwnd()
        if not h:
            return False
        sc = scan if scan is not None else u32.MapVirtualKeyW(vk, 0)
        u32.PostMessageW(h, 0x0100, vk, 1 | (sc << 16))
        time.sleep(down_ms / 1000.0)
        u32.PostMessageW(h, 0x0101, vk, 1 | (sc << 16) | (1 << 30) | (1 << 31))
        return True

    def post_click(self, x=10, y=10):
        """left click in OUR window's client coords (PostMessage). Prefer console commands (+attackprimary)."""
        h = self.hwnd()
        if not h:
            return False
        lp = (y << 16) | (x & 0xFFFF)
        u32.PostMessageW(h, 0x0201, 1, lp)
        time.sleep(0.06)
        u32.PostMessageW(h, 0x0202, 0, lp)
        return True

    def capture_png(self, path):
        """window-content capture (PrintWindow PW_CLIENTONLY|PW_RENDERFULLCONTENT) - never a desktop grab (bug-3053)"""
        from PIL import Image
        h = self.hwnd()
        if not h:
            return None
        gdi = ctypes.WinDLL("gdi32")
        rc = wt.RECT()
        u32.GetClientRect(h, ctypes.byref(rc))
        w, hh = rc.right, rc.bottom
        hdc = u32.GetDC(h)
        mdc = gdi.CreateCompatibleDC(hdc)
        bmp = gdi.CreateCompatibleBitmap(hdc, w, hh)
        gdi.SelectObject(mdc, bmp)
        ok = u32.PrintWindow(h, mdc, 3)
        buf = ctypes.create_string_buffer(w * hh * 4)

        class BIH(ctypes.Structure):
            _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                        ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                        ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]
        bi = BIH(ctypes.sizeof(BIH), w, -hh, 1, 32, 0, 0, 0, 0, 0, 0)
        gdi.GetDIBits(mdc, bmp, 0, hh, buf, ctypes.byref(bi), 0)
        gdi.DeleteObject(bmp)
        gdi.DeleteDC(mdc)
        u32.ReleaseDC(h, hdc)
        if not ok:
            return None
        Image.frombuffer("RGBA", (w, hh), buf, "raw", "BGRA", 0, 1).convert("RGB").save(path)
        return path

    def close(self, grace=30):
        """WM_CLOSE to our windows (SDL_QUIT -> engine `quit`), then terminate. Harnesses should rcon `quit` first."""
        if self.alive():
            for h in windows_of(self.pid, visible_only=True):
                u32.PostMessageW(h, 0x0010, 0, 0)
            try:
                self.proc.wait(grace)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                try:
                    self.proc.wait(10)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
        self.watcher.stop()
        if self.job:
            k32.CloseHandle(self.job)
            self.job = None

    def report(self):
        return self.watcher.report()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def launch_background(exe, args, cwd, env=None, *, display=None, log=None, width=None, height=None, noborder=True,
                      policy=True, watch_audio=False, preshow_classes=PRESHOW_CLASSES,
                      unfocused_fps=UNFOCUSED_FPS, below_normal=True, guard=True, enforce=True,
                      kill_on_harness_exit=True, job_ui_limits=True):
    """Start `exe args...` as a background test client on the test display. `args` excludes the exe.
    Returns a BackgroundClient (a context manager: leaving it closes the client). handle.cfg_lines = soft policy
    cvars that did not fit the '+' budget - the caller should already have put them in its boot cfg (use
    apply_policy() first if it needs them before launch)."""
    d = display or test_display()
    exedir = os.path.dirname(os.path.abspath(exe))    # the renderer DLLs and SDL2.dll load from the EXE's folder
    pf = sdl_preflight(exe)
    patched = supports_window_cvars(exedir)
    cbt, cbt_err = None, None
    if guard:
        try:
            cbt = ensure_cbt_dll()
        except Exception as e:
            cbt_err = repr(e)
        if not cbt and not (pf.get("ok") and patched):
            raise PolicyError("refusing to launch %s: no in-process activation guard (%s), and not (SDL hint proven %s "
                              "+ engine placement patch %s) - bug-3147" % (exe, cbt_err, pf, patched))
    pf.update({"guard_dll": cbt, "guard_error": cbt_err, "engine_patch": patched})
    argv = [exe] + list(args)
    cfg_lines = []
    if policy:
        wd = sdl_display_index(d) if patched else None
        argv, cfg_lines = apply_policy(argv, width, height, d, noborder, wd, unfocused_fps)
    if _plus_count(argv) > PLUS_LIMIT:
        raise PolicyError("%d '+' commands; the engine keeps only %d (bug-2996)" % (_plus_count(argv), PLUS_LIMIT))
    cbt_log = None
    extra = dict(env or {})
    if cbt:
        os.makedirs(os.path.join(CACHE, "logs"), exist_ok=True)
        cbt_log = os.path.join(CACHE, "logs", "cbt_%s_%d.log" % (time.strftime("%Y%m%d_%H%M%S"), os.getpid()))
        extra.update({"HZM_CBT_RECT": "%d,%d,%d,%d" % tuple(d["rect"]), "HZM_CBT_LOG": cbt_log})
    kw = popen_kwargs(extra, below_normal)
    kw["creationflags"] |= CREATE_SUSPENDED
    p = subprocess.Popen(argv, cwd=cwd, **kw)
    job = None
    try:   # never let the client run unwatched: any failure here kills the still-suspended process
        job = _make_job(kill_on_harness_exit, job_ui_limits)
        if job:
            hp = k32.OpenProcess(0x0100 | 0x0001, False, p.pid)    # PROCESS_SET_QUOTA | PROCESS_TERMINATE
            if not (hp and k32.AssignProcessToJobObject(job, hp)):
                k32.CloseHandle(job)
                job = None
            if hp:
                k32.CloseHandle(hp)
        killer = (lambda: k32.TerminateJobObject(job, 1)) if job else None
        w = Watcher(p.pid, display=d, log=log, watch_audio=watch_audio, preshow_classes=preshow_classes,
                    enforce=enforce, killer=killer, cbt_dll=cbt, cbt_log=cbt_log, cbt_required=bool(cbt))
        w.start()
        if not w.ready.wait(5):
            raise RuntimeError("watchdog did not start")
        h = k32.OpenProcess(0x0800, False, p.pid)        # PROCESS_SUSPEND_RESUME
        st = ntdll.NtResumeProcess(h) if h else -1
        if h:
            k32.CloseHandle(h)
        if st != 0:
            raise RuntimeError("could not resume the suspended client (NTSTATUS %s)" % st)
    except BaseException:
        p.kill()
        if job:
            k32.CloseHandle(job)
        raise
    w.log("launched pid %d on %s %s (%d '+') guard=%s job=%s sdl=%s" % (
        p.pid, d["device"], d["rect"], _plus_count(argv), bool(cbt), bool(job), pf.get("ok")))
    return BackgroundClient(p, w, argv, cfg_lines, job, pf)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "displays":
        for m in monitors():
            print(m)
        try:
            print("test display:", test_display()["device"])
        except NoTestDisplay as e:
            print("NO TEST DISPLAY:", e)
        fg = u32.GetForegroundWindow()
        print("foreground:", hex(fg or 0), _cls(fg) if fg else None, "pid", _pid_of(fg)[0] if fg else None)
    else:
        print(__doc__)
