"""Fail (exit 1) when a setting the MOH Coop Server app shows has no plain label (bug-11490).

The app (installer/servergui/hzm_server_gui.ps1) lists every catalogue setting on the Gameplay, Server tuning and
Server tabs; each needs a short "label" (docs/tools/servergui_overlay.json "labels" / "overrides", merged by
gen_server_catalogue.py into docs/generated/server_settings.json). A label that is only the raw cvar name, longer
than 40 characters or not ASCII also fails.

  python docs/tools/check_servergui_labels.py [path/to/server_settings.json]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(HERE, "..", "generated", "server_settings.json")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    cat = json.load(open(path, encoding="utf-8"))
    bad = []
    for s in cat["settings"]:
        lab = (s.get("label") or "").strip()
        why = ""
        if not lab:
            why = "no label"
        elif lab.lower() == s["name"].lower():
            why = "label is the cvar name"
        elif len(lab) > 40:
            why = "label longer than 40 characters"
        elif not lab.isascii():
            why = "label not ASCII"
        if why:
            bad.append("%s (%s page): %s" % (s["name"], s.get("page", "?"), why))
    print("servergui labels: %d settings, %d problems" % (len(cat["settings"]), len(bad)))
    for b in bad[:50]:
        print("  " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
