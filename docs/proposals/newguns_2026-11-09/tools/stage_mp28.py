"""Stage the MP 28 into the wpnfix sources (stagelib): the Sten Mk II's tik re-pointed at the new mesh, its clips with tag_barrel on the
MP 28's muzzle (1.5 u shorter than the Sten's at the magazine both are held by); the ejection port is near the Sten's, kept.
    python stage_mp28.py
"""
import os, json
import stagelib as S
import mp28lib as L

meta = json.load(open(os.path.join(L.BUILD, 'coop_bergmann.json')))
CFG = dict(
    donor_tik='models/weapons/sten.tik', donor_path='models/weapons/sten_smg', stem='coop_bergmann', name='MP28', rank=331,
    ih=('smg', 'MP28'),
    setup_note=['HZM coop [newguns 2026-11-09] the MP 28: BrendanStakenburg\'s "MP-28" (Sketchfab a8838ccaf87243cfa71a321092065d6a,',
                'CC BY 4.0, modified: 530k -> ~7.4k triangles, its PBR maps baked to one 2048 sheet), rigged on the Sten Mk II\'s bones',
                '(its magazine rides Sten_Clip) so the Sten\'s hands and clips drive it (docs/proposals/newguns_2026-11-09).'],
    setup_surfaces=[('mp28*', 'coop_bergmann'), ('mp28clip', 'coop_bergmann')],
    mag_from='sten_clip', mag_to='mp28clip',
    extra_subs=[('clipsize		30', 'clipsize		32')],   # the MP 28's 32-round box (the Sten's is 30)
    skd_file=os.path.join(L.BUILD, 'ship', 'models', 'weapons', 'coop_bergmann', 'coop_bergmann.skd'),
    sheet_file=os.path.join(L.BUILD, 'mp28.jpg'), sheet_rel='textures/models/weapons/coop_bergmann/mp28.jpg',
    shader='coop_bergmann', shader_note="[newguns 2026-11-09] the MP 28's sheet: BrendanStakenburg's MP-28 (CC BY 4.0, modified), PBR baked to one diffuse",
    credit_key='BrendanStakenburg',
    credit="""
MP 28 (models/weapons/coop_bergmann.tik, models/weapons/coop_bergmann/, textures/models/weapons/coop_bergmann/, its finishes)
  "MP-28" by BrendanStakenburg
  https://sketchfab.com/3d-models/a8838ccaf87243cfa71a321092065d6a
  Licence: Creative Commons Attribution 4.0 International (CC BY 4.0) - https://creativecommons.org/licenses/by/4.0/
  Modified: reduced from about 530,000 to about 7,400 triangles, rigged on the Sten Mk II's skeleton and animations,
  PBR maps baked into one diffuse sheet, finish variants derived from it.
""",
)

if __name__ == '__main__':
    import numpy as np
    M = np.load(os.path.join(os.path.dirname(L.BUILD), 'sten_affine_1.npy'))      # gun = local @ M[:3] + M[3] (Sten_SMG)
    muz = np.array([meta['gun_max'][0], -0.70, -2.95])
    loc = (muz - M[3]) @ np.linalg.inv(M[:3])
    ax = int(np.argmax(np.abs(M[:3, 0])))                                          # the local axis that carries gun x
    print('gun x <- local axis', ax, 'muzzle local', loc.round(3))
    CFG['muzzle'] = (ax, float(loc[ax]))
    print(S.stage(CFG))
