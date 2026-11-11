# eapolish - THEIR DYING BREATH (coop_ea_1_11) toward 1:1, 2026-11-10

Everything here is our code. Converted output, the fidelity reference, logs and stills stay under
`H:\hzm_work\eapolish` (never committed, never shipped).

## What changed

| area | before | after |
|---|---|---|
| object DB names (`docs/tools/ea/eadb.py`) | `eaents` read the offset table before the string pool as a string index and snapped to the nearest string: most names and every class wrong | records walked as a chain (header [26]+0x20, count [27]); names, classes and string fields by string-POOL index |
| links | none decoded ("BR_* use another reference scheme") | activation groups (0x29/0x2a/0x2e ids, 0x200xx channels, ids in 0x11-0x1d) + CRC32 message ids (Activate, Deactivate, ObjectiveSucceeded, Play; the counter increment is `ha9d0350f`) |
| mission (`eavm.py` + `maps/coop_ea_1_11.scr`) | hand-made from the objective list, player in the church, all AI at load | the original's graph interpreted: 137 logic objects, 19 gags, 86 spawn points, 80 squad objective points, 40 pickups, 39 props, 3 tanks, 9 MG points, 6 objectives, 27 subtitled lines |
| fidelity reference (`eafidelity.py`) | - | local JSON + MD of the whole graph |
| converter | 0.2.1 | 0.3.0; hzmconv 1.10.73.2 (updater re-converts) |

## Record layout notes (eadb.py / eavm.py)

- Dispatcher: `n listen-groups`, `n targets`, `1 listen-message`, `n sent messages`.
- Counter: `n listen-groups` (counts `ha9d0350f` on the first), `n targets`, `n sent messages`; count = field 19.
- BasicTimer: listen, targets, sent; seconds = field 20.
- Triggers: shape field 15 (1 sphere, radius f16 m; 2 box, f19-f21), lists after the `@Trigger Fired` string:
  targets, enter-messages, exit-messages. GagTrigger: gag name field 26, a list after the marker = listen groups.
- NPCSpawnPoint: archetype 18, character 19 (team), weapon 20, count 48, alive-at-once 55, group 72, death lists from 73.
- SquadObjective_New: group 49; squad = name between `_SquadObjective_` and the number.
- TreadedVehicle: member group 32, death targets + message from field 30.
- PlaySound actions: field 20 = CRC32 of the strings.viv cue key (the subtitle).

## Audits

See the agent report for numbers; commands:

```
python docs/tools/ea/eafidelity.py <level_a.str> H:\hzm_work\eapolish\fidelity
python <byoaudit>/geoaudit.py <local pk3> coop_ea_1_11 <outdir> --png
python docs/tools/ea/ea_aiaudit.py <outdir> mission|faceoff      # byoaudit aiaudit + user-clip filter, BYO_CLIENT G:\mohaa-ea
```

`ea_aiaudit.py` ignores only cursor clips whose rectangle lies outside the test display (the user's own game clipping
its cursor on the ultrawide while it has the foreground); any clip on our display still stops the run.

## Open

- Smart-object meshes (railgun, radio tower, ammo dump, bridge, gates, tombstones, crates) are not converted: stock
  stand-ins or nothing. The bridge and gates matter for the route; their collision is in the level `.cdb`.
- 1,966 blocked moves with nothing drawn near (geoaudit): only 151 near smart objects; look on screen first.
- Voices: the cue -> speech-file hash is still unknown (study); subtitles play.
- Music triggers (10) not mapped to the score's segments.
- Effects packages (fires, smoke, fog, birds) not placed; tank paths not driven; end static camera not played.
