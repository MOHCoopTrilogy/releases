# Omaha (m3l1a) - the 2026-09-05/06 batch, bugs 2473-2511

Pruned out of `OPEN.md` on 2026-09-08 for space. These items are still owed a playtest; each
names the marker that proves it. `OPEN.md` keeps the summary and the pointer.

- **2026-09-05/06 Omaha batch (bugs 2473-2511) - SHIPPED as v1.5.2, later builds AWAITING PLAYTEST.** Three
  runs on 09-06 (08:52, 13:03, 18:30) verified from markers everything from the waders to the crowd's
  charge (`FIRSTSEQ start`, `RADIOTX`, 044a, whistles, `BEACHADV fired`, flank guns 2 and 4 `drvfire=1`;
  guns 1 and 3 read `see=0` - sightline) and, at 18:30, the Higgins sink at last (`HIGGINSSINK leg 1..4
  done`, `complete` +56 s) after four runs where it never rolled (a solid clip, then the hull's
  model swap making it SOLID_BBOX, 2487/2496). Also DISPROVED and re-fixed: beach fire (the cover trace
  ended inside the player's own box, 2497), crowd poses (2498), quick-draw flip axis (2499). Still
  unseen, with the marker that proves each: beach fire (`BEACHLOS seen=1` on open sand, `BEACHHIT`,
  felt hits; `coop_dmgProbe 1` is the engine cross-check) · crowd crouched / shaking / wounded at the
  hedgehogs, running on the whistle, prone short of the bank, no `HEDGECROWD drift` · quick-draw muzzle
  up-left, sights up (`coop_qdrawHoldFlip` 0-3 by rcon if not) · weapon-lag rotation · ragged wet line
  on gl2 and gl1 · the sink's END STATE (roll 30 / drop 72, ramp dead bound, 2510) · caustics dimmed
  (2509) · urgency after the smoke (`URGENCY say`, 2511). Caveats: a busy voicebank can hold the smoke
  advance ~17 s; the timber ramp draws no hits; LOS cover plays no suppression sound (NULL trigger in
  the in-cover branch). Unpublished builds: boat stare off, pace 0.9, waders slid (2503); smoke blinds
  the guns (2501); arms carry the lag swing (2502); hull fires at deck height (2504); placeholder
  aliases reverted (2505); radioman pair moved (2506); the DROWNING pass (2507: air ramp `RAMPUW air=`,
  heart `bpm=`, bubbles `burst=`, lid `alpha=`, exit flash/ring/inhale, caustics on the real seabed);
  the OCEAN pass (2508: sheet fades out at T 0.82 into the strip's wet line (4-param tCoord, T2 knee), swash blood, a tint +
  break-foam band in the two reclaimed stages, froth + sky sheen offshore, a boat wake (v13 skc
  re-encode), the bob resynced to the sheet's 10 s, gl2 alphaGen dot + a real sun (r_hzmAlphaGenDot),
  an open-sea wave mesh behind coop_seaMeshOn - up only from the grounding to the plunge, the ride's
  sheet is $ocean_calm (2513); A/Bs owed on the stage-2 seam and the 1936 thin branches).
