"""WIRING PATCH (option A): the double barrel as a switch on the trench gun's loadout page. STAGED - this lane does not
apply it to the mod tree; the harness overlay is built from it (tools/mkov_dbs.py --wire).

    python wiring/patch_wiring_dbs.py --check <mod root>            anchors only, writes nothing, prints the list
    python wiring/patch_wiring_dbs.py --apply <mod root>            the integration step (idempotent)
    as a library:  patched(read) -> {relative path: text}           `read(relpath)` returns a file's text (latin-1)

How a player's choice travels (the armory's own way, the "name bus"): the page button execs a cfg that archives the
choice client-side and appends a token to the player's name; coop_mod/player.scr reads tokens out of the name and
dispatches them; the server sets the player's flag and answers with the cvars that draw the menu; at every join the
server replays the archived token (loadout_resend) - that is what carries the pick across map changes and sessions.

  token   " ,db" + 1 digit (1 = double barrel, 0 = trench gun)          name-bus command 53
  flag    player.flags["coop_dbsPick"]                                  read at ONE place: loadout_finResolve
  gate    cvar coop_dbShotgun (server, default 1; 0 = the pick is ignored and the trench gun is given)
  client  seta coop_loDbsA "append name ,db1"   (replayed at join)       seta coop_loDbsShow "exec ui/loadout/dbs_show1.cfg"
  menu    two buttons on the same spot of ui/coop_loadout.urc (URC titles are static): "DOUBLE BARREL: OFF" / ": ON",
          lit by coop_loDbsOn0 / coop_loDbsOn1, which only page 44 (the trench gun) switches on

Files and what is done to each (EXACT list):
  coop_mod/variables.scr      + local.command["53"]=" ,db"
  coop_mod/player.scr         + dispatch row for index 53 -> loadoutpick.scr::loadout_dbs
  coop_mod/loadoutpick.scr    + 3 lines at the top of loadout_finResolve (the swap), + the token's replay in
                                loadout_resend, + label loadout_dbs at the end of the file
  coop_mod/itemhandler.scr    + the tik in getAmmoType ("shotgun") and in isPrimaryWeapon
  coop_defaults.cfg           + seta coop_dbShotgun 1
  ui/coop_loadout.urc         + 2 Button resources after finbtn8 (the file has no generator and is checksum-locked by
                                docs/tools/check_mp_isolation.py: update the checksum there after applying)
  ui/loadout/init.cfg         + the two button cvars seeded 0
  ui/loadout/p<NN>.cfg        + 2 lines (both buttons off) on every page, + `vstr coop_loDbsShow` on p44.cfg
                                (= what docs/tools/gen_loadout.py emits once patch_gen_loadout() is applied to it)
  NEW (assets/ui/loadout/)    dbs_on.cfg  dbs_off.cfg  dbs_show0.cfg  dbs_show1.cfg
Not patched, to do at integration: coop_mod/recoil_table.txt is GENERATED - re-run its extractor (it reads the tik's
viewkick); docs/generated cvar docs rebuild themselves.
"""
import os, re, sys, glob

TIK = 'models/weapons/coop_dbshotgun.tik'
MARK = '[dbshotgun]'


def _ins_after(s, anchor_rx, text, count=1):
    rx = re.compile(anchor_rx, re.M)
    m = rx.findall(s)
    assert len(m) == count, (anchor_rx, len(m))
    return rx.sub(lambda k: k.group(0) + text, s)


def _ins_before(s, anchor_rx, text, count=1):
    rx = re.compile(anchor_rx, re.M)
    m = rx.findall(s)
    assert len(m) == count, (anchor_rx, len(m))
    return rx.sub(lambda k: text + k.group(0), s)


def variables(s):
    return _ins_after(s, r'^\tlocal\.command\["51"\]=" ,f4"[^\n]*\n',
                      '\tlocal.command["53"]=" ,db" //%s armory: the double barrel in place of the trench gun (data: 1 digit, 1 = on)\n' % MARK)


def player(s):
    return _ins_after(s, r'^\telse if\(local\.arrayIndex==51\)\{[^\n]*\n',
                      '\telse if(local.arrayIndex==53){ thread coop_mod/loadoutpick.scr::loadout_dbs local.player local.dataExtract } //%s armory: double barrel on / off\n' % MARK)


SWAP = ('\t//%s the double barrel stands in for the trench gun (and any of its finishes) when this player switched it on\n'
        '\tif( local.give == "models/weapons/shotgun.tik" && local.player.flags["coop_dbsPick"] == 1 && getcvar( "coop_dbShotgun" ) != "0" ){\n'
        '\t\tend "%s"\n'
        '\t}\n') % (MARK, TIK)
RESEND = ('\t//%s the archived double-barrel pick, replayed like the finishes above - and AGAIN until the server has\n'
          '\t//seen it (loadout_dbs sets coop_dbsSeen): the name bus cleans the name after every token, and a token that\n'
          '\t//is appended while the one before it is still on its way is cleaned away with it (measured: one send, lost).\n'
          '\t//A player with no archived pick has no such cvar: the vstr does nothing, four times.\n'
          '\tlocal.player.flags["coop_dbsSeen"] = 0\n'
          '\t//run w6: four sends while the player had joined but not yet spawned were all lost, the same send after the\n'
          '\t//spawn landed. So: wait (up to four minutes) until he is in the game alive, then send.\n'
          '\tfor(local.dw = 0; local.dw < 480; local.dw++){\n'
          '\t\tif(local.player == NULL){ end }\n'
          '\t\tif(local.player.dmteam != "spectator" && (isAlive local.player)){ break }\n'
          '\t\twait 0.5\n'
          '\t}\n'
          '\twait 2\n'
          '\tfor(local.dtry = 0; local.dtry < 4; local.dtry++){\n'
          '\t\twait 1.5\n'
          '\t\tfor(local.t = 10; local.t > 0; local.t--){\n'
          '\t\t\tif(local.player == NULL){ end }\n'
          '\t\t\tif(!(waitthread coop_mod/main.scr::containsText local.player.netname " ," 0)){ break }\n'
          '\t\t\twait 0.5\n'
          '\t\t}\n'
          '\t\tif(local.player == NULL){ end }\n'
          '\t\tif(local.player.flags["coop_dbsSeen"] == 1){ break }\n'
          '\t\tlocal.player stufftext ( "vstr coop_loDbsA" )\n'
          '\t\tprintln( "^~^~^ DBSRESEND " + local.player.entnum + " try " + local.dtry )\n'
          '\t\twait 3\n'
          '\t\tif(local.player == NULL){ end }\n'
          '\t\tif(local.player.flags["coop_dbsSeen"] == 1){ break }\n'
          '\t}\n') % MARK
LABEL = ('\n//=========================================================================\n'
         '// %s armory: the double barrel in place of the trench gun. Name-bus token " ,db" + 1 digit.\n'
         '// The flag is read in loadout_finResolve only; the two seta lines keep the pick (replayed at\n'
         '// every join by loadout_resend) and draw the right one of the two page buttons.\n'
         'loadout_dbs local.player local.v:{\n'
         '//=========================================================================\n'
         '\tif(local.player == NULL){ end }\n'
         '\tlocal.on = 0\n'
         '\tif(local.v == "1"){ local.on = 1 }\n'
         '\tif(local.on == 1 && getcvar( "coop_dbShotgun" ) == "0"){\n'
         '\t\tlocal.on = 0\n'
         '\t\twaitthread coop_mod/feed.scr::feed_player local.player 2 "armory" "The double barrel is switched off on this server"\n'
         '\t}\n'
         '\tlocal.player.flags["coop_dbsPick"] = local.on\n'
         '\tlocal.player.flags["coop_dbsSeen"] = 1\n'
         '\tlocal.player stufftext ( "seta coop_loDbsA append name ,db" + local.on )\n'
         '\tlocal.player stufftext ( "seta coop_loDbsShow exec ui/loadout/dbs_show" + local.on + ".cfg" )\n'
         '\tlocal.player stufftext ( "exec ui/loadout/dbs_show" + local.on + ".cfg" )\n'
         '\tprintln( "^~^~^ DBSPICK " + local.player.entnum + " " + local.on )\n'
         '\twaitthread loadout_finKick local.player\n'
         '}end\n') % MARK


def loadoutpick(s):
    s = _ins_after(s, r'^loadout_finResolve local\.player local\.slot local\.give:\{[^\n]*\n', SWAP)
    s = _ins_before(s, r'^\t//\[user 07-18 pre-release\] SHOW-ALL-WITH-LOCK[^\n]*\n', RESEND)
    return s.rstrip('\n') + '\n' + LABEL


def itemhandler(s):
    s = _ins_before(s, r'^\t\tcase "models/weapons/shotgun\.tik":[ \t]*\n\t\t\tend\("shotgun"\)',
                    '\t\tcase "%s": //%s\n' % (TIK, MARK))
    s = _ins_before(s, r'^\t\tcase "models/weapons/shotgun\.tik":[ \t]*\n\t\tcase "models/weapons/springfield\.tik":[ \t]*\n\t\tcase "models/weapons/thompsonsmg\.tik":',
                    '\t\tcase "%s": //%s\n' % (TIK, MARK))
    return s


def defaults(s):
    return _ins_after(s, r'^seta coop_lmsLateJoin 1[^\n]*\n',
                      'seta coop_dbShotgun 1\t\t// %s the double-barrel shotgun may be picked on the trench gun\'s armory page (0 = the pick is ignored)\n' % MARK)


def _button(name, title, cvar, cfg):
    return ('\n// %s the double barrel in place of the trench gun: two buttons on one spot (URC titles are static),\n'
            '// lit by coop_loDbsOn0 / coop_loDbsOn1 - only the trench gun\'s page (p44.cfg) switches one of them on\n'
            'resource\nButton\n{\n'
            'name "%s"\ntitle "%s"\nrect 500 451 95 14\n'
            'fgcolor 0.90 0.85 0.60 1.00\nbgcolor 0.09 0.10 0.13 0.90\nborderstyle "3D_BORDER"\nfont "verdana-12"\n'
            'enabledcvar "%s"\nclicksound "sound/menu/apply.wav"\nstuffcommand "exec ui/loadout/%s"\n}\n') % (MARK, name, title, cvar, cfg)


def urc(s):
    rx = re.compile(r'(^name "finbtn8"\n.*?^\}\n)', re.M | re.S)
    assert len(rx.findall(s)) == 1
    return rx.sub(lambda m: m.group(1) + _button('dbsbtn0', 'DOUBLE BARREL: OFF', 'coop_loDbsOn0', 'dbs_on.cfg')
                  + _button('dbsbtn1', 'DOUBLE BARREL: ON', 'coop_loDbsOn1', 'dbs_off.cfg'), s)


def init_cfg(s):
    rx = re.compile(r'^set coop_loMvOn 0\n', re.M)
    assert len(rx.findall(s)) >= 1
    return rx.sub(lambda m: m.group(0) + 'set coop_loDbsOn0 0\nset coop_loDbsOn1 0\n', s, count=1)


PAGE_OFF = ['set coop_loDbsOn0 0', 'set coop_loDbsOn1 0']
PAGE_44 = ['set coop_loDbsOn0 1', 'set coop_loDbsOn1 0', 'vstr coop_loDbsShow']


def page(s, pid):
    """a pNN.cfg: the lines gen_loadout.py emits after patch_gen_loadout(), put after its `set coop_loMvOn` line"""
    rx = re.compile(r'^set coop_loMvOn [01]\n', re.M)
    assert len(rx.findall(s)) == 1, pid
    add = PAGE_44 if pid == '44' else PAGE_OFF
    return rx.sub(lambda m: m.group(0) + '\n'.join(add) + '\n', s)


def patch_gen_loadout(s):
    """docs/tools/gen_loadout.py: the same lines out of the generator"""
    a = "        'set coop_loMvOn %s' % mv_on,\n"
    assert s.count(a) == 1
    return s.replace(a, a + "        # %s the double barrel's two page buttons: off everywhere, the trench gun's page lights the archived one\n"
                            "        *(['set coop_loDbsOn0 1', 'set coop_loDbsOn1 0', 'vstr coop_loDbsShow'] if w[\"id\"] == \"44\" else ['set coop_loDbsOn0 0', 'set coop_loDbsOn1 0']),\n" % MARK)


NEWFILES = {
    'ui/loadout/dbs_show0.cfg': '// %s the trench gun page shows "DOUBLE BARREL: OFF"\nset coop_loDbsOn0 1\nset coop_loDbsOn1 0\n' % MARK,
    'ui/loadout/dbs_show1.cfg': '// %s the trench gun page shows "DOUBLE BARREL: ON"\nset coop_loDbsOn0 0\nset coop_loDbsOn1 1\n' % MARK,
    'ui/loadout/dbs_on.cfg': ('// %s switch the double barrel ON: archive the pick (the server replays coop_loDbsA at every join) and tell the\n'
                              '// server now (name-bus token ,db1). The server re-checks coop_dbShotgun and answers with the button state.\n'
                              'seta coop_loDbsShow "exec ui/loadout/dbs_show1.cfg"\nseta coop_loDbsA "append name ,db1"\nappend name ,db1\nexec ui/loadout/dbs_show1.cfg\n') % MARK,
    'ui/loadout/dbs_off.cfg': ('// %s back to the trench gun\n'
                               'seta coop_loDbsShow "exec ui/loadout/dbs_show0.cfg"\nseta coop_loDbsA "append name ,db0"\nappend name ,db0\nexec ui/loadout/dbs_show0.cfg\n') % MARK,
}
FILES = [('coop_mod/variables.scr', variables), ('coop_mod/player.scr', player), ('coop_mod/loadoutpick.scr', loadoutpick),
         ('coop_mod/itemhandler.scr', itemhandler), ('coop_defaults.cfg', defaults), ('ui/coop_loadout.urc', urc),
         ('ui/loadout/init.cfg', init_cfg)]


def _scr_check(name, text):
    """docs/TRAPS.md parse killers on a patched script: no em dash, no bare negative in parentheses in what we add,
    running brace depth never negative and 0 at the end"""
    d = 0
    for i, l in enumerate(text.split('\n')):
        c = l.split('//')[0]
        d += c.count('{') - c.count('}')
        assert d >= 0, (name, 'brace depth below zero at line', i + 1)
    assert d == 0, (name, 'braces do not balance', d)


def patched(read, pages):
    """read(relpath) -> text or None; pages: list of page ids ('01'..) -> {relpath: new text} (only changed files)"""
    out = {}
    for rel, fn in FILES:
        raw = read(rel)
        assert raw is not None, rel
        nl = '\r\n' if '\r\n' in raw else '\n'
        s = raw.replace('\r\n', '\n')
        if MARK in s:
            continue
        t = fn(s)
        if rel.endswith('.scr'):
            _scr_check(rel, t)
        out[rel] = t.replace('\n', nl)
    for pid in pages:
        rel = 'ui/loadout/p%s.cfg' % pid
        raw = read(rel)
        if raw is None or 'coop_loDbsOn0' in raw:
            continue
        nl = '\r\n' if '\r\n' in raw else '\n'
        out[rel] = page(raw.replace('\r\n', '\n'), pid).replace('\n', nl)
    for rel, txt in NEWFILES.items():
        if read(rel) is None:
            out[rel] = txt
    for txt in (SWAP, RESEND, LABEL):
        assert '—' not in txt and '(-' not in txt
    return out


def main():
    mode, root = sys.argv[1], sys.argv[2]

    def read(rel):
        p = os.path.join(root, rel)
        return open(p, 'rb').read().decode('latin-1') if os.path.isfile(p) else None
    pages = sorted(os.path.basename(p)[1:-4] for p in glob.glob(os.path.join(root, 'ui', 'loadout', 'p[0-9][0-9].cfg')))
    out = patched(read, pages)
    for rel in sorted(out):
        print('%-32s %s' % (rel, 'NEW' if read(rel) is None else 'patched'))
    print('%d files (%d loadout pages)' % (len(out), len([r for r in out if re.match(r'ui/loadout/p\d\d\.cfg', r)])))
    if mode == '--apply':
        for rel, txt in out.items():
            p = os.path.join(root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(txt.encode('latin-1'))
        print('applied. Then: patch docs/tools/gen_loadout.py with patch_gen_loadout(), update the coop_loadout.urc checksum in docs/tools/check_mp_isolation.py, re-run the recoil table extractor.')


if __name__ == '__main__':
    main()
