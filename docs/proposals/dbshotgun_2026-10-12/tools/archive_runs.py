"""MOVE finished harness runs to the archive disk, ONE FOLDER PER RUN, with a file-count and byte check (bug-3808: a
loop that merged 28 runs into one folder).

    python tools/archive_runs.py <run> [<run> ...]

Refuses a run whose archive folder already exists. Counts files and bytes before the move and in the archive after it.
"""
import os, sys, shutil
import dbslib as L

ARCH = r'H:\hzm_archive\dbs'


def tally(d):
    n = b = 0
    for r, _, fs in os.walk(d):
        for f in fs:
            n += 1
            b += os.path.getsize(os.path.join(r, f))
    return n, b


def main():
    for run in sys.argv[1:]:
        src = os.path.join(L.RUNS, run)
        dst = os.path.join(ARCH, run)
        assert os.path.isdir(src), src
        assert not os.path.exists(dst), 'archive folder exists: ' + dst
        before = tally(src)
        shutil.move(src, dst)
        after = tally(dst)
        assert before == after and not os.path.exists(src), (run, before, after)
        print('%s: %d files, %d bytes -> %s (counted again there: equal)' % (run, after[0], after[1], dst))


if __name__ == '__main__':
    main()
