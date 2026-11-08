# v1.10.64 weapon fixes: viewer issues, the heavy-MG split, bipod MG heat, the gold Thompson (2026-11-08)

User: *"Fix the issue in the weapons viewer, btw I don't feel like all of our heavy mg's are actually in the class of heavy
mg's, some are reskinned varients of other weapons. they should be ported as their own weapon under heavy class."* +
*"All heavy machine guns that have bipods should technically have overheat capability and the same mount ability as the mg42
and be stable when using bipod."* + *"Bar probably doesn't need to overheat"* + *"The thompson gold shouldn't be its own
weapon, it's a variant so it follows the variant unlock path."*

| piece | where |
|---|---|
| mod | branch `wpnfix` (worktree `H:\hzm_work\wpnfix-mod`, off `hotfix-1.10.53` b4f53a1f) |
| engine | branch `wpnfix-eng` (worktree `H:\hzm_work\wpnfix-eng`, off `rel-1.10.38-engine` 829344d7): game.dll + cgame.dll only |
| new pak | `zzzzzzzzzzzzzzzz_coop_wpnfix.pk3` = `python docs/tools/gen_wpnfix_pak.py build` from `docs/tools/assets/wpnfix/` (listed in build.ps1 / publish_release.ps1) |
| harness | `docs/proposals/wpnviewer_2026-11-04/tools/wpnview_run.py setup_fix / mg / shots` on `G:\mohaa-wpnview` (DISPLAY2) |

## The trap this work kept hitting: the copy the game loads is not the one you edit
A weapon .tik ships in up to six places - mod tree (assets pak), fixes (10 z), fixes2 (12 z), stress (13 z), late (14 z),
scopeglass (15 z) - and the last-sorting one loads. The out-of-band paks have no sources. **v1.10.63 shipped the two invisible WW1
variants anyway** (bug-10526 was fixed in the mod tree; scopeglass carried the broken copies), and the first TT-33 SILENCED fix
went into the fixes pak under a stress copy. `gen_wpnfix_pak.py winner <rel>` names the copy that loads; `adopt` takes it into
`docs/tools/assets/wpnfix/` and pins its md5, so `check` fails if someone changes the base under us.

## What changed
* **WW1 imports dark / see-through in menu previews** - measured, not guessed: `r_fastentlight`, `r_light_nolight` and a HUD
  ambient cvar changed nothing (a preview is already lit 1:1); swapping meshes and shaders showed the cause is the art (flat,
  low-key sheets). `gen_east_lift.py`: luminance-only lift of the 59 East sheets (G98, SMLE, MP18, Webley, C96 trench, M1903,
  G98 scoped, P14, Lewis) to the stock guns' exposure (p90 ~70), hue kept. This also brightens them in game (they were dim there too).
* **Mills bomb black** - its sheet's alpha is ~0 on 99.95 % of texels. `scripts/coop_wpnfix.shader` maps the same stage on an RGB
  copy; the viewer shows the 3D model (no 2D icon).
* **TT-33 SILENCED finishes** - gen_skins.py: a silenced twin's body surfaces take the base gun's finish shaders (bug-10532), the
  fixed tiks ship in the wpnfix pak (over stress).
* **Lewis gun -> its own HEAVY gun (Armory 81)**, same tik (`bar_bar1918.tik`, "Lewis Gun"), 47-round pan. Unlock = the challenge
  that unlocked the BAR variant, `wpn_bar_mv9` (275 BAR kills): kept at the same Service Record index with the same reward token,
  so everyone who had the variant has the gun. The BAR's fid 9 is RETIRED (wire_mv2.py / variant_challenges.py retired-fid
  support): later fids, their archived picks and challenge ids do not move; an archived pick of BAR variant 9 lands on the Lewis.
* **Gold Thompson (71) folded into the Thompson's GOLD finish** - it was the Thompson's gold finish tik filed as a gun, unlocked
  by `wpn_thompson_gold`, which is already the Thompson's gold rung (finchal_gen.scr). An archived pick of 71 lands on the
  Thompson (24) + gold. No unlock migration needed (same challenge).
* **DP-28** carried the BAR's 20-round magazine; the pan holds 47 (the Armory card always said so).
* **Bipod MGs overheat** (engine): `BG_CoopHandHeatPerRound` (bg_misc.cpp, shared by game.dll and cgame.dll) replaces the
  MG42 / .30 cal model test; per-gun heat per round, finish suffix stripped; BAR excluded. Brace / mount / braced stability were
  already gun-agnostic (CoopBraceEnv; the bipod recoil cut for WEAPON_CLASS_MG, which every one of these is); the bipod-on-cover
  flush gained the Lewis / DP-28 / Vickers offsets (generic, as the Breda's).
* Gates brought back to green on the way: gen_loadout check (row 79 missing since the FG 42 irons integration, finish hovers
  derived from the retired account challenges, the v1.10.61 caption fit missing from gen_armory_urc) -> EXACT REPRODUCTION.

## Reskin audit (standalone Armory entries that are really a finish / skin)
Every roster gun now has its own mesh (77 guns, 77 distinct skd). Flagged for the user, not changed:
* 25 THOMPSON DRUM (`thompson50.tik`) - a Thompson with the 50-round drum; arguably a Thompson variant.
* 33 MOSCHETTO M38 (`it_w_moschetto.tik`) and 34 BERETTA M38A (`moschetto.tik`) - the same weapon, two models.
* The silenced / scoped / iron-sight entries are separate guns by design (own stats, own unlocks) - left.

## Bipod MG table (harness `mg` on m2l1, private client, wpnfix game/cgame; HANDHEAT / HANDHEATHUD log lines)
| gun (Armory id) | bipod in service | heat / round | measured cook-off (sustained fire, prompt reloads) | heat meter | brace / braced stability |
|---|---|---|---|---|---|
| MG42 (43) | yes | 3.5 (unchanged) | 1st belt | yes | as before |
| M1919 .30 cal (42) | no (tripod) | 4.5 (unchanged) | not re-run | yes | as before |
| Lewis Gun (81, new) | yes | 2.35 | in the 2nd pan (141 rounds, 3 pans) | yes | generic brace; MG kick cut (weapontype mg); bipod flush offset generic |
| DP-28 (72) | yes | 2.6 | start of the 3rd pan | yes | same |
| Breda M30 (41) | yes | 4.5 | 3rd charger (60 rounds in 24 s; its reload is ~6 s) | yes | same |
| Vickers-Berthier (40) | yes | 3.0 | 3rd magazine | yes | same |
| BAR M1918 (36) | yes (A2) | none (user) | no meter, no cook-off (measured) | no | same |

Brace, mount (cover and prone) and the braced recoil / spread cut are gun-agnostic in the engine (Player::m_fCoopBrace for
every weapon, the bipod recoil cut for WEAPON_CLASS_MG), so these guns already had the MG42's behaviour; this was read from the
code, not exercised on cover in the harness. The bipod-on-cover flush offsets for the Lewis / DP-28 / Vickers are the generic
(Breda) values and were not checked visually. `weapdrop` drops neither the BAR nor the Lewis in a coop game (same behaviour).

Media: `media/viewer_before_after_720.jpg` (12 guns, v1.10.63 vs wpnfix), `media/armory_heavy_lewis_720.jpg`,
`media/viewer_heavy_tab_720.jpg`, `media/lewis_fire_reload_drop_720.jpg` (red heat meter while firing). Runs: `H:\hzm_work\wpnviewer\runs\`.
