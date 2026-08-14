# Single-instance traps moved out of TRAPS.md (2026-08-12)

TRAPS.md's own bar is "a failure family that RECURRED". These three are each a single confirmed
bug with a single cause - real, worth keeping, but they were consuming ceiling that the recurring
families need. Nothing here is superseded; look for it by bug number.

## Entities at health <= 0 that never died are UNKILLABLE (bug-1323)
`Entity::DamageEvent` early-outs on `health <= 0` (entity.cpp:2705) and script `hurt` routes
through it. An entity that crosses zero without its death completing visibly is entombed - no
shot, blast or scripted `hurt` will ever land again, and every `waittill death` waiter blocks
forever. A script failsafe MUST reset `self.health = 1` (script setter bypasses DamageEvent)
BEFORE the `hurt`. Vehicles are auto-rescued engine-side (Vehicle::CoopZombieRescue, `^~^~^
VEHZOMBIE` log line); other classes are not.


## ui_startdmmap silently re-pushes g_* server cvars from the archived menu values (bug-1326)
`UI_StartDMMap_f` (cl_ui.cpp:3422-3480) appends `set g_inactivespectate/g_inactivekick/
g_gametype/g_teamdamage/fraglimit/timelimit/sv_maxclients/sv_maplist/sv_hostname/cheats 0` from
the `ui_*` archived cvars to the command buffer AFTER any cfg that ran before it. Any `set g_<X>`
in start_server.cfg for those keys is stomped unless the `ui_<X>` twin is seeded alongside it.


## Scripted `surface head ...` silently hits the wrong LOD (bug-1332)
head1.skd (and likely other heads) contains TWO surfaces both named "head". An exact-name
surface command flips only the FIRST (Surface_NameToNum first-match); the rendered LOD stays
unchanged - no error, no warning. Use the retail prefix form `surface "head*" ...` which
applies to every match (entity.cpp:4237). Engine gore tiers are immune (they loop by index).

