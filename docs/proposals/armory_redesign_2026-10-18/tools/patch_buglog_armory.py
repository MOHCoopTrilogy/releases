"""patch_buglog_armory.py - append the Armory B defects to .wolf/buglog.json (next free ids at run time; idempotent by error_message).
The buglog is mixed LF/CRLF: the file is edited as text, the new entries are inserted before the final ']'."""
import io, json, re, sys

P = r"C:\mohaa-coop-dev\.wolf\buglog.json"
NOW = "2026-10-18T19:00:00-06:00"
ENTRIES = [
    ("Armory B first real-engine capture: card / compare text overlapped, finish chip names hid behind their padlocks",
     "docs/tools/gen_armory_urc.py",
     "The layout was composed from a text-size model measured on a downscaled capture (verdana-12 = 7.5 vy). In the engine a verdana-12 label is a 12-unit cell (capitals ~9, ~4.5 vx wide) and facfont-20 a ~16-unit cell, so every 8-9 unit text pitch overlapped.",
     "Re-measured in the harness (run ab1), re-pitched every row to >= 11 units, 4 text lines per card (name 2 / info or requirement 2, 11 characters, hyphen breaks), shorter finish chip names, progress bar moved under the gun image; TRAPS entry has the metrics.",
     ["armory", "urc", "font-metrics", "harness"]),
    ("Armory B compare panel showed the previous slot's gun as 'NOW' on a fresh client (slot 4 / grenade)",
     "docs/proposals/armory_redesign_2026-10-18/tools/run_armory_proof.py",
     "The harness seeds clients from a pristine coop_defaults.cfg that predates the mod, so ui/loadout/armory_defaults.cfg (the compare and sort defaults) was never exec'd; slots without a server self-heal push kept stale values.",
     "The proof runner copies the worktree's coop_defaults.cfg into the client home after seeding (a real install gets it from the pak / deploy); the defaults file also seeds coop_loPubS1-4.",
     ["armory", "harness", "defaults"]),
    ("Armory B: the server's EQUIPPED backfill (loadout_slotLocksExport) still wrote the old per-gun marker flag",
     "hzm-mohaa-coop-mod/coop_mod/loadoutpick.scr",
     "The equipped marker became a card (position) flag; the server pushed 'seta coop_loEqR<tab>_<slot> set coop_loEqV<id> 1', which no widget reads any more, so picks restored from the server showed no green bar.",
     "docs/tools/patch_armory_b.py rewrites the push to 'vstr coop_loEqOn<id>' (the command the card chain publishes); sim test test_armory_open.py checks equip -> mark.",
     ["armory", "loadoutpick", "equipped-marker"]),
    ("Armory B: Mills bomb renders solid black in the 3D preview (texture alpha), blank card and hero",
     "docs/tools/gen_loadout.py",
     "mills_grenade.tik's texture alpha makes the model draw black; reported by the gun-fit agent.",
     "gen_loadout.ICON2D = ('66',): the card, hero and slot tile show the stock 2D grenade icon (textures/hud/weap_grenade.tga) instead of the model; the model path is blanked in the card chain.",
     ["armory", "mills", "icon"]),
]


def main():
    t = io.open(P, encoding="utf-8", newline="").read()
    ids = [int(x) for x in re.findall(r'"id":\s*"bug-(\d+)"', t)]
    nxt = max(ids) + 1
    e = "\r\n" if "\r\n" in t[-200:] else "\n"
    add = []
    for msg, f, rc, fx, tags in ENTRIES:
        if msg in t:
            continue
        d = {"id": "bug-%d" % nxt, "timestamp": NOW, "error_message": msg, "file": f, "root_cause": rc, "fix": fx, "tags": tags,
             "related_bugs": [], "occurrences": 1, "last_seen": NOW}
        nxt += 1
        add.append(json.dumps(d, indent=2, ensure_ascii=True).replace("\n", e))
    if not add:
        print("nothing to add")
        return 0
    k = t.rstrip().rfind("]")
    head = t[:k].rstrip()
    new = head + "," + e + (("," + e).join(add)) + e + "]" + e
    json.loads(new)
    io.open(P, "w", encoding="utf-8", newline="").write(new)
    print("added", len(add), "entries, ids from", nxt - len(add))
    return 0


if __name__ == "__main__":
    sys.exit(main())
