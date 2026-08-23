# Paradrop Medic — Kneel-and-Tend Animation

Follow-up to `medic_heal_anim_research.md`. Replaces the standing canteen-pass
gesture on the paradrop medic with a kneeling "tending the wounded" motion — the
exact D-Day mission medic clip the user asked for.

---

## 1. Chosen clip + label

**Clip: `models/human/animation/scripted/level_m3l1/medic01.skc`**
(the D-Day mission `dday_ranger_medic` kneeling-beside-a-wounded-comrade clip
used at `maps/m3l1a.scr` lines ~6793/6808 — `$right_medic anim medic01`, etc.)

- **Pak/location:** `main/Pak0.pk3` — loads on **every AA map** under
  `fs_game=maintt`. No `mainta` copy needed. (The e1l1 `A_11_cot_medic.skc` and
  e2L1 `AA_soldier*_kneel.skc` alternates live in `maintt/pak1.pk3`; medic01 in
  base Pak0 is the safer, always-present choice and is the literal D-Day medic.)
- **Root translation: ZERO.** SKAN header `totalDelta = (0,0,0)` (verified by
  binary decode of the header at offset 0x14). The medic kneels exactly where it
  stands — no drift away from the player. Confirmed for both medic01 and medic02.
- **Length:** 99 frames @ 15 fps = ~6.6 s full clip (we break out early, see below).
- **No prop attach** in the clip (no canteen model auto-attaches; medic01 has no
  server/client block in the source `level_m3l1.tik`).
- In the shipping game it is played with plain `anim medic01` on a `notsolid`,
  non-combatant scripted actor placed at a fixed origin ~52 u from the patient,
  facing it. We reproduce "fixed origin + facing" via lookat/turnto + dumb.

**New label (defined by this change): `coop_medic_kneel`**
(plus `coop_medic_kneel_alt` -> medic02.skc, available if you want variety).

Why a new label and not the stock `medic01`: stock `medic01` is only defined
inside the `$mapspec m3l1a` / `includes m3l1a` blocks of `new_generic_human.tik`,
so it is NOT loaded on m4l3 or any other coop map. We define our own global label.

---

## 2. Anim-config / include approach (non-breaking)

The mod already ships its own override of the shared anim config
`models/human/new_generic_human.tik` (which `dday_ranger_medic.tik` `$include`s).
The medic model file itself is NOT touched — spawning as a normal Actor is
unchanged.

**New file:** `models/human/animation/scripted/coop_medic.tik`
```
animations
{
	$path models/human/animation
	coop_medic_kneel		scripted/level_m3l1/medic01.skc
	coop_medic_kneel_alt		scripted/level_m3l1/medic02.skc
}
```

**Edit to `models/human/new_generic_human.tik`** — one `$include` added in the
GLOBAL (unconditional) section, right after the existing HZM weapon-pack block
and BEFORE the first `includes <map> { }` block (so the label exists on every
map, exactly like the HZM weapon includes):
```
$include models/human/animation/human_beretta.tik
// HZM COOP MOD - global kneeling medic gesture (coop_medic_kneel) for the paradrop medic
$include models/human/animation/scripted/coop_medic.tik
```

This does not break the base anim set: it only ADDS two labels in the global
scope; no existing label/path/block is modified.

---

## 3. coop_paradrop_medic changes (coop_mod/paradrop.scr)

Both heal paths changed; `dbno_ai_revive` and all combat/follow/voice functions
untouched. The med_kit sound and the revive/heal logic are kept intact.

### PRIORITY-1 (DBNO revive) branch — was upperanim pass_canteen_*:
```
} else {
	local.actor lookat local.down
	local.actor turnto local.down
	local.actor dumb
	local.actor anim_scripted coop_medic_kneel
	wait 1.6
	thread coop_mod/dbno.scr::dbno_ai_revive local.down
	local.actor playsound med_kit
	iprintlnbold "An Allied Medic revived a teammate!"
	wait 1.4
	local.actor lookat NULL
	local.actor aion
}
```

### PRIORITY-2 (heal) branch — was upperanim pass_canteen_*:
```
} else {
	local.actor lookat local.target
	local.actor turnto local.target
	local.actor dumb
	local.actor anim_scripted coop_medic_kneel
	wait 1.6
	local.nh = local.target.health + 35
	if( local.nh > 100 ){ local.nh = 100 }
	local.target.health = local.nh
	local.actor playsound med_kit
	iprintlnbold ("Allied Medic patched you up! HP: " + local.nh)
	if( level.coop_medic_voicetime == NIL ){ level.coop_medic_voicetime = 0 }
	if( (level.time - level.coop_medic_voicetime) >= 8 ){
		level.coop_medic_voicetime = level.time
		local.actor playsound coop_para_help
	}
	wait 1.4
	local.actor lookat NULL
	local.actor aion
}
```

### dumb / anim_scripted / restore rationale
- The paradrop medic is a `forceactivate`d LIVE combat AI (unlike the SP medic,
  which was an inert scripted prop-actor). A full-body scripted anim on a
  thinking AI would be fought by its think loop, so we must `dumb` it first.
- `dumb` disables AI -> `anim_scripted coop_medic_kneel` plays the locked
  full-body kneel cleanly (anim_scripted also resists interruption) -> `aion`
  re-enables AI, which stands the medic back up and resumes combat/seeking.
  `aion` is the correct re-enable (NOT another forceactivate).
- **Fixed `wait`s, no `waittill animdone`** (per the safety requirement): the
  clip is ~6.6 s but we heal at 1.6 s (medic kneeling/reaching) and hold the
  pose 1.4 s more, then `aion` cuts back to AI. No waittill means no possible
  hang if the actor is damaged / the anim is interrupted mid-play.
- `lookat`/`turnto <patient>` set facing before the kneel (mirrors the SP medic's
  fixed `angles "0 90 0"` toward the patient); `lookat NULL` clears it after.

---

## 4. Precache

No new cache line required. `dday_ranger_medic.tik` is already cached
(`coop_mod/precache.scr` line 155). Animation `.skc` clips are loaded as part of
the model's anim list via the `$include` chain (not via the `cache` command), so
medic01.skc/medic02.skc are precached when the medic model is cached. The clips
also already ship in base Pak0.

---

## 5. Verification results

Files created/changed:
- CREATED `models/human/animation/scripted/coop_medic.tik`
- EDITED  `models/human/new_generic_human.tik` (one global `$include` added)
- EDITED  `coop_mod/paradrop.scr` (two heal branches)

Byte / brace checks (run on the live tree):
- `coop_mod/paradrop.scr`        : no BOM, pure ASCII, braces { 77 / } 77 BALANCED
- `coop_medic.tik`               : no BOM, pure ASCII, braces { 1 / } 1 BALANCED
- `new_generic_human.tik`        : braces { 169 / } 169 BALANCED.
  NOTE: this file already had a UTF-8 BOM + em-dashes in PRE-EXISTING HZM comment
  lines (17,170,497,...) before this change — that is the shipping state of the
  live tree and was left untouched (out of scope). The line *I* added (33) is
  pure ASCII with a plain hyphen.

Not modified: dbno_ai_revive, combat/follow/voice functions, the medic .tik
model file, build.ps1 (not run — main session reviews + builds).
