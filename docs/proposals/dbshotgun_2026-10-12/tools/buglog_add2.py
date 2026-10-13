"""append this lane's defects of 2026-10-13 to .wolf/buglog.json (ids from the file's tail at the moment of writing;
the existing bytes are not re-encoded - the file is mixed LF / CRLF). Run ONCE."""
import json, re, time

P = r'C:\mohaa-coop-dev\.wolf\buglog.json'
TS = time.strftime('%Y-%m-%dT%H:%M:%S-06:00')
F = "docs/proposals/dbshotgun_2026-10-12/"
E = [
    dict(error_message="Double-barrel shotgun: its first texture was composed from the author's baked sheets, which were presumably made from two Textures.com images packed in his .blend files; and the 'retail' wood source the MP18 skin tool reads is really the HRRTM pak's 2048 Kar98 sheet",
         file=F + "tools/dbs_skin.py",
         root_cause="The first pass projected the author's diffuse / glossy sheets onto our atlas (dbs_tex.py). weapon_hd/vfs.resolve_image returns the WINNING copy of a texture, which for kar98 / mp40 is zzzzzz-HRRTM_Pak4_Weapons.pk3, not a retail pak.",
         fix="dbs_skin.py paints the 2048 sheet from the mesh alone (position / normal / curvature per texel, the material-slot wood flag, our AO), the RETAIL Kar98 butt wood (main/Pak2.pk3, picked by pak name in tools/srclist.py) and procedural steel; bl_build.py --own opens neither the author's sheets nor his low file (mesh + atlas identical to the first pass); dbs_tex.py deleted; SOURCE.md rewritten.",
         tags=["dbshotgun", "texture", "provenance", "licence"]),
    dict(error_message="Double barrel, aimed: the second barrel would not fire for 1.2 s after the first",
         file="hzm-mohaa-coop-mod/coop_mod/player_Torso.st",
         root_cause="ATTACK_SHOTGUN_PRIMARY_AIM leaves only on ANIMDONE_TORSO (the pump gun's 36-frame fire clip = its pump stroke); the hip state has the CHECK_PRIMARY_ATTACK_SEMIAUTO exit, the aimed one has none. Found because a two-shot aimed demo reloaded ONE shell (run re2).",
         fix="STAGED patch wiring/patch_torso_dbs.py: for the exact name \"Shotgun (Double Barrel)\" one exit row to a new routing state COOP_DBS_REFIRE_AIM (action none, straight back), so the aimed second shot comes at the gun's own 0.30 s fire delay. Run re3: both shots fired, the gun emptied.",
         tags=["dbshotgun", "statemap", "ads", "fire", "torso"]),
    dict(error_message="Double barrel, aimed reload of the emptied gun: the LEFT-chamber shell was loaded with the HIP clip (a big hand in the middle of the view, 11-22 % of the centre box)",
         file="openmohaa-hzm/code/cgame/cg_viewmodelanim.c",
         root_cause="The aimed alias coopr_shotgun_double_barrel_reload_single_first_ads is 51 characters; a tiki animation alias holds 47. Anim_NumForName never found it, so the `_ads` clip was skipped silently and the hip row played inside the aim.",
         fix="The left-chamber hands row is `_l` (coopr_shotgun_double_barrel_reload_single_l_ads = 47 characters), cgame dbshotgun-next and rows/fps_rows_coop_dbshotgun.txt. Run re5: 0.07-1.55 % from the reload's start in six stances.",
         tags=["dbshotgun", "cgame", "alias", "ads", "reload", "name-length"]),
    dict(error_message="No space left on device: G: full (932 of 932 GB) during harness runs; two sessions died at start",
         file=F + "tools/dbslib.py",
         root_cause="Every measured stance writes ~275 screenshots of 0.6 MB; six stances = 1 GB a run, on a drive other lanes fill too.",
         fix="This lane's run folders moved to the scratchpad on C: (moved, not deleted); dbslib.RUNS is where frames are kept now (run_dbs.py, run_dbsh.py, box_dbs.py, animruns.py read it). The engine still writes into the harness copy's home on G: during a run.",
         tags=["dbshotgun", "harness", "disk"]),
    dict(error_message="Name-bus tokens (armory picks): a token appended to the player name while another is still in the name is lost; every token is dispatched about 8 times",
         file="hzm-mohaa-coop-mod/coop_mod/player.scr",
         root_cause="manageNamechange cleans the WHOLE name after a token (stufftext set name <clean>); a second token that arrived in between goes with it. The join replay in loadout_resend waits for a clean name on the SERVER's view, which is clean before the client has even appended the previous token. The repeated dispatch is the name being re-read until the client's clean name arrives (existing behaviour, all tokens).",
         fix="Not changed (shared). The double barrel's own replay (wiring/patch_wiring_dbs.py RESEND) is repeated until the server has seen the token (flag coop_dbsSeen), up to four tries; the harness test sends one token at a time with 8 s between.",
         tags=["dbshotgun", "armory", "name-bus", "loadout", "join"]),
    dict(error_message="Double barrel put away / raised: half way the gun stood on end in front of the camera (8 IK clamps)",
         file=F + "tools/dbs_hands.py",
         root_cause="pullout / putaway were the pump gun's clips blended into the new hold; the two poses are 15 u and 30 deg apart and the blend of their rotations passes through a gun-on-end pose.",
         fix="Own motions about the grip (LOWERED: 15 u down, 38 deg muzzle down, 12 deg roll), retail frame counts; the clamps that remain are in frames below the view.",
         tags=["dbshotgun", "viewmodel", "ik", "raise", "holster"]),
    dict(error_message="Double barrel reload, first tries: the loading hand covered the centre of the view; the ejected case drew 100 px wide; the raise played the pump's sound",
         file=F + "tools/dbs_hands.py",
         root_cause="(1) the shell was held like a dart, the hand behind it on the chamber axis - which points at the eye; (2) moving the whole hand back to bring the thumb behind the shell head brought its fingers 1.5 u nearer the eye, into the centre box; (3) tag_eject threw the cases back at 0.45 of their speed, 3 u past the eye; (4) snd_shotgun_pullout is ShotgunForward1.wav, the pump run forward.",
         fix="(1) ring pinch (thumb against the first two fingers, the shell through the ring), the hand to the left and below the shell; (2) the hand stays at the breech face and only the thumb goes behind the head (fit_thumb); (3) EJECT_DIR (-0.22, 0.86, -0.46); (4) the raise row uses snd_shotgun_putaway.",
         tags=["dbshotgun", "viewmodel", "reload", "eject", "sound"]),
    dict(error_message="Harness: the emptied-gun demo captured no reload / only its tail; the wiring test spawned with the wrong gun",
         file=F + "tools/run_dbsh.py",
         root_cause="(1) aimed, the second shot never fired (the statemap defect above), so --demoempty waited for a reload that did not come; once it fired, the emptied gun reloads by itself 1 s after the shot, hip and aimed, so the capture must start at the shot (--demoempty) and run 290 frames; (2) run folders moved to C: made the runner refuse the old ids; (3) the test profile has the trench gun LOCKED (Shadow Hunter challenge), so slot 1 never became the trench gun.",
         fix="Emptied runs: --shots 2 --demoempty --demoreload 290, BOXENG_AFTER=66 for the figure from the reload's start; new run ids; the wiring run sets coop_lockLoadout 0.",
         tags=["dbshotgun", "harness", "measure", "loadout"]),
]


def main():
    raw = open(P, 'rb').read()
    txt = raw.decode('utf-8')
    ids = [int(x) for x in re.findall(r'"id":\s*"bug-(\d+)"', txt)]
    n = max(ids) + 1
    out = []
    for e in E:
        d = dict(id='bug-%d' % n, timestamp=TS, error_message=e['error_message'], file=e['file'], root_cause=e['root_cause'], fix=e['fix'],
                 tags=e['tags'], related_bugs=[], occurrences=1, last_seen=TS)
        out.append('\n'.join('  ' + l for l in json.dumps(d, indent=2, ensure_ascii=False).splitlines()))
        n += 1
    k = txt.rstrip().rfind(']')
    body = txt[:k].rstrip()
    new = body + ',\n' + ',\n'.join(out) + '\n]\n'
    json.loads(new)
    open(P, 'wb').write(new.encode('utf-8'))
    print('appended bug-%d .. bug-%d' % (n - len(E), n - 1))


if __name__ == '__main__':
    main()
