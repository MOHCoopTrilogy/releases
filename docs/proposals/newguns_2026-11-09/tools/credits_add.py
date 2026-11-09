"""Credit the three CC BY models in hzm_credits.txt (mod) and docs/SKIN_CREDITS.md (root), next to the FG42's entry."""
def patch(path, anchor, add):
    b = open(path, 'rb').read()
    nl = b'\r\n' if b.count(b'\r\n') * 2 > b.count(b'\n') else b'\n'
    a = anchor.replace(b'\n', nl)
    assert b.count(a) == 1, (path, b.count(a))
    assert b'maximiliaanmaene' not in b
    b2 = b.replace(a, a + add.replace(b'\n', nl))
    open(path, 'wb').write(b2)
    print(path, len(b), '->', len(b2), 'CRLF' if nl == b'\r\n' else 'LF')


patch(r'H:\hzm_work\newguns-mod\hzm_credits.txt',
      b"                         baked his PBR maps to one sheet. It is the FG 42 Irons since v1.10.66.\n",
      b"maximiliaanmaene (Sketchfab) - Bren Mk I model (sketchfab.com/3d-models/df74f7e3720d469e8bf425407e7ddc34),\n"
      b"                         CC BY 4.0 (creativecommons.org/licenses/by/4.0). \"Bren Mk1 LMG\" by maximiliaanmaene,\n"
      b"                         modified: cut to game size, levelled, rigged on the Vickers-Berthier's skeleton,\n"
      b"                         PBR maps baked to one sheet. The Bren since v1.10.68.\n"
      b"BrendanStakenburg (Sketchfab) - MP 28 model (sketchfab.com/3d-models/a8838ccaf87243cfa71a321092065d6a),\n"
      b"                         CC BY 4.0 (creativecommons.org/licenses/by/4.0). \"MP-28\" by BrendanStakenburg,\n"
      b"                         modified: cut from ~530k to ~7.4k triangles, rigged on the Sten's skeleton,\n"
      b"                         PBR maps baked to one sheet. The MP 28 since v1.10.68.\n"
      b"marcusww (Sketchfab)   - Panzerfaust 60 model (sketchfab.com/3d-models/bb5ac613b7b84c5384900bc64ee83ead),\n"
      b"                         CC BY 4.0 (creativecommons.org/licenses/by/4.0). \"Panzerfaust 60\" by marcusww,\n"
      b"                         modified: cut to game size, rigged on the Panzerschreck's skeleton, the warhead\n"
      b"                         split off as the projectile, PBR maps baked to one sheet with the warning label\n"
      b"                         re-lettered. The Panzerfaust since v1.10.68.\n")

patch(r'C:\hzm-newguns\root\docs\SKIN_CREDITS.md',
      b"- **Mauser C96** by **no12u** (Sketchfab), CC BY 4.0, modified - see the C96 line above.\n",
      b"- **Bren Mk I** - \"Bren Mk1 LMG\" by **maximiliaanmaene** - https://sketchfab.com/3d-models/df74f7e3720d469e8bf425407e7ddc34 - licensed **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/). **Modified**: reduced to about 10,000 triangles, levelled, the bipod folded, rigged on the Vickers-Berthier's skeleton and animations (the reload hands retargeted onto its magazine), PBR maps baked into one diffuse sheet, the finishes (standard seven and finish set 2) derived from that sheet (v1.10.68). Credits file: `credits/coop_cc_models.txt` in zzzzzzzzzzzzzzzz_coop_wpnfix.pk3.\n"
      b"- **MP 28** - \"MP-28\" by **BrendanStakenburg** - https://sketchfab.com/3d-models/a8838ccaf87243cfa71a321092065d6a - licensed **CC BY 4.0**. **Modified**: reduced from about 530,000 to about 7,400 triangles, rigged on the Sten Mk II's skeleton and animations, PBR maps baked into one diffuse sheet, finishes derived from it (v1.10.68). Same credits file.\n"
      b"- **Panzerfaust 60** - \"Panzerfaust 60\" by **marcusww** - https://sketchfab.com/3d-models/bb5ac613b7b84c5384900bc64ee83ead - licensed **CC BY 4.0**. **Modified**: one of the model's two copies, reduced to about 7,300 triangles, rigged on the Panzerschreck's skeleton and animations, the warhead split off as the projectile, PBR maps baked into one diffuse sheet with the warning labels re-lettered (\"Starker Feuerstrahl !\"; the source misspells it), finishes derived from it (v1.10.68). Same credits file.\n")
