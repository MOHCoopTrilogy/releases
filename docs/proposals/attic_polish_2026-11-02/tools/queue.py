"""queue.py <jobfile.json> - run harness jobs back to back (each waits for its own quiet window).
job = {"mod": dir, "ship": pk3, "extra": dir|null, "cmd": ["survey", "1080", "before"]}"""
import json, os, subprocess, sys, time
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_window as hw  # noqa: E402


def wait_display():
    """never the primary: hold the job until a second (non-primary) display is connected"""
    while True:
        try:
            d = hw.test_display()
            if not d.get("primary"):
                return d
        except Exception:
            pass
        print("waiting: no non-primary display", time.strftime("%H:%M:%S"), flush=True)
        time.sleep(30)

H = os.path.dirname(os.path.abspath(__file__))
for j in json.load(open(sys.argv[1])):
    env = dict(os.environ, ATTIC_MOD=j["mod"], ATTIC_SHIP=j["ship"])
    if j.get("extra"):
        env["ATTIC_EXTRA"] = j["extra"]
    wait_display()
    subprocess.check_call([sys.executable, os.path.join(H, "attic_run.py"), "setup"], env=env)
    print("JOB", j["cmd"], flush=True)
    subprocess.call([sys.executable, os.path.join(H, "attic_run.py")] + j["cmd"], env=env)
print("QUEUE DONE", flush=True)
