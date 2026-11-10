"""QA 4 (build_bren.py): the source aperture leaf (part 34's rear end, 110 tris: 1 u wide x 1.8 u tall, 4 u from the eye) filled
~75 % of the aim view. It goes; a THIN ring takes its place on the sight line (outer 0.5 u -> ~7 deg radius at the 4 u relief,
about a third of the screen height across), both faces, so the rear sight reads as a soft ring around the target."""
P = r'C:\hzm-newguns\root\docs\proposals\newguns_2026-11-09\tools\build_bren.py'
s = open(P, 'rb').read()
nl = b'\r\n' if b'\r\n' in s else b'\n'
old = (b'    # [newguns QA 3] no ghost ring: the sight row looks through the source aperture leaf (part 34), the disc (49) stays out' + nl +
       b'    A = A[keep]; part = part[keep]' + nl + b'    _unused_ring = ring')
assert s.count(old) == 1
new = (b'    # [newguns QA 4] the source aperture leaf (rear end of part 34, above the receiver) filled the aim view: out. A thin ring' + nl +
       b'    # on the sight line instead (APERTURE_G, gun frame before SIGHT_DY), outer 0.5 u / inner 0.43 u, both faces' + nl +
       b'    G0 = L.to_gun(A[:, :, :3]).mean(1)' + nl +
       b'    leaf = (part == 34) & (G0[:, 0] > -10.4) & (G0[:, 0] < -8.6) & (G0[:, 2] < -4.3)' + nl +
       b'    assert leaf.sum() == 110, leaf.sum()' + nl +
       b'    keep = keep & ~leaf' + nl +
       b'    Ls = np.array([-1.0, 1.0, -1.0])' + nl +
       b'    L.RING_C = ((APERTURE_G - L.T) / L.S) * Ls' + nl +
       b'    L.RING_RO, L.RING_RI = 0.50 / L.S, 0.43 / L.S' + nl +
       b'    ring = L.ring_tris(uv)' + nl +
       b'    back = ring[:, ::-1].copy(); back[:, :, 3:6] *= -1.0' + nl +
       b'    ring = np.concatenate([ring, back])' + nl +
       b'    A = np.concatenate([A[keep], ring]); part = np.concatenate([part[keep], np.full(len(ring), 49)])')
s = s.replace(old, new)
anchor = b'SIGHT_DY = -0.70'
assert s.count(anchor) == 1
i = s.index(anchor)
j = s.index(nl, i) + len(nl)
s = s[:j] + b'APERTURE_G = np.array([-9.5922, -1.2388, -5.65])           # the rear sight point (cg_adssights.h R, before SIGHT_DY)' + nl + s[j:]
open(P, 'wb').write(s)
print('patched')
