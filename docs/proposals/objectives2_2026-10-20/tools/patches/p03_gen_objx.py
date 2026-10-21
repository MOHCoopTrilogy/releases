import sys
sys.path.insert(0, r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad")
from pp import F
f = F(r"C:\mohaa-coop-dev\docs\tools\gen_objx.py")
if "after_id" in f.b:
    print("already patched"); sys.exit(0)
f.rep('TYPES = ("intel", "hold", "radio", "escort")', 'TYPES = ("intel", "hold", "radio", "escort", "charge", "perform")')
f.rep('WHEN = ("auto", "trigger", "after")', 'WHEN = ("auto", "trigger", "after", "near")')
f.rep('KINDS = ("pickup", "prop", "radio", "actor")', 'KINDS = ("pickup", "prop", "radio", "actor", "kit", "target")')
f.rep('''    OBJX_MOD=<mod checkout> overrides the checkout the file is written to (default: hzm-mohaa-coop-mod).''',
      '''    OBJX_MOD=<mod checkout> overrides the checkout the file is written to (default: hzm-mohaa-coop-mod).
    [objectives2 2026-10-20] the base mod checkout moved to H:\\hzm_archive: set OBJX_MOD=C:\\mohaa-coop-dev\\hzm-mod-objectives2.''')
f.rep('''    objectives[]: id, type (intel | hold | radio | escort), line (3..5, the HUD side line), text, done, when (auto | trigger | after),
                  arg (the trigger entity targetname / the objective id waited for), items[], and per type:''',
      '''    objectives[]: id, type (intel | hold | radio | escort | charge | perform), line (3..5 hint: objx.scr picks a free HUD side line),
                  text, done, when (auto | trigger | after | near), arg (the trigger entity targetname / the objective id waited for),
                  near {pos, r} (when=near: any player within r), after_id (also wait for that objective), delay (s), items[], and per type:''')
f.rep('''                  escort: zone (the destination), items[kind=actor]''',
      '''                  escort: zone (the destination), items[kind=actor]
                  charge : fuse (s), chain (1 = every target blows together after the last plant), items[kind=kit (optional) | target (aux = wreck model)]
                  perform: secs + zone like hold; items[kind=actor: model, pos (his work spot), yaw, seq (sequence), aux (work prop model), prop_pos, prop_yaw]''')
f.rep('''    items[]     : kind (pickup | prop | radio | actor), model, pos, yaw, label; radio: ref (vanilla targetname to replace), loop (sound alias)''',
      '''    items[]     : kind (pickup | prop | radio | actor | kit | target), model, pos, yaw, label; radio: ref (vanilla targetname to replace),
                  loop (sound alias); aux (wreck / work-prop model), seq (actor sequence), prop_pos, prop_yaw''')
f.rep('''        assert 1 <= len(objs) <= 3, m''', '''        assert 1 <= len(objs) <= 6, m''')
f.rep('''            assert 3 <= o["line"] <= 5 and o["line"] not in lines, o
            lines.add(o["line"])''', '''            o.setdefault("line", 3 + (i - 1) % 3)
            assert 3 <= o["line"] <= 5, o''')
f.rep('''            w("\\tlevel.objx_secs[%d] = %d" % (i, int(o.get("secs", 0))))''',
      '''            w("\\tlevel.objx_after[%d] = %s" % (i, s(o.get("after_id", ""))))
            if o.get("after_id"):
                assert o["after_id"] in ids and o["after_id"] != o["id"], o
            w("\\tlevel.objx_delay[%d] = %d" % (i, int(o.get("delay", 0))))
            nr = o.get("near")
            if o["when"] == "near":
                assert nr, o
            if nr:
                w("\\tlevel.objx_npos[%d] = %s" % (i, v(nr["pos"])))
                w("\\tlevel.objx_nr[%d] = %d" % (i, int(nr["r"])))
            w("\\tlevel.objx_fuse[%d] = %d" % (i, int(o.get("fuse", 0))))
            w("\\tlevel.objx_chain[%d] = %d" % (i, int(o.get("chain", 0))))
            w("\\tlevel.objx_secs[%d] = %d" % (i, int(o.get("secs", 0))))''')
f.rep('''            if o["type"] == "hold":
                assert z and o.get("secs", 0) >= 20, o''', '''            if o["type"] in ("hold", "perform"):
                assert z and o.get("secs", 0) >= 20, o''')
f.rep('''                w("\\tlevel.objx_it_loop[%d] = %s" % (k, s(it.get("loop", ""))))''',
      '''                w("\\tlevel.objx_it_loop[%d] = %s" % (k, s(it.get("loop", ""))))
                w("\\tlevel.objx_it_aux[%d] = %s" % (k, s(it.get("aux", ""))))
                w("\\tlevel.objx_it_seq[%d] = %s" % (k, s(it.get("seq", ""))))
                w("\\tlevel.objx_it_pos2[%d] = %s" % (k, v(it.get("prop_pos", it["pos"]))))
                w("\\tlevel.objx_it_yaw2[%d] = %d" % (k, yaw(it.get("prop_yaw", it.get("yaw", 0)))))''')
f.save()
