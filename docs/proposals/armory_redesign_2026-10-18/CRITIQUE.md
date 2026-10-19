# Armory (loadout) critique, 2026-10-18

Evidence: a fresh 1920x1080 capture of the real menu from a private harness (`media/real_open.jpg`, `real_tab_smg.jpg`,
`real_locked_click.jpg`, `real_finish_gold.jpg`; run `arm1`, mod = gunfit2-next @ c12c83bd, veteran test record with a
partial unlock set) plus the 76-gun slot-thumbnail sheet `docs/proposals/loadout_review_2026-10-15/media/fit_v2.jpg`.
Font sizes below were measured against the live menu: verdana-12 is about 7.5 vy tall (a 640x480 virtual grid), i.e. 17 px at
1080p and 11 px at 720p.

## What makes it look bad (ordered by impact)

1. **No focal point, because the gun itself is not on screen.** The one thing a player comes for, the gun, lives in four
   108x50 thumbnails and a 20 px text list. The big inspect preview (`prevC0..5`, 152x100, gated on `coop_loPvC*`, which every
   `p<id>.cfg` sets to 0) is never shown, so the right panel is a name, a caliber line and four thin bars with a ~150 px
   hole above them (`real_open.jpg`, x 1430-1900, y 70-330). The picker is 13 identical dark bars: nothing in a row
   tells a Garand from a Kar98K except its text.
2. **The stat panel is the weakest block and is not comparative.** DMG/RPM/ACC/MOB are 7 px labels beside gold
   bars with no number, no unit and no reference, so "is this better than what I carry" cannot be answered. The bars are
   hand-typed texture indices (`b0..b3` in `loadout_weapons.tsv`), not derived from the weapon files. Worse, the panel can
   show a **stale gun**: on open it described an STG 44 that is neither equipped nor selected, and the operator held it too
   (`real_open.jpg`, `real_tab_smg.jpg`). For a locked gun the bars are blanked, leaving four empty outlines.
3. **Lock state is a 12 px padlock at the end of a row, and sort order is authoring order.** Locked and unlocked rows
   share the same fill, text colour and weight, so the lock icon is the only signal; there is no progress ("Staff
   Sergeant: 54%"), the requirement only appears after a click. On the SMG tab the order is Thompson, Drum (locked), MP40
   (locked), MP40 Silenced (locked), Sten, PPSh (`real_tab_smg.jpg`): unlocked and locked interleave, so the player scans
   past locks to find what they can use.
4. **Hierarchy is flat.** Everything is the same slate rectangle, the same cream 12-unit verdana, the same 1 px border.
   The selected state is a 1 px green edge on the slot card; the active tab (RIFLE / SMG) has no visible state at all,
   so a player cannot tell which category is open. Headings (OPERATOR, LOADOUT, WEAPONS, DMG...) are 6-7 vy grey caps; the
   only large type is the baked "ARMORY".
5. **Contrast and legibility at small sizes.** Grey-on-slate captions (OPERATOR, LOADOUT, RDS, RECOIL PATTERN, the
   footer) are about 3:1 and 11 px at 720p, below what is readable at arm's length. The operator caption text is **clipped**:
   "Finish the Ardennes with nobody g(" runs out of its panel (`real_open.jpg`, x 40-430, y 130-175).
6. **Spacing and card design are inconsistent.** Slot cards are 4 stacked boxes with a decorative circle (meaning
   nothing) and the gun thumbnail left-aligned in a box that has a second, empty, differently-tinted box beside it;
   gutters differ (4, 5, 6 px) between columns; the finish chips sit on the very bottom edge touching the footer and their
   lock icons overlap the chip text ("CHROME" / "BLUED" render as "CHROM(lock)").
7. **Dead space in the wrong places.** The centre column below GRENADE (about 60 px), the whole lower half of the picker
   when a tab has fewer than 13 guns, and the area right of the stat panel are empty, while the operator column is a
   tall black box with a small figure and three stepper rows pushed to its floor.
8. **Colour carries nothing.** One slate, one cream, a gold bar fill. None of the HUD palette (revive red / heal green /
   place orange / use cream / objective blue / track #131211) is used, so the Armory does not read as part of the same
   game as the HUD; "equipped" is a 12 px green square, and there is no better/worse colour.

## What the redesign must therefore do

* Put a big, real gun render on screen (turn the inspect preview on and make it the hero) and make the picker visual.
* Sort **unlocked first** in every list (guns now; skins, helmets, gloves, finishes use the same rule), locked items dimmed
  with the requirement and a progress line visible without a click.
* Replace the four anonymous bars with a five-row comparison against what the slot holds now: damage, rate of fire,
  accuracy, mobility, reload, numbers + green/red deltas, derived from the `.tik` files.
* A clear category strip with counts and an active state; consistent 4 vx gutters; no clipped text; HUD palette.

See `BUILD_A.md` / `BUILD_B.md` for what each direction costs, and `mockup_A.jpg` / `mockup_B.jpg`.
