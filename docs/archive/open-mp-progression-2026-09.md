# Archived from OPEN.md 2026-11-17 (shipped v1.7.0; playtest tail)

## MP Progression + Service Record — SHIPPED v1.7.0 (2026-09-14); playtest tail only (details: buglog, FEATURES)

Engine + script bot-verified; client-rendered parts need a real machine. The armory/appearance/service-record
detail and the preview helmet-double (Allied `_nohat` twins exist, Axis don't; live spawn correct via nodraw) are
carried by the **2026-09-20 session block below**. The MP framework engages on ALL dm maps (stock `mohdm1-6`) +
`obj/mp_*` (bug-2638); Push/Base-Assault keep their own Campaign-Maps pickers for the SP maps.

### MP session (2026-09-20) — progression persistence FIXED, rank card SHIPPED, menu-parity roadmap
- **PROGRESSION PERSISTENCE — the real cause FIXED 2026-11-10 (bug-10912, branch `mpprog`, not released).** bug-2749
  (CL_Init USERINFO registration) was one of THREE gates; the other two kept every MP record at zero: the blob stufftext
  was QUOTED (client set it empty, T8) and `;`-delimited (userinfo refuses `;`). Now `,` on the wire, unquoted. Rank tiers
  now load at join, not at the first kill (bug-10913). Proven bot-driven on a dedicated + private client + server restart
  (`docs/proposals/mpprog_2026-11-10/`); **still needs one real playtest** (kill, quit, rejoin: `MPPROG load VERIFIED`).
  **Open:** `win_buildabase` has no writer (basebuild has no win point) - Architect challenge unreachable, its skin
  stays earnable by kills; `mp_unlock_audit.py` lists it as a known WARN.
  **Open:** the Armory FINISH padlocks read the old global `coop_mpUfin_*` cvars, but finishes now open per gun
  (`mp_finish_map.scr::mpfin_open`) - the padlock can disagree with the server. Weapon-tile padlocks fixed (bug-10926).
- **MP END-OF-ROUND RANK CARD — SHIPPED + code-path verified (bug-2751).** `xp.scr::xp_mp_roundcard` draws a debrief
  in the pre-next-round pause (emblem, +XP, bar, PROMOTED; HUD 160-167), wired into `push_win`+`rounds_win`. The
  rank-up **bar + ceremony already fired in MP** via `xp_award_mp`; this card was the missing visual. **VERIFY** the
  emblem/bar render on a real client (devboot confirmed `MPROUNDCARD shown`).
- **MENU PARITY (user 2026-09-20: "MP menus as good as coop"). DONE this session (detail in buglog):** armory default
  label fixed off Panzerschreck (2752); WEAPON FINISH moved Appearance→Armory (2753); cosmetic LOCK display (padlock +
  "Unlocks at N kills") added (2755); SR graphical PROGRESS BARS added, reusing coop's `coop_bf*` art (2756);
  **preview helmet-DOUBLE FIXED** (2754 — vstr-free body-swap: viewer body = `_nohat` twin + the skin's baked hat as an
  attached Standard-Issue piece, `SKIN_STD`); **skin DEPTH** allied 12→24, axis 12→18 (2757, each with a twin + std
  piece; auto-fit menu layout). **All of these render only on a real client — the bars, the preview de-double, and the
  new skins' fit need your eyes.** **STILL OPEN (need art / an engine command / curation):**
  - **Preview fit verification.** The 30 skins' twin+piece pairings should look right (allied reuse coop's fit-tested
    pairs; axis map to matching German/Italian pieces) — but confirm on a client; report any helmet that sits wrong.
  - **Deeper skin depth** toward coop's 135: more allied is pure `skinGet` rows (twins+std already exist); more axis
    needs a `_nohat` twin generated per skin (`gen_axis_nohat.py`, ~1 line each once its headgear is classified).
  - **SR pins/favorites + MEDALS view.** Pins need a client command like coop's `coop_pintoggle` (`CL_PinToggle_f`);
    medals + page background art are **new art assets** I can't author. Coop ref: `ui/coop_sr.urc`.

