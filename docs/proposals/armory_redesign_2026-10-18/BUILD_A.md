# Direction A - "Quartermaster" (build note)

Four columns on the existing 640x480 virtual grid: operator | 4 loadout slots | weapon card grid | inspector.
Picker = 2-column grid of gun cards (render + name), **unlocked first**, then a `LOCKED n` divider and dimmed cards that carry a
padlock, the requirement and a progress line. Inspector = big render on a plate, finish swatches, five-row comparison against the
gun in the active slot, EQUIP button, "next unlock" card with XP progress.

## Where every number comes from (no hand-typed stats)
`tools/gen_weapon_stats.py` reads `docs/tools/loadout_weapons.tsv` (which guns), the `.tik` of each gun (mod tree first, then the game
paks, `$include` chains flattened) and writes `tools/armory_stats.json/.tsv`:

| row | source in the .tik | raw shown | bar |
|---|---|---|---|
| damage | `dm bulletdamage` (x `bulletcount` only for pellet guns, >= 6) | per shot | /100 |
| rate of fire | `dm firedelay` -> 60 / delay | rpm | /800 |
| accuracy | `dm bulletspread` (min+max)/2, x `zoomspreadmult` for scoped guns | score | 1 - spread/130 |
| mobility | `dm movementspeed` (default 1.0) | % of walk | 0.5..1.1 |
| reload | frames x frameTime of the `reload` .skc | seconds | 4.5 s..1.0 s |

Rule: the `dm` line wins, else the bare line; `sp`/`realism`/`dmrealism` are ignored (coop runs `g_gametype 2`). Caps are global
constants, so a bar means the same thing on every tab. Unlock text = `ui/loadout/req<id>.cfg` (already generated from challenges.scr /
xp.scr); rank names and XP thresholds = `xp.scr`. **Known gaps**: 14 of 76 guns have no reload (their `.skc` is a version-14 "processed"
anim, MSG-coded; needs a port of `LoadProcessedAnimEx` or a one-off engine dump), and bazooka/PIAT/Schreck have no `dmg` (it sits in
the projectile `.tik`). Challenge progress and the player's rank/XP in the mock-up are sample data.

## urc only (no engine change)
* New static chrome: panels, keylines, headings, column frames baked into a new `textures/mohmenu/coop_lo_bg*.tga` by a generator
  (the current texture already bakes the panels, the "ARMORY" title and the DMG/RPM/ACC/MOB labels, so this is a texture swap, made
  at build time, not in this mock-up).
* Cards, tabs (with counts and an active state via a second Button/Label gated on `coop_loNP*`), swatches, padlocks (`coop_lo_lock.tga`
  is already used), progress lines (a Label with `bgcolor`, 11-step gated widgets like the existing `coop_bfN` bars), delta colours
  (three Labels per row, green/red/grey, gated by `enabledcvar`).
* The big inspect = the existing `prevC*` model Label with `rendermodelfit 1`, enabled by setting `coop_loPvC<class>` in `p<id>.cfg`
  and re-rect'd to 140x84. Finishes already work by swapping the model tik (`finp<id>_<n>.cfg`). This mock-up's renders were made
  by a full-screen copy of that widget (`tools/run_armory_capture.py` overlay), so the look is what the engine draws.
* Card grid thumbnails: one model Label per visible card (about 13 per tab) reading `coop_loG<n>` (generated).

## Needs scripting (game DLL, `loadoutpick.scr`)
* **Unlocked-first order**: the order depends on the player, so the server pushes `coop_loOrd<tab><n> = <id>` (diff-only, same
  mechanism as the lock export), and a generated `gridfill<tab>.cfg` maps positions to the id's name / model / lock cvars.

## Needs cgame (engine, small)
* **Delta arithmetic**: a cfg cannot subtract. One new client command (e.g. `coop_cmpstat`) that reads the candidate's and the
  slot's stat cvars and writes `coop_loDl<r>` text plus `coop_loDs<r>` = 0/1/2 (worse/better/equal). Without it the fallback is
  the server push in Direction B.
* Fonts used: verdana-12, facfont-20, delima-30 only (the safe set); text sizes are the real 7.5 / 10.7 / 19.5 vy.

Risk: medium. Most work is generator output; the two moving parts are the server-side order push and the cgame command.

## Provenance of the mock-up pixels
Renders: harness runs `arm1` / `arm2` (private copy, gunfit2-next @ c12c83bd + a test-only overlay urc; raw frames in
`G:\claude_scratch_archive\armory_design\`), matted by `tools/build_cutouts.py` into `assets/`; composite: `tools/build_mockups.py`
(`bm_core.py`, `layouts.py`, `gamefont.py`). Regenerate everything: `python tools/gen_weapon_stats.py && python tools/build_mockups.py`.
