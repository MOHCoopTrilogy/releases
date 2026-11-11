#!/usr/bin/env python3
"""eamusic - the European Assault interactive score's EVENT -> SEGMENT table, read from the level's own
SOUND/mus_ctrl.mpf (xDFP v5) on the player's PC. Our code; no disc data in it.

Layout (little-endian, decoded 2026-11-10 from the 1_11 file; offsets in bytes unless noted):
  0x0d u8 tracks, 0x0e u8 sections, 0x0f u8 events, 0x11 u8 vars, 0x12 u16 nodes
  0x14 u16 node table offset; 0x18 u32 node data; 0x1c u32 event table; 0x20 u32 event data;
  0x24 u32 var names; 0x34 u32 sample table (8 bytes each) ... 0x38 u32 eof
  node table: u16 per node, node offset / 4. node: u16 sample (1-based subsong; 0 = section entry, 0xffff = end,
    0xfffd = 'fire event' whose 3-byte hash follows), u16, u8 0, u8, u8 type, u8 branches, u8 owner (the entry node
    of its section; on entry/end nodes the section id), ..., branches as (u8 0, u8 0x7f, u16 next node) at the end
  event table: u16 per event, event offset / 4. event: 12 bytes 0, u24 hash, u8 action count, 4 bytes 0, then
    12-byte actions (u32 flags, u8 0, u8 op, u8 sub, u8 0, 4 bytes args). op 04 sub 03 (node, ff) plays a node now;
    op 04 sub 02 (var, ff) plays the node held in a variable (the 'go back' of a stinger); op 08 sub 0e (val, var)
    sets a variable; op 01 sub 9e / 01 sub 30 open and close an 'if var == val' block; op 05/02 sub 0c fade.

  python eamusic.py <mus_ctrl.mpf>        print the table
"""
import struct
import sys


def _u16(d, o):
    return struct.unpack_from("<H", d, o)[0]


def _u32(d, o):
    return struct.unpack_from("<I", d, o)[0]


def parse(d):
    if d[:4] != b"xDFP" or d[4] != 5:
        raise ValueError("not an xDFP v5 music map")
    n_nodes = _u16(d, 0x12)
    nt = _u16(d, 0x14)
    ev_tab, ev_end = _u32(d, 0x1c), _u32(d, 0x20)
    var_off = _u32(d, 0x24)
    n_ev = (ev_end - ev_tab) // 2
    noffs = [_u16(d, nt + 2 * i) * 4 for i in range(n_nodes)] + [ev_tab]
    nodes = []
    for i in range(n_nodes):
        b = d[noffs[i]:noffs[i + 1]]
        smp = _u16(b, 0)
        nxt = _u16(b, len(b) - 2) if len(b) >= 20 and b[-3] == 0x7f else None
        hsh = int.from_bytes(b[12:15], "little") if smp == 0xfffd else None
        nodes.append({"sample": smp, "next": nxt, "fires": hsh})
    eoffs = [_u16(d, ev_tab + 2 * i) * 4 for i in range(n_ev)] + [var_off]
    events = []
    for i in range(n_ev):
        o = eoffs[i]
        if eoffs[i + 1] <= o:
            eoffs[i + 1] = var_off            # the table's 0 terminator
        if o == 0 or o >= var_off or o + 20 > len(d):
            events.append({"hash": None, "acts": []})
            continue
        n = d[o + 15]
        acts = [(d[o + 25 + 12 * k], d[o + 26 + 12 * k], d[o + 28 + 12 * k], d[o + 30 + 12 * k]) for k in range(n)
                if o + 32 + 12 * k <= eoffs[i + 1]]
        events.append({"hash": int.from_bytes(d[o + 12:o + 15], "little"), "acts": acts})
    return nodes, events


def section(nodes, entry):
    """the samples an entry node plays: (intro, loop, end) - loop is the repeating tail ([] = plays once), end the
    hash of the event its last node fires (None = stops)"""
    seq, seen, k, fires = [], {}, nodes[entry]["next"], None
    while k is not None and k < len(nodes):
        if k in seen:
            i = seen[k]
            return [s for s in seq[:i]], [s for s in seq[i:]], None
        nd = nodes[k]
        if nd["sample"] in (0, 0xffff):
            if nd["sample"] == 0xffff and nd["next"] is not None and nd["next"] not in seen:
                k = nd["next"]          # an end node that branches back to its entry: the section repeats whole
                if k == entry:
                    return [], seq, None
                continue
            break
        if nd["sample"] == 0xfffd:
            fires = nd["fires"]
            break
        seen[k] = len(seq)
        seq.append(nd["sample"])
        k = nd["next"]
    return seq, [], fires


def table(d):
    """{event: {"node", "intro", "loop", "after"}} for every event that plays a literal node; after = "return" when
    the cue's closing event plays the node a variable saved (a stinger: the score goes back to what it played),
    "stop" otherwise"""
    nodes, events = parse(d)
    by_hash = {e["hash"]: e for e in events if e["hash"] is not None}
    out = {}
    for i, e in enumerate(events):
        play = [a for a in e["acts"] if a[0] == 0x04 and a[1] == 0x03]
        if not play:
            continue
        node = play[-1][2]
        if node >= len(nodes) or nodes[node]["sample"] != 0:
            continue
        intro, loop, fires = section(nodes, node)
        after = "stop"
        if fires is not None and fires in by_hash:
            if any(a[0] == 0x04 and a[1] == 0x02 for a in by_hash[fires]["acts"]):
                after = "return"
        out[i] = {"node": node, "intro": intro, "loop": loop, "after": after}
    return out


if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        t = table(f.read())
    for e in sorted(t):
        print(e, t[e])
