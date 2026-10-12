# Video-memory readout: where each number comes from, on any PC (2026-10-12)

User: "on by default, assuming it is smart enough to detect the video card, vram and usage for anyone. If it
can't it needs to be able to." Code: `openmohaa-hzm/code/renderergl2/tr_hzm_vram.c` + `tr_hzm_vram_pick.h`
(engine `small-next`). **The default is still OFF** (`HZM_VRAMBAR_AUTO 0`) until the look is chosen.

## 1. The source chain

Each number has its own chain. The first source that answers wins; a number no source can give is left out and
the line says so. Nothing is estimated.

| Number | 1st | 2nd | 3rd | nothing answers |
|---|---|---|---|---|
| This game | our own count (walk over the renderer's tables). P2.0: within 1.3 % of the per-process GPU counter on 10 maps | - | - | cannot happen |
| Which adapter | GL device LUID (`GL_EXT_memory_object_win32`) = a DXGI adapter's LUID | best match of `GL_RENDERER` against the DXGI adapter names, within `GL_VENDOR`'s vendor | the only adapter of that vendor / the only hardware adapter | name = `GL_RENDERER`; nothing per-adapter is shown |
| Card name | DXGI adapter description | `GL_RENDERER` (cut at the first `/`) | - | - |
| Scale of the bar | card with its own memory (>= 512 MB dedicated): DXGI `DedicatedVideoMemory`. Integrated chip: the Windows budget, else DXGI dedicated + shared | no DXGI adapter: NVX total (NVIDIA) | registry `HardwareInformation.qwMemorySize` of the display-class entry whose name matches `GL_RENDERER` | no bar; the lines still show |
| The limit | `IDXGIAdapter3::QueryVideoMemoryInfo` budget, local segment (Windows 10+, any vendor) | - | - | no marker; the line names the card size (`CARD 16 GB`) or the shared memory (`RAM 7.9 GB`) |
| Other programs | Windows GPU counter of the adapter's LUID (dedicated usage; shared usage for an integrated chip) minus this process (DXGI usage, else our count) | NVX: total - available - our count | AMD `GL_ATI_meminfo`: scale - free - our count | segment not drawn, line reads `OTHER n/a` |

Rules on top:
- **The software adapter is never picked** (Microsoft Basic Render Driver).
- **One card listed several times** (`same-card`): virtual-display drivers list the card again under their own
  LUID. Without the GL LUID the first listing is taken for the card's size only; budget and counters (kept per
  LUID) are not used.
- **A guess** (`largest`: two different cards nothing tells apart) never shows shared memory, budget or counters.
- **Never on the render thread:** DXGI and the counter library are opened and polled on a worker thread; the
  render thread signals it and reads its last answer. A worker that never answers leaves the game's own number.

## 2. Every path this PC can take

One boot per row (m3l2, 1280x720, renderer 9b6286c5's successor - see the report for the md5), sources removed
with the test cvar `r_vramDebugNo`, or another DXGI adapter forced with `r_vramDebugAdapter`. "Outside" = the
Windows counters read by PowerShell for the test client's own process id at the same moment.
Stills: `detect_<path>.jpg` in this folder (look A).

| Path | What the chain returned | What the panel showed | Outside (process / other) | Publish cost, render thread | Worker open |
|---|---|---|---|---|---|
| full | dxgi + budget + counters, adapter by **luid** | GAME 1.2 GB / OTHER 7.5 GB / LIMIT 15 GB | 1205 MB / 7614 MB (panel 1237 / 7729) | 159-241 us | 188 ms |
| noluid (driver without the LUID extension) | dxgi + nvx, adapter **same-card** (this PC lists the RTX 3 times) | GAME 1.2 GB / OTHER 7.6 GB / CARD 16 GB | 1205 / 7506 (panel 7770) | 300-360 us | 187 ms |
| nobudget (Windows 7/8, old driver) | dxgi + counters | GAME 1.2 GB / OTHER 5.0 GB / CARD 16 GB | 1205 / 5103 (panel 5082) | 175 us | 172 ms |
| nocounters (counters off / denied) | dxgi + budget + nvx | GAME 1.2 GB / OTHER 6.5 GB / LIMIT 15 GB | 1205 / 6436 (panel 6685) | 160 us | 16 ms |
| nocounters_nonvx | dxgi + budget | GAME 1.2 GB / OTHER n/a / LIMIT 15 GB | - | 140 us | 16 ms |
| nodxgi | nvx-total + nvx, name from GL | GAME 1.2 GB / OTHER 6.5 GB / CARD 16 GB | 1205 / 6444 (panel 6693) | 156-205 us | 0 ms |
| nodxgi_nonvx | registry | GAME 1.2 GB / OTHER n/a / CARD 16 GB | - | 141-161 us | 0 ms |
| nothing | count-only | GAME 1.2 GB / OTHER n/a / (no third line, no lamps) | - | 150-246 us | 0 ms |
| virtualdup (forced onto the 2nd listing of the card) | dxgi + budget + nvx (that LUID has no counter instance) | GAME 1.2 GB / OTHER 7.0 GB / LIMIT 15 GB | 1207 / 6916 (panel 7168) | 179-250 us | 157 ms |
| software (forced onto Microsoft's software adapter: 0 MB dedicated, the integrated-chip shape) | dxgi + budget + counters, scale = the budget | GAME 1.2 GB / OTHER 0.0 GB / LIMIT 15 GB | - | 159-234 us | 140 ms |

Reading the table:
- The counter path agrees with the outside reading to within 2 % (7729 vs 7614; 5082 vs 5103 - the two are
  sampled a moment apart while other clients run).
- **NVX over-reads "other" by about 250 MB (4 %)** on this card: it counts memory the driver holds for itself.
- A publish costs the render thread 0.14-0.36 ms, at most twice a second, only while the panel is open. The first
  open is no different from any other (138-300 us). Opening DXGI and the counters took up to 188 ms - on the worker.
- Menu closed: no publish at all (counted earlier: 0 in 12 s; open: 12 in 6 s).

## 3. Machines we do not own: the adapter match as unit cases

`docs/tools/vram_pick_selftest` compiles `tr_hzm_vram_pick.h` unchanged and feeds it recorded adapter lists.
16 of 16 pass:

NVIDIA desktop with and without the LUID extension; AMD desktop (two driver namings); Intel UHD laptop (128 MB
dedicated, shared memory only); hybrid laptop with the game on the NVIDIA card, on the integrated chip, and with
the LUID naming the integrated chip although the card is bigger; AMD APU beside an AMD card (same vendor id) with
the game on either; a renderer string that names nothing (vendor decides); an unknown vendor; only Microsoft's
software adapter (nothing is picked); one card listed three times (this PC) with and without the LUID; two
different cards nothing tells apart (a flagged guess).

## 4. Not proven without other hardware

- **AMD**: `GL_ATI_meminfo` never ran (the extension does not exist on NVIDIA). The DXGI + counter path is
  vendor-neutral and is what an AMD card with a current driver takes; the ATI path is the fallback behind it.
- **Intel integrated / a real hybrid laptop**: the shared-memory path ran only against Microsoft's software
  adapter. Whether an Intel driver reports the budget and the "Shared Usage" counter the way this code expects is
  untested, as is which adapter a real hybrid laptop's GL context lands on.
- **Windows 10 vs 11, Windows 7/8, Wine / Proton, a remote session**: only this Windows 11 PC ran. Their failures
  were simulated by removing sources, not by running there. Under Wine the DXGI calls may succeed and return
  Wine's own idea of the adapter.
- **A hung counter library**: the worker is terminated after 3 s at shutdown by design; never exercised.
- The numbers a tester's PC produced arrive in the bug report (`report_info.txt`, graphics section:
  `r_vramAdapter`, `r_vramHow`, `r_vramSource`, `r_vramGameMB`, `r_vramOtherMB`, `r_vramCardMB`, `r_vramBudgetMB`).
