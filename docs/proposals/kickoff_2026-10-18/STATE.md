# STATE - overwrite at every handoff, never append, under 60 lines

**Written:** 2026-10-14 (late), by the coordinator that stopped at the weekly cap.
**Usage then:** weekly 98 %, extra usage off. Reset 2026-10-18 06:00 local.

## Live
- **v1.10.24 HOTFIX published 2026-10-14 15:40**: remote join flood fixed (bug-3910 / 3909 / 3905): client exe sends every fragment, server caps reliable bytes in flight per remote client (sv_cmdParkBytes 2400), lobby.scr flood fix. Engine rel-1.10.24 f551686f (= 277bdb9d + 15732bb2; exe d33febc3, ded aa883b7c, built in openmohaa-hzm-rel/.cmake like the release) pushed as release-1.10.24 (origin + org); mod coop-wip 098f93eb pushed. game/cgame = v1.10.23, renderers = v1.10.22. Public servers run it; their loose lobby.scr was moved to public_servers/_superseded_lobby_patch/. Handover: docs/proposals/joinflood_2026-10-14/README.md.
- **v1.10.23 HOTFIX published 2026-10-14**: progression follows the player to any server (bug-3903). Only game.dll 126a66e3 + cgame.dll d84e0679 + the code pak changed; exe / ded / renderers = v1.10.22. Engine source pushed as release-1.10.23 (origin + org) = progsync-next e8838a89; mod coop-wip 7a5211a0 pushed to org. The .cmake folder now holds these two dlls (the v1.10.22 ones are in SCRATCH/pre_1.10.23_cmake).
- Public release v1.10.22 "Eyes on Target" (GitHub MOHCoopTrilogy/releases, verified). The user's
  install matches it. Mod `coop-wip` = `org/coop-wip` = 4f8a1019.
- Engine source for v1.10.22 is on GitHub: joncurry94-tech/openmohaa `release-1.10.22` = 0206e3c9
  (pushed 2026-10-14). The lane branches are still PC-only; a backup push needs the user's yes.
- Release binaries: `SCRATCH\built_integ10` (exe 5cd827eb, cgame b4b5c4e2, game 6b515fbf,
  gl2 8296bf86). Engine branches `integ-1.10.22` 277bdb9d and `integ-ads` 0206e3c9. Engine not pushed.

## Next
- Stage 0 (the "first ten minutes" in KICKOFF.md), then Stage 1 (Stage 0b, progression sync, SHIPPED in v1.10.23).
- Because this file is dated 2026-10-14, the resume memory file IS still needed this once: read its
  2026-10-13 and 2026-10-14 entries only.

## Possibly changed since (check, do not assume)
- A local session "Continue coop mod work from saved notes" was started 2026-10-14 on the same
  queue (give-all key, sandstorm, reinforcements). It had about 1 % of the weekly allowance.
- A cloud session may have run from `docs/proposals/officer_reinforcements_2026-10-14/CLOUD_BRIEF.md`
  and left a side branch on the mod's org remote (script drafts, untested).

## Lanes (one line each)
- Give-all key bug: not started, not in the buglog.
- SAS mission sandstorm + hint: not started.
- Aim audit (Stage 2b, all 162 weapons): ON HOLD by the user (2026-10-14) - do not run.
- Officer and reinforcements: design approved, nothing built. README in
  `docs/proposals/officer_reinforcements_2026-10-14/`.
- Rifles: `ads-rifle-next` c7ce5e86; reloads built for Kar98, Mosin, Enfield, Springfield, Garand,
  not released; path fix and M1 Carbine next.
- SMGs: `ads-smg-next` 9ae4d1b0; MP18 + Sten built (await the user's eyes); Thompson family partly
  built, M1928 failing.
- Heavy: `ads-heavy-next` 1af86b8f; FG 42 pair + FG 42 Irons built (integrate up to aa84c42d only);
  M1919 sights done, reloads not.
- Pistols: `ads-next` f8d0f895 (M10 fix unverified); old C96 ship2 superseded.
- C96 replacement: model downloaded and inspected, not built.
- Repaints: silencer shipped; grease gun partly checked; shotgun receiver top and the wood set not
  started.
- Small-maps ideas, main menu, performance moves 2-5: not started.

## Waiting on the user
- bug-3915: only player 1 can change uniform in the co-op lobby. Batch with bug-3913/3914; ask before changing.
- bug-3914: co-op lobby bottom bar shows the PvP Allied/Axis armories; should be Loadout + Service Record only. Batch with bug-3913; ask before changing.
- bug-3913: a departed player's lobby mannequin stays in co_lobby1 (cause in the buglog entry). User: do NOT change it yet - ask before fixing.
- The decision sheet in KICKOFF.md section 5 (defaults apply if they say "all defaults").
- Their eyes on v1.10.22: scope view, downpour density, What's New card layout.

## Public servers (started 2026-10-14 at the user's request)
- Two v1.10.22 coop dedicated servers (names "MOH Coop Trilogy #1/#2 - discord.gg/cVjMYPBFZ", ports 12203 / 12204, 4 players) play the FULL TRILOGY: coop_campaign 1 from co_lobby1; server-only loose copies of the three finales in `public_serverssrvNmainttmaps` (made by `public_serverssetup_trilogy.py` from the released paks) hand AA -> SH -> BT -> AA. The finale hand-offs are untested (need a full campaign end). Listed on the public browser (333networks master, game "mohaab"); browser query ports 12205 / 12206 sit inside the firewall rule the user made for UDP 12203-12214 (12300+ is blocked). Start with `public_serversstart_servers.ps1`; the runner restarts on exit; stop with `public_serversstop_servers.ps1`. Re-run setup_trilogy.py after any release that changes m6l3e, t3l2 or e3l4/Outro.
- They BLOCK deploys (deploy_window.ps1 aborts while omohaaded runs from G:\GOG): stop them first, restart after a release.
- bug-3909/3910 shipped in v1.10.24. The public servers keep sv_lagProbe 1 for a few days: watch SVCMDQ / SVFRAME lines in public_servers/srvN/maintt/qconsole.log.

## v1.10.25 HOTFIX SHIPPED 2026-10-14 ~17:30: join lag fixed (bug-3911 client reads network every frame, bug-3912 4 MB sockets); engine rel-1.10.25-netfix dfc7079f pushed as release-1.10.25 (exe aa8304ff, ded 0de5f7ca). Notes below are the history of the hunt.
- v1.10.24 still lags for real clients. Repro: user cfg at com_maxfps 200 never enters (H:\hzm_archive\joinflood\r1_rel_user200, r2); at 60 fps it joins but backlog ~926, as low as 7 snapshots/s (r3); pristine cfg at 200 is fine (r4).
- The agent (handover docs/proposals/joinflood_2026-10-14/README.md, engine worktree openmohaa-hzm-joinflood) was cut off while starting: "Add a socket-buffer helper and call it for both sockets" (raise the UDP send/receive buffers - Windows defaults are small and drop bursts of 1300-byte fragments at high frame rates). Unverified lead.
- User requirement: anyone must be able to join at ANY settings (no settings workaround). Proof after the fix = 6 runs: user cfg@200, worst case (fps 0/333, maxpackets 125, packetdup max, rate 90000, snaps 40), lightest (60, 30, 0, 25000, 20), pristine@200, two clients, listen host. Ship as a hotfix (user approved), rebuild exes in openmohaa-hzm-rel (DLOPEN on), then restart the public servers.
