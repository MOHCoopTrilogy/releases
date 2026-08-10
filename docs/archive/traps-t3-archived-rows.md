# Archived T3 rows (silent-veto instances)

Moved out of `docs/TRAPS.md` 2026-08-10 to stay under the 60 KB ceiling. Kept as evidence only —
each row's failure *shape* is still taught in TRAPS (T1 for the parse-error case, the T4 note for
the not-yet-populated-data case). Full detail lives in `.wolf/buglog.json` under the cited ids.

| Feature | Why it never ran | Bug |
|---|---|---|
| **gl2 grade + zone pre-clear** | (a) `FBO_Blit` passes `UNIFORM_COLOR` (`u_Color`) but the shader declared `u_Grade` — location -1, every set silently dropped. (b) A **function-scope `static`** guard reset on every `vid_restart` (which reloads the renderer DLL), so `ri.Hunk_Clear()` never ran and bug-1128's fix had never once executed (+53 MB per apply). | 1146, 1148 |
| **AI maneuver mover** | A silent T1 parse error (inline vector literals + `enableEnemy`-as-command) meant every earlier "enemies don't move" measurement was reading a **dead script**. | 1069 |
| **`coop_weather_init`** | Threaded from inside `main.scr::main`, but maps set `level.coop_weatherTheme` on the *next* line — so the theme always read NIL. Fixed by waiting for prespawn. | dynamic_weather |
