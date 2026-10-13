"""append this lane's defects of 2026-10-13 (fourth pass: world behaviour, server timing, merge with integ-ads, ship
cut) to .wolf/buglog.json (ids from the file's tail at the moment of writing; existing bytes are not re-encoded).
Run ONCE."""
import json, re, time

P = r'C:\mohaa-coop-dev\.wolf\buglog.json'
TS = time.strftime('%Y-%m-%dT%H:%M:%S-06:00')
F = "docs/proposals/dbshotgun_2026-10-12/"
E = [
    dict(error_message="(itemhandler.scr::handleWeaponPickup) *ERROR*: Weapon  with model models/weapons/coop_dbshotgun.tik cannot be picked up by <player> - cause of bug-3813 established",
         file="openmohaa-hzm/code/fgame/weapon.cpp",
         root_cause="Not this gun. Weapon::PickupWeapon, branch `!hasweapon && !hasclass` for an item that is NOT a dropped item (BSP-placed, script-spawned, the mod's death drops): `ItemPickup(other); return;` leaves before `Unregister(STRING_PICKUP)` at the function's end, so the script's `waittill pickup` (itemhandler.scr::waitTillPickupEvent) never fires for that pickup. handleWeaponPickup forces the pickup (gametype 0 + triggereffect), sees no pickup event and prints the line - while the gun IS in the inventory (the item is gone: `group.item` prints empty, the loop ends, addWeaponToInventory runs). Reproduced with the pump gun in run w1 (`... models/weapons/shotgun.tik cannot be picked up` followed by `Picked Up Shotgun`, coop_hasitem 1); 77 x kar98, 2 x thompsonsmg, 2 x shotgun in other lanes' archived logs. The third pass's note that the kit held a double barrel was wrong (run a3's kit: Frag, Colt 45, StG 44, Thompson).",
         fix="None in this lane (no fgame change; the line is harmless). The double barrel is registered like every other gun (tik init exec + getAmmoType + isPrimaryWeapon): the staged wiring needs no change. Mod-wide options, not done: Unregister(STRING_PICKUP) before that early return (fgame), or treat `!group.item` after the forced trigger as picked up (itemhandler.scr).",
         tags=["dbshotgun", "itemhandler", "pickup", "false-alarm", "waittill-pickup", "fgame"], related_bugs=["bug-3813"]),
    dict(error_message="Use-to-loot: with a PUMP shotgun in the kit, an AI-dropped double barrel cannot be taken as a gun - the tap is cancelled (`LOOT cancel ... tap-owned`), only its shells are offered",
         file="openmohaa-hzm/code/fgame/player.cpp",
         root_cause="Player::CoopLootOwns -> s_hzmLootSameGun compares the two item names cut at \" (\" (a finish is the same gun). \"Shotgun (Double Barrel)\" cut there is \"Shotgun\": the loot rule calls the double barrel OWNED by anyone who carries a pump gun, and a pump gun owned by anyone who carries the double barrel. Run w2: kind 3 (owned, pool full) / kind 2 (owned): hold = +2 shells, gun consumed. Run w3 (no shotgun in the kit): kind 1, tap = `LOOT picked ... asNewGun=1`.",
         fix="None (fgame is outside this lane). Consistent with the touch rule (same weapon class = the other gun's shells only). No map and no AI alias hands an AI this gun, so today the case exists only in a test. If both guns are to be carried from the world: one exception row in s_hzmLootSameGun for full-name matches.",
         tags=["dbshotgun", "use-to-loot", "naming", "fgame", "sibling"], related_bugs=["bug-3809"]),
    dict(error_message="Harness: a script-spawned German could not be killed (`exec global/bullethit.scr ( 0 0 250 ) 5000 0 1`: still alive; third pass: `damage 5000`, `kill`), and it shot the test player dead with the double barrel",
         file=F + "tools/dbs_world.scr",
         root_cause="(1) bullethit.scr sends `damage NULL ...`: aihandler.scr::actorPainHandler ends at once on an attacker-less hit and the actor's health is the mod's 5000 buffer (the real HP is in flags coop_actorActualHealth). (2) The mod's spawn protection ends with `takedamage`, which undid the test's `nodamage` 8 s after the respawn; with g_ai 1 the armed AI fired (SHOTDIST lines, `<player> died`).",
         fix="dbsw_ai: `nodamage` on the player right before g_ai 1; the kill is `local.g damage local.p 5000 local.p ( 0 0 0 ) local.fw ( 0 0 0 ) 0 16 17 3` (attacker = the player: the event a real bullet makes), repeated until not alive - one hit was enough (runs w2, w3). g_ai 1 only around the AI's life.",
         tags=["dbshotgun", "harness", "actor", "pain-handler", "bullethit", "spawn-protection"], related_bugs=["bug-3812"]),
    dict(error_message="Double barrel on the mod tree's state file: a reload begun with a shell in the gun would be broken off through RELOAD_SHOTGUN_BREAK_QUICK - the shot 0.33 s after the trigger with the gun still OPEN",
         file=F + "wiring/patch_torso_dbs.py",
         root_cause="The heavy lane's break-off (patch_sgbreak.py, mod tree 02405cef) added RELOAD_SHOTGUN_BREAK_QUICK / _SINGLE_CH for the pump gun (a hand-back with no pump). The double barrel shares the shotgun reload states and its torso patch only knew the end rows.",
         fix="patch_torso_dbs.py: two routing rows in front of the BREAK_QUICK rows (RELOAD_SHOTGUN, RELOAD_SHOTGUN_SINGLE_CH) send THIS gun to RELOAD_SHOTGUN_BREAK_END (its own end row: the gun is shut, then the owed shot). 0 such rows in a file without the break-off, 2 in the tree; --check passes on the deployed file and on the tree (tools/torso_check.py). Run w2: trigger -> RELOAD_SHOTGUN_BREAK_END -> shot 1.150 s later; the pump gun still goes BREAK_QUICK -> shot 0.325 s later, equal with and without the patch (run wb).",
         tags=["dbshotgun", "statemap", "player_Torso.st", "break-off", "heavy-lane"]),
    dict(error_message="Double barrel third-person end row lacked the heavy lane's `removeattachedmodel tag_weapon_left 0 models/ammo/shotgunshell.tik`",
         file=F + "rows/tps_rows_coop_dbshotgun.txt",
         root_cause="The shared shotgun_reload_loop row now attaches a shell to the support hand (third person) and counts the shell on frame 14; shotgun_reload_end removes a shell left in the hand when a reload is broken off. Our own end row (coop_dbs_reload_end) was written before that.",
         fix="The same server line added to coop_dbs_reload_end.",
         tags=["dbshotgun", "third-person", "anims_shotgun.txt", "heavy-lane"]),
    dict(error_message="Merge of dbshotgun-next with integ-ads: an EMPTIED double barrel reloaded while aiming would have thrown out ONE case (plain `reload`), and cg_viewmodelanim.c / cg_adssights.h conflict",
         file="openmohaa-hzm/code/cgame/cg_modelanim.c",
         root_cause="integ-ads's aimed-reload block in CG_ModelAnim owns the `reload` row: at the hip it swaps to `reload_empty`, while aiming to `reload_ads_empty` / `reload_ads_loaded` - names the double barrel's tiks did not have. The README's merge note (\"each block would swap the other's result back\") was wrong: neither swaps back; the gap was the missing aimed name.",
         fix="The 8 tiks carry `reload_ads_empty` (= the reload_empty clip; tools/dbs_tik.py, tools/dbs_tikrow.py). dbshotgun-next 45373131 = integ-ads 37e5dde8 merged in: cg_adssights.h = integ's table + our row (sightrow_dbs.py re-run), cg_viewmodelanim.c = integ's side + our `_l` block, cg_modelanim.c: our block reduced to reload_single -> reload_single_first. Harness DLL cgame_dbs9 (md5 db892524); runs w2, w3, rs1, rs2.",
         tags=["dbshotgun", "cgame", "merge", "integ-ads", "CG_ModelAnim", "reload_ads_empty"]),
    dict(error_message="Harness overlay base (ovbase_1021.pk3) carried the 1.10.21 weather.scr; the deployed weather.scr is 2.3 KB longer since 2026-10-13",
         file=F + "tools/mkbase_dbs.py",
         root_cause="The ADS lanes' plumbing pak replaces coop_mod/weather.scr whole (test thread spliced in). After the day's deploy the harness's game paks hold a newer weather.scr; the old base would have put the released file over it.",
         fix="tools/mkbase_dbs.py rebuilds the plumbing on the weather.scr that is deployed now (build/ovbase_cur.pk3); mkov_dbs.py uses it (env DBS_OVBASE for another). The shared ovbase_1021.pk3 was not touched.",
         tags=["dbshotgun", "harness", "overlay", "weather.scr"]),
    dict(error_message="Python edits passed through a Git-Bash heredoc broke twice: `\\\\t` / `\\\\n` arrived as real tabs / newlines inside a quoted string (SyntaxError), a Windows path raised a unicodeescape error",
         file=F + "tools/_fix_torso_patch.py",
         root_cause="The known heredoc escape trap (memory: heredoc-escape-gotcha), walked into again for 'small' edits.",
         fix="Every edit of a file that holds escapes is a script written with the Write tool (tools/_edit_*.py, _fix_torso_patch.py) or the Edit tool.",
         tags=["dbshotgun", "git-bash", "heredoc", "escape", "repeat"]),
    dict(error_message="Armory: with coop_dbShotgun 0 the hidden DOUBLE BARREL tile left an empty row in the middle of the heavy tab",
         file=F + "wiring/stage_armory_dbs.py",
         root_cause="The tile sat directly under the trench gun and the four tiles below were moved down; a hidden tile keeps its row.",
         fix="The tile is the LAST tile of the heavy tab (y = the tab's last tile + 19); no other tile moves (the checksum-locked urc changes by two blocks). Looked at with the switch on and off (run w3, media/dbs_armory_heavy_tab_switch_on_off.jpg).",
         tags=["dbshotgun", "armory", "urc", "master-switch"]),
    dict(error_message="World test: the second AI drop was not offered (coop_lootT 0) - the driver aimed at the player's own holstered gun",
         file=F + "tools/dbs_world.scr",
         root_cause="dbsw_find takes the first Weapon entity of the model whose origin is not the world origin; a gun the player carries sits at the player, not at 0 0 0, and had the lower entity number (run w3, part H).",
         fix="Not re-run: the hold (shells) is proven by run w2's part H (`LOOT ammotake ... pool 10 -> 12`). A later driver should skip weapons that have an owner (e.g. only entities farther than 40 u from every player).",
         tags=["dbshotgun", "harness", "test-flaw"]),
]


def main():
    raw = open(P, 'rb').read()
    txt = raw.decode('utf-8')
    ids = [int(x) for x in re.findall(r'"id":\s*"bug-(\d+)"', txt)]
    n = max(ids) + 1
    out = []
    for e in E:
        d = dict(id='bug-%d' % n, timestamp=TS, error_message=e['error_message'], file=e['file'], root_cause=e['root_cause'], fix=e['fix'],
                 tags=e['tags'], related_bugs=e.get('related_bugs', []), occurrences=1, last_seen=TS)
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
