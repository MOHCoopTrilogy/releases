# Surgical Operation — version hunt (is 2.0+ obtainable?)

**Date:** 2026-08-08
**Question:** Does a downloadable release of *Surgical Operation HD* at version **2.0 or higher** exist anywhere?
**Answer:** **No.** Nothing above **1.0** has ever been published to a public host. Versions 2.0 through
5.4 are real and finished, but the author distributes them **privately, by WeChat, for a fee**.
The highest publicly obtainable build is **1.0** — and, contrary to the earlier note in
`surgical_operation_hd_analysis.md`, a **real 2.9 GB 1.0 is alive** on gamepressure/gry-online.

Companion doc: `surgical_operation_hd_analysis.md` (analysis of the 0.1a payload).

---

## 1. Bottom line

| Version | Exists? | Publicly downloadable? | Evidence |
|---|---|---|---|
| 0.1a (2016) | yes | **yes** — ModDB, `so2.zip` | already analysed |
| 1.0 (Jul 2017) | yes | **yes** — gamepressure / gry-online, 2907.4 MB | verified live, see §2 |
| 2.0 (announced Jul 2020) | superseded | no | announcement only, never shipped |
| 3.0 (Mar 2021) | yes | no | Bilibili `BV1yh411S7yH`, 2021-03-23 |
| 4.0 (~2021/22) | yes | no | Bilibili videos; Tieba thread `p/7650445258` ("60余种枪械"); ModDB comment begging for it |
| 5.0 / 5.1 (2023) | yes | no | author's own videos, incl. ModDB upload |
| 5.3 (2024) | yes | no | author's Bilibili, ~100 weapons |
| **5.4 (2025)** | yes — **current** | **no** | ~130 weapons + 25-level custom campaign |

**2.0 was never released as a discrete version.** It was announced in Jul 2020 and then rolled
forward into the 3/4/5 line, which was never published anywhere.

### The author says so himself

The decisive evidence is fukun's own statement on Baidu Tieba (荣誉勋章吧, thread `p/7650445258`):

> 2017年本人发过自己制作的三部曲高清重制版1.0模组，**后续的所有版本本人都没发过**，
> 其实在业余时间里一直没有放弃对这款游戏的改良和研究。
>
> *"In 2017 I released my self-made trilogy HD remaster 1.0 mod; **I have never released any of the
> subsequent versions.** In fact I have never given up improving and researching this game in my
> spare time."*

**Verification caveat:** this text was recovered from search-engine snippets, consistent across
three independent queries. Baidu Tieba returns HTTP 403 / a 百度安全验证 challenge to direct
fetches and to every proxy tried, so the thread body could not be read first-hand.

He had also promised a public 3.0 release in Mar 2021 (`BV1yh411S7yH`: 「这个系列视频做完我会放出下载」
— *"I'll put out the download once this video series is finished"*). It never came.

---

## 2. The one real find: 1.0 is alive (2907.4 MB)

The ModDB "full version 1.0" entry is a **242-byte link stub**, as previously established:

- Filename `Surgical_operation1.0_download_link.zip`, 242 bytes,
  MD5 `8476f64864d02b0e764d94c193a5cf21`, uploaded Jul 29 2017, 6,070 downloads.
- Its Baidu link is dead; both MEGA mirrors are dead (see §3).

But a Polish file host mirrored the **actual** 1.0 payload in Sept 2017 and still serves it:

| Field | Value |
|---|---|
| **URL (EN)** | https://www.gamepressure.com/download/medal-of-honor-allied-assault-surgical-operations-v10-mod/z1fafd |
| **URL (PL, same file)** | https://www.gry-online.pl/download/medal-of-honor-allied-assault-surgical-operations-v10-mod/z1fafd |
| Legacy redirect | `gamepressure.com/download.asp?ID=64253` → 200, redirects to the above |
| **File size** | **2907.4 MB** |
| Last update | September 29, 2017 |
| Downloads | 9.4K total, **7 in the last 7 days** |
| Delivery | self-hosted; `POST` form (`#DOWNLOAD_FORM`) behind a "DOWNLOAD" button — no login, no captcha seen |

**Verification status: page verified live by me** (HTTP 200 on both domains; size, date and counters
read off the live DOM). **The file transfer itself was not initiated** — per instructions, nothing was
downloaded. The "7 downloads in the last 7 days" counter is good evidence the file still serves.

**Corroboration from the mod's own comment thread** (independent users, 2021):
- `methoz84`, Jan 2021 — "You can download it from this polish site - Gry-online.pl"
- `grossmarschall`, Aug 2021 — links `gamepressure.com/download.asp?ID=64253`

Note the size discrepancy is expected: 2.9 GB is the real 1.0 payload, whereas ModDB's own file
statistics for the uploader total only 960.88 MB across 3 files (because the 1.0 entry is a stub).
**0.1a (925.2 MB) is the only build ModDB genuinely hosts itself.**

---

## 3. Dead links (do not chase)

| Link | Status |
|---|---|
| `mega.nz/#!l5UERaRJ!7KvMwQhChi_vDUvyO_byc9Sr329IK20hluKdhtpsnDY` (FeRu's 1.0 mirror, the one the author himself linked in his Aug 2017 news post) | **DEAD** — MEGA API returns `-16` (administratively blocked). Users reported "File deleted" in Aug 2021. |
| `mega.nz/file/DWJD3YiY#q0OY-WJ3xujbUlgYZEJ79M9hQ_lqvW5mFFIJBSvprAc` (Kelmith's Sep 2021 re-upload) | **DEAD** — MEGA API returns `-16`. |
| Baidu Pan link inside the 242-byte ModDB stub | dead (previously established) |
| `mega.nz/file/A75zlShT#7KvMwQhChi_vDUvyO_byc9Sr329IK20hluKdhtpsnDY` — in the description of **all 9** videos in SturmFuhrer PK's YouTube playlist (Jul–Aug 2020) | **DEAD** — MEGA API `-9` (ENOENT, node gone; matches a bogus-handle control). Also **not 2.0**: its decryption key is byte-identical to fukun's official 1.0 link, so it is a re-upload of the same 1.0 archive. The Jul-2020 date is coincidental with the 2.0 announcement. |
| mohaaaa.co.uk | **no results at all** for "surgical operation" — site searched directly, zero hits |
| archive.org (item search) | **nothing** — `q="surgical operation" AND (mohaa OR "medal of honor")` → `numFound: 0`. No copy of the mod was ever uploaded. |
| Wayback CDX sweep of `moddb.com/mods/surgical-operation-hd*` (500+ rows) | Exactly **two** file pages have ever existed: 0.1a (first seen 2016-08-14) and 1.0 (2017-10-06). **No trace of a removed 2.0+ file entry.** |
| 3DM / Gamersky / 游侠 / xmodo.cn | no Surgical Operation entry on any of them |
| ModDB — any file above 1.0 | does not exist; `fukun` has uploaded exactly **3 files** ever, none above 1.0 |
| gamepressure — any version above 1.0 | does not exist; only the v1.0 entry among 26 MOHAA files |
| Steam release (promised Dec 2021) | never happened — MOHAA is not on Steam, as a commenter pointed out |

Both MEGA checks were done via MEGA's own metadata API (`a:g` status query), not a download.

---

## 4. Why 2.0+ is not obtainable: the author's distribution model

**Author:** ModDB handle **`fukun`** (joined Jun 2013, **last online Aug 4 2026** — still active).
**Bilibili:** **法外狂鹏**, uid **212941462** (66 videos).
**WeChat ID:** `keep_real_kun` — stated by the author himself.

The decisive evidence is in the author's own Bilibili video description for 5.3
(`BV12m421V7EF`, 2024-06-20), which ends:

> 欢迎➕vx来获取我的模组：keep_real_kun
> *("Welcome to add me on WeChat to obtain my mod: keep_real_kun")*

That is the **only** distribution channel he advertises. There is no public mirror, no Baidu link,
no patreon/afdian page found. A ModDB commenter (`edu123xd`, Feb 2026) independently reports:

> "I contacted the mod owner, but he charges **$6** to download the mod."

**Caveat on the $6:** this price appears only in that one ModDB comment. It could **not** be
corroborated from any Chinese-language source — no 爱发电 / 微店 / Taobao / QQ-group listing for this
author exists in any reachable index. The only acquisition route he states anywhere is the WeChat ID.

The same commenter (Mar 2026) confirms the same WeChat ID. Another user notes he could not even register for
WeChat (QR-code requirement). A Turkish user in Mar 2026 was still trying to buy a copy.

So: **2.0+ is a paid, person-to-person, WeChat-gated distribution.** Not a public download.

---

## 5. Version ladder, from the author's own uploads

Recovered from Bilibili (`recArchivesByKeywords` API against uid 212941462) — these are the
author's *own* videos, so they are direct evidence the builds exist:

- **4.0** — 2022-ish. Weapon showcases (pistols, SMGs).
  Corroborated by a Sep 2022 comment on fukun's ModDB profile:
  「请问能否放出4.0的下载呢？」 *("Could you please release the 4.0 download?")* — never answered.
- **5.0** — Jul–Nov 2023. Weapon showcases across all three games (Allied Assault / Spearhead /
  Breakthrough). fukun also uploaded a **video to ModDB itself** on Oct 31 2023 titled
  *"Surgical Operation5.0(mohaa part)all smgs"* — hard proof 5.0 was built.
- **5.1** — Oct/Nov 2023. **Includes 联机合作战役 (online co-op campaign) showcases**
  (`BV1Lw41167tH`, `BV1Wu4y1a7YY`) — "enemies have new weapons, all pickable; new textures, gore
  effects, weapon sounds, models; enemy AI adjusted and counts greatly increased."
- **5.3** — May–Jun 2024. ~100 weapons, new campaigns (Norway, German port, etc.).
- **5.4** — May–Jun 2025. **Current.** Per his own description: *"~10 years of solo work; 5.4 has
  nearly **130 guns**, different enemy AI, gameplay and visual effects"*, plus a brand-new
  **25-level custom campaign 《欧洲战火》 ("Fires of Europe")** playable as US / Soviet / British /
  German forces. 24+ level-by-level videos posted. He also claims to have pulled *Soldier of
  Fortune II* engine code into it (unverified claim, from a Tieba snippet).
- **Since Apr 2026** the author has moved on to a different project: a **Unreal Engine 4 remake of
  the original Medal of Honor** (`荣誉勋章初代UE4引擎重置版`). Surgical Operation appears finished
  and parked.

---

## 6. The 2.0 roster (for the record)

From the Jul 11 2020 ModDB news post *"2.0 is incoming…"* — announced content, never shipped as 2.0:

> *remodel all weapons (almost) · retexture and reshader (RTCW VenomMOD-like reflections) ·
> ADD new weapons like FG42, nambu · retexture all game*

Named guns: **FG42** (a weapon cut from MOHAA SP), **L42A1**, **Luger P08**, **Breda 30**,
**SVT-40**, **Delisle**, **Nambu**. This matches the 7-gun roster noted in the 0.1a materials.
The Dec 2021 follow-up posts claim the mod was by then **finished with 60 guns** and would be
released **free on Steam** — which never happened.

---

## 7. Leads a human could still follow

Ranked by plausibility. None of these are things I can or should do unattended.

1. **Buy it from the author.** WeChat `keep_real_kun`, ~$6. This is the only channel that
   demonstrably works — but WeChat registration requires an existing user to scan a QR code, which
   is the wall other people hit. Requires a WeChat account and Chinese-language contact.
2. **Message `fukun` on ModDB.** He was **online 4 days ago (Aug 4 2026)** and has replied to
   comments historically. https://www.moddb.com/members/fukun — "Send Message". Worth asking
   directly whether he'll share or sell a 5.4 build. Cheapest lead by far.
3. **Ask `edu123xd` on ModDB** (109 comments, active Jun 2026) — he says he has the mod creator's
   contact and has dealt with him. He explicitly declined to reupload publicly, but may broker.
4. **Bilibili DM** to 法外狂鹏 (uid 212941462) — requires a Bilibili account.
5. **Note on `Soares93`** — fukun's ModDB friend and a fellow MOHAA weapons modder; the project
   already tracks his Extra WW2 Weapons pack. Some 2.0 weapon models may overlap with assets that
   are separately obtainable through Soares93 rather than through Surgical Operation at all.

---

## 7b. Decoys — things that look like a find but are not

- **ali213 「荣誉勋章三部曲重制版 v1.0」, 2.59 GB** (`3g.ali213.net/down/mote31.html`) — a torrent repack
  of the **base trilogy**, not Surgical Operation. Ignore.
- **Bilibili `av411834118`** ("五部荣誉勋章系列精品合集") — five 夸克网盘 links, but they are pirated
  **base games** (Pacific Assault, Airborne, MOH 2010…), no mod.
- **`xmodo.cn/zh/game-categories/game-details/1410`** — page states 该游戏暂未启动MOD. Empty.
- **The SturmFuhrer PK YouTube playlist "+ Link"** — the link is 1.0, and it is dead (see §3).
- **ModDB's own 1.0 "Download Now" button** — yields a 242-byte zip containing a dead Baidu link.

## 8. Relevance to this project

- The **1.0 payload (2.9 GB)** is obtainable now if the user wants MOHAA HD textures / weapon
  models / effects to study. Licensing is unclear — the mod itself bundles third-party work
  (Marcomix's weapon models and textures are credited).
- **5.1+ has its own co-op campaign mode.** If Surgical Operation ships a co-op implementation,
  that is a directly competing/parallel effort to HZM coop and would be interesting to inspect —
  but only 1.0 (which predates it) is actually obtainable.
- The 2.0 roster gun list (FG42, SVT-40, Breda 30, Luger P08, Delisle, L42A1, Nambu) overlaps
  heavily with guns this project already ships via the Extra WW2 Weapons import.

---

## 9. Method / verification notes

- moddb.com returns HTTP 403 to `WebFetch`; all ModDB reads were done through the browser pane.
- MEGA link status checked via `POST https://g.api.mega.co.nz/cs` with `[{"a":"g","p":"<handle>"}]`
  — returns `-16` for both mirrors. This is a metadata query; **no file data was transferred**.
- Bilibili video/uploader data via `api.bilibili.com/x/web-interface/view` and
  `api.bilibili.com/x/series/recArchivesByKeywords`. The `space/arc/search` endpoint needs WBI
  signing and returned `-799`; `recArchivesByKeywords` is unsigned and returned the full list.
- **Nothing was downloaded.** Only web pages and JSON metadata endpoints were read.
