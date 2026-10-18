import io, re
MOD = "C:/mohaa-coop-dev/hzm-mod-smokec/"


def rd(p):
    return io.open(MOD + p, "r", encoding="utf-8", newline="").read()


def wr(p, t):
    io.open(MOD + p, "w", encoding="utf-8", newline="").write(t)


def sub(t, old, new):
    if t.count(old) != 1:
        raise SystemExit("expected 1 of %r, found %d" % (old[:70], t.count(old)))
    return t.replace(old, new)


# every place the smoke is handed over clears the consumed mark (a fresh pickup is a fresh smoke)
for f in ("coop_mod/officer.scr", "coop_mod/objective_drop.scr", "maps/m1l2a.scr"):
    t = rd(f)
    pat = re.compile(r"^([ \t]*)(local\.player item models/weapons/coop_smoke_grenade\.tik)([ \t]*\r?)$", re.M)
    n = len(pat.findall(t))
    t = pat.sub(lambda m: m.group(1) + 'local.player.flags["coop_smokeUsed"] = NIL	//[bug-4005] a fresh pickup is a fresh smoke' + m.group(3) + "\n" + m.group(1) + m.group(2) + m.group(3), t)
    print(f, "grant sites", n)
    wr(f, t)

# consume function
t = rd("coop_mod/officer.scr")
crlf = "\r\n" in t
anchor = "// Watches the smoke owner; drop the smoke again if he dies BEFORE throwing it (paradrop armed).\n"
if crlf:
    anchor = anchor.replace("\n", "\r\n")
fn = """// [bug-4005] The signal smoke has been THROWN: it is spent for that player, for good. Called by paradrop.scr::smokeDropZone.
// coop_smoke_player stays set for the rest of the call-in (xp, squad, landing zones read it), so the key-item guardian
// (keyitems.scr) used to see "owner without a smoke in hand" and re-give it - the smoke came back, armed == 0, and a
// second throw called nothing. The consumed mark is what every re-give path now respects.
coop_smoke_consume local.player:{
	if( local.player == NULL ){ end }
	local.player.flags["coop_smokeUsed"] = 1
	level.coop_smoke_spent[local.player.entnum] = 1
	local.player take "Signal Smoke Grenade"
	local.player setammo smokegrenade 0
	thread coop_smoke_hud_clear
	println( "^~^~^ SMOKE_CONSUMED p=" + local.player.netname )
}end

"""
if crlf:
    fn = fn.replace("\n", "\r\n")
t = sub(t, anchor, fn + anchor)
wr("coop_mod/officer.scr", t)

# paradrop.scr: mark it at the throw
t = rd("coop_mod/paradrop.scr")
old = "	level.coop_paradrop_armed = 0\n"
new = "	level.coop_paradrop_armed = 0\n	thread coop_mod/officer.scr::coop_smoke_consume level.coop_smoke_player	//[bug-4005] spent for good: no re-give path may bring it back\n"
if "\r\n" in t:
    old = old.replace("\n", "\r\n"); new = new.replace("\n", "\r\n")
t = sub(t, old, new)
wr("coop_mod/paradrop.scr", t)

# keyitems guardian: only re-give an UNUSED smoke that is still armed
t = rd("coop_mod/keyitems.scr")
old = "			if( level.coop_smoke_player == local.player ){\n"
new = "			if( level.coop_smoke_player == local.player && level.coop_paradrop_armed == 1 && local.player.flags[\"coop_smokeUsed\"] != 1 ){	//[bug-4005] a THROWN smoke is gone for good\n"
if "\r\n" in t:
    old = old.replace("\n", "\r\n"); new = new.replace("\n", "\r\n")
t = sub(t, old, new)
wr("coop_mod/keyitems.scr", t)
print("done")
