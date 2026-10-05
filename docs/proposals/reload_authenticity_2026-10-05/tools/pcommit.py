"""pcommit.py - commit ONLY given content via a PRIVATE index (the shared index is never touched until the end, so a
parallel agent's staging cannot leak into this commit nor this into theirs).
    python pcommit.py <msgfile> <spec> ...
spec:  path                      -> working-tree file as is (binary)
       path::drop1.txt,drop2.txt -> working-tree file with those exact text blocks removed ('a.txt=b.txt' = replace)
Afterwards: HEAD advanced with update-ref (only if HEAD did not move), shared index entries of these paths reset to HEAD."""
import sys, os, subprocess, tempfile
msg = sys.argv[1]; specs = sys.argv[2:]
def git(*a, inp=None, env=None):
    r = subprocess.run(['git'] + list(a), input=inp, capture_output=True, env=env)
    if r.returncode:
        raise SystemExit('git %s failed: %s' % (a[:2], r.stderr.decode()))
    return r.stdout
head = git('rev-parse', 'HEAD').decode().strip()
env = dict(os.environ); env['GIT_INDEX_FILE'] = os.path.join(tempfile.gettempdir(), 'pcommit_index_%d' % os.getpid())
git('read-tree', head, env=env)
paths = []
for sp in specs:
    path, _, mods = sp.partition('::')
    data = open(path, 'rb').read()
    if mods:
        s = data.decode('latin1')
        for m in mods.split(','):
            if '=' in m:
                a, b = m.split('=')
                x = open(a, 'rb').read().decode('latin1'); y = open(b, 'rb').read().decode('latin1')
            else:
                x = open(m, 'rb').read().decode('latin1'); y = ''
            assert s.count(x) == 1, (path, m, s.count(x))
            s = s.replace(x, y)
        data = s.encode('latin1')
    if not path.lower().endswith(('.skc', '.skd', '.tga', '.jpg', '.png', '.wav', '.pk3', '.dll', '.exe')):
        data = data.replace(b'\r\n', b'\n')     # autocrlf working copies: store LF like git add would (c5dd07d)
    blob = git('hash-object', '-w', '--stdin', inp=data).decode().strip()
    ls = git('ls-files', '-s', '--', path, env=env).decode().split()
    mode = ls[0] if ls else '100644'
    git('update-index', '--add', '--cacheinfo', '%s,%s,%s' % (mode, blob, path), env=env)
    paths.append(path)
tree = git('write-tree', env=env).decode().strip()
c = git('commit-tree', tree, '-p', head, '-F', msg).decode().strip()
git('update-ref', 'HEAD', c, head)
os.remove(env['GIT_INDEX_FILE'])
subprocess.run(['git', 'reset', '-q', '--'] + paths)
print('committed', c[:8], len(paths), 'paths')
