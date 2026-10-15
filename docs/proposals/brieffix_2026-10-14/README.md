# bug-3917 - briefing flicker for remote clients (2026-10-14)

**Cause** (`coop_mod/menumirror.scr::coop_mirrorSlideSend`): every 4th 0.5 s sync tick (2 s) a "forced" pass re-sent
`ui_addhud <current slide>` to each remote player even when unchanged. Engine `UI_AddHud_f` (cl_ui.cpp) calls
`hud->ShowMenu()` on every add, which restarts the full-screen card -> a black blink every 2 s, wider at 200 ms ping.
Slide changes also removed the old card before adding the new one (black gap).

**Fix** (mod worktree `hzm-mod-brieffix`, branch `brieffix-next`, commit 6e53cbd6): add the NEW slide first, then remove
the old; an unchanged slide is never re-sent; the forced pass only repeats `ui_removehud` of the previous slide (no-op when
already down). Host/listen behaviour unchanged. Ship: code pak only (no engine change).

**Proof** (`run_brieffix.py`, run `bf_fix4`, archive `H:\hzm_archive\brieffix\bf_fix4`): dedicated server + one remote
client on 127.0.0.1 with 100 ms packet delay each way (server-logged ping 228-240 ms), rcon map briefing/briefing1, player
joined and spawned. Server log: slides 1a, 1b, 1c, 1c2 each sent once; 0 Script Errors. Six screenshots across the 15 s
briefing1c slide (`pc1/maintt/screenshots/brief_c_0..5.jpg`) show the card up each time, no black frames (checked c_2, c_4).
Limit: the server log prints only slide changes, so "no re-add" is proven by code order, not by a client command count.
Earlier runs bf_fix1-3 failed only because the harness player never spawned (join sequence); no mod issue.
