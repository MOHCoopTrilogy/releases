# Archived P0 block, cleared 2026-08-15

Verified and cleared on 2026-08-15 — see docs/OPEN.md for the surviving item and the method.
Kept verbatim because the protocol-coupling REASONING is still correct guidance even though the
conditions it described are resolved.

## P0 — infrastructure, fix before feature work

### The deployed engine binaries do not match each other
`OPEN` · *Re-measured 2026-08-12 from GOG-root mtimes. The 2026-07-29 table here was stale in every
row and its central claim was wrong — see the deploy-gap note below.*

Still a **5-day spread**, so the protocol-coupling risk stands: `renderer_opengl2.dll` 08-07,
`cgame.dll` 08-08, `openmohaa.exe` / `omohaaded.exe` / `renderer_opengl1.dll` 08-10, `game.dll` 08-12.
`gameState_t` is sized by `MAX_CONFIGSTRINGS` and `memcpy`'d **whole** across the exe↔cgame boundary
with no version guard; `GENTITYNUM_BITS` also changes entity wire encoding. Ship the set, not one file.

**The deploy gap is now much smaller than this entry used to claim.** `build.ps1` *does* deploy
`cgame.dll`, `game.dll` (+`game.pdb`) and `omohaaded.exe`, to the GOG root **and** `G:\mohaa-gl2`
(`build.ps1:149-161`). Only **`openmohaa.exe` and `renderer_opengl2.dll` are still hand-copied** —
so the old "no exe deploy block / copy game.dll by hand" fix text no longer applies.

Corroborated independently: **bug-1219 still reports `SV_FindIndex overflow (max=1280)` ×243** from a
live m3l2 log while `q_shared.h:1742` says 1600 — re-run it once the client exe is refreshed.

**Caveat:** mtime proves when a file was written, not what it was compiled from. Confirm, don't assume.
And since `.cmake`, `G:\mohaa-gl2` and the GOG root can each hold a different build of the same
module, **no "verified" claim means anything unless it names the install AND the timestamp.**

### Six days of engine work and v1.1.55 mod content exist only in the working tree
`OPEN` · *Anchor: engine HEAD `819a6e93` + 119 dirty files / ~10,750 insertions / 20 untracked; mod HEAD `f10ac19` + 65 dirty files*

Uncommitted engine work includes the headshot gore chain, the entity-1023 aliasing fix,
`MAX_SOUNDS 1600`, `MAX_RELIABLE_COMMANDS 1024`, `MAX_CONFIGSTRINGS 8192`, the 13-bit `frameInfo`
widening, **all** gl2 work, the font pipeline and `coop_unsponge`. Untracked (not in git at all):
`tr_gore.c` in both renderers and 17 GLSL post-FX shaders.

**There is no restore point for any of it.** Same hazard class as a doc/code disagreement: the record
(git) does not describe the artefact (the tree).

### `renderer_opengl2.dll` has zero rollback points
`OPEN` · *Anchor: 157 `.bak` files in the GOG root — `game.dll` 75, `openmohaa.exe` 37, `cgame.dll` 25, `renderer_opengl1.dll` 19, `renderer_opengl2.dll` **0***

The `<binary>_pre_<feature>_bak.<ext>` convention **is** the project's binary rollback system, and it
is entirely by hand. The most-churned module (29 uncommitted files, +5,794 lines) has no backup.

### A v1.1.51-era gl2 DLL ships to players
`OPEN` · *Anchor: `manifests/latest.json` ships `renderer_opengl2.dll` sourced from v1.1.51; session rules say "gl2 NEVER ships"*

Both statements are true and the combination is a trap. The rule means in-progress gl2 work must not
reach the player-facing engine directory; it does **not** mean players have no gl2 DLL. Any player who
sets `cl_renderer opengl2` gets a build predating bugs 1144/1145/1146/1147/1148/1189/1209/1210/1211 —
including the **settings-apply crash** (1145) and the **`r_ppSSAO 1` black screen** (1211) — and
`coop_defaults.cfg` ships `r_ppSSAO 1`.

**Decide explicitly:** stop shipping the gl2 DLL until the port is done, or ship a current one.

### Shipped binaries lag source; exe/cgame frozen at v1.1.51
`OPEN` · *Anchor: `manifests/latest.json` v1.1.55 — `openmohaa.exe`→v1.1.51, `cgame.dll`→v1.1.51, `game.dll`→v1.1.55, `renderer_opengl1.dll`→v1.1.50, `renderer_opengl2.dll`→v1.1.51*

Everything landed after 2026-07-21 is source-only for players: `MAX_SOUNDS 1600`,
`MAX_RELIABLE_COMMANDS 1024`, `MAX_SKELMORPH 131072`, the `SOUND_INDEX_BITS` `#error` guard,
bug-1189 portal/`RF_SHADOW_PLANE`, bug-1196 sort-key fog, bug-1206 sandstorm lens, bug-1208/1217
helmet 3P + 5 latent cgame defects, bug-1209/1210/1211 gl2 work.

⚠️ Note `game.dll` advanced **alone** to 1.1.55 while the exe stayed at 1.1.51 — safe only because the
protocol constants had not yet moved at that point. **That pattern is exactly how a silent protocol
mismatch ships.**

---

