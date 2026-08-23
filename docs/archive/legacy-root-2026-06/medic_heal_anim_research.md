# Medic Heal / Give-Aid Animation Research

Research target: a believable "healing / giving aid" gesture to play on an allied AI medic
(`models/human/dday_ranger_medic.tik`) when the coop paradrop medic heals a player.

Result: **There is no dedicated `heal` / `bandage` / `inject` / `medkit` animation in the human
skeleton.** The shipping single-player medic uses the **canteen-pass** scripted gesture
(`pass_canteen_start` / `pass_canteen_end`), played as an **upperanim** while the actor stands.
That is the confirmed, ready-to-copy answer.

---

## 1. Skeleton + animation config (confirmed)

Both relevant models are the standard MOHAA human skeleton:

- `models/human/dday_ranger_medic.tik` (Pak0.pk3)
  - `path models/human/allied_army_soldier`, `skelmodel usarmy.skd`
  - anim path: `path models/human/protoanimations`
  - `$include models/human/new_generic_human.tik`  <- **the anim list**
  - `$include models/human/animation/dialogue/generic_dialogue_US.tik`
- `models/human/allied_airborne_soldier.tik` (Pak0.pk3)
  - `path models/human/allied_airborne`, `skelmodel airborne.skd`
  - same `$include models/human/new_generic_human.tik`

**Confirmed anim-config file: `models/human/new_generic_human.tik` (inside Pak0.pk3).**
This file maps every animation *label* (what you pass to `anim` / `upperanim` / `anim_scripted`)
to a `.skc` file. All human models on AA maps share it, so any label below is valid on the medic.

The `.skc` clips physically resolve to `models/human/animation/scripted/pickup_obj/*.skc`
(also mirrored under `newanim/...`), all present in **Pak0.pk3**.

---

## 2. Valid candidate animation labels (verified to exist for this skeleton)

All defined in `new_generic_human.tik`; their `.skc` files were confirmed present in Pak0.pk3.

| Anim label              | .skc clip                                   | Notes |
|-------------------------|---------------------------------------------|-------|
| `pass_canteen_start`    | scripted/pickup_obj/pass_canteen.skc        | Crouch/lean forward offering motion. **Used by SP medic.** Attaches a canteen model at frame 0 of the clip via the TIK server block. |
| `pass_canteen_end`      | scripted/pickup_obj/pass_canteen_end.skc    | Withdraw / finish motion; removes the attached canteen on enter. **Used by SP medic.** |
| `pass_canteen_idle`     | scripted/pickup_obj/pass_canteen_idle.skc   | Hold pose (loopable middle). |
| `pass_canteen_drink`    | scripted/pickup_obj/pass_canteen_drink.skc  | Self-drink (used for medic healing *himself*). Plays a drink sound. |
| `pass_obj01`            | scripted/pickup_obj/passgun_01.skc          | Hand-off motion (attaches a pistol model). |
| `pass_obj02`            | scripted/pickup_obj/passgun_02.skc          | Hand-off finish. |
| `pickup_obj`            | scripted/pickup_obj/pickup_table.skc        | Reach-down pickup. |
| `point`                 | misc/point.skc                              | Point gesture (fallback signal). |
| `american_salute`       | misc/salute.skc                             | Salute (fallback gesture). |

There is **no** `heal`, `bandage`, `inject`, `medkit`, `medic`, `give`, `giveitem`, `useitem`,
or `kneel_pickup` label anywhere in the human anim set. The canteen-pass set is the engine's
intended "give aid to a friendly" gesture.

---

## 3. Exact shipping-game pattern (copy this)

`global/friendly.scr` (Pak0.pk3) contains the real SP medic. The `friendtype == 5` medic loop
(line ~960) calls `waitthread heal <ent>`, and the `heal` label (line ~1224) is:

```c
heal local.ent:
    if (isalive local.ent)
    {
        local.health = (local.ent.health * 100) / local.ent.maxhealth
        if (local.health < level.medicmin)        // medicmin = 65
        {
            self.no_idle = 0
            self.movedoneradius = 100
            self runto local.ent                  // walk to the wounded ent
            self waittill movedone
            self exec global/stand.scr            // stop and stand
            if (isalive local.ent)
            {
                local.vec = vector_length (self.origin - local.ent.origin)
                if (local.vec < 140)              // must be close
                {
                    self nodamage
                    self.avoidplayer = 0
                    self upperanim pass_canteen_start   // <-- THE GESTURE
                    self waittill upperanimdone
                    local.ent heal 0.5                  // actual HP restore
                    self playsound med_kit              // sound alias (Pak0 ubersound.scr)
                    self upperanim pass_canteen_end     // <-- withdraw
                    self waittill upperanimdone
                    self.avoidplayer = 1
                    self takedamage
                }
            }
        }
    }
end
```

Self-heal variant (`canteen` label, line ~1182) uses:
```c
self upperanim pass_canteen_drink
self waittill upperanimdone
```

Sound alias confirmed: `med_kit` -> `sound/items/Health_MedKit_01.wav` (ubersound/ubersound.scr, Pak0).

---

## 4. Trigger guidance for an ACTIVE / forceactivated actor

The SP medic is a live, thinking AI and it uses **`upperanim`** — NOT `dumb`, NOT `anim_scripted`.
This is the right choice for our forceactivated medic:

- **Use `upperanim`** — it is upper-body-only. The actor stays standing on its lower-body locomotion
  state, so it does not need to be put `dumb` and AI does not have to be torn down/re-enabled.
  No `disable_ai` / re-enable dance required.
- **`anim_scripted` / `dumb` are NOT needed** and would over-constrain it (full-body lock, would
  fight the active think state). Avoid them here.
- **Stationary requirement:** the gesture reads best standing still. The SP medic does
  `runto` -> `waittill movedone` -> `exec global/stand.scr` *before* the gesture. For our paradrop
  medic, make sure it is not mid-run when the gesture fires (have it reach the player / stop first).
  `upperanim` itself does not stop the legs, so if the medic is sprinting the legs will still run —
  call it when the medic is idle/stationary next to the player.
- **Always pair with `waittill upperanimdone`** so the start/heal/end sequence is ordered.
- `self nodamage` ... `self takedamage` around the gesture is optional polish (invuln during the
  animation); fine to keep or drop in coop.
- Canteen model auto-attaches/detaches via the TIK animation server blocks (frame 0 attach,
  `enter` remove) — no manual attachmodel needed.

Caveat: `pass_canteen_start` is a slight crouch-forward lean, not a pure standing pose; it looks
correct when the medic is stationary and facing the player. If you want the medic to keep facing
the player, `self lookat <player>` (or `lookat NULL` like the canteen routine) before the gesture.

---

## 5. Recommendation

**Best gesture: `pass_canteen_start` -> heal -> `pass_canteen_end`, played via `upperanim`.**
It is the exact motion the shipping game's medic uses, exists on this skeleton, auto-handles the
prop, and works on an active actor without disabling AI.

Drop-in for `coop_paradrop_medic` (medic already stopped next to the player):

```c
local.medic nodamage
local.medic upperanim pass_canteen_start
local.medic waittill upperanimdone
local.player heal 0.5            // or your coop HP-restore call
local.medic playsound med_kit
local.medic upperanim pass_canteen_end
local.medic waittill upperanimdone
local.medic takedamage
```

Minimal one-liner if you only want the offering motion:
`local.medic upperanim pass_canteen_start; local.medic waittill upperanimdone`
