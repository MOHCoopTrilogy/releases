r"""cgame patch (ads-heavy-next worktree, cgame only): THE PUMP IS WORKED ONLY WHEN THE GUN WAS EMPTY
(user 2026-10-12, shotgun: start / single / end reload rows).

A reload that STARTED with rounds in the gun ends with
  hands: `<prefix>_reload_end_loaded` (then `_ads` / `_adsb` as usual) when fps_anims has the row
  gun:   `reload_end_loaded` when the tik has it (hip and aimed alike; it wins over `reload_end_ads`)
A reload that started EMPTY, or a gun without those rows: exactly as before. Client-only, display only; the server
runs `reload_end` either way. The flag is taken when the `reload` (start) row is chosen, from the snapshot's clip.

    python apply_sgpump.py <worktree>     (idempotent)
"""
import sys, os
W = sys.argv[1]
MARK = 'CG_CoopReloadFromEmpty'


def patch(rel, pairs):
    p = os.path.join(W, rel)
    s = open(p, encoding='utf-8', newline='').read()
    if MARK in s and rel.endswith(('cg_viewmodelanim.c', 'cg_modelanim.c')):
        print(rel, 'already patched'); return
    nl = '\r\n' if '\r\n' in s else '\n'
    for a, b in pairs:
        a = a.replace('\n', nl); b = b.replace('\n', nl)
        assert s.count(a) == 1, (rel, a[:60], s.count(a))
        s = s.replace(a, b)
    open(p, 'w', encoding='utf-8', newline='').write(s)
    print(rel, 'patched')


patch('code/cgame/cg_viewmodelanim.c', [
    ("static qboolean s_coopAdsClip = qfalse;",
     "// HZM coop [heavy lane 2026-10-13, shotgun] the reload in progress STARTED on an empty gun (taken when its `reload` row\n"
     "// is chosen): the end of a start / single / end reload racks the action only then (apply_sgpump.py)\n"
     "static qboolean s_coopReloadFromEmpty = qtrue;\n"
     "qboolean        CG_CoopReloadFromEmpty(void)\n"
     "{\n"
     "    return s_coopReloadFromEmpty;\n"
     "}\n"
     "static qboolean s_coopAdsClip = qfalse;"),
    ("        if (cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD && cg.snap && cg.snap->ps.stats[STAT_MAXCLIPAMMO] > 0\n"
     "            && cg.snap->ps.stats[STAT_CLIPAMMO] == 0) {\n",
     "        if (cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD && cg.snap && cg.snap->ps.stats[STAT_MAXCLIPAMMO] > 0) {\n"
     "            s_coopReloadFromEmpty = (cg.snap->ps.stats[STAT_CLIPAMMO] == 0) ? qtrue : qfalse;\n"
     "        }\n"
     "        // HZM coop [heavy lane, shotgun] a reload that started with rounds in the gun ends WITHOUT the pump:\n"
     "        // `<row>_loaded` for the end row when fps_anims has it (the `_ads` step below then finds `<row>_loaded_ads`)\n"
     "        if (cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_END && !s_coopReloadFromEmpty) {\n"
     "            char szLoaded[MAX_QPATH];\n"
     "            Com_sprintf(szLoaded, sizeof(szLoaded), \"%s_loaded\", szAnimName);\n"
     "            if (cgi.Cvar_Get(\"coop_vmEmptyReload\", \"1\", 0)->integer && cgi.Anim_NumForName(pTiki, szLoaded) != -1) {\n"
     "                Q_strncpyz(szAnimName, szLoaded, sizeof(szAnimName));\n"
     "            }\n"
     "        }\n"
     "        if (cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD && cg.snap && cg.snap->ps.stats[STAT_MAXCLIPAMMO] > 0\n"
     "            && cg.snap->ps.stats[STAT_CLIPAMMO] == 0) {\n"),
])
patch('code/cgame/cg_modelanim.c', [
    ("                iRowAds      = s_rowChoice[r] ? cgi.Anim_NumForName(model.tiki, s_rows[r][1]) : -1;\n",
     "                iRowAds      = s_rowChoice[r] ? cgi.Anim_NumForName(model.tiki, s_rows[r][1]) : -1;\n"
     "                // HZM coop [heavy lane 2026-10-13, shotgun] rounds were left when the reload started: the gun's end\n"
     "                // row without the pump (and without its sound), hip and aimed alike, when the tik has it\n"
     "                if (r == 0 && !CG_CoopReloadFromEmpty()) {\n"
     "                    int iLoaded = cgi.Anim_NumForName(model.tiki, \"reload_end_loaded\");\n"
     "                    if (iLoaded != -1) {\n"
     "                        iRowAds = iLoaded;\n"
     "                    }\n"
     "                }\n"),
])
patch('code/cgame/cg_local.h', [
    ("    float CG_CoopBrace(void);",
     "    qboolean CG_CoopReloadFromEmpty(void); // HZM coop [heavy lane] the reload in progress started on an empty gun\n"
     "    float CG_CoopBrace(void);"),
]) if MARK not in open(os.path.join(W, 'code/cgame/cg_local.h'), encoding='utf-8').read() else print('cg_local.h already patched')
