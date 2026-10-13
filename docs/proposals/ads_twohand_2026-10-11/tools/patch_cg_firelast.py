"""cgame (ads-next): `fire_last` - the gun clip of the shot that EMPTIES the gun (pistol lane, 2026-10-13).

The server plays `fire` for every shot and `idle_empty` once it is over. A gun whose action stays open on empty
(Luger toggle) therefore shut its action after the last shot and opened it again when the row ended. When the local
player's held gun starts `fire` with an empty clip in the snapshot and its tik has a `fire_last` row, that row is shown
instead (same length as `fire`; client-only, display only - the same index swap as `fire_ads`).
    coop_vmFireLast 1 (0 = off). Inert for a tik without the row.

    python patch_cg_firelast.py [worktree]        idempotent
"""
import sys, os, io
WT = sys.argv[1] if len(sys.argv) > 1 else r"C:\mohaa-coop-dev\openmohaa-hzm-ads"
P = os.path.join(WT, 'code', 'cgame', 'cg_modelanim.c')
s = io.open(P, encoding='latin-1', newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
if 'coop_vmFireLast' in s:
    print('already patched'); sys.exit(0)
OLD1 = "                    s_fireChoice = (CG_AimingDownSights() && cg.snap->ps.stats[STAT_CLIPAMMO] > 0) ? 1 : 0;" + nl
assert s.count(OLD1) == 1
NEW1 = OLD1 + '''                    // HZM coop [fire_last 2026-10-13] the shot that empties the gun: `fire_last` when the tik has it (the
                    // action stays open - Luger toggle - instead of shutting until the server's idle_empty)
                    {
                        static cvar_t *pFireLast = NULL;
                        if (!pFireLast) {
                            pFireLast = cgi.Cvar_Get("coop_vmFireLast", "1", 0);
                        }
                        if (pFireLast->integer && cg.snap->ps.stats[STAT_MAXCLIPAMMO] > 0
                            && cg.snap->ps.stats[STAT_CLIPAMMO] == 0 && cgi.Anim_NumForName(model.tiki, "fire_last") != -1) {
                            s_fireChoice = 2;
                        }
                    }
'''.replace('\n', nl)
s = s.replace(OLD1, NEW1, 1)
OLD2 = '                iFireAds   = s_fireChoice ? cgi.Anim_NumForName(model.tiki, "fire_ads") : -1;'
assert s.count(OLD2) == 1
s = s.replace(OLD2, '                iFireAds   = s_fireChoice ? cgi.Anim_NumForName(model.tiki, s_fireChoice == 2 ? "fire_last" : "fire_ads") : -1;', 1)
io.open(P, 'w', encoding='latin-1', newline='').write(s)
print('patched', P)
