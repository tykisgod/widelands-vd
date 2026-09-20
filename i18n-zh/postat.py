import glob, os, sys

def stats(path):
    total = trans = fuzzy = 0
    cur_fuzzy = False
    state = None          # 'id' | 'str' | None
    has_id = False
    id_empty = True
    str_empty = True

    def flush():
        nonlocal total, trans, fuzzy, has_id, id_empty, str_empty, cur_fuzzy
        if has_id and not id_empty:
            total += 1
            if not str_empty:
                trans += 1
            if cur_fuzzy:
                fuzzy += 1
        has_id = False
        id_empty = True
        str_empty = True
        cur_fuzzy = False

    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        s = line.strip()
        if not s:
            flush()
            state = None
            continue
        if s.startswith('#'):
            if s.startswith('#,') and 'fuzzy' in s:
                cur_fuzzy = True
            state = None
            continue
        if s.startswith('msgid_plural'):
            state = 'id'
            payload = s[len('msgid_plural'):].strip()
        elif s.startswith('msgid'):
            has_id = True
            state = 'id'
            payload = s[len('msgid'):].strip()
        elif s.startswith('msgstr'):
            state = 'str'
            payload = s.split(None, 1)[1] if ' ' in s else ''
            if s.startswith('msgstr[') and ']' in s:
                payload = s.split(']', 1)[1].strip()
        elif s.startswith('"'):
            payload = s
        else:
            state = None
            continue
        body = payload.strip()
        if body.startswith('"') and body.endswith('"') and len(body) >= 2:
            body = body[1:-1]
        if body:
            if state == 'id':
                id_empty = False
            elif state == 'str':
                str_empty = False
    flush()
    return total, trans, fuzzy


files = sys.argv[1:] or sorted(glob.glob('zh_*.po'))
print(f"{'domain':<44}{'total':>7}{'done':>8}{'fuzzy':>7}{'pct':>8}")
gt = gtr = 0
for p in files:
    t, tr, f = stats(p)
    gt += t
    gtr += tr
    name = os.path.basename(p)
    print(f"{name:<44}{t:>7}{tr:>8}{f:>7}{(100*tr/t if t else 0):>7.1f}%")
print(f"{'TOTAL':<44}{gt:>7}{gtr:>8}{'':>7}{(100*gtr/gt if gt else 0):>7.1f}%")
