"""apply_ejectcases.py - revolvers drop their SPENT CASES on reload (fgame sentient.cpp / sentient.h).

    python apply_ejectcases.py <engine root> [--check]

User: "revolvers should also drop old shells as needed too when you reload them right."
New sentient event  coop_ejectcases <model> [tag] [max]  - for torso reload notetracks. It drops
min(max, coop_caseEjectMax, rounds FIRED) spent cases = the mainhand weapon's clip size minus the rounds still in it
(live rounds stay in a partial reload). Each case is one CoopEjectMagazine prop, so it inherits that path: brass
model of the caller's choosing, owner-hide while it falls past the first-person view, tumble, land on its side
(apply_magflat.py), the live-prop ring cap (coop_magEjectMax). The per-frame budget and same-model debounce are
lifted only for the cases of THIS call (a top-break throws all six at once), bounded by the cap above.
  top-break (Webley): one call at the break-open, max 6   -> all fired cases at once
  gate-loaded (Nagant): one call per rod push, max 1      -> one case per round
  swing-out (S&W M10): one call at the ejector-rod push, max 6
"""
import sys, io, os

MARK = "HZM coop [reload audit phase B] spent cases"
EDITS_CPP = [
    ('''Event EV_Sentient_DropItems
(
    "dropitems",''',
     '''// HZM coop [reload audit phase B] spent cases: revolver reload notetracks drop the FIRED cases (apply_ejectcases.py)
Event EV_Sentient_CoopEjectCases
(
    "coop_ejectcases",
    EV_DEFAULT,
    "sSI",
    "modelname [tagname] [max]",
    "HZM coop - drop the mainhand weapon's spent cases (clip size minus rounds left, capped)",
    EV_NORMAL
);
Event EV_Sentient_DropItems
(
    "dropitems",'''),
    ('''    {&EV_Sentient_CoopEjectMag,           &Sentient::EventCoopEjectMag            },
''',
     '''    {&EV_Sentient_CoopEjectMag,           &Sentient::EventCoopEjectMag            },
    {&EV_Sentient_CoopEjectCases,         &Sentient::EventCoopEjectCases          },
'''),
    ('''    CoopEjectMagazine(tik.c_str(), tag.length() ? tag.c_str() : NULL, 0);
}
''',
     '''    CoopEjectMagazine(tik.c_str(), tag.length() ? tag.c_str() : NULL, 0);
}

// HZM coop [reload audit phase B] spent cases (apply_ejectcases.py) - see the event above.
void Sentient::EventCoopEjectCases(Event *ev)
{
    static cvar_t *pCap = NULL;
    str            tik  = ev->GetString(1);
    str            tag  = (ev->NumArgs() > 1) ? ev->GetString(2) : str("");
    int            iMax = (ev->NumArgs() > 2) ? ev->GetInteger(3) : 6;
    Weapon        *weap = GetActiveWeapon(WEAPON_MAIN);
    int            fired, i;

    if (!pCap) {
        pCap = gi.Cvar_Get("coop_caseEjectMax", "6", CVAR_ARCHIVE);
    }
    if (!weap) {
        return;
    }
    fired = weap->GetClipSize(FIRE_PRIMARY) - weap->ClipAmmo(FIRE_PRIMARY);
    if (fired > iMax) {
        fired = iMax;
    }
    if (fired > pCap->integer) {
        fired = pCap->integer;
    }
    for (i = 0; i < fired; i++) {
        // one burst: lift the same-model debounce and the frame budget for these cases only
        m_fCoopLastMagEject = 0;
        if (s_coopMagThisFrame > 0) {
            s_coopMagThisFrame = 0;
        }
        CoopEjectMagazine(tik.c_str(), tag.length() ? tag.c_str() : NULL, 0);
    }
}
'''),
]
EDITS_H = [
    ('''    void EventCoopEjectMag(Event *ev);
''',
     '''    void EventCoopEjectMag(Event *ev);
    void EventCoopEjectCases(Event *ev); // HZM coop [reload audit phase B] spent cases
'''),
]


def patch(p, edits, check):
    raw = io.open(p, "rb").read()
    crlf = b"\r\n" in raw
    s = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in s or "EventCoopEjectCases" in s:
        print("already applied:", p)
        return 0
    for a, _ in edits:
        if s.count(a) != 1:
            print("ANCHOR MISMATCH (%d) in %s: %r" % (s.count(a), p, a[:60]))
            return 1
    if check:
        print("check OK:", p)
        return 0
    for a, b in edits:
        s = s.replace(a, b, 1)
    if crlf:
        s = s.replace("\n", "\r\n")
    io.open(p, "wb").write(s.encode("utf-8"))
    print("applied:", p)
    return 0


def main():
    root = sys.argv[1]
    check = "--check" in sys.argv
    r = patch(os.path.join(root, "code", "fgame", "sentient.cpp"), EDITS_CPP, check)
    r |= patch(os.path.join(root, "code", "fgame", "sentient.h"), EDITS_H, check)
    return r


if __name__ == "__main__":
    sys.exit(main())
