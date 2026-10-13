# applied by build_scr.py: the .30 cal goes to the RIFLEMAN (member 3, the M1 Garand), not to the BAR man (member 1).
# User 2026-10-12: "can we make it so it's not the BAR paratrooper and it's a riflemen instead?" /
# "Don't completely remove the BAR paratrooper".


def apply(out):
    out = sub(out, """		if( local.k == 1 ){ thread gunner self local.sid }""",
              """		// the .30 cal is the RIFLEMAN's (member 3, the M1 Garand): the BAR man (member 1) keeps his BAR
		// and stays the squad's automatic rifle. Member 3 is also the man who gets out of a C-47 that
		// is lost to flak; a squad that lands without him has no .30 cal (the sniper and the medic
		// never take it).
		if( local.k == 3 ){ thread gunner self local.sid }""")
    out = sub(out, """// One brain per stick (paradrop.scr::coop_paradrop_main -> newSquad + brain). Members 1-4 are
// driven here; member 5 (medic) keeps its own tend/advance loop and only counts for safety.""",
              """// One brain per stick (paradrop.scr::coop_paradrop_main -> newSquad + brain). Members 1-4 are
// driven here; member 5 (medic) keeps its own tend/advance loop and only counts for safety.
// Who is who (paradrop.scr, by door order): 1 BAR, 2 Thompson, 3 M1 Garand - he carries the
// .30 cal -, 4 Springfield sniper, 5 medic.""")
    return out
