"""offline look at the baked hand clips: one bake, several sheets ->  build/_h_<clip>.jpg
    python tools/dbs_hsheets.py [clip:f,f,f ...]      (default: a standard set); needs IRONSIGHT_EXTRA_PAKS = the overlay
"""
import sys, os
import dbslib as L
import dbs_hands as H

DEFAULT = ['idle:0', 'fire:0,1,2,5', 'reload:0,6,10,14,18,22', 'reload_single:0,5,8,10,12,13,15,19',
           'reload_single_first:10,13,15,19', 'reload_end:0,3,6,9,11,14,22,31']


def main():
    specs = sys.argv[1:] or DEFAULT
    clips, paths = H.bake_all()
    for s in specs:
        nm, fr = s.split(':')
        H.sheet(clips, nm, [int(x) for x in fr.split(',')], os.path.join(L.BUILD, '_h_%s.jpg' % nm))


if __name__ == '__main__':
    main()
