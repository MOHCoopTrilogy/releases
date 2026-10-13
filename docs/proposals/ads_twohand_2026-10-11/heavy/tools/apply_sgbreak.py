r"""cgame patch (ads-heavy-next worktree, cgame only): THE QUICK BREAK-OFF ROW of a start / single / end reload
(shotgun; user 2026-10-12 "break off the reload", coordinator 2026-10-13: 1.18 s from the press to the shot is too slow).

The server (state file, tools/patch_sgbreak.py stage 2) ends a reload that is broken off by the trigger with a round
already chambered through a SHORT torso row (0.37 s) and says so with what it already has: it sends
`viewmodelanim reload_end` twice in the same frame, so the snapshot's change counter steps by TWO with the anim
RELOAD_END. No new view-anim id, no protocol change, fgame untouched.

  hands: `<prefix>_reload_end_break` (then `_ads` / `_adsb` as usual) when fps_anims has the row; no row = the
         `_loaded` / normal end row as before (it is simply cut by the shot)
  gun:   unchanged - `reload_end_loaded` (still clip, no pump sound) is already chosen for a reload that began loaded

    python apply_sgbreak.py <worktree>     (idempotent; needs apply_sgpump.py applied)
"""
import sys, os
W = sys.argv[1]
MARK = 's_coopReloadBreak'
p = os.path.join(W, 'code/cgame/cg_viewmodelanim.c')
s = open(p, encoding='utf-8', newline='').read()
if MARK in s:
    print('already patched'); sys.exit(0)
nl = '\r\n' if '\r\n' in s else '\n'
PAIRS = [
    ("static qboolean s_coopReloadFromEmpty = qtrue;\n",
     "static qboolean s_coopReloadFromEmpty = qtrue;\n"
     "// HZM coop [heavy lane 2026-10-13, shotgun] the end row now starting is a BREAK-OFF with a round chambered: the server\n"
     "// stepped the view-anim change counter by two (state RELOAD_SHOTGUN_BREAK_QUICK, apply_sgbreak.py)\n"
     "static qboolean s_coopReloadBreak = qfalse;\n"),
    ("    if (cg.snap->ps.iViewModelAnimChanged != cgi.anim->g_iLastVMAnimChanged) {\n"
     "        bAnimChanged                   = qtrue;\n",
     "    if (cg.snap->ps.iViewModelAnimChanged != cgi.anim->g_iLastVMAnimChanged) {\n"
     "        s_coopReloadBreak = (cg.snap->ps.iViewModelAnim == VM_ANIM_RELOAD_END\n"
     "                             && ((cg.snap->ps.iViewModelAnimChanged - cgi.anim->g_iLastVMAnimChanged) & 3) == 2\n"
     "                             && (cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD || cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_SINGLE))\n"
     "                                ? qtrue\n"
     "                                : qfalse;\n"
     "        bAnimChanged                   = qtrue;\n"),
    ("        if (cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_END && !s_coopReloadFromEmpty) {\n"
     "            char szLoaded[MAX_QPATH];\n"
     "            Com_sprintf(szLoaded, sizeof(szLoaded), \"%s_loaded\", szAnimName);\n"
     "            if (cgi.Cvar_Get(\"coop_vmEmptyReload\", \"1\", 0)->integer && cgi.Anim_NumForName(pTiki, szLoaded) != -1) {\n"
     "                Q_strncpyz(szAnimName, szLoaded, sizeof(szAnimName));\n"
     "            }\n"
     "        }\n",
     "        if (cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_END && !s_coopReloadFromEmpty) {\n"
     "            char szLoaded[MAX_QPATH];\n"
     "            Com_sprintf(szLoaded, sizeof(szLoaded), \"%s_%s\", szAnimName, s_coopReloadBreak ? \"break\" : \"loaded\");\n"
     "            if (cgi.Cvar_Get(\"coop_vmEmptyReload\", \"1\", 0)->integer && cgi.Anim_NumForName(pTiki, szLoaded) == -1\n"
     "                && s_coopReloadBreak) {\n"
     "                Com_sprintf(szLoaded, sizeof(szLoaded), \"%s_loaded\", szAnimName); // no break row: the normal end\n"
     "            }\n"
     "            if (cgi.Cvar_Get(\"coop_vmEmptyReload\", \"1\", 0)->integer && cgi.Anim_NumForName(pTiki, szLoaded) != -1) {\n"
     "                Q_strncpyz(szAnimName, szLoaded, sizeof(szAnimName));\n"
     "            }\n"
     "        }\n"),
]
for a, b in PAIRS:
    a = a.replace('\n', nl); b = b.replace('\n', nl)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('code/cgame/cg_viewmodelanim.c patched')
