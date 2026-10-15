import json, re
p = r'C:\mohaa-coop-dev\.wolf\buglog.json'
raw = open(p, 'rb').read().decode('utf-8')
FIX = {
 'bug-3913': ("FIXED on branch lobbyfix-next (mod worktree hzm-mod-lobbyfix), commit 0621420e + ea9124a7. coop_mod/lobby.scr lobbySpawnMannequin: the idle loop now also requires self != NULL and removes the mannequin when the owner is gone, plus lobbyMannequinReaper (thread on the mannequin) deletes it if no connected player still holds it in flags[coop_lobbyMannequin]. Slots are derived from the live players so they free themselves. Proven in the private harness (H:\\hzm_archive\\lobbyfix\\lf2-lf4): client 2 disconnects, 'LOBBY mannequin reaped (owner left)' logged and the mannequin is gone from client 1's screenshot. Awaits ship (code pak)."),
 'bug-3914': ("FIXED on branch lobbyfix-next, commit 08ab745c. The lobby bar (coop_mod/lobbyui.scr, not a .urc) showed LOADOUT + SERVICE RECORD, but clicking LOADOUT swapped it for an ALLIED / AXIS / COOP / BACK sub-bar (and Service Record vanished). LOADOUT now execs ui/loadout/open.cfg (the co-op armory) directly; the sub-bar and its lo_allied/lo_axis handlers are removed, so the bar stays LOADOUT + SERVICE RECORD. Default bar screenshot with 2 clients: H:\\hzm_archive\\lobbyfix\\lf4\\pc1\\maintt\\screenshots\\a_lobby_two_default.jpg. The click path itself is not exercised in the harness (no cursor driver)."),
 'bug-3915': ("NOT REPRODUCED as a code asymmetry; no behaviour change shipped. Harness lf4 (H:\\hzm_archive\\lobbyfix\\lf4): two clients with identical unlocks both change uniform through the armory name bus (',sn100' / ',sn101'), 'ARMSKIN apply ... mannequin=1' is logged for each and client 2's mannequin changes in the screenshot. Likely cause of the report: armory_skin_set refuses locked skins server-side (SHOW-ALL-WITH-LOCK, user 07-18) and the preview can still park on a locked skin, so a player whose record lacks the skin sees no change while player 1 (the user, everything unlocked) does; per-client records also arrive ~28 s after join. Added a developer-gated 'ARMSKIN apply' println in helmet.scr::armory_skin_applyIdx. Needs the user to say whether the friend saw 'Uniform locked: ...' when it failed; if skins were unlocked for them it is something else (ask for their qconsole)."),
 'bug-3916': ("FIXED on branch lobbyfix-next, commit 128d1656 (+4df3274d test mode). maps/m1l2a.scr coop_sasGateFailsafe (started next to coop_grilloLeadKeeper): while a living player stands within 800u of the live charge site (gate $explosives100 when door==0, then flak $flak88b) and Grillo is >600u away, not in attack and not closing the gap by 60u: after 20 s re-issue his move (coop_forceGrilloToFollow), after 40 s warp him to the friendly node nearest the site that is >=350u from every player and out of line of sight (traced), after 60 s set level.coop_gateNoSas / coop_flakNoSas which blowdoor / blowflak honour (skip the Grillo distance check and the flak combat check) with a hint. Hands off during the finale (flagthread9). Dev cvars, default off: coop_sasfs_fast 1 (3/6/9 s), coop_sasfs_test 1 (ignore flags/proximity), 2 (also no warp node). Proven in harness lf3 (H:\\hzm_archive\\lobbyfix\\lf3): stage 1, stage 2 (warp to node set 695 in lf2 / no node in lf3) and stage 3 all fired, m1l2a loaded with 0 Script Error lines. Not proven: a real stuck-Grillo playthrough (the stuck itself is intermittent)."),
}
for bid, fx in FIX.items():
    i = raw.index('"id": "%s"' % bid)
    j = raw.index('"fix": "', i)
    k = j + len('"fix": ')
    # end of the JSON string value
    e = k + 1
    while True:
        if raw[e] == '\\':
            e += 2
            continue
        if raw[e] == '"':
            break
        e += 1
    raw = raw[:k] + json.dumps(fx) + raw[e + 1:]
    # tags: open -> fixed/verified-note
    seg_end = raw.index('"occurrences"', k)
    seg = raw[k:seg_end]
    seg2 = seg.replace('"open"', '"not-reproduced"' if bid == 'bug-3915' else '"fixed-awaiting-ship"')
    raw = raw[:k] + seg2 + raw[seg_end:]
open(p, 'wb').write(raw.encode('utf-8'))
json.loads(raw)
print('ok')
