# ARCHIVED from docs/OPEN.md on 2026-09-04 - the m1l1 scripted intro ride

Moved out of OPEN.md to keep that file inside its 50 KB ceiling, following the same pattern it
already used for the 2026-08-18 playtest batch. The hunt itself is CLOSED (bug-2064); what is kept
here is its residual open list, every item of which is also in `.wolf/buglog.json` under the bug id
it names, which is the live record. Nothing here is lost - it is one grep away.

## m1l1 scripted intro ride - CLOSED 2026-08-22, one item left

CLOSED: `notarget` reached `Player::NoTargetCheat`, a **toggle** that discards its argument
(**bug-2064**, with 2065/2066/2067 in the same pass). SCOPE WAS TRILOGY-WIDE, not m1l1-only - every
`notarget` write is in shared coop code and `replace.scr::glue` has 15 map callers; m1l1 broke every
run only because it also sets vanilla `level.glueplayer`, firing `playerGlue` twice. Verified live on
m1l1 (4 rides) only. Full narrative in `buglog.json` 2064-2068 and HISTORY.md.

**STILL OPEN from that hunt:**
- **OWED VERIFICATION (bug-2068).** `coop_notargetWatch` now releases only the flag it acquired,
  so build mode and the MoM dev `notarget` toggle survive it - an earlier draft would have revoked
  them within 0.5 s. The ride was re-verified live; the FOREIGN-OWNER path was **not** executed
  (testing paused). Next session: boot m1l1, and while NOT in the ride run
  `rcon set coop_probe notgt` - require `foreign=RESPECTED`. A guard that has never run is not a
  fix (bug-2034).
- **bug-2055 - wall cover.** The open-side solver's STEP 2 (does the body fit through the gap) fails
  in 4864 of 6271 samples - the hull sweep starts at the player's own origin, which in cover is
  against the wall, so it returns startsolid and both sides read closed. The other 22% proves the
  logic sound. Likely fix: offset the sweep off the wall first, or use a reduced hull. The **pose,
  camera and auto-cover symptoms are NOT diagnosed** and need their own probe pass.
- **The gun flicker is NOT measurably reduced** - correction to my own claim. Gives per spawn went
  3 -> 2 (measured), but flickers were 2-over-4-spawns before and 0-over-1-spawn after, which is what
  an unchanged build would produce; and `GUNVIS` is edge-triggered, so a sub-frame unarmed window
  neither prints nor shows. Mechanism settled, rate change unproven. Real fix: make the give
  idempotent (`coop_hasitem`, already used by `coop_backfillPrimaries` but only AFTER the give).
- **The m1l1 ride hiding the weapon/arms for ~74 s is INTENDED - do not "fix" it.** (User,
  2026-08-22: "the m1l1 ride hide I don't want to change that's normal.") The glue calls
  `local.player hide`, which sets `RF_DONTDRAW`, and the viewmodel submission is gated on that
  same flag - so the first-person gun and arms go with the body for the length of the scripted
  ride. It shows up in any capture as a `dontdraw=1 unarmed=0` span of ~74 s and looks exactly
  like a defect if you meet it cold. It is not one. See DECISIONS.md.
- **NEW, larger: the JOIN blank is 3.7-5.6 SECONDS of no arms.** You spawn and the viewmodel is
  empty until the first kit is given. Same `EF_UNARMED` mechanism, far more visible than a 141 ms
  blip, and not the reported defect. **NOT the map holding you unarmed for the scene** (user
  hypothesis, checked and refuted): m1l1 has no `takeall`/`coop_noWeapon`, its four `holster` calls
  are on `level.guard`/`guard2`/`driver`/`passenger` (ACTORS), and `playerGlue` only does
  `notsolid`/`physics_off`/`hide`. Two clocks agree the arms return when the KIT lands, not when the
  scene ends - server "entered the battle" -> KITGIVE = 4.0 s, client HIDE -> SHOW = 3.68 s - and
  the blank closes entirely BEFORE `glued=1` (t=50..110). So it is spawn->first-give latency. Why
  that latency is ~4 s is not investigated.
- **bug-2053 - free-cam scroll** consumes the mouse wheel instead of switching weapons. Narrowed by
  the user to free cam only (chase cam is correct), so the search is small. Not investigated.
- **Probe fidelity:** `canSeePlayer` read 0 through two otherwise-correct rides and 8-10 through two
  others - `replace.scr::player_closestTo` sometimes returns NULL for a glued player. Harmless to
  play, but it is a census column being trusted in diagnosis.

