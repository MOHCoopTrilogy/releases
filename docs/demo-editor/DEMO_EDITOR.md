# Demo Editor - Field Manual

Play back any recorded demo, step out of the soldier's eyes, fly a free camera around the fight,
lay down smooth camera paths, hide the HUD and put a film look over the picture. It is all built
into the game: nothing to install, nothing external. Run it from the numeric keypad or the console.

![Free camera on a recorded soldier](media/freecam-body.jpg)

## Quick start

1. **Record while you play.** Press **F9** to start and stop, or type `record mynight` in the
   console (`~` or `§`) and `stoprecord` when you are done.
2. **Play it back** with `demo mynight`. The editor is on for every demo, old ones included.
3. **Press KP 0** to leave the soldier's eyes. Fly with **W A S D** and the mouse; **Space** goes
   up, **Ctrl** goes down.
4. **Press Del** to pause, **KP 4 / KP 6** to jump 5 seconds back or forward. At the end, the demo
   holds on its last frame instead of quitting.

## The keypad

| Key | Does |
|---|---|
| KP 0 | Free camera on / off |
| KP 4 / KP 6 | Back / forward 5 seconds |
| KP 5 | Step one snapshot (pauses) |
| Del or KP . | Pause / resume |
| KP 1 / 2 / 3 / 7 / 9 | Speed 0.5x / 1x / 2x / 4x / 5x |
| KP Enter | Add a camera waypoint |
| KP + | Play / stop the camera path |
| KP - | HUD: full, player names only, none |
| KP * / KP / | Next / previous filter |
| W A S D, Space, Ctrl | Fly the free camera (Shift 3x faster, Alt slower) |
| Mouse | The timeline cursor; in the free camera, look around (works while paused) |
| Right mouse (hold) | In the free camera: the timeline cursor instead of looking |
| Esc | Leave the demo |

Your own key bindings are untouched, F10 and F11 included.

## Timeline

A bar along the bottom of the screen, like a video player's, shows up by itself whenever a demo
plays with the full HUD. It shows the time played and the demo's full length, across map changes.

![Scrubbing the timeline](media/timeline-scrub.gif)

- **Click** anywhere on the bar to jump there. **Drag** to scrub: the picture follows the mouse.
- **Hover** to see the time under the mouse. The **mouse wheel** over the bar jumps 5 seconds.
- **The play button** on the left pauses and resumes; the speed is shown next to it.
  Clicking in the picture also pauses and resumes.
- **Markers:** green ticks are enemy soldiers killed (by anyone), orange ticks are player and
  allied deaths, a red flag is the recording player's own death, a gold square is an objective
  added or completed, and a blue tick below the bar is a camera waypoint. Hover a marker to see
  what happened; click it to jump to that moment.
- **Long demos** scrub as fast as short ones: once a stretch has been played or jumped through,
  jumping back into it is instant.
- **Map changes** split the bar (L1, L2 ...). The map that is loaded is lightly shaded. A drag
  stays inside it; let go past the split and the other map loads.
- **In the free camera** the mouse turns the camera, so hold the **right mouse button** to get the
  cursor.
- The bar is never in a clean picture: it hides with the KP - modes, and neither the bar nor the
  editor panel is in an F10 render. `demo_timeline 0` turns it off.
- **F10 renders** write `videos/videoNNNN.avi` at a steady 60 fps, however slow the PC renders.
  The video has no sound.

## Free camera

Away from the soldier's eyes, every player is drawn as his full character, from any angle and
distance: his uniform, helmet, gear, the gun in his hands and the ones on his back, every armory
skin and every armory gun, animating exactly as recorded - sprinting, sliding, prone, leaning,
aiming, reloading, throwing, dying. Weather falls around the camera and the soldier's own sounds
come from where he stands.

The camera ignores whatever happens to the soldier's own view. When he scopes in or aims down his
sights, the camera keeps its own field of view and no scope overlay is drawn:

| His eyes, scoped | The free camera, same moment |
|---|---|
| ![Scoped first person](media/scope-firstperson.jpg) | ![Free camera, no scope](media/scope-freecam.jpg) |

To frame a particular player, use his slot number from `demo_names`:
`demo_camera chase 200 90 80 1` puts the camera 200 units from player 1, 90 degrees round from
where he faces, 80 units up.

![Two players from the free camera](media/two-players.jpg)

## Camera paths

Pause, place the camera, press **KP Enter**; move on in the demo, place it again, press KP Enter
again. **KP +** flies the camera through every waypoint on a smooth curve, in step with the demo's
own time. Waypoints added at the same moment play as a fly-through instead
(`demo_pathSegTime` seconds per leg).

![A camera path](media/path.gif)

| Command | Does |
|---|---|
| `demo_waypoint add` | Adds a waypoint at the camera, now |
| `demo_waypoint update 2` | Moves waypoint 2 to the camera (`retime` also moves its time) |
| `demo_waypoint delete 2` | Deletes waypoint 2 |
| `demo_waypoint goto 2` | Jumps to waypoint 2 |
| `demo_waypoint list` | Lists them |
| `demo_camera_clear` | Deletes them all |

## A clean picture, and filters

**KP -** hides every HUD element - in play too, including while F9 records, and it stays hidden
through map changes and into an F10 render. The scope and iron-sight picture stays: it is the view,
not the HUD. The console command is `cleanhud`.

| Full HUD | KP - |
|---|---|
| ![Full HUD](media/hud-full.jpg) | ![Clean](media/hud-clean.jpg) |

**KP *** and **KP /** step through ten film looks, in play or in a demo. The name shows for a
moment, unless the HUD is hidden, so it never lands in a clean recording.

![The ten filters](media/filters.jpg)

`filter list` prints them, `filter sepia` or `filter 2` picks one, `filter off` clears it, and
`r_ppFilterStrength 0.5` softens any of them. Cinematic adds 2.39:1 bars on screens narrower than
that.

## Other players, map changes

Every player in the demo, not only the one who recorded it, plays back with his own skin, helmet
and guns. A demo that changes map part-way plays straight through: the clock runs on across the
change, seeking works everywhere, and jumping back into an earlier map reloads the demo for you.
You can start another demo with `demo name` while one is playing.

![An aimed reload, free camera](media/reload.gif)

## Renaming players

```
demo_names
demo_setname 0 "Sgt. Demo Tester"
demo_setname 0 -          // back to the recorded name
```

The new name shows over his head, on the scoreboard and in the kill feed.

## Every command

| Command | Does |
|---|---|
| `demo_seek 1:30` | Jump to a time (seconds or minutes:seconds) |
| `demo_seekby -10` | Jump relative to now |
| `demo_step 3` | Pause and step 1 (or 3) snapshots |
| `demo_pause` | Toggle pause; `1` / `0` sets it |
| `demo_speed 0.25` | Playback speed, 0.05 to 16 |
| `demo_camera ...` | `on`, `off`, `fov 70`, `speed 500`, `chase`, `where`, `set`, `save`, `load` |
| `demo_waypoint ...` | See Camera paths |
| `demo_path play` | Play / stop the path |
| `demo_hidehud` | Cycle the demo HUD modes, or `0` / `1` / `2` |
| `cleanhud` | Hide / restore every HUD element |
| `filter ...` | Pick a filter |
| `demo_names` | List the players by slot |
| `demo_setname 3 "Name"` | Rename slot 3 (`-` restores) |

| Setting | Default | Meaning |
|---|---|---|
| `demo_fov` | 90 | Free camera field of view |
| `demo_camSpeed` | 320 | Free camera flying speed |
| `demo_pathSegTime` | 2 | Seconds per leg of a fly-through path |
| `r_ppFilterStrength` | 1 | How strongly the filter is applied |
| `demo_editor` | 1 | `0` plays demos the old way |
| `demo_timeline` | 1 | `0` hides the timeline bar |

## Recording everything

A normal demo only holds what the game sent *you*: the players, soldiers and effects near you. Fly
the free camera somewhere you never looked and that part of the map is empty. When **you host**,
F9 records **the whole map** instead: every player, every soldier, every shot, explosion and sound,
wherever it happens. Nothing to type and nothing to switch on: host a game, press **F9**, play,
press **F9** again. The file is the same `demos/lastclip`, it plays with `demo lastclip`, and F10
renders it as before. It keeps going across map changes.

![A U-boat pen worker far from the host, only in a whole-map demo](media/record-everything.jpg)

- **On someone else's server** F9 records the normal demo of what you saw (only the server can
  see everything).
- **Dedicated servers record every map by themselves** into `demos/auto_<date>_<time>_<map>`, and
  delete the oldest ones so the disk never fills. Server owners can tune it; players never need to:

| Setting | Default | Does |
|---|---|---|
| `sv_autoRecord` | `1` | `1` = dedicated servers record every map, `2` = listen servers too, `0` = off |
| `sv_autoRecordMax` | `30` | Keep at most this many auto demos |
| `sv_autoRecordMaxMB` | `2048` | ...and at most this many MB of them |
| `cl_recordFull` | `1` | `0` = F9 on your own server makes a normal demo |

`sv_record <name>`, `sv_stoprecord` and `sv_recordstatus` do it by hand from the server console.
The recorder costs the server 0.1 to 0.2 ms a frame. A whole-map demo is less than twice the size
of a normal one: roughly 40-50 MB an hour on a coop map.

## Where things are saved

| File | Holds |
|---|---|
| `demos/mynight.dm_17` | The recording |
| `demos/cameras/mynight.cam` | Its camera path |
| `demos/cameras/mynight.names` | Its renamed players |

They live in your game's `maintt` home folder. The `.cam` and `.names` files are plain text: send
them with a demo to share a finished camera move.
