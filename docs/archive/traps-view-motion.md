# Procedural view/weapon motion - the six rules

*Moved out of `docs/TRAPS.md` on 2026-09-01 to keep that file inside its ceiling. Read this before
touching view bob, weapon sway, recoil, lean, the ADS transform, or any other code that writes
`cg.refdef` / the view-model transform.*

Each survived review, a clean build and a deploy, and was caught only by the user playing.

**1. Never compute an oscillator's phase as `time * frequency`. Integrate it.**

```c
ph = cg.time * 0.001f * (4.0f + fSpeed * 0.012f);   // WRONG
s_phase += fDt * (4.0f + fSpeed * 0.012f);          // right
```
When a frequency multiplying elapsed time changes, the phase jumps by `elapsed * delta_frequency` -
and elapsed only grows, so it worsens the longer the map runs. Five minutes in, a ONE-unit speed change
displaced the footfall bob by 3.6 radians in a frame; player speed changes every frame, so the bob
teleported around the sine continuously. Idle breathing had the same bug keyed on health. (bug-1983)

**2. Never write a periodic term into a state variable that an exponential ease is tracking.**

An ease `x += (target - x) * k` OWNS `x`. Adding a sine into it fails three ways at once: the ease fights
the tremor as signal; an entry gate `|x| > eps` is held true BY the tremor so it never stops; and the
return-to-rest snap `|x| < eps` never fires. Result: a permanent ~2.75 Hz CAMERA tremor lasting until map
change - and because it rode the camera it made ADS, weapon handling and walking all look broken, sending
three diagnoses the wrong way first.

**The fix pattern for both:** separate STATE from OUTPUT. Ease only an *amplitude*; recompute the
oscillation statelessly at apply time from fixed frequencies. Gate on an external condition (is the
animation live?), never on the magnitude of the value the oscillator itself feeds. (bug-1984)

**3. A cap expressed as a multiple of the thing it caps is not a cap.** The sustained-fire recoil ceiling
was `6 x the per-shot kick`, so it scaled with every factor the kick did and reached 6.1u on an MG - half
of it straight back into the near plane, putting the gun through the camera. **Ceilings on a physical
displacement belong in world units**, and a component that can reach the eye needs its own saturation
separate from the total. (bug-1985)

**4. A shared budget that uniformly scales its members makes every control inside it non-linear, and past
saturation, INERT.** The viewmodel feel budget clamps the summed offset to 9u and scales every layer to
fit. The idle inspect wrote raise/pull/centre into it without registering as an authored stow, asking
~9.4u by itself while sharing 9u with breathing, sway, bob and mass lag. Turning `coop_inspectCentre` UP
raised the total, raised the scale-down factor and cancelled the gain - the control genuinely did nothing.
**When a user says "adjusting X has no effect", suspect a clamp before suspecting the value.** A
deliberate large pose must be registered in the budget's exemption (`s_vFeelExempt`), as the medkit stow,
collision retract and DBNO eye drop already are. Exempt only what must be large. (bug-2016)

**5. Never low-pass the pose-to-camera alignment term.** `CG_OffsetFirstPersonView` places the viewmodel with
`vDelta = camera - (lerpOrigin + eyesBone(pose))`. That is camera motion PLUS whatever the current animation does to
the eyes bone, and animations move it a lot: the retail StG 44 idle keys the skeleton root 52u up, while its fire,
reload and ADS clips do not. An engine scan of all 658 fps anims found 18 weapon sets with 50-65u eye steps between
clips. Vanilla hands the alignment over rigidly each frame, so none of this is ever visible. `coop_weaponMass`
low-passed the whole `vDelta` and smeared each step into an ~18u, ~200 ms pop of the arms: the StG "weight" pop and
the residue of the "STG44 ADS jolt". Filter only `camera - lerpOrigin`; apply the eye offset rigidly. More
generally: before smoothing a quantity, split out any term that is a coordinate-frame alignment, because it can be
discontinuous by design. (bug-3207; staged docs/proposals/stg44_viewmodel_2026-09-28)

**6. A per-class constant tuned on one geometry is not a feel - measure what reaches the screen.** Aimed fire holds
the static `charge` pose for EVERY gun (player_Torso.st `ATTACK_*_PRIMARY_AIM`; the `<gun>_adsfire` aliases are dead,
bug-074 - not "the hip fire clip", as the ironsights README s7 says), so the ADS kick is 100% the procedural recoil
layer. That layer turns the rig about the GRIP: right for a shouldered rifle whose front sight is 40u out, nearly
invisible for a pistol whose sights sit over the grip at arm's length - one aimed Colt shot moved its sights 0.3-0.6
deg for ~3 frames against a Garand's 1.5-2.8 deg over 430 ms, and every pistol got the identical kick. Judge a kick by
the on-screen motion of F/R/G (the ADSFRAME trace), per gun, never by the degrees fed in. (bug-3262; staged
docs/proposals/pistol_ads_recoil_2026-09-29)

**Related, same family:** the reverted ragdoll torso-twist limit (bug-1981) pumped rotational energy
because a correction moved `pt` without `ptPrev` - in Verlet, velocity IS `pt - ptPrev`. Same underlying
error: mutating state another integrator owns.
