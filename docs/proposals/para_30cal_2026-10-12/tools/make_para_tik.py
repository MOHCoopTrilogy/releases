"""make_para_tik.py <out> - bug-3562: the paratroopers' fixed .30 cal = Breakthrough's models/statweapons/30cal.tik
(read from the retail pak, never modified) with the players' .30 cal firing sound and cadence. Binary I/O, CRLF kept,
every anchor exactly once."""
import sys, zipfile
SRC = "G:/GOG/Medal of Honor - Allied Assault War Chest/maintt/pak1.pk3"
d = zipfile.ZipFile(SRC).read("models/statweapons/30cal.tik")
assert d.count(b"\r\n") == d.count(b"\n")
t = d.decode("latin-1")
EDITS = [
    ("TIKI\r\n",
     "TIKI\r\n"
     "// HZM coop [bug-3562] the paratroopers' .30 cal (coop_mod/parasquad.scr). Breakthrough's\r\n"
     "// models/statweapons/30cal.tik with two changes: it fires the same sample as the .30 cal the players\r\n"
     "// carry (WaW30cal - the retail file plays jeep_snd_fire, a .50 cal recording) at that weapon's\r\n"
     "// cadence (firedelay 0.09 - the retail 0.06 is the MG42's 1000 rpm). Generated: docs/proposals/\r\n"
     "// para_30cal_2026-10-12/tools/make_para_tik.py. A NEW name on purpose: nothing retail is overridden.\r\n"),
    ("\t\tfiredelay\t\t0.06\r\n", "\t\tfiredelay\t\t0.09\r\n"),
    ("\t\t\tentry stopaliaschannel jeep_snd_fire\r\n\t\t\tentry sound jeep_snd_fire\r\n",
     "\t\t\tentry stopaliaschannel WaW30cal\r\n\t\t\tentry sound WaW30cal\r\n"),
    ("/*QUAKED addon_turretweapon_allied_30cal-3rdperson", "/*QUAKED addon_turretweapon_allied_coop-30cal-para"),
]
for old, new in EDITS:
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new, 1)
out = t.encode("latin-1")
assert b"\xe2\x80\x94" not in out
open(sys.argv[1], "wb").write(out)
print("wrote", sys.argv[1], len(out), "bytes")
