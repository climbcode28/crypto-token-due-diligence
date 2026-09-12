from solana_scaffold import scaffold
from solana_facts import encoded
from solana_compose import CHECKLISTS


def note(b):
    n=scaffold(b.root,allow_synthetic=True);n.pop('judgment_todo');n.pop('decision_template');n['signal_assignments']={};return n


def save(b,n,owner='coordinator'):
    p=b.root/'notes'/(owner+'.json');p.parent.mkdir(exist_ok=True);p.write_bytes(encoded(n))


def lane(b,owner):
    n=scaffold(b.root,owner,True);n['checklist']={k:{'status':'done','reason':'Bounded synthetic checklist supported by the retained source.'} for k in CHECKLISTS[owner]};n['evidence_ids']=['controls'];save(b,n,owner);return n
