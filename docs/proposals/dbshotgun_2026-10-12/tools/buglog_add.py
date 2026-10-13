"""append this lane's defects to .wolf/buglog.json (ids taken from the file's tail at the moment of writing; the
existing bytes are not re-encoded - the file is mixed LF / CRLF)"""
import json, re, time

P = r'C:\mohaa-coop-dev\.wolf\buglog.json'
TS = time.strftime('%Y-%m-%dT%H:%M:%S-06:00')
E = [
    dict(error_message="New weapon mesh (coop_dbshotgun.skd): 20,175 vertices in 23 surfaces for a mesh with 9,200 real vertices",
         file="docs/proposals/dbshotgun_2026-10-12/tools/dbs_build.py",
         root_cause="Blender's triangle order after planar dissolve + triangulate is scattered over the mesh; a surface filled in file order (limit 900 vertices, TIKI_MAX_VERTEXES 1000) shares almost no vertices.",
         fix="Triangles sorted along the gun (centroid x) per part before the surface split: 10,856 vertices, 13 surfaces.",
         tags=["dbshotgun", "skd", "mesh", "blender"]),
    dict(error_message="Baked sheet of the double-barrel shotgun: magenta fringes round every UV island in the second baked sheet; steel pure black in the first",
         file="docs/proposals/dbshotgun_2026-10-12/tools/bl_build.py",
         root_cause="(1) Blender's bake margin with use_clear off wrote fringe texels of the image's magenta fill in the second emit bake; (2) the author's diffuse sheet is black on the steel (metal workflow) - the steel's colour is in his glossy sheet.",
         fix="Bake margin 0 and our own island dilation (dbs_tex.py); steel taken from the glossy sheet, levelled to the retail guns (median sRGB 42), wood pulled from orange to walnut after two engine looks.",
         tags=["dbshotgun", "texture", "bake", "blender"]),
    dict(error_message="Script Error: You must specify an explicit classname for misc object tik models / Cannot cast 'none' to listener (test overlay weather.scr, coop_dbsDrop)",
         file="docs/proposals/dbshotgun_2026-10-12/tools/mkov_dbs.py",
         root_cause="`spawn getcvar( \"x\" ) \"origin\" local.o`: spawn takes the next token as the model name, so it tried to spawn models/getcvar.tik.",
         fix="The cvar is read into a local first (local.dtik = getcvar(...); spawn local.dtik \"origin\" local.o). Test overlay only.",
         tags=["dbshotgun", "script", "spawn", "harness"]),
    dict(error_message="First-person rows: a gun named \"Shotgun (Double Barrel)\" could only override the three reload rows - idle / fire / charge / pullout / putaway stayed the pump gun's (left hand works a pump that is not there)",
         file="openmohaa-hzm-dbs/code/cgame/cg_viewmodelanim.c",
         root_cause="CoopPerWeaponReloadAnim (coopr_<weapon>_<row>) was called for VM_ANIM_RELOAD / _SINGLE / _END only.",
         fix="Branch dbshotgun-next d67ba09e: called for every row and for the first idle after a weapon change. No coopr_ row of another suffix exists in the fixes pak, so no shipped gun changes.",
         tags=["dbshotgun", "cgame", "viewmodel", "engine"]),
    dict(error_message="Double-barrel shotgun reload bake: loading hand stood palm-out in front of the camera, later palm-down over the shell; gun pose moves put the grip hand in the eye or out of the arms' reach (39 IK clamps); pullout with the gun pushed out from frame 0 threw an arm across the view",
         file="docs/proposals/dbshotgun_2026-10-12/tools/dbs_hands.py",
         root_cause="The retail shell-feeding hand is an OPEN hand pushing up into a port under the receiver - turned onto a chamber that faces the eye it is the wrong hand; the index-minus-pinky direction of the L hand's local frame points away from the thumb; the eye sits 7 u left of and beside the grip, so there is little room to move the gun.",
         fix="Loading hand built from the idle hand's curl with thumb side on the chamber axis, palm up (pinky-minus-index); reload pose kept inside the reach (move 0 -2 -2); pullout / putaway ramp the push over the clip. 3 IK clamps left (putaway / pullout far frames).",
         tags=["dbshotgun", "viewmodel", "ik", "reload"]),
    dict(error_message="Harness capture: the second shot of the double-barrel shotgun never fired and the 'one shell left' reload captured the tail of the previous reload",
         file="docs/proposals/dbshotgun_2026-10-12/tools/run_dbs.py",
         root_cause="`wait` in the step cfgs is milliseconds: 'wait 20' after ten captured frames was 0.19 s after the first shot, under the 0.30 s fire delay; the next step began 0.6 s after a 3.2 s reload had started.",
         fix="wait 250 between the shots, explicit `reload`, 2.5 s after each reload capture (run act3: both cases whole).",
         tags=["dbshotgun", "harness", "timing"]),
]


def main():
    raw = open(P, 'rb').read()
    ids = re.findall(rb'"id": "bug-(\d+)"', raw[-200000:])
    n = max(int(x) for x in ids) + 1
    end = raw.rstrip().rfind(b']')
    body = raw[:end].rstrip()
    out = []
    for k, e in enumerate(E):
        d = dict(id='bug-%d' % (n + k), timestamp=TS, error_message=e['error_message'], file=e['file'],
                 root_cause=e['root_cause'], fix=e['fix'], tags=e['tags'], related_bugs=[], occurrences=1, last_seen=TS)
        out.append('\n'.join('  ' + l for l in json.dumps(d, indent=2, ensure_ascii=True).split('\n')))
    new = body + b',\n' + ',\n'.join(out).encode('ascii') + b'\n]\n'
    json.loads(new.decode('utf-8', 'replace'))
    open(P, 'wb').write(new)
    print('appended bug-%d .. bug-%d' % (n, n + len(E) - 1))


if __name__ == '__main__':
    main()
