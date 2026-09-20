import re, sys

path = sys.argv[1]
n = w = ctx = plural = fmt = 0
cur = []
state = None
has_id = False
in_block_ctx = False

def flush():
    global n, w, cur, has_id, in_block_ctx, fmt
    text = ''.join(cur)
    if has_id and text.strip():
        n += 1
        w += len(re.findall(r"[A-Za-z0-9']+", text))
        if re.search(r'%(\d+\$)?[-0-9.]*[sdfux%]', text):
            fmt += 1
    cur = []
    has_id = False
    in_block_ctx = False

for raw in open(path, encoding='utf-8'):
    s = raw.strip()
    if not s:
        flush(); state = None; continue
    if s.startswith('#'):
        state = None; continue
    if s.startswith('msgctxt'):
        ctx += 1 if not in_block_ctx else 0
        in_block_ctx = True
        state = 'skip'; continue
    if s.startswith('msgid_plural'):
        plural += 1
        state = 'skip'; continue
    if s.startswith('msgid'):
        has_id = True; state = 'id'; payload = s[5:].strip()
    elif s.startswith('msgstr'):
        state = 'skip'; continue
    elif s.startswith('"'):
        payload = s
    else:
        state = None; continue
    if state == 'id':
        b = payload.strip()
        if b.startswith('"') and b.endswith('"') and len(b) >= 2:
            b = b[1:-1]
        cur.append(b)
flush()
print(f"{path}: {n} 条 | {w} 英文词 | {ctx} 条带 msgctxt | {plural} 条复数形式 | {fmt} 条含 printf 占位符")
