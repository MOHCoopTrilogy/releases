// HZM coop [aircraft 2026-10-05] coop call-in aircraft (coop_mod/aircraft.scr, docs/proposals/aircraft_2026-10-05).
// Marks the entity as an aircraft for the cgame (Doppler, fog see-through). radius > 0 also makes it a German
// plane that allied fire can shoot down: hp is accounted in DamageFunc, bullets reach it through
// G_HZM_AircraftBulletHits (above the sky brush, whatever its link box), allied projectiles get a proximity fuse.
Event EV_ScriptSlave_HzmAircraft
(
    "coop_aircraft",
    EV_DEFAULT,
    "fF",
    "damage_radius hp",
    "HZM coop: flag this script model as a coop aircraft. damage_radius > 0 = shootable by allied fire with hp hit "
    "points (default 600); 0 = cosmetic (Doppler + fog see-through only).",
    EV_NORMAL
);

Event EV_ScriptSlave_HzmAirThink
(
    "coop_aircraft_think",
    EV_DEFAULT,
    NULL,
    NULL,
    "HZM coop internal: per-frame proximity fuse for allied projectiles near a shootable aircraft.",
    EV_NORMAL
);

