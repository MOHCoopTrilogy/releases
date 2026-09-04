# T8 - server->client stufftext is a lossy, filtered channel

*Moved out of `docs/TRAPS.md` on 2026-09-01 to keep that file inside its ceiling. Read this before
sending anything from the server to a client: a stufftext, a cvar push, a name-bus command, or a
`.urc` widget that a cvar drives.*

**Bugs:** 595, 597, 736, 758, 772, 773, 1364, 1365.

1. **Quote truncation** - `Player::EventStuffText` sends `stufftext "<cmd>"`, so an embedded quote ends
   the wire argument early; tell is client-side `Cvar ... does not exist` spam. **Send values UNQUOTED,
   ONE statement per stufftext**; `;`-joined multi-statements are the other half. (bug-736, bug-758)
2. **The whitelist** - `cg_servercmds_filter.cpp:304-316` silently drops server-stuffed `exec` and `vstr`
   as Reborn-exploit protection, which ate the **entire coop-detect handshake**
   (`coop_mod/cfg/detect.cfg`), the objectives setup and the armory pick carry-over, presenting as
   **three unrelated bugs**. Fixed with scoped exemptions: exec only for mod-namespaced paths, vstr only
   for `coop_*`/user-created cvars. (bug-597)
   **A plain `set <cvar>` is filtered the same way, invisibly.** Stuff two cvars with only one listed
   and the listed half still works, so it reads as a *logic* bug: the 3-mode view cycle set
   `cg_3rd_person` (listed) + `cg_freecam` (not), so first person worked, free-cam and chase were
   identical, and archived `cg_freecam` was unclearable. **Symptom → check the list:** one mode of a
   multi-mode client feature works, the rest collapse together. (bug-1991)
3. **Whitespace collapse** - `Cvar_Set_f` (`cvar.c:936`) takes its value from `Cmd_ArgsFrom(2)`, which
   re-joins *tokenised* args with a single space. Multi-word values survive unquoted (why the
   `coop_so1`/`coop_cp1` HUD pushes work), but **any run of whitespace normalises to one space** - never
   pad with spaces to align columns; use a visible separator. (bug-1364)
4. **An undispatchable token** - a bare name-bus token with no data character makes `playerExtract`
   return NIL. (bug-772)
5. **Client `exec`/`vstr` INSERT at the buffer front; only stufftext APPENDS.** `Cmd_Exec_f`/`Cmd_Vstr_f`
   call `Cbuf_InsertText` (`cmd.c`), so a click's whole cfg chain runs depth-first, atomically, in textual
   order, and **the LAST textual line in a client chain wins** (`s<n>sel.cfg` corrects `coop_loMvPN` on its
   final line *because of* insert semantics - do not move it earlier). Server stufftext arrives frames
   later over the wire (`Cbuf_AddText`), always after the client's chain, so a server echo races the next
   click by a round trip and can revert a preview. Any comment claiming exec APPENDS is wrong.
6. **The name bus dispatches ONE token per ~0.75 s batch; every other stacked token is destroyed.**
   `playerNameCommand` breaks at the FIRST token with data and `playerCleanName` truncates at the first
   `" ,"`. Priority is **BUS INDEX order, not click order** (skin 31 > helmet 35 > weapons 42-45 > menu
   46 > pins 47 > finishes 48-51), so rapid armory clicking silently drops actions - helmets/skins got
   close-time commit replays for this (bug-773); weapons/finishes have none. A new bus feature must
   tolerate drops (archived-`seta` + join replay) or add a close-commit.

**Related silent loss, receiving end:** a `.urc` widget placed below its menu's declared canvas height
**draws nothing at all** - `UIWidget::CalcClippedFrame` (`uilib/uiwidget.cpp:872`) clamps a child to its
parent's frame, so the height goes to 0. No error, no console line; the cvar push works and the row is
just absent. Set `noparentclip` (`WF_DIRECTED`, `uiwidget.cpp:1496`) or grow the canvas - prefer growing
it. **Check the menu's declared size before adding rows to any panel.** (bug-1365)

**⚠️ Remote clients need the updated `cgame.dll` too.** Server-stuffed SETs of `CVAR_ARCHIVE` cvars are
dropped by `CG_IsSetVariableAllowed` unless whitelisted - see [T3](#t3).

---

<a name="t9"></a>
