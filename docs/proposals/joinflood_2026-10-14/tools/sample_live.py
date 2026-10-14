"""READ-ONLY sampler for the user's live client during a lag report: every 100 ms the process's I/O counters
(GetProcessIoCounters via PROCESS_QUERY_LIMITED_INFORMATION - no handle with write/inject rights), its CPU time, and
the config/log file sizes+mtimes; every 500 ms the server-measured ping of every player (a getstatus query, what the
server browser sends). Touches nothing.

    python -I sample_live.py <pid> <server port> <seconds> <out.tsv>
"""
import ctypes, os, socket, sys, time
from ctypes import wintypes

pid, port, secs, out = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class IO(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in ("ro", "wo", "oo", "rb", "wb", "ob")]


k32.OpenProcess.restype = wintypes.HANDLE
h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
assert h, ctypes.get_last_error()
FT = wintypes.FILETIME


def cpu():
    c, e, kk, u = FT(), FT(), FT(), FT()
    k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kk), ctypes.byref(u))
    return ((kk.dwHighDateTime << 32 | kk.dwLowDateTime) + (u.dwHighDateTime << 32 | u.dwLowDateTime)) / 1e4


FILES = [r"G:\mohaa-gl2\home\maintt\configs\omconfig.cfg", r"G:\mohaa-gl2\home\maintt\qconsole.log"]
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.3)
t0 = time.time()
lastq = 0
prev = None
with open(out, "w") as f:
    f.write("t\tcpu_ms\twrite_ops\twrite_bytes\tread_ops\tcfg_mtime\tlog_size\tpings\n")
    while time.time() - t0 < secs:
        io = IO()
        k32.GetProcessIoCounters(h, ctypes.byref(io))
        st = [os.stat(p) for p in FILES]
        pings = ""
        if time.time() - lastq >= 0.5:
            lastq = time.time()
            try:
                sock.sendto(b"\xff\xff\xff\xff\x02getstatus", ("127.0.0.1", port))
                lines = sock.recv(65535).decode("latin1").split("\n")
                pings = ",".join(l.split(" ")[1] for l in lines[2:] if l.strip())
            except Exception as e:
                pings = "err"
        f.write("%.2f\t%.0f\t%d\t%d\t%d\t%.2f\t%d\t%s\n" % (time.time() - t0, cpu(), io.wo, io.wb, io.ro,
                                                             st[0].st_mtime % 1000, st[1].st_size, pings))
        time.sleep(0.1)
print("done", out)
