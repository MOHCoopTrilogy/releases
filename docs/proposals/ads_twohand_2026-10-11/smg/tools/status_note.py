"""SMG lane: the hand-written fields of a weapon in ../coverage_status.json (shared schema) - who works the action,
what was looked at, the three rules and their run id. Notes live in status_notes.json so they are re-appliable.

    python status_note.py            applies every entry of status_notes.json
status_notes.json: {"models/weapons/x.tik": {"action": "...", "qa": "...", "rule": {"target": "yes", "reacts": "yes",
                                             "action": "yes", "run": "sc3"}}}
"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.join(HERE, '..', 'coverage_status.json')
st = json.load(open(ST))
notes = json.load(open(os.path.join(HERE, 'status_notes.json'), encoding='utf-8'))
for tik, d in notes.items():
    e = st.setdefault(tik.lower(), {})
    for k in ('action', 'qa', 'rule'):
        if k in d:
            e[k] = d[k]
    print(tik, '->', ', '.join(sorted(d)))
json.dump(st, open(ST, 'w'), indent=1, sort_keys=True)
