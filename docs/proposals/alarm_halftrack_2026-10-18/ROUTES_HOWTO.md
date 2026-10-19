# How to give an alarm vehicle a route on a map (about 5 minutes a map)

Maps with no route stay **vehicle-off**: the alarm works as before and nothing drives in. This guide is for the six maps that have alarm
switches but no vanilla vehicle road: **m1l1, m2l1, m3l2, e3l1, e3l2, t1l1**. (m3l3, t2l3, t3l1, m4l1, m4l2 already ship routes.)

You place a few marker models with the normal build tool, walk the road once, and the agent turns the markers into the route file.
Nothing you place stays in the map: markers are only read from the save file.

## 1. Start build mode (same as for the alarm switches)

1. Launch normally, start the mission with the coop menu (Apply), open the console and run `exec coop_mod/cfg/buildmode.cfg`
   (first ever use: restart the map once afterwards).
2. Numpad keys: KP4/KP6 model, KP1/KP3 category, KP_ENTER place, KP_DEL undo, KP7/KP9 turn 15 degrees, `,` `.` pull/push the object along your aim.
   `;` snaps to the grid (leave it off for a road).

## 2. Pick a road

Choose a road or track that:
- a truck-sized thing can drive (no trees, sandbags, steps, narrow doors; about 220 units wide, 450 units long for the halftrack);
- **starts out of sight** of where the squad fights: behind a building, a bend, a hill or a gate, at least about 1800 units from the fight;
- **ends in the open 500-1500 units from the fight** where it can stop, with a wall or crates nearby for the squad to take cover behind.

The game checks the entry live every time and simply skips the vehicle when somebody could see it, so a good entry matters more than a perfect one.

## 3. Place the markers IN THIS ORDER (the build number decides the order)

| # | What | Model (category in the build tool) | How |
|---|---|---|---|
| 1 | **ENTRY**: where the vehicle appears | `models/vehicles/sdkfz.tik` (TRUCKS + HALFTRACKS, item 45) | stand on the road, face the DIRECTION IT WILL DRIVE, place. The model is only a marker. |
| 2..n | **ROAD POINTS**: one at every bend, and at least one every 400-600 units on a straight | `models/static/lightpost_globe.tik` (FLAGS + SIGNS + POSTS, item 13) | in driving order, on the middle of the road. The vehicle cuts corners between points, so put a point before and after each bend. |
| last | **STOP**: where it parks and fights/unloads | `models/vehicles/sdkfz_no_cannon.tik` (ARTILLERY + AT GUNS, item 35) | face the way the front of the vehicle should point. |
| any time after the entry | **ROCKET CRATE**: only needed for a halftrack route (and nice for a truck) | `models/weapons/panzerschreck.tik` or `models/weapons/bazooka.tik` (WEAPONS) | on the squad's side of the stop, behind cover, 300-900 units from the stop, never in the line of fire. Face it along the cover. |

Rules: exactly one ENTRY and one STOP per route, road points between them in build order, undo (KP_DEL) removes the last one.
Make a second route on the same map by repeating this after you have imported the first (use a different name).

## 4. Hand it to the agent

Tell the agent the map and whether the route is a `truck` (3-5 infantry dismount, no gun) or a `halftrack` (MG, needs the rocket crate):

```
python docs/tools/gen_alarm_vehicle_routes.py import-dat <map> <routename> truck      # or halftrack
python docs/tools/gen_alarm_vehicle_routes.py build                                    # writes coop_mod/alarmveh_routes.scr
```

`import-dat` reads `coop_mod/save/build_<map>.dat`, warns if two points are more than 700 units apart, and rewrites the route in
`docs/tools/alarm_vehicle_routes.json`. The agent then does a dedicated-server boot to prove the vehicle drives it, stops, and is
hidden at the entry.

Optional: `--model models/vehicles/opeltruckgreen.tik` picks a truck skin that matches the map (green, canopy, gray, desert; winter
maps use `halftrack_winter.tik` for the halftrack).

## 5. Where to look first (suggestions per map, not measured)

| Map | Hint |
|---|---|
| m1l1 | the night fort: a road that reaches the compound from outside the walls; avoid the intro truck lane that is used by the opening cutscene |
| m2l1 | an approach road to the town/camp from the edge of the map; check the first alarm switch area |
| m3l2 | the base has 2 static halftrack props at (-1921, 1208, -145); a road near them is the natural arrival |
| e3l1 | the camp has 4 trucks parked; use the road they face |
| e3l2 | the town has 8 trucks; a street that is open end to end |
| t1l1 | the truck the map already drives for the final area; its road is a candidate |

## 6. Testing a route yourself

`set coop_alarmVeh 1`, `set coop_alarmVehDebug 1`, `set coop_alarmVehDelay 5`, then pull the alarm as usual. Console lines to look for:
`^~^~^ ALMVEH crate ok`, `ARRIVING`, `ARRIVED`, `FIRING` (halftrack), `WITHDRAW`, or `SKIP: no hidden entry, reason ...`
(`seen` = a player could see the entry, `near` = a player was within 1800 units, `blocked` = the vehicle box did not fit).
