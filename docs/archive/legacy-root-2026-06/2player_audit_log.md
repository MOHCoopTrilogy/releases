# 2-Player Live Coop Audit Log
**Date:** 2026-06-25  
**Session:** Full campaign rotation, 2 players (P1=listen server, P2=client on 127.0.0.1:12204→12203)  
**Goal:** Identify all issues affecting 2-player coop playability across all 53 maps  
**Fix policy:** Log only — no fixes executed without user approval

---

## Issue Categories
- **CRASH** — game crashed, map failed to load
- **AUDIO** — missing sounds, channel problems, wrong audio
- **SCRIPT** — script errors, logic bugs visible in console
- **VISUAL** — rendering problems, missing geometry, wrong textures
- **P2-SPECIFIC** — issues that only manifest with a second client connected
- **LOCALIZATION** — missing localization strings
- **SPAWN** — player spawn problems, death/respawn issues
- **AI** — AI behavior broken in 2-player context

---

## Map Progress

| # | Map | Status | Issues |
|---|-----|--------|--------|
| 01 | m1l1 | ✅ Loaded, both players confirmed in-game | AI weapon slot errors; `'was shot in the'` localization missing |
| 02 | m1l2a | ✅ Both players live-spawned (M1 Garand, night Normandy streets confirmed) | `SV_FindIndex overflow`; `Box data corrupted: allied_pilot.tik`; `ter_restart Already defined`; P2 reconnect after map transition required clicker |
| 03 | m1l2b | — pending — | — |
| 04 | m1l3a | — pending — | — |

---

## Confirmed Working
- Music mood system: normal → success → failure transitions confirmed live (m1l1)
- P2 spawn/respawn: working (requires clicker)
- Map rotation: m1l1 → m1l2a transition clean
- P2 connection: 127.0.0.1:12203, ping 15ms, stable

---

## Issues Log

### [m1l1] SCRIPT — "No active weapon in slot #: 0"
**Severity:** Low  
**Description:** Repeated console spam. AI actors being queried for weapon in slot 0 when none equipped. Likely coop_mod spawning AI without fully initializing weapon loadout before the weapon-query runs.  
**P2-specific?** Unknown — may occur in single-player too  

### [m1l1] LOCALIZATION — "'was shot in the' does not have a localization entry"
**Severity:** Low  
**Description:** Kill feed message for P2 death shows localization error. The "X was shot in the [bodypart]" death string is missing from the localization table.  
**P2-specific?** Yes — only appears when a second player dies  

### [ALL MAPS] LOCALIZATION — Console version string missing localization entry
**Severity:** Low  
**Description:** Every time the in-game console is opened, prints: `LOCALIZATION ERROR: 'OpenMoHAA console version 0.82.1' does not have a localization entry`. Engine issue — version string not in localization table. Cosmetic only.

### [m1l2b/m1l3a] SPAWN — P2 disconnects on every server map transition
**Severity:** High (blocks 2-player testing)  
**Description:** When `stuffsrv "map <next>"` fires, the server drops all clients. P2 shows "Server Connection Timed Out" and must reconnect manually. Root cause: MOHAA client-server protocol disconnects all players on `SV_SpawnServer` which runs on each `map` command. The auto-reconnect spawn clicker (spawn_clicker_2player.ps1) handles this automatically going forward.  
**P2-specific?** Yes — affects any non-host clients. P1 (listen server host) is unaffected.

### [m1l3a] VISUAL/ASSET — rubble_bigpile.skb not found
**Severity:** Low (visual degradation only)  
**Description:** `shader CacheInhimchel: could not open binary file models/static/rubble_bigpile.skb` + `TIK_IntFlk: Failed to load animation... no valid animations found`. Rubble pile uses a binary-format SKB that isn't in the pak. Fallback rendering likely occurs.

### [m1l3a] VISUAL/ASSET — jeep.tik missing surface 'swp2'
**Severity:** Low  
**Description:** `TIKI_AnimFile: could not load surface 'swp2' in 'models/vehicles/jeep.tik'`. Surface reference is missing from the jeep model. Cosmetic — jeep still renders.

### [m1l3a] VISUAL/ASSET — allied_british_tank.tik animation param refs missing
**Severity:** Low  
**Description:** `TIKI_PrefTrk: could not find source 'Sc_AI_brit_tkt' / 'Sc_Al_Stf_Inf'` in `models/player/allied_british_tank.tik`. Missing animation parameter references.

### [m1l3a] AUDIO — gameplus channel Bpl_1.5 / Bpl_1.1 not registered
**Severity:** Low  
**Description:** `Channel named Bpl_1.5: Cannot use the gameplus not added. (Done will not work without it)` × 2. These are additional audio channels for special effects that aren't registered in the current game mode setup.

---

## Raw Console Notes (running)

```
[m1l1] Player2 has joined the Allies
[m1l1] Game Message: Will switch to new weapon next time you respawn (×2)
[m1l1] Game Message: Picked Up Frag Grenade
[m1l1] Game Message: Picked Up Colt .45
[m1l1] Game Message: Picked Up M1 Garand
[m1l1] Game Message: Picked Up MP40
[m1l1] MUSIC: normal|normal → success|normal (objective complete)
[m1l1] LOCALIZATION ERROR: 'was shot in the' does not have a localization entry
[m1l1] Player2 was shot in the [incomplete string]
[m1l1] MUSIC: success|normal → failure|normal (player death)
[m1l2a] status: map m1l2a, P1 loopback, P2 127.0.0.1:12203 ping 15
[m1l2a] No active weapon in slot #: 0 (repeated)
[m1l2a] S_LoadSound ENTER den_attack_*.wav (many — normal AI combat audio loading)
```
