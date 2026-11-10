"""(user 2026-11-08: "move testing over to my primary monitor") test clients on the 3440x1440 ULTRAWIDE (by resolution):
wait until no openmohaa*.exe runs (another agent's test), then attic_run.py setup + the given job with the test display = primary."""
import os, runpy, subprocess, sys, time
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_window as hw  # noqa: E402

T = r"C:\mohaa-coop-dev\docs\proposals\attic_polish_2026-11-02\tools"
os.environ.setdefault("ATTIC_MOD", r"C:\mohaa-coop-dev\hzm-mod-attic")
os.environ.setdefault("ATTIC_SHIP", r"H:\hzm_work\attic62\ship\zzzzzzzzzzzzzz_hzm_menus3d.pk3")
# (user 2026-11-09: a second screen, 1920x1080, takes ONE client of its own: HZM_TEST_RES=1920x1080 runs there without waiting for the
# ultrawide's clients - only for this client dir's own exe, G:\mohaa-attic, which two of our runs must never share)
RES_WANT = tuple(int(v) for v in os.environ.get("HZM_TEST_RES", "3440x1440").lower().split("x"))
SECOND = RES_WANT == (1920, 1080)
quiet = 0
while quiet < 3:
    if SECOND:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              r"Get-Process openmohaa -ErrorAction SilentlyContinue | Where-Object { $_.Path -like 'G:\mohaa-attic\*' } | Select -Expand Id"],
                             capture_output=True, text=True).stdout
        busy = bool(out.strip())
    else:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq openmohaa*"], capture_output=True, text=True).stdout
        busy = "openmohaa" in out.lower()
    quiet = 0 if busy else quiet + 1
    if busy:
        print("waiting: a game client is running", time.strftime("%H:%M:%S"), flush=True)
    time.sleep(10)
subprocess.check_call([sys.executable, os.path.join(T, "attic_run.py"), "setup"])
# user 2026-11-08 correction: the test display is the 34" ULTRAWIDE, found by its RESOLUTION (3440 x 1440) - never by "primary"
# (that is the Hisense TV now) or by device name (names renumber)
prim = [m for m in hw.monitors() if (m["rect"][2] - m["rect"][0], m["rect"][3] - m["rect"][1]) == RES_WANT][0]
hw.test_display = lambda name=None: prim
sys.argv = [os.path.join(T, "attic_run.py")] + sys.argv[1:]
sys.path.insert(0, T)
runpy.run_path(os.path.join(T, "attic_run.py"), run_name="__main__")
