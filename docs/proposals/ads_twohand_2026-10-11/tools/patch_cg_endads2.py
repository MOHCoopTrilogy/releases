p = r'C:\mohaa-coop-dev\openmohaa-hzm-ads\code\cgame\cg_modelanim.c'
s = open(p, 'rb').read().decode('latin-1')
nl = '\r\n' if '\r\n' in s else '\n'
i = s.index('        // HZM coop [aimed revolver close 2026-10-12]')
j = s.index('        if (bPlaying) {', i)
new = '''        // HZM coop [aimed revolver close 2026-10-12] the same for `reload_end` -> `reload_end_ads` and `reload_single`
        // -> `reload_single_ads`: an aimed revolver reload works the action LOW, under the centre of the screen, and
        // then comes back up on the sights - the gun's own close has to be over earlier than in the hip clip, and a
        // case thrown for the hip view would fly through the aim. Chosen when the animation (or a new loop of it)
        // starts; same length as the hip clip, the server still runs the hip row.
        {
            static const char *const s_rows[2][2] = {
                {"reload_end",    "reload_end_ads"   },
                {"reload_single", "reload_single_ads"}
            };
            static int s_rowEnt[2] = {-1, -1}, s_rowSeen[2] = {0, 0}, s_rowChoice[2] = {0, 0};
            int        r;
            for (r = 0; r < 2; r++) {
                int      iRow  = pAimedGun->integer ? cgi.Anim_NumForName(model.tiki, s_rows[r][0]) : -1;
                qboolean bRow  = qfalse;
                float    fRowT = 999.0f;
                int      iRowAds;
                for (k = 0; k < MAX_FRAMEINFOS && iRow != -1; k++) {
                    if (model.frameInfo[k].weight && model.frameInfo[k].index == iRow) {
                        bRow = qtrue;
                        if (model.frameInfo[k].time < fRowT) {
                            fRowT = model.frameInfo[k].time;
                        }
                    }
                }
                if (!bRow) {
                    continue;
                }
                if (s_rowEnt[r] != s1->number || cg.time - s_rowSeen[r] > 250 || cg.time < s_rowSeen[r] || fRowT < 0.05f) {
                    s_rowChoice[r] = CG_AimingDownSights() ? 1 : 0;
                }
                s_rowEnt[r]  = s1->number;
                s_rowSeen[r] = cg.time;
                iRowAds      = s_rowChoice[r] ? cgi.Anim_NumForName(model.tiki, s_rows[r][1]) : -1;
                for (k = 0; k < MAX_FRAMEINFOS && iRowAds != -1; k++) {
                    if (model.frameInfo[k].weight && model.frameInfo[k].index == iRow) {
                        model.frameInfo[k].index = iRowAds;
                    }
                }
            }
        }
'''.replace('\n', nl)
s = s[:i] + new + s[j:]
open(p, 'wb').write(s.encode('latin-1'))
print('patched')
