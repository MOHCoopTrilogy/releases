"""Stage the Panzerfaust 60 into the wpnfix sources: launcher tik (the Panzerschreck's, made single-shot and disposable), its view
clip copy (tag_barrel on the warhead's nose), two projectile tiks (sp / dm: the retail shells' numbers, the Panzerfaust warhead as the
flying model), mesh, sheet, shader, credit.
Single shot: startammo 1 in every mode, no reload animation, `autoputaway` + `usenoammo 0` (the engine holsters an empty weapon,
grenade-style); the fire frame hides the warhead (pzfhead*) so the tube is visibly empty; coop_mod/panzerfaust.scr::discard (called
from weaponstate.scr on ATTACK_BAZOOKA_PRIMARY) then takes the spent tube.
    python stage_pzf.py
"""
import os, json, re
import stagelib as S
import pzflib as L

meta = json.load(open(os.path.join(L.BUILD, 'coop_panzerfaust.json')))
SRCDIR = os.path.join(L.BUILD, 'ship')

SETUP = """setup
{
	scale 0.52
	// HZM coop [newguns 2026-11-09] the Panzerfaust 60: marcusww's "Panzerfaust 60" (Sketchfab bb5ac613b7b84c5384900bc64ee83ead,
	// CC BY 4.0, modified: one of its two copies, ~7.3k triangles, its PBR maps baked to one 2048 sheet, the misspelt warning labels
	// re-lettered), rigged on the Panzerschreck's bones so its hands and clips drive it (docs/proposals/newguns_2026-11-09).
	// pzfhead* = the warhead: hidden the frame it is fired; the spent tube is then taken from the player (coop_mod/panzerfaust.scr).
	path models/weapons/coop_panzerfaust
	skelmodel coop_panzerfaust.skd
	surface pzftube* shader coop_panzerfaust
	surface pzfhead* shader coop_panzerfaust
}
"""


def launcher():
    t = S.pk.read('models/weapons/panzerschreck.tik').decode('latin-1')
    t = re.sub(r"setup\s*\{.*?\}\s*\n", SETUP, t, count=1, flags=re.S)
    t = t.replace('name\t\t\t"Panzerschreck"', 'name\t\t\t"Panzerfaust"')
    t = re.sub(r"(\n\s*rank\s+)620 620", r"\g<1>621 621", t, count=1)
    t = t.replace('\t\tsemiauto\n', '\t\tsemiauto\n\t\tautoputaway\t\t1\t// [newguns] single shot: holster the empty tube (grenade-style) until it is taken\n'
                  '\t\tusenoammo\t\t0\n')
    t = t.replace('models/projectiles/panzerschreckshell.tik', 'models/projectiles/coop_panzerfaustshell.tik')
    t = t.replace('models/projectiles/bazookashell_dm.tik', 'models/projectiles/coop_panzerfaustshell_dm.tik')
    t = re.sub(r'(\n\s*dm startammo\s+)\d+', r'\g<1>1', t)
    t = re.sub(r'(\n\s*dmrealism startammo\s+)\d+', r'\g<1>1', t)
    t = t.replace('\t\t// this is attached to the player during reload\n\t\tcache models/ammo/panzer_shell.tik\n\n\t\tsurface shell +nodraw\n', '')
    t = t.replace('exec coop_mod/itemhandler.scr "initialiseItem" "heavy" "Panzerschreck"', 'exec coop_mod/itemhandler.scr "initialiseItem" "heavy" "Panzerfaust"')
    # animations: no reload; raise / idle show the warhead, fire hides it
    a0 = t.index('animations')
    anims = """animations
{
	raise	panzerschreck.skc
	{
		server
		{
			last idle
		}
	}
	idle	panzerschreck.skc
	fire	panzerschreck.skc
	{
		server
		{
			entry shoot
			entry surface pzfhead* +nodraw
		}
		client
		{
"""
    fire = t.index('fire\tpanzerschreck.skc', a0)
    cl = t.index('client', fire)
    body = t[t.index('{', cl) + 1:]
    t = t[:a0] + anims + body
    t = re.sub(r"/\*QUAKED.*?\*/", "/*QUAKED weapon_coop_panzerfaust (0.0 0.0 0.0) (-65 -40 0) (65 40 120) Panzerfaust\n*/", t, flags=re.S)
    bad = [l for l in t.splitlines() if ('Panzerschreck"' in l or 'panzer_reload' in l or 'surface shell' in l) and not l.strip().startswith('//')]
    assert not bad, bad
    return t


def projectile(src, model_rel):
    t = S.pk.read(src).decode('latin-1')
    t = re.sub(r"setup\s*\{.*?\}\s*\n", "setup\n{\n\tscale 0.52\n\t// HZM coop [newguns 2026-11-09] the Panzerfaust's warhead in flight (%s's numbers)\n"
               "\tpath models/projectiles/coop_panzerfaust\n\tskelmodel coop_pzfhead.skd\n\tsurface pzfshell* shader coop_panzerfaust\n}\n" % src.split('/')[-1], t, count=1, flags=re.S)
    return t


def main():
    man = S.json.load(open(S.MAN))
    S.put('models/weapons/coop_panzerfaust/coop_panzerfaust.skd', open(os.path.join(SRCDIR, 'models', 'weapons', 'coop_panzerfaust', 'coop_panzerfaust.skd'), 'rb').read(), man)
    S.put('models/projectiles/coop_panzerfaust/coop_pzfhead.skd', open(os.path.join(SRCDIR, 'models', 'projectiles', 'coop_panzerfaust', 'coop_pzfhead.skd'), 'rb').read(), man)
    S.put('textures/models/weapons/coop_panzerfaust/pzf.jpg', open(os.path.join(L.BUILD, 'pzf.jpg'), 'rb').read(), man)
    # the view clip: the Panzerschreck's, tag_barrel on the warhead nose (gun x -> panzer01? no: tag_barrel's parent is origin)
    import numpy as np
    M = np.load(os.path.join(os.path.dirname(L.BUILD), 'pzs_affine_2.npy'))   # not used for the tag: its parent is `origin`
    nose = np.array([meta['head_max_x'], 0.0, L.TUBE_Z])
    # origin-local = gun / 0.52 with the origin bone's own frame: measured from the shipped tag (tag_barrel gun 43.84 0.79 -5.11
    # vs its channel value) inside clip()
    ch, fr = S.pk.skc(S.C.convert(S.pk.read('models/weapons/panzerschreck/panzerschreck.skc')) if S.struct.unpack_from('<i', S.pk.read('models/weapons/panzerschreck/panzerschreck.skc'), 4)[0] == 14 else S.pk.read('models/weapons/panzerschreck/panzerschreck.skc'))
    tb = np.array(fr[0][ch.index('tag_barrel pos')][:3])
    gun_tb = np.array([43.84, 0.79, -5.11])
    # find the axis map of origin-local -> gun from the tag itself: local = A^-1 (gun) with the PS's x along the tube
    print('panzerschreck tag_barrel local', tb.round(3), 'gun', gun_tb)
    data = S.clip('models/weapons/panzerschreck/panzerschreck.skc', 0.52)
    b = bytearray(data); ch, fr = S.pk.skc(bytes(b)); nf = S.struct.unpack_from('<i', b, 44)[0]
    ib = ch.index('tag_barrel pos')
    # scale the tag's local vector so its gun position moves from the Panzerschreck's muzzle to the warhead nose along the tube
    k = None
    for f in range(nf):
        ov = S.struct.unpack_from('<i', b, 48 + 48 * f + 44)[0]
        v = np.array(S.struct.unpack_from('<4f', b, ov + 16 * ib)[:3])
        ax = int(np.argmax(np.abs(v)))
        v2 = v.copy(); v2[ax] = v[ax] * (nose[0] / gun_tb[0])
        S.struct.pack_into('<4f', b, ov + 16 * ib, float(v2[0]), float(v2[1]), float(v2[2]), 0.0)
        k = (ax, v[ax], v2[ax])
    print('tag_barrel axis %d: %.3f -> %.3f (gun x %.2f -> %.2f)' % (k[0], k[1], k[2], gun_tb[0], nose[0]))
    S.put('models/weapons/coop_panzerfaust/panzerschreck.skc', bytes(b), man)
    S.put('models/weapons/coop_panzerfaust.tik', launcher().encode('latin-1'), man)
    S.put('models/projectiles/coop_panzerfaustshell.tik', projectile('models/projectiles/panzerschreckshell.tik', '').encode('latin-1'), man)
    S.put('models/projectiles/coop_panzerfaustshell_dm.tik', projectile('models/projectiles/bazookashell_dm.tik', '').encode('latin-1'), man)
    sh = os.path.join(S.SRC, 'scripts', 'coop_newguns.shader')
    s = open(sh, 'rb').read().decode('latin-1')
    if '\ncoop_panzerfaust\n' not in s:
        s = s.rstrip() + ("\n\n// [newguns 2026-11-09] the Panzerfaust 60's sheet: marcusww's Panzerfaust 60 (CC BY 4.0, modified), PBR baked to one diffuse\n"
                          "coop_panzerfaust\n{\n\tqer_editorimage textures/models/weapons/coop_panzerfaust/pzf.jpg\n\t{\n\t\tmap textures/models/weapons/coop_panzerfaust/pzf.jpg\n"
                          "\t\trgbGen lightingSpherical\n\t}\n}\n")
    S.put('scripts/coop_newguns.shader', s.encode('latin-1'), man)
    cr = os.path.join(S.SRC, 'credits', 'coop_cc_models.txt')
    c = open(cr, 'rb').read().decode('utf-8')
    if 'marcusww' not in c:
        nl = '\r\n' if '\r\n' in c else '\n'
        c = c.rstrip() + nl + ("""
Panzerfaust 60 (models/weapons/coop_panzerfaust.tik, models/weapons/coop_panzerfaust/, models/projectiles/coop_panzerfaust*, textures/models/weapons/coop_panzerfaust/, its finishes)
  "Panzerfaust 60" by marcusww
  https://sketchfab.com/3d-models/bb5ac613b7b84c5384900bc64ee83ead
  Licence: Creative Commons Attribution 4.0 International (CC BY 4.0) - https://creativecommons.org/licenses/by/4.0/
  Modified: one of the model's two copies, reduced to about 7,300 triangles, rigged on the Panzerschreck's skeleton and
  animations, the warhead split off as the projectile, PBR maps baked into one diffuse sheet with the warning labels
  re-lettered ("Starker Feuerstrahl !"), finish variants derived from it.
""").replace('\n', nl)
        open(cr, 'wb').write(c.encode('utf-8'))
    open(S.MAN, 'w', encoding='utf-8', newline='\n').write(S.json.dumps(man, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
