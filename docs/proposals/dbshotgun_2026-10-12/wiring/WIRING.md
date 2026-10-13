# Wiring the double-barrel shotgun into the mod - OWN ARMORY ENTRY (id 80) - STAGED, nothing applied

Option A (a switch on the trench gun's page) is **superseded**: `superseded/patch_wiring_dbs.py`, kept for the record,
do not apply. The cvar `coop_dbShotgun` stays, as a master on / off only.

## What to apply, in this order
| step | what | file here |
|---|---|---|
| 1 | game files: 8 tiks, mesh, clips, 2 shader files, 7 textures, loot picture, the 2-round clip picture | `../assets/` (same paths in the mod tree / fixes pak) |
| 2 | hands rows + third-person alias rows | `../rows/fps_rows_coop_dbshotgun.txt`, `../rows/tps_rows_coop_dbshotgun.txt` (inside the shared files, README sec. 10) |
| 3 | torso state rows (no pump stroke, the aimed second barrel) | `patch_torso_dbs.py <player_Torso.st>` (`--check` passes on the mod tree of 2026-10-13 and on the released file) |
| 4 | the armory entry: 18 mod files changed + the TSV row + 2 generator patches | `gen/armory_dbs.patch`, `gen/generators.patch` |
| 5 | the armory entry: 12 new files `ui/loadout/p80 t80 w80_s1 w80_s2 req80 finp80_1..7 .cfg` | `gen/new/` |
| 6 | regenerate, then check | `gen_loadout.py build`, `gen_skinbase.py`, `armory_unlocks.py --emit`, `gen_service_record.py build` (build.ps1 runs the last one); `gen_loadout.py check` must pass. The generated files in the patch (`unlockreq_gen.scr`, `loadoutskins_base.scr`, the `roster_ids` block, `ui/loadout/*80*`) are what the generators write from the edited sources - re-running them is the clean way; `unlockreq_gen.scr` had drift in the tree before this gun |
| 7 | `ui/coop_loadout.urc` has no generator and is checksum-locked: update `LOCKS["ui/coop_loadout.urc"]` in `docs/tools/check_mp_isolation.py` (sha256_lf / sha256_crlf / lf_bytes) after applying, or build.ps1 blocks | - |
| 8 | the cgame: `dbshotgun-next` 96c32bd9 (unchanged this pass) | `C:\mohaa-coop-dev\openmohaa-hzm-dbs` |

`stage_armory_dbs.py [--sr]` makes steps 4-5 from the mod tree AS IT IS (re-run it when the tree changes; every anchor
is a name and is asserted). The G 43 Irons (78) and the FG 42 Irons (79) edit the same roster count, lktab files and
tile list: apply one, re-run the next one's script.

## The entry
* Roster id **80**, give `models/weapons/coop_dbshotgun.tik`, tile **"DOUBLE BARREL"** on the HEAVY tab directly under
  the TRENCH GUN (bazooka, panzerschreck, PIAT, DP-28 move one row down), "12 GAUGE / BREAK-ACTION", bars DMG 10 / RPM 3 /
  ACC 6 / MOB 10 (trench gun 10 / 1 / 8 / 9), 2 rounds (`textures/hud/clip/clip_2.tga`, new), slot / ammo / class as the
  trench gun (primary, shotgun, heavy, 40 shells).
* **Unlock: challenge "Both Barrels" - Get 60 kills with the Shotgun** (`wpn_shotgun_v`, SUPPORT WEAPONS). The mod's
  rule for a gun's sibling (the "VARIANT UNLOCK CHAINS" block: drum Thompson, silenced MP40, scoped StG ... = 100 kills
  with the base gun, between its base and its elite challenge); the shotgun's are 30 and 90, hence 60. It rides the
  EXISTING statistic `wpn_shotgun` - no new statistic, no engine or save-format work; the double barrel's own kills count
  on it too (`chal_widFromModel`: "shotgun" is in the tik name). Progress is stored per challenge id, so everyone starts
  this one at 0, and no existing record is rewritten. It is the last `chal_def` of challenges.scr: no existing
  challenges.scr row changes its export index (the 77 generated variant rows after it move by one).
* **Finishes** fid 1-7 -> the 7 staged finish tiks. They unlock exactly as the pump gun's: the finish itself is
  account-wide (its own challenge), and the gun takes finishes once `wpn_shotgun` (30 shotgun kills) is done - the
  same gate as the pump gun, shared.
* **Master switch** `coop_dbShotgun` (server, default 1). At 0: the pick is refused ("... is switched off on this
  server", the client keeps its archived pick), the tile is hidden (`coop_loP3d`, set by `ui/loadout/lktab3.cfg` through
  the archived client command `coop_loDbT` the server sends with the padlocks) and its padlock is off. The row stays as
  a gap in the list; the PRIMARY card keeps showing the archived pick.

## Run (private test install, overlay `mkov_dbs.py --armory`, coop_lockLoadout 1) - README sec. 8 has the table
