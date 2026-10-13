"""repair: two Printf format strings in cg_modelanim.c got a literal newline (Git-Bash heredoc trap)"""
import re
p = r'C:\mohaa-coop-dev\openmohaa-hzm-ads\code\cgame\cg_modelanim.c'
s = open(p, encoding='latin-1', newline='').read()
n0 = len(s)
s, k = re.subn(r'(SRVPROBE st %d (?:ps|went)[^"\r\n]*)\r?\n"', lambda m: m.group(1) + '\\n"', s)
print('fixed', k)
assert k == 2
open(p, 'w', encoding='latin-1', newline='').write(s)
