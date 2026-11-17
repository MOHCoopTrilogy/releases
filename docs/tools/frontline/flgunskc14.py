"""[flguns] copy of docs/proposals/ironsights_2026-09-28/tools/skc14.py for the converter bundle. SKC v14 ("processed" Breakthrough animation) reader - pistolsB batch addition, NOT a shared tool.

The shared skdlib.read_skc only reads raw SKC v13. Breakthrough's own weapons (e.g. maintt/pak1.pk3
models/weapons/Beretta/It_W_Beretta.skc) ship v14: after "SKAN" + version the body is a Quake3 msg_t
bitstream, Huffman-coded with the static msg_hData table (qcommon/msg.cpp MSG_initHuffman) and read by
skeletor_c::LoadProcessedAnimEx + ReadEncodedFramesEx (openmohaa-hzm/code/skeletor/skeletor_loadanimation.cpp).
This is a straight port of qcommon/huffman.cpp (adaptive tree built by Huff_addRef over msg_hData) and of those
two readers. read_skc14(data) returns an object compatible with skdlib.Skc for gungeo: .channels, .numFrames,
and skc_channel14(a, frame, i) -> 4 floats (value at that frame: RLE channels hold the last key <= frame).
"""
import os, re, struct, pickle

HMAX = 256
NYT = HMAX
INTERNAL = HMAX + 1
import sys
_HERE = os.path.dirname(os.path.abspath(getattr(sys, '_MEIPASS', None) or __file__))


class Node:
    __slots__ = ('left', 'right', 'parent', 'next', 'prev', 'head', 'weight', 'symbol')

    def __init__(self):
        self.left = self.right = self.parent = self.next = self.prev = self.head = None
        self.weight = 0
        self.symbol = 0


class Huff:
    def __init__(self):
        n = Node(); n.symbol = NYT; n.weight = 0
        self.tree = self.lhead = n
        self.loc = [None] * (HMAX + 1)
        self.loc[NYT] = n

    def swap(self, n1, n2):
        p1, p2 = n1.parent, n2.parent
        if p1:
            if p1.left is n1: p1.left = n2
            else: p1.right = n2
        else:
            self.tree = n2
        if p2:
            if p2.left is n2: p2.left = n1
            else: p2.right = n1
        else:
            self.tree = n1
        n1.parent = p2; n2.parent = p1

    @staticmethod
    def swaplist(n1, n2):
        p = n1.next; n1.next = n2.next; n2.next = p
        p = n1.prev; n1.prev = n2.prev; n2.prev = p
        if n1.next is n1: n1.next = n2
        if n2.next is n2: n2.next = n1
        if n1.next: n1.next.prev = n1
        if n2.next: n2.next.prev = n2
        if n1.prev: n1.prev.next = n1
        if n2.prev: n2.prev.next = n2

    def increment(self, node):
        while node is not None:
            if node.next is not None and node.next.weight == node.weight:
                ln = node.head[0]
                if ln is not node.parent:
                    self.swap(ln, node)
                self.swaplist(ln, node)
            if node.prev is not None and node.prev.weight == node.weight:
                node.head[0] = node.prev
            else:
                node.head[0] = None          # cell freed (Python: just dropped)
            node.weight += 1
            if node.next is not None and node.next.weight == node.weight:
                node.head = node.next.head
            else:
                node.head = [node]
            if node.parent is not None:
                # C recursion: increment(parent) THEN the list fix-up below; emulate with an explicit stack
                par = node.parent
                self.increment(par)
                if node.prev is par:
                    self.swaplist(node, par)
                    if node.head[0] is node:
                        node.head[0] = par
            return

    def add_ref(self, ch):
        if self.loc[ch] is None:
            t = Node(); t2 = Node()
            lh = self.lhead
            t2.symbol = INTERNAL; t2.weight = 1
            t2.next = lh.next
            if lh.next is not None:
                lh.next.prev = t2
                if lh.next.weight == 1:
                    t2.head = lh.next.head
                else:
                    t2.head = [t2]
            else:
                t2.head = [t2]
            lh.next = t2; t2.prev = lh
            t.symbol = ch; t.weight = 1
            t.next = lh.next
            if lh.next is not None:
                lh.next.prev = t
                if lh.next.weight == 1:
                    t.head = lh.next.head
                else:
                    t.head = [t2]
            else:
                t.head = [t]
            lh.next = t; t.prev = lh
            t.left = t.right = None
            if lh.parent is not None:
                if lh.parent.left is lh: lh.parent.left = t2
                else: lh.parent.right = t2
            else:
                self.tree = t2
            t2.right = t; t2.left = lh
            t2.parent = lh.parent
            lh.parent = t.parent = t2
            self.loc[ch] = t
            self.increment(t2.parent)
        else:
            self.increment(self.loc[ch])


def hdata():
    src = os.path.join(_HERE, 'flgun_msg_hdata.txt')
    txt = open(src).read()
    vals = [int(x) for x in re.findall(r'\d+', txt.split('{', 1)[1].split('}', 1)[0])]
    assert len(vals) == 256, len(vals)
    return vals


_TREE = None


def decode_tree():
    """Flatten the decompressor tree to (left, right, symbol) arrays; cached on disk (building takes a while)."""
    global _TREE
    if _TREE is not None:
        return _TREE
    cache = os.path.join(os.environ.get('TEMP', _HERE), 'flgun_skc14_hufftree.pkl')
    if os.path.exists(cache):
        _TREE = pickle.load(open(cache, 'rb'))
        return _TREE
    import sys
    sys.setrecursionlimit(100000)
    h = Huff()
    for i, n in enumerate(hdata()):
        for _ in range(n):
            h.add_ref(i)
    ids = {}
    order = []
    stack = [h.tree]
    while stack:
        n = stack.pop()
        ids[id(n)] = len(order); order.append(n)
        if n.symbol == INTERNAL:
            stack += [n.left, n.right]
    L = [ids[id(n.left)] if n.symbol == INTERNAL else -1 for n in order]
    R = [ids[id(n.right)] if n.symbol == INTERNAL else -1 for n in order]
    S = [n.symbol for n in order]
    _TREE = (L, R, S)
    pickle.dump(_TREE, open(cache, 'wb'))
    return _TREE


class Msg:
    def __init__(self, data):
        self.d = data; self.bit = 0; self.maxbit = len(data) * 8
        self.L, self.R, self.S = decode_tree()

    def getbit(self):
        b = (self.d[self.bit >> 3] >> (self.bit & 7)) & 1
        self.bit += 1
        return b

    def huffbyte(self):
        n = 0
        while self.S[n] == INTERNAL:
            if self.bit >= self.maxbit:
                raise EOFError('msg overrun')
            n = self.R[n] if self.getbit() else self.L[n]
        return self.S[n]

    def bits(self, nb):
        v = 0
        k = nb & 7
        for i in range(k):
            v |= self.getbit() << i
        for i in range(0, nb - k, 8):
            v |= self.huffbyte() << (i + k)
        return v

    def byte(self): return self.bits(8)
    def short(self):
        v = self.bits(16)
        return v - 0x10000 if v & 0x8000 else v
    def long(self):
        v = self.bits(32)
        return v - 0x100000000 if v & 0x80000000 else v
    def float(self): return struct.unpack('<f', struct.pack('<I', self.bits(32) & 0xffffffff))[0]
    def string(self):
        out = bytearray()
        while True:
            c = self.byte()
            if c == 0:
                break
            out.append(ord('.') if c == ord('%') else c)
        return out.decode('latin-1')


class Skc14:
    pass


def read_skc14(data):
    assert data[0:4] == b'SKAN'
    ver = struct.unpack_from('<i', data, 4)[0]
    assert ver == 14, ver
    m = Msg(data[8:])
    a = Skc14()
    a.version = 14
    nch = m.short()
    a.flags = m.long(); a.frameTime = m.float()
    a.totalDelta = (m.float(), m.float(), m.float()); a.totalAngleDelta = m.float()
    a.numFrames = m.long()
    a.hasDelta, a.hasUpper, a.hasMorph = m.byte(), m.byte(), m.byte()
    a.numChannels = nch
    a.channels = [m.string() for _ in range(nch)]
    for _ in range(a.numFrames):
        [m.float() for _ in range(11)]
    [m.float() for _ in range(6)]
    a.keys = []
    for name in a.channels:
        cnt = m.short()
        if name.endswith(' rot'):
            w = 4
        elif name.endswith(' pos'):
            w = 3
        else:
            w = 1
        ks = []
        for _ in range(cnt):
            fn = m.short(); pv = m.short()
            ks.append((fn, tuple(m.float() for _ in range(w))))
        a.keys.append(ks)
    return a


def skc_channel14(a, frame, i):
    ks = a.keys[i]
    val = None
    for fn, v in ks:
        if fn <= frame:
            val = v
        else:
            break
    if val is None and ks:
        val = ks[0][1]
    return tuple(val) + (0.0,) * (4 - len(val))

