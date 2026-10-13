r"""cgame patch (ads-heavy-next worktree, cgame only): a RELOAD hands row that is LONGER than the server's torso reload
plays to its end.

Measured (run hj26 / hj27, FG 42 and FG 42 Irons): the torso state leaves the reload after 2.33 s (row
coop_reload_fg42) and the view anim goes to idle / charge, but the WEAPON's own `reload` row - WEAPON_RELOADING, the
gun cannot fire - runs 3.0 s (fg42.skc, 91 frames). A 91-frame hands row was cut at 2.34 s (trace coop_vmTrace:
`coopr_fg_42_irons_reload_empty` at t=90576, `fg42_idle` at t=92915). The emptied FG 42 works its charging handle in
exactly that last 0.67 s.

The change: while the current hands row is a RELOAD (view anim id VM_ANIM_RELOAD) that still has more than 0.05 s to
play, a change to IDLE or CHARGE from the server is not taken yet - it is taken when the row has ended. Anything else
(fire, put away, a new reload, another weapon) replaces the row at once, as before. Only rows that OPT IN by name:
`coopr_*` (the per-weapon rows of the aimed-reload work) and `fg42_reload*` - every other gun's row is cut exactly as
before. A row no longer than its torso reload has nothing left when the idle arrives: no change for it either.
Display only; no server state, no new anim id. `coop_vmReloadFinish 0` switches it off.

    python apply_reloadfinish.py <worktree>     (idempotent)
"""
import sys, os
W = sys.argv[1]
p = os.path.join(W, 'code/cgame/cg_viewmodelanim.c')
s = open(p, encoding='utf-8', newline='').read()
if 'coop_vmReloadFinish' in s:
    print('already patched'); sys.exit(0)
nl = '\r\n' if '\r\n' in s else '\n'
a = "    if (cg.snap->ps.iViewModelAnimChanged != cgi.anim->g_iLastVMAnimChanged) {" + nl
assert s.count(a) == 1, s.count(a)
b = ("    // HZM coop [heavy lane 2026-10-13] LONG RELOAD ROWS (apply_reloadfinish.py): the torso leaves its reload state\n"
     "    // (FG 42: 2.33 s) and the server sends idle / charge while the weapon's own `reload` row still holds\n"
     "    // WEAPON_RELOADING (3.0 s). A hands row that opted in (`coopr_*`, `fg42_reload*`) and has time left is played\n"
     "    // to its end before that idle / charge is taken; any other change replaces it at once. Display only.\n"
     "    qboolean bCoopHoldReload = qfalse;\n"
     "    {\n"
     "        static cvar_t *pFinish = NULL;\n"
     "        if (!pFinish) {\n"
     "            pFinish = cgi.Cvar_Get(\"coop_vmReloadFinish\", \"1\", 0);\n"
     "        }\n"
     "        if (pFinish->integer && !bWeaponChanged && cg.snap->ps.iViewModelAnimChanged != cgi.anim->g_iLastVMAnimChanged\n"
     "            && cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD\n"
     "            && (cg.snap->ps.iViewModelAnim == VM_ANIM_IDLE || cg.snap->ps.iViewModelAnim == VM_ANIM_CHARGE)) {\n"
     "            int iSlot = cgi.anim->g_iCurrentVMAnimSlot;\n"
     "            int iRow  = cgi.anim->g_VMFrameInfo[iSlot].index;\n"
     "            if (iRow >= 0 && cgi.anim->g_VMFrameInfo[iSlot].weight > 0.0f) {\n"
     "                const char *pszRow = cgi.Anim_NameForNum(pTiki, iRow);\n"
     "                float       fLeft  = cgi.Anim_Time(pTiki, iRow) - cgi.anim->g_VMFrameInfo[iSlot].time;\n"
     "                if (pszRow && (!Q_stricmpn(pszRow, \"coopr_\", 6) || !Q_stricmpn(pszRow, \"fg42_reload\", 11))\n"
     "                    && fLeft > 0.05f && fLeft < 1.5f) {\n"
     "                    bCoopHoldReload = qtrue;\n"
     "                }\n"
     "            }\n"
     "        }\n"
     "    }\n"
     "    if (!bCoopHoldReload && cg.snap->ps.iViewModelAnimChanged != cgi.anim->g_iLastVMAnimChanged) {\n").replace('\n', nl)
s = s.replace(a, b)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('patched', p)
