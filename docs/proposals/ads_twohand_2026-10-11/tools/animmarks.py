import re, sys
RUNS_DIR = __import__('os').environ.get('ADS_RUNS', 'G:/mohaa-adsanim/runs').rstrip('/')   # another lane's harness: set ADS_RUNS
cur=None; i=0; last=None; out={}
for ln in open(RUNS_DIR + '/%s/qconsole.log' % sys.argv[1], encoding='latin-1'):
    m=re.search(r'ABSCEN (begin|end) (\S+)',ln)
    if m and 'echo' not in ln:
        cur=m.group(2) if m.group(1)=='begin' else None; i=0; last=None; continue
    if cur and 'ADSFRAME' in ln:
        a=re.search(r'anim=(\d+)',ln).group(1)
        if a!=last: out.setdefault(cur,[]).append('%d:%s' % (i,a)); last=a
        i+=1
for k,v in out.items(): print(k.split('__')[2], k.split('__')[-3], ' '.join(v[:3]), '...', ' '.join(v[-4:]))
