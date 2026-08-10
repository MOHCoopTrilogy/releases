# AI ammunition and reloading — what the code actually does

Read-only investigation, 2026-08-07. Engine paths are `openmohaa-hzm/code/fgame/`; script
paths are `hzm-mohaa-coop-mod/` unless the file is quoted from a retail pak (noted inline).

**One-line answer:** AI bullet ammo is *infinite at the engine level* — no counter is ever
decremented for a non-client owner — but AI *do* play real reload animations, driven entirely
by a **script-side** round counter (`self.roundsinclip`) that has no connection to the engine's
ammo and cannot stop an actor from firing. AI **grenades are the exception**: they are genuinely
finite and genuinely consumed.

---

## 1. Does an Actor consume ammo when it fires?

**No. Not one counter is decremented on the AI fire path.**

The path, traced end to end:

1. The AI's shoot animation carries the shot commands. Retail `models/human/animation/human_mp40.tik`
   (extracted from `main/Pak0.pk3`), `mp40_shootauto` at lines 38-50, issues eight `fire` commands
   on the `server` channel at frames 0,2,4,…,14.
2. `fire` is `EV_Sentient_Attack` — `sentient.cpp:55-63` (event declaration), bound at
   `sentient.cpp:671` to `Sentient::FireWeapon(Event*)`.
   (Note: `Actor::FireWeapon(Event*)` exists at `actor.cpp:5518` but is **not** registered in
   Actor's response table — grep of `actor.cpp` for `&Actor::FireWeapon` returns nothing — and
   `Sentient::FireWeapon(Event*)` is non-virtual (`sentient.h:275`), so the Actor override is
   dead code. The dispatch lands on the Sentient handler either way and both converge below.)
3. `Sentient::FireWeapon(Event*)` → `Sentient::FireWeapon(int, firemode_t)` at
   `sentient_combat.cpp:481-495`. Actor does not override the `(int, firemode_t)` form (only
   `Player` does, `player.cpp:13852`), so the Sentient version runs.
4. It gates on `activeWeapon->ReadyToFire(mode)` (`sentient_combat.cpp:485`) then calls
   `activeWeapon->Fire(mode)` (`sentient_combat.cpp:490`).
5. `Weapon::Fire` calls `UseAmmo(ammorequired[mode], mode)` — `weapon.cpp:2791`.
6. **`Weapon::UseAmmo` returns immediately for any AI owner** — `weapon.cpp:1472-1478`:

   ```cpp
   void Weapon::UseAmmo(int amount, firemode_t mode)
   {
       mode = m_bShareClip ? FIRE_PRIMARY : mode;
       if (UnlimitedAmmo(mode) && (!owner || !owner->isClient())) {
           return;
       }
   ```

   and `Weapon::UnlimitedAmmo` — `weapon.cpp:2319-2332`:

   ```cpp
   qboolean Weapon::UnlimitedAmmo(firemode_t mode)
   {
       if (!owner) { return true; }
       if (!owner->isClient() || DM_FLAG(DF_INFINITE_AMMO)) { return true; }
   ```

   An Actor is a Sentient but not a client, so `UnlimitedAmmo()` is `true` **and**
   `!owner->isClient()` is `true` → early return. `ammo_in_clip[]` is never decremented, and the
   reserve-pool branch below it (`weapon.cpp:1493-1496`) is itself guarded by
   `owner->isClient()`, so the actor's `Ammo` inventory is never touched either.

Consequences that follow directly:

- `SetShouldReload(qtrue)` at `weapon.cpp:1488` is inside the block that AI never reach, so an
  AI weapon's `m_bShouldReload` never goes true.
- `Weapon::ReadyToFire` gates on `HasAmmoInClip(mode)` (`weapon.cpp:2431`), and
  `HasAmmoInClip` returns true whenever `ammo_in_clip[mode] >= ammorequired[mode]`
  (`weapon.cpp:2381-2384`). The clip is filled once at spawn and never falls, so this is
  permanently true.
- The clip is filled by `Weapon::GiveStartingAmmoToOwner` (`weapon.cpp:3041-3075`), posted from
  `Sentient::giveItem` (`sentient.cpp:1334-1341`) for any weapon given to any Sentient — actor
  or player alike.

**Confidence: high.** Read directly; the early return is unambiguous and there is no alternate
AI fire path (`Weapon::Fire` is the only route from `Sentient::FireWeapon`).

**HZM vs retail:** the ammo functions are unmodified. `git diff` on `code/fgame/weapon.cpp`
shows no change in the `UseAmmo` / `UnlimitedAmmo` / `ammo_in_clip` region. The only HZM addition
nearby is the `coop_fireDebug` diagnostic block at the head of `ReadyToFire`
(`weapon.cpp:2401-2418`), which only prints. So this is stock MOHAA/OpenMOHAA behaviour, not
something a previous session introduced.

---

## 2. Is there a reload behaviour for AI at all?

**Yes, and it is reachable and runs constantly — but it is purely cosmetic.** It lives in
script, not in the engine's ammo system.

### The script counter

`anim/reload.scr` is **not** shipped by the mod (the mod's `anim/` folder has no `reload.scr`),
so the retail file is used. Quoted from `maintt/pak3.pk3 → anim/reload.scr` (452 lines):

- `ReloadInit:` (lines 7-18) runs once per actor, calls `ReloadClip`, sets `self.reloadinit = 1`.
- `ReloadClip:` (lines 21-172) is a switch on `self.weapon` that sets `self.maxroundsinclip` /
  `self.roundsinclip` — e.g. `mp40` = 32 (lines 83-86), `stg44` = 30 (88-91),
  `mauser kar 98k` = 5, `bazooka`/`panzerschrek` = 1.
- `Reload local.upperbodyanimonly local.norechamberanim local . shootFromCover:` (line 180
  onward) picks a per-weapon `local.roundsfired` — `mp40` = 8 (line ~239), `stg44` = 8,
  bolt rifles = 1 — then at line ~283:

  ```
  self.roundsinclip = self.roundsinclip - local.roundsfired;
  if (self.roundsinclip <= 0 && local.reloadanimname != "")
  {
      self.roundsinclip = self.maxroundsinclip
      ...
      self setupperanim (local.reloadanimname + "_reload")
      ...
      self waittill upperanimdone;
  }
  ```

  That is a real blocking upper-body reload animation with a sound
  (`human_mp40.tik:56-62`, `mp40_reload` → `entry sound mp40_reload_npc`).

The `roundsfired` figures are calibrated to the burst animations: `mp40_shootauto` fires exactly
8 `fire` commands (`human_mp40.tik:38-50`) and `reload.scr` debits exactly 8 per call. So an
MP40 AI plays a reload every 4 bursts.

### What triggers it

Every AI combat anim-state script calls it:

- `anim/attack.scr:487-489` (`AttackStand`, on entry if `self.needreload == 1`) and
  `anim/attack.scr:528-531` (after each burst, unconditionally: `waitexec anim/reload.scr::Reload 1 0`).
  Same pattern repeats at attack.scr lines 582, 727, 767, 928, 1160, 1198, 1206, 1242, 1275, 1290, 1583.
- `anim/shoot.scr:9` (`ReloadInit`), then `:53`, `:63`, `:110`, `:126`, `:132`
  (`waitexec anim/reload.scr::Reload 1 NIL 1` after each burst).
- `anim/cornerleft.scr:27/87/92/126/174/193` and `anim/cornerright.scr:26/90/95/129/179/193`,
  which additionally use `Reload.scr::CheckForCornerReload` (reload.scr line ~360) to set
  `self.needreload`.

`anim/attack.scr` is what `THINK_TURRET` — the stand-and-shoot state most coop enemies sit in —
drives, via `Anim_Attack()` at `actor_turret.cpp:256`. `anim/shoot.scr` is driven by
`Anim_Shoot()` at `actor_cover.cpp:498`. `actor_runandshoot.cpp:158` also uses `Anim_Attack()`.
All three roads lead to the reload.

### The engine's half of the reload

The engine has two reload flags, both **written only from script**:

- `m_bInReload` — `actor.h:824`, set by the `inreload` setter event
  (`actor.cpp:2239-2247`, handler `actor.cpp:12915-12918`). `reload.scr` writes it
  (`self.inreload = 1` / `= 0`). Read at `actor_cover.cpp:279` and `:293` so a reloading actor
  runs to cover with the right end-anim and finishes the reload before poking out.
- `m_bNeedReload` — `actor.h:826`, set by `setreloadcover` (`actor.cpp:2248-2255`, handler
  `actor.cpp:12935-12938`), which `reload.scr` issues when the `shootFromCover` parameter is set.
  Read once, at `actor_cover.cpp:487` (`State_Cover_Shoot` breaks off to find cover when a
  reload is pending). It is **cleared at the end of every `Actor::Think`** —
  `actor.cpp:7785` — so it is a one-frame signal.

There is no engine timer, no engine trigger, and no engine condition that can start an AI
reload. Nothing checks `Weapon::ShouldReload()` for an actor (`Weapon::CheckReload` at
`weapon.cpp:3609` is called only from `player_combat.cpp:159`, `ammo.cpp:111` and
`playerbot.cpp:384` — all player/bot paths).

**Confidence: high** for the mechanism and the call sites. **Medium** for exact reload.scr line
numbers, which I read from an extracted copy of the retail pak rather than a repo file.

---

## 3. What is `ammo_grenade`, and what does `"ammo_grenade" "0"` do?

`ammo_grenade` is a **completely separate, genuinely finite** pool, and it is the only AI ammo
in the game that is really consumed.

- Declared as an Actor event at `actor.cpp:1527-1553` (`ammo_grenade`, normal / setter / getter),
  bound at `actor.cpp:2666-2668`.
- Setter: `Actor::EventSetAmmoGrenade` — `actor.cpp:10663-10666` — is
  `GiveAmmo("grenade", ev->GetInteger(1))`, which lands in `Sentient::GiveAmmo`
  (`sentient_combat.cpp:155-181`). Note it **adds**, it does not assign.
- Gate: `Actor::DecideToThrowGrenade` returns false immediately if `!AmmoCount("grenade")` —
  `actor.cpp:10521-10525`.
- Spend: `Actor::GenericGrenadeTossThink`'s throw calls `UseAmmo("grenade", 1)` —
  `actor.cpp:10622` — which reaches `Sentient::UseAmmo` (`sentient_combat.cpp:183-207`) and
  really decrements the `Ammo` inventory object. Nothing short-circuits this path, because it
  is `Sentient::UseAmmo(str, int)`, not `Weapon::UseAmmo(int, firemode_t)`.

So: **grenades run out; bullets do not.** An AI with `ammo_grenade 2` throws exactly two and
then never throws again.

`"ammo_grenade" "0"` on a BSP actor means "this actor throws no grenades". Because the setter is
`GiveAmmo(..., 0)`, it creates (or leaves) a `grenade` Ammo entry at amount 0, and
`DecideToThrowGrenade` bails at `actor.cpp:10523`. It is the map author explicitly disarming the
grenade behaviour — very common: across `map_entities/*_entities.txt`, `"ammo_grenade" "0"`
appears 2008 times vs 433 at `"2"`, 212 at `"4"`, 103 at `"1"`, 38 at `"3"`, 18 at `"5"`, 5 at
`"6"`, 3 at `"12"`, 1 at `"8"`. m3l1b has 27 `ammo_grenade` keys, most of them `0`
(`map_entities/m3l1b_entities.txt:57, 82, 108, 183`, with `"2"` at :156).

Coop-side users of the same key: `coop_mod/officer.scr:1954` (`local.s.ammo_grenade = 3`) and
`:2380` (`= 5`); `coop_mod/bunker.scr:420` (`= 0`); `global/mg42_active.scr:140` and `:144`
(spawns gunner and spotter with `ammo_grenade "5"`); `global/spawner.scr:64/181` and
`global/parade.scr:755-758` propagate it from spawner to spawned actor.

There is also a coop-only consumer: `coop_mod/itemhandler.scr:513-520` does
`self ammo_grenade local.grencount` with `local.grencount` set to `-1` or `-2` for some weapon
classes — since the setter *adds*, this **subtracts** grenades from the actor (it is the
drop-a-grenade-pickup bookkeeping).

**Confidence: high.**

---

## 4. Do our own spawned actors differ from BSP-placed actors?

**In bullet ammo, no — not at all.** Everything funnels through the same two calls.

- `local.x gun "stg44"` → `EV_Actor_SetGun` (`actor.cpp:66-83`) → `Actor::EventGiveWeapon`
  (`actor.cpp:2556-2557`, body at `:5197`) → `weapon_internal` →
  `Actor::EventGiveWeaponInternal` (`actor.cpp:5168-5188`) → `giveItem` → the same
  `EV_Weapon_GiveStartingAmmo` post at `sentient.cpp:1338`. Identical to what a BSP actor gets.
- Officer waves / guards: `coop_mod/officer.scr:524, 664, 1864-1875, 1957-1961, 2072-2076, 2167,
  2229, 2378, 2835, 2854, 3065, 3397-3403` — all plain `gun "..."`.
- Paradroppers: `coop_mod/paradrop.scr:238-249` — plain `gun "bar" / "thompson" / "m1 garand" /
  "springfield '03 sniper"`.
- AI-handler clones: `coop_mod/aihandler.scr:263` (`local.r gun local.gun`) — copies the source
  actor's gun string; same path.
- m3l1b rear garrison / bunker nest gunner: `coop_mod/bunker.scr:404`
  (`spawn "models/human/german_wehrmact_grenadier.tik" gun "MG42"`) — same path.

**Grenades do differ, deliberately:** officer waves grant 3 and 5 (`officer.scr:1954`, `:2380`);
the bunker nest gunner is explicitly given 0 (`bunker.scr:420`); paradroppers and aihandler
clones are given none at all (no `ammo_grenade` anywhere in `paradrop.scr` or `aihandler.scr`),
so those actors will never throw a grenade.

**One real difference, and it is about reloading, not ammo:** see §5 — the `bunker.scr`
MG nest gunner never plays the MG42 reload that BSP nests play.

**Confidence: high** for the weapon path, **high** for the grenade grants (grepped the whole mod
tree for `ammo_grenade`).

---

## 5. Do MG42 turret gunners differ from riflemen?

Yes — differently plumbed, but with the same bottom line (infinite rounds).

- `TurretGun` derives from `Weapon`, so its shots also go through `Weapon::Fire` →
  `Weapon::UseAmmo` → the same non-client early return. `weapturret.cpp` contains **no** ammo or
  clip logic of its own (a case-insensitive grep for `ammo|clip` in that file returns only
  `edict->clipmask` at :413/:590/:608).
- The MG42 gunner's reload is a *state*, not an ammo event:
  `ACTOR_STATE_MACHINE_GUNNER_RELOADING` (`actor.h:579`), entered only via
  `Actor::EventReload_mg42` (`actor.cpp:10869-10877`), which is the script command
  `reload_mg42` (`actor.cpp:276-284`, bound at `:2522`). While in that state
  `Actor::ThinkHoldGun_TurretGun` plays `STRING_ANIM_MG42_RELOAD_SCR`
  (`actor_machinegunner.cpp:133-135`) and shifts the actor's height/pitch
  (`actor_machinegunner.cpp:155-172`).
- The **only** caller is the scripted-nest thinker: `global/mg42_active.scr:223-241` fires the
  reload when `self.reload_counter >= 13`, where the counter ticks once per think while firing
  (`global/mg42_active.scr:419`) and resets to 0 (`:240`). It is a pure tick counter — nothing
  to do with rounds.
- **Our `bunker.scr::mg_nest_manned` gunner never reloads.** It builds the gun and gunner and
  sets `type_attack = "machinegunner"` (`coop_mod/bunker.scr:380-424`) but never threads
  `global/mg42_active.scr` (grep of `bunker.scr` for `mg42_active` → no match; the twelve map
  scripts that do thread it are m3l1a, m3l1b, M3L3, m4l1, m4l2, m4l3, m6l1a, M6L1b, m6l1c,
  m6l2a, t2l1, t2l2). So it is driven only by `Think_MachineGunner_TurretGun`, which has no
  reload trigger of its own.

**Overheat is a separate HZM system and is not ammo.** `TurretGun::AI_DoFiring`
(`weapturret.cpp:1353-1420`) runs a heat cycle: heat +50/s while firing, cook-off at a
per-gunner random ceiling of 55..95 (`:1403-1410`), 2 s dead-gun floor (`:1411`), cool at 25/s
until a random resume point 0..35 (`:1375-1382`), bleed 8/s between bursts (`:1417-1418`),
disable with `coop_mg42AiOverheat 0` (`:1364-1371`). The comment at `weapturret.cpp:1383-1389`
records that before the resume-fire fix, an overheated scripted nest only came back ~6.5 s later
"via mg42_active.scr's FAKE RELOAD path, playing a reload the designer never intended" — i.e.
the reload was a *symptom* of the overheat desync, which is one plausible reason an MG42 reload
has looked arbitrary in play.

**Confidence: high.**

---

## 6. Bottom line

**"Infinite ammo" is correct. "Never reloads" is not — but the reload is theatre.**

- Bullets: infinite, engine-enforced, cannot be exhausted (§1). No AI has ever run dry and none
  can.
- Reloads: real animations with real sounds, driven by a script counter calibrated to the burst
  animations (§2). An MP40 AI in `attack.scr`/`shoot.scr` should reload roughly every fourth
  burst. Skipping the reload would not let him fire more, and being caught in one does not make
  him defenceless in any ammo sense — it just costs him the animation's duration.
- Grenades: genuinely finite and genuinely spent (§3).

Why the user may never have registered a reload:

1. **There is no consequence, so there is no tell.** A player reads "reload" from the pause in
   incoming fire and the dry click. AI never click dry (`m_NoAmmoSound` at `weapon.cpp:2452` is
   in the `playsound` branch that only the player's fire path reaches), never stop shooting for
   lack of ammo, and the reload is `setupperanim` — legs keep the alert stance, so the silhouette
   barely changes. It reads as "he paused", not "he reloaded".
2. **It is short and it is upper-body only**, over open ground at typical coop engagement range.
3. **The coop "reloading!" voice line is decoupled from it** — `coop_mod/aivoice.scr:394` rolls
   `"reload"` as one of three random sustained-combat chatter situations, not on the actual
   reload — so the audio cue that would draw attention to it fires at unrelated times.
4. **MG42 nests built by `bunker.scr` genuinely never reload** (§5), and those are the AI a
   player stares at longest.
5. *(Inference, not confirmed by reading a specific line)* — the reload is only reached when a
   burst thread runs to completion (`self waittill upperanimdone` then `waitexec ... Reload`).
   An actor whose anim state changes mid-burst — pain, new enemy, cover break — has that thread
   torn down and the decrement never happens, so in a churning firefight `roundsinclip` should
   advance more slowly than the true rate of fire. I did not verify the thread-teardown
   semantics against engine code; treat as a hypothesis.

**Not found / not confirmed:**
- No engine-side AI ammo pool, AI reload timer, or AI dry-fire behaviour exists. Searched
  `actor*.cpp`, `sentient*.cpp`, `weapon.cpp`, `weapturret.cpp`, `ammo.cpp`.
- No `.wolf/buglog.json` entry covers AI ammo or AI reloading (the `reload` hits there are all
  the player's `cg_reloadCam` saga and weapon-tik audio aliases).
- I could not confirm reload behaviour at runtime: the current
  `%APPDATA%/openmohaa/maintt/qconsole.log` is a boot-only log with no gameplay, and it contains
  zero instances of `reload.scr`'s `"^~^~^ Reload clip default case for weapon ..."` marker —
  which is *absence of evidence about coverage*, not evidence that reloads happen or don't.

---

## Closing note — one opportunity, clearly separated

The lever already exists and is not wired to anything: `reload.scr` maintains an accurate
per-actor round count in `self.roundsinclip`/`self.maxroundsinclip`, and the engine exposes
`setreloadcover` (`actor.cpp:12935`) and `inreload` (`actor.cpp:12915`) with `State_Cover_Shoot`
(`actor_cover.cpp:487`) already honouring them. A reload that the player can *read* — and
therefore push into — would not need new ammo plumbing, only a way to make the existing count
visible and consequential. Separately, `coop_mod/bunker.scr::mg_nest_manned` is the one spawner
whose MG gunner has no reload path at all, which is a straightforward gap next to the twelve
retail maps that thread `global/mg42_active.scr`. Not proposing either here.
