#!/usr/bin/env python3
# MOH Coop Trilogy - GitHub download tracker.
#   python docs/tools/dl_stats.py            # show current counts + delta since baseline
#   python docs/tools/dl_stats.py --baseline # (re)set the baseline to "now"
# The web-installer count is the cleanest signal of NEW players since the one-click funnel went live.
import json, os, subprocess, sys, datetime

REPO = "MOHCoopTrilogy/releases"
BASELINE = os.path.join(os.path.dirname(__file__), "dl_baseline.json")

def gh_path():
    for p in (os.path.expandvars(r"%LOCALAPPDATA%\Programs\GitHub CLI\gh.exe"),
              r"C:\Program Files\GitHub CLI\gh.exe"):
        if os.path.exists(p): return p
    return "gh"

def fetch():
    out = subprocess.run([gh_path(), "api", f"repos/{REPO}/releases", "--paginate"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("gh api failed: " + out.stderr.strip())
    data = json.loads(out.stdout)
    web = full = total = 0
    for r in data:
        for a in r.get("assets", []):
            n, c = a["name"], a["download_count"]
            total += c
            if "WebSetup" in n: web += c
            if n.startswith("MOHCoopTrilogy-Setup") and n.endswith(".exe"): full += c
    return {"web": web, "full_alltime": full, "all_assets": total}

def main():
    cur = fetch()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if "--baseline" in sys.argv or not os.path.exists(BASELINE):
        json.dump({"when": now, **cur}, open(BASELINE, "w"), indent=2)
        print(f"Baseline set @ {now}")
        print(f"  web installer (new funnel): {cur['web']}")
        print(f"  full installers (all-time): {cur['full_alltime']}")
        print(f"  all assets (all-time):      {cur['all_assets']}")
        return
    base = json.load(open(BASELINE))
    print(f"Downloads (now {now}  vs baseline {base['when']}):")
    for k, label in (("web","web installer (NEW players)"),
                     ("full_alltime","full installers all-time"),
                     ("all_assets","all assets all-time")):
        d = cur[k] - base.get(k, 0)
        print(f"  {label:28} {cur[k]:6}   ({'+' if d>=0 else ''}{d} since baseline)")

if __name__ == "__main__":
    main()
