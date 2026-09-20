"""Extract terminology pairs from high-completion Widelands zh_CN po files.

Source domains (tribes 84%, world 98%, maps 83%, win_conditions 86%) hold the
authoritative names for buildings, wares, workers and terrain. The main UI must
match them exactly.
"""
import re
import sys
import json
from collections import defaultdict

ESCAPES = {'\\n': '\n', '\\t': '\t', '\\"': '"', '\\\\': '\\'}


def unescape(s):
    out = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            pair = s[i:i + 2]
            out.append(ESCAPES.get(pair, pair))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


def parse_po(path):
    """Yield dicts with ctxt / id / str / comments for every entry."""
    entry = {'ctxt': [], 'id': [], 'str': [], 'xcomment': [], 'ref': []}
    state = None

    def fresh():
        return {'ctxt': [], 'id': [], 'str': [], 'xcomment': [], 'ref': []}

    for raw in open(path, encoding='utf-8'):
        s = raw.rstrip('\n').strip()
        if not s:
            if entry['id']:
                yield entry
            entry = fresh()
            state = None
            continue
        if s.startswith('#.'):
            entry['xcomment'].append(s[2:].strip())
            state = None
            continue
        if s.startswith('#:'):
            entry['ref'].append(s[2:].strip())
            state = None
            continue
        if s.startswith('#'):
            state = None
            continue

        if s.startswith('msgctxt'):
            state, payload = 'ctxt', s[7:].strip()
        elif s.startswith('msgid_plural'):
            state, payload = None, ''
        elif s.startswith('msgid'):
            state, payload = 'id', s[5:].strip()
        elif s.startswith('msgstr['):
            idx = s.split(']', 1)
            state = 'str' if idx[0] == 'msgstr[0' else None
            payload = idx[1].strip() if len(idx) > 1 else ''
        elif s.startswith('msgstr'):
            state, payload = 'str', s[6:].strip()
        elif s.startswith('"'):
            payload = s
        else:
            state = None
            continue

        if state:
            b = payload.strip()
            if b.startswith('"') and b.endswith('"') and len(b) >= 2:
                entry[state].append(unescape(b[1:-1]))
    if entry['id']:
        yield entry


def is_term(en):
    """Terminology = short noun phrases, no placeholders, no sentence punctuation."""
    if not en or len(en) > 60:
        return False
    if re.search(r'%(\d+\$)?[-0-9.]*[sdfux]|%%', en):
        return False
    if re.search(r'[.!?;:]\s|[.!?]$', en):
        return False
    if '\n' in en or '<' in en:
        return False
    return len(en.split()) <= 6


def main(paths):
    terms = defaultdict(lambda: defaultdict(list))  # en -> zh -> [sources]
    for p in paths:
        domain = p.split('zh_', 1)[-1].rsplit('.po', 1)[0]
        for e in parse_po(p):
            en = ''.join(e['id'])
            zh = ''.join(e['str'])
            if not en or not zh or not is_term(en):
                continue
            ctxt = ''.join(e['ctxt'])
            key = f'{en}\x00{ctxt}' if ctxt else en
            terms[key][zh].append(domain)

    rows = []
    conflicts = []
    for key, variants in sorted(terms.items()):
        en, _, ctxt = key.partition('\x00')
        if len(variants) > 1:
            conflicts.append((en, ctxt, {z: sorted(set(d)) for z, d in variants.items()}))
        # pick the reading attested in the most domains, ties -> most occurrences
        best = max(variants.items(), key=lambda kv: (len(set(kv[1])), len(kv[1])))
        rows.append({
            'en': en,
            'zh': best[0],
            'ctxt': ctxt,
            'sources': sorted(set(best[1])),
            'variants': {z: sorted(set(d)) for z, d in variants.items()} if len(variants) > 1 else None,
        })

    out = sys.argv[1] if len(sys.argv) > 1 else None
    print(f'抽取词条 {len(rows)} 条，其中译法冲突 {len(conflicts)} 条')
    with open('glossary_raw.json', 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    if conflicts:
        print('\n--- 译法冲突（需裁决）---')
        for en, ctxt, variants in conflicts[:40]:
            tag = f' [{ctxt}]' if ctxt else ''
            desc = ' | '.join(f'{z} ({",".join(d)})' for z, d in variants.items())
            print(f'  {en}{tag}  ->  {desc}')


if __name__ == '__main__':
    import glob
    main(sorted(glob.glob('zh_tribes.po') + glob.glob('zh_world.po') +
                glob.glob('zh_maps.po') + glob.glob('zh_win_conditions.po')))
