"""append this lane's defects of 2026-10-13 (third pass: finish set, own armory entry, world tests) to
.wolf/buglog.json (ids from the file's tail at the moment of writing; existing bytes are not re-encoded). Run ONCE."""
import json, re, time

P = r'C:\mohaa-coop-dev\.wolf\buglog.json'
TS = time.strftime('%Y-%m-%dT%H:%M:%S-06:00')
F = "docs/proposals/dbshotgun_2026-10-12/"
E = [
    dict(error_message="Archive move of 28 finished run folders to H:\\hzm_archive\\dbs landed in ONE folder 'H:\\hzm_archive\\dbs$d'; files with the same name in several runs overwrote each other",
         file=F + "tools/archive_sort.py",
         root_cause="A Git-Bash loop called robocopy with the destination \"H:\\\\hzm_archive\\\\dbs\\\\$d\"; the string reached bash with single backslashes, so `\\$d` was a literal `$d` and every run was moved (/MOVE) into the same folder. The 15,117 frames named ab__<run>__... kept their identity; 511 files without a run id in their names (qconsole.log, notes.json, wire.json, wire_*.jpg, tp_* / act_* / ms_* frames, look stills) collided - ONE copy of each survived, the others are lost.",
         fix="tools/archive_sort.py sorted the frames back into H:\\hzm_archive\\dbs\\<run>\\ by the run id in their names (renames only); the rest is in H:\\hzm_archive\\dbs\\_merged_no_run_id\\ with a README. Later moves in this lane use python shutil.move per run folder with a file-count check before and after. Rule: never build a Windows path with a shell variable behind a backslash in Git-Bash - move with python.",
         tags=["dbshotgun", "archive", "data-loss", "git-bash", "robocopy", "escape"]),
    dict(error_message="Double barrel: a finish named the mod's way (\"<Gun> (<Finish>)\") would play the PUMP gun's hands, third-person pump stroke and sight row",
         file=F + "tools/dbs_finish.py",
         root_cause="The gun's name is \"Shotgun (Double Barrel)\" so that the engine's first-\" (\" strip resolves it to \"Shotgun\" (CoopStripSkinSuffix in cgame, CondWeaponActive in fgame). A second suffix (\"Shotgun (Double Barrel) (Gold)\") matches no exact row (coopr_shotgun_double_barrel_*, the five torso rows of patch_torso_dbs.py, the sight row, the loot picture) and strips to \"Shotgun\". gen_skins.py also skips any tik whose name carries \" (\" (it is 'already a variant'), so the mod's generator never makes finishes for this gun.",
         fix="All eight tiks carry the SAME name \"Shotgun (Double Barrel)\"; the armory tells finishes apart by tik path (coop_skinGive / coop_skinBase), ranks are unique (3000-3006, base 645). No engine change, no extra state or sight rows. Seen in engine: all seven finishes at the hip, in the aim, in third person, open (runs f1-f3); WINTER applied from the armory and kept over a map restart and a map change (run a1).",
         tags=["dbshotgun", "finish", "naming", "CoopStripSkinSuffix", "statemap"]),
    dict(error_message="Double barrel base tik shared rank 640 with the pump shotgun",
         file=F + "tools/dbs_tik.py",
         root_cause="The tik was written from the pump gun's tik and kept its `rank 640 640`. The mod's rule (gen_skins.py): a shared rank hides a gun on the weapon wheel - a player carrying both shotguns would lose one.",
         fix="rank 645 645 (free; 610-640 are taken in tens). Finishes 3000-3006.",
         tags=["dbshotgun", "tik", "rank"]),
    dict(error_message="Double barrel: the armory pick was lost at a map change (wiring option A, README sec. 8 of the second pass)",
         file=F + "wiring/stage_armory_dbs.py",
         root_cause="Option A carried the choice as its own name-bus token (,db1) replayed from loadout_resend; a token sent before the first spawn was lost every time (runs w3-w7).",
         fix="Option A is superseded (wiring/superseded/). The gun is an own roster entry (id 80): its pick is the ordinary slot pick (seta coop_loA1 \"append name ,w180\"), replayed by the armory's existing join volleys like every other gun. Run a1: slot 1 = the tik and finish 6 after a map restart (m3l2) and after a map change (m3l2 -> m2l1), looked at in both.",
         tags=["dbshotgun", "armory", "roster", "map-change", "name-bus"]),
    dict(error_message="Harness: after the test `give`, `kill` does nothing (three respawn waits of 75 s, no DEATHDROP) and a scripted `damage 5000` / `kill` did not kill a script-spawned test AI",
         file=F + "tools/mkov_dbs.py",
         root_cause="The ironsight harness's test thread sets `nodamage` on the player at every give. The AI case is not understood: `takedamage` + `kill` on the spawned german_wehrmact_soldier left it standing (run a3).",
         fix="Player: test hook coop_dbsMortal (`takedamage`) before a kill (run_arm.py die()). AI: NOT solved - use-to-loot of an AI-dropped double barrel is still unverified.",
         tags=["dbshotgun", "harness", "nodamage", "ai", "use-to-loot", "open"]),
    dict(error_message="(itemhandler.scr::handleWeaponPickup) *ERROR*: Weapon  with model models/weapons/coop_dbshotgun.tik cannot be picked up by <player>",
         file="hzm-mohaa-coop-mod/coop_mod/itemhandler.scr",
         root_cause="NOT established. Seen 3 times in run a3, each right after a respawn at the place of the player's own death drop while the armory kit (which holds a double barrel) was being issued: the touch found no pickup event, isCarryingAmmoType was false at that instant, and the gametype-0 trigger retry did not pick it up either. Not seen in runs a1 / f1-f3.",
         fix="None yet. To check: the same sequence with the PUMP gun in the kit (is it this gun or any gun at a respawn on one's own drop), and a touch pickup by a player who carries no shotgun.",
         tags=["dbshotgun", "itemhandler", "pickup", "death-drop", "open"]),
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
