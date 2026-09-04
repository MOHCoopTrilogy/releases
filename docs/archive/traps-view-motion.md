# Procedural view/weapon motion - the four rules

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

**Related, same family:** the reverted ragdoll torso-twist limit (bug-1981) pumped rotational energy
because a correction moved `pt` without `ptPrev` - in Verlet, velocity IS `pt - ptPrev`. Same underlying
error: mutating state another integrator owns.
