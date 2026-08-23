# Destroyed-Radio Model Search (MOHAA trilogy paks)

Goal: find a model to spawn at the radio objective position after the player blows up
`models/miscobj/radio_military.tik` with a planted charge. Searched AA (`main`), SH
(`mainta`), BT (`maintt`) paks. Mod runs `fs_game=maintt`, so on AA maps the engine
loads `main` + `maintt` (NOT `mainta`/SH). Note that for the destroyed swap.

All radio meshes use `scale 0.52`. The intact `radio_military` is a small German field
radio with a QUAKED bbox of `(-16 -16 0)(8 16 24)` (~24x32 wide x ~24 tall units).

---

## Table 1 — Every radio model in the trilogy

| Path | Theater / pak | skelmodel | scale | QUAKED desc | type |
|---|---|---|---|---|---|
| models/miscobj/radio_military.tik | AA Pak0; SH pak1; BT pak1 | radio/german_radio.skd | 0.52 | `equipment_radio-military` bbox (-16 -16 0)(8 16 24) | INTACT handheld/field radio (the objective model) |
| models/miscobj/radio_military_pulsing.tik | AA Pak0 | radio/german_radio.skd | 0.52 | (none) classname animate | same mesh, pulsing shader |
| models/miscobj/radio_military_pulse.tik | BT pak1 | radio/german_radio.skd | 0.52 | `radio-military-pulse` | same mesh, pulsing, scriptmodel |
| models/animate/military_radio.tik | AA Pak0 | radio/german_radio.skd | 0.52 | non-pulsing animate version for objective | same mesh, animate |
| models/animate/pulse_military_radio.tik | AA Pak0 | radio/german_radio.skd | 0.52 | pulsating, for objective radios | same mesh, animate |
| models/miscobj/radio_civilian.tik | AA Pak0; SH/BT pak1 (mesh) | radio/radio_civilian.skd | 0.52 | `decor_radio-civilian` (-16 -16 0)(16 16 32) | INTACT civilian desktop radio |
| models/static/static_radio2.tik | AA Pak0 | submodels/radio2.skd | 0.52 | `static_uboat_radio2` (no bbox) | INTACT U-boat radio submodel |
| models/static/static_radiostation1.tik | AA Pak0 | submodels/radiostation1.skd | 0.52 | `static_uboat_radiostation1` | INTACT large U-boat radio console |
| models/static/static_radiostation2.tik | AA Pak0 | submodels/radiostation2.skd | 0.52 | `static_uboat_radiostation2` | INTACT console (station) |
| models/static/static_radiostation3.tik | AA Pak0 | submodels/radiostation3.skd | 0.52 | `static_uboat_radiostation3` | INTACT console (station) |
| models/static/static_radiostation4.tik | AA Pak0 | submodels/radiostation4.skd | 0.52 | `static_uboat_radiostation4` | INTACT console (station) |
| models/static/static_subradio1.tik | AA Pak0 | submodels/subradio1.skd | 0.52 | `static_uboat_subradio1` (-16 -16 0)(24 24 40) | INTACT sub radio unit (mid size) |
| models/animate/Sc_P_RadioTower.tik | BT pak1 | RadioTower/...skd | 0.52 | `RadioTower` bbox (-65 -40 0)(65 40 120) | INTACT large antenna TOWER (huge) |
| models/animate/Sc_P_RadioTowerFallen.tik | BT pak1 | RadioTower_Fallen/...skd | 0.52 | `RadioTowerFallen` (-65 -40 0)(65 40 120) | DESTROYED/collapsed TOWER (huge) |
| models/animate/Sc_P_RadioTowerLeg.tik | BT pak1 | RadioTowerLeg/...skd | 0.52 | (busted leg, has `fall` anim) | tower leg, animated topple (huge) |
| models/animate/Sc_P_RadioTowere3l4.tik | BT pak1 | (variant) | 0.52 | e3l4 tower variant | INTACT tower (huge) |

Human "radioman/radio paratrooper" TIKIs (dday_29th_private_radio, allied_uk_radio_paratrooper,
Sc_Al_US_radio, etc.) are soldiers carrying a backpack radio — not props — excluded.

---

## Table 2 — Broken / destroyed RADIO states or variants

**No dedicated broken/destroyed handheld or tabletop radio exists anywhere in the trilogy.**

Checked:
- Every radio TIKI's `animations` block: all define ONLY `idle`. None have a
  `broken`/`destroyed`/`dmg`/`death` animation. (The one exception is the giant
  `Sc_P_RadioTowerLeg` which has a `fall` topple anim — a tower, not a radio.)
- Surface lists: no swappable `*_destroyed`/`*_dmg` surface or skin on any radio.
- No sibling `radio_*_broke/_destroyed/_dmg` file in any pak (`models/miscobj/radio/`
  contains only `german_radio.skd` + `radio_civilian.skd`, both intact).

The ONLY "destroyed radio" asset in the trilogy is **`Sc_P_RadioTowerFallen.tik`** (BT/maintt)
— but it is a collapsed steel antenna mast (bbox 130 x 80 x 120 units), wildly oversized for a
tabletop field radio. Not usable as an in-place swap for `radio_military`.

---

## Table 3 — Best general broken/destroyed-prop & debris stand-ins

| Path | Theater / pak | Depicts | Approx size | Fit for wrecked radio |
|---|---|---|---|---|
| models/fx/destruction/chunkcrete/chunkcrete.tik (models/fx/chunkcrete.tik) | AA Pak0 (loads under maintt) | broken concrete/debris chunk, real persistent mesh, `classname Object` | scale 1.0, bbox (-16 -16 0)(8 16 56) | A single solid debris chunk the right footprint; reads as blasted material. Generic (concrete), not electronics. |
| models/fx/crates/crate-jib-chunk.tik | AA Pak0 | splintered wooden crate chunk, single static mesh | scale 0.52, small | Small jagged wreckage piece; good scale, but obviously wood. |
| models/fx/crates/crate-jib-smallchunk.tik | AA Pak0 | smaller crate splinter chunk | scale 0.52, smaller | Even smaller debris piece. |
| models/static/rubble_smallpile.tik | AA Pak0 | brick/board rubble pile | scale 0.52, bbox (-32 -32 0)(32 32 128) | A small rubble heap; footprint a bit wide and tall (~128 units) but reads clearly as "blown up". Persistent static. |
| models/static/librarytabledestroyed.tik | AA Pak0 | "destroyed" library table | same mesh as intact table, damaged skin only | Same SHAPE as intact table (skin-only damage) — does NOT look smashed. Poor. |
| models/static/loveseatdestroyed.tik | AA Pak0 | "destroyed" loveseat | same intact mesh, damaged skin | Same shape, skin only. Poor. |
| models/fx/barrel_empty_destroyed.tik / barrel_gas_destroyed.tik | AA Pak0 | barrel explosion | FX EMITTER ONLY (dummy model + flying debris particles, no persistent mesh) | Good as the moment-of-explosion burst, but leaves nothing behind. Pair with a static. |
| models/fx/crates/debris_0.tik | AA Pak0 | crate-shatter burst | FX EMITTER ONLY (spawns flying crate jibs) | Same — transient effect, no residual prop. |
| models/static/generator.tik | SH mainta only | industrial generator | huge (264 wide) — and SH-only, won't load under maintt | Not usable (size + theater). |

---

## Recommendation — what to spawn at the radio position post-explosion

Because no broken-radio model exists, the realistic options are: (A) keep the
tipped-over intact `radio_military` you already use, or (B) replace it with a small
debris/chunk static and play a one-shot explosion FX emitter at the moment of detonation.

Ranked (all must be in `main` or `maintt` since the mod is `fs_game=maintt`):

1. **Keep the tipped-over intact `models/miscobj/radio_military.tik` + smoke** — and add a
   one-shot `models/fx/crates/debris_0.tik` (or `models/fx/barrel_empty_destroyed.tik`) burst
   at the instant of detonation for the "blown up" read. This is the most convincing result
   because there is genuinely no smashed-radio mesh; the flying-debris FX sells the destruction,
   and the tipped intact radio remains recognizable as "the radio you destroyed."
2. **Swap to `models/fx/destruction/chunkcrete/chunkcrete.tik`** at the radio origin (its TIKI
   path string is `models/fx/chunkcrete.tik`, `classname Object`, persistent mesh). It's a
   solid blasted chunk at roughly the right footprint and leaves permanent wreckage. Generic
   material, but unmistakably "destroyed."
3. **Swap to `models/fx/crates/crate-jib-chunk.tik`** (small splintered chunk, scale 0.52) for a
   smaller, less concrete-looking debris piece if chunkcrete reads too large/grey.

Avoid: `Sc_P_RadioTowerFallen` (giant tower, wrong object entirely), the `*destroyed`/`*damaged`
furniture (skin-only, same shape — won't look broken), and SH-only `generator` (won't load).
