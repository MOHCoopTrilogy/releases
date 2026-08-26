# T7 cvar/exec-order summary table
*(moved out of docs/TRAPS.md 2026-08-26 for budget; the prose rules it summarises stay in T7.)*

| Trap | Tell | Bug |
|---|---|---|
| **Exec order** — engine execs `default.cfg` → saved config → `autoexec.cfg` **LAST**; `autoexec` `seta`-ing ~200 curated defaults overwrote every menu change on every launch. | Menu changes don't stick | 710 |
| **A renderer cvar's FLAGS are as sticky as its value**, and four bugs are one lesson: `Cvar_Get` ORs flags (`r_lodscale` twice-registered in gl2 became `CVAR_CHEAT`, slider reverted, 1125); a flag flipped for one A/B test archived it (`r_entlight_scale` dimmed every entity, 918); a `CVAR_ARCHIVE` rcon probe is retained forever (`r_toneMap 0`, 1148); and `CVAR_CHEAT` probes are useless on a listen server since `sv_cheats 0` clamps them back — use `CVAR_TEMP` (`r_globalFogDebug` **is still `CVAR_TEMP` at `renderergl2/tr_init.c:1926` — restore it**). | Slider reverts, or a test becomes a global regression | 918, 1125, 1148 |
| **Fail-open locks** — the armory padlock recompute zeroed all lock cvars then relied on a server push that might never arrive. Redesigned fail-**LOCKED**. | Content unlocked that shouldn't be | 682 |
| **Clamped cvars lie to menus** — gl2 clamps `r_ext_multisample` to 4, so the 8× MSAA plate was repointed at the unclamped `r_ext_framebuffer_multisample`. | Menu offers a value the renderer refuses | 1152 |
| **Never `seta` a genuine user preference** in `autoexec.cfg` (`cg_adsShoulderRight`). | Preference resets each launch | 258 |
| **Never seed `coop_uiB*`/`coop_uiN*`** — wipes last-known challenge progress. | Progress lost | — |
| **`g_gametype` is LATCHED - the FIRST map of a launch runs before it applies.** `ui_startdmmap` sets it and starts the map in the same frame, so map 1 boots under the OLD value: coop gates read 0 and never arm. Put `+set g_gametype 2` on the command line for any automated/dedicated run. |
