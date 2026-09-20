"""Pick verification cases from the live zh_CN.po: entries already translated,
short, no placeholders, no msgctxt -- safe anchors for an end-to-end smoke test.
"""
import sys
sys.path.insert(0, '.')
from extract_glossary import parse_po
import re

path = sys.argv[1]
picked = []
for e in parse_po(path):
    if e['ctxt']:
        continue
    en = ''.join(e['id'])
    zh = ''.join(e['str'])
    if not en or not zh:
        continue
    if re.search(r'%|\\|\n', en) or len(en) > 28 or len(en.split()) > 3:
        continue
    if not re.search(r'[一-鿿]', zh):
        continue
    picked.append((en, zh))

seen = set()
out = []
for en, zh in picked:
    if en in seen:
        continue
    seen.add(en)
    out.append((en, zh))

for en, zh in out[:14]:
    print(f'   {{ "{en}", "{zh}" }},')
print(f'-- 共 {len(out)} 条候选', file=sys.stderr)
