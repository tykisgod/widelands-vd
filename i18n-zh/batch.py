#!/usr/bin/env python3
"""翻译批次的导出与回写。

导出时带齐译者需要的全部上下文：msgctxt 消歧、上游译者注释（#.）、源码位置
（#: 用以判断该串出现在哪个界面）、术语表命中项、以及现有译文（供重译对照）。

用法:
    # 导出第 1 批（按源码位置分组，同批同界面）
    python i18n-zh/batch.py export --count 80 --out batch01.json

    # 只导出尚未翻译的
    python i18n-zh/batch.py export --untranslated-only --count 80 --out b.json

    # 回写：译文文件形如 {"<key>": "译文", ...}，key 取导出时的 key
    python i18n-zh/batch.py import batch01.zh.json

    # 进度
    python i18n-zh/batch.py status
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_po import parse_po, load_glossary                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_PO = os.path.join(REPO, 'data/i18n/translations/widelands/zh_CN.po')
DEFAULT_GLOSSARY = os.path.join(HERE, 'glossary.tsv')
STATE = os.path.join(HERE, '.batch_state.json')


def escape(s: str) -> str:
    out = s.replace('\\', '\\\\').replace('"', '\\"')
    return out.replace('\n', '\\n').replace('\t', '\\t')


def key_of(e) -> str:
    """条目的稳定标识。用行号会在回写后失效，故用 ctxt+msgid 的短哈希。"""
    import hashlib
    h = hashlib.sha1(f'{e.ctxt}\x00{e.msgid}\x00{e.msgid_plural}'.encode()).hexdigest()
    return h[:10]


def ui_hint(refs):
    """从源码路径猜测该串出现在哪个界面，帮助判断语气与长度。"""
    seen = []
    for r in refs:
        m = re.search(r'src/([a-z_]+)/([a-z_]+)', r)
        if m:
            tag = f'{m.group(1)}/{m.group(2)}'
            if tag not in seen:
                seen.append(tag)
    return ', '.join(seen[:3])


def glossary_hits(text, terms_by_en):
    """原文中命中的术语，按长度降序，供翻译时直接采用。"""
    hits = []
    low = text.lower()
    for en, zh in terms_by_en:
        if len(en) < 3:
            continue
        if en.lower() in low:
            hits.append(f'{en} = {zh}')
        if len(hits) >= 8:
            break
    return hits


def cmd_export(args):
    entries = [e for e in parse_po(args.po) if not e.is_header and e.msgid]
    terms = load_glossary(args.glossary)
    terms_by_en = sorted({(en, zh) for (en, _c), zh in terms.items()},
                         key=lambda kv: -len(kv[0]))

    done = set()
    if os.path.exists(STATE):
        done = set(json.load(open(STATE, encoding='utf-8')).get('done', []))

    pool = []
    for e in entries:
        k = key_of(e)
        if k in done:
            continue
        if args.untranslated_only and e.translated:
            continue
        pool.append((k, e))

    # 按源码位置分组，让同一界面的字符串落在同一批，语气才好统一
    pool.sort(key=lambda ke: (ke[1].ref[0] if ke[1].ref else '~', ke[1].line))

    batch = pool[:args.count]
    out = []
    for k, e in batch:
        item = {
            'key': k,
            'msgid': e.msgid,
            'zh': '',
        }
        if e.msgid_plural:
            item['msgid_plural'] = e.msgid_plural
        if e.ctxt:
            item['msgctxt'] = e.ctxt
        if e.comments:
            item['note'] = ' | '.join(e.comments)
        hint = ui_hint(e.ref)
        if hint:
            item['ui'] = hint
        if e.translated:
            item['current'] = e.msgstrs[0]
        hits = glossary_hits(e.msgid, terms_by_en)
        if hits:
            item['terms'] = hits
        out.append(item)

    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f'导出 {len(out)} 条到 {args.out}（池中剩余 {len(pool)} 条）')
    return 0


def cmd_import(args):
    with open(args.translations, encoding='utf-8') as fh:
        data = json.load(fh)
    if isinstance(data, list):
        data = {it['key']: it['zh'] for it in data if it.get('zh')}

    entries = parse_po(args.po)
    by_key = {key_of(e): e for e in entries if not e.is_header and e.msgid}

    targets = {}
    unknown = []
    for k, zh in data.items():
        e = by_key.get(k)
        if e is None:
            unknown.append(k)
            continue
        if not zh.strip():
            continue
        targets[e.line] = zh

    if unknown:
        print(f'警告：{len(unknown)} 个 key 在 po 中找不到：{unknown[:5]}')

    with open(args.po, encoding='utf-8', newline='') as fh:
        lines = fh.readlines()
    newline = '\r\n' if lines and lines[0].endswith('\r\n') else '\n'

    starts = sorted(targets)
    out = []
    i = 0
    n = len(lines)
    written = 0
    while i < n:
        raw = lines[i]
        stripped = raw.strip()
        if stripped.startswith('msgstr'):
            owner = None
            for s in starts:
                if s <= i + 1:
                    owner = s
                else:
                    break
            if owner is not None and owner in targets:
                prefix = 'msgstr[0] ' if stripped.startswith('msgstr[') else 'msgstr '
                out.append(f'{prefix}"{escape(targets[owner])}"{newline}')
                del targets[owner]
                written += 1
                i += 1
                while i < n and lines[i].strip().startswith('"'):
                    i += 1
                continue
        out.append(raw)
        i += 1

    with open(args.po, 'w', encoding='utf-8', newline='') as fh:
        fh.writelines(out)

    done = set()
    if os.path.exists(STATE):
        done = set(json.load(open(STATE, encoding='utf-8')).get('done', []))
    done |= set(data)
    json.dump({'done': sorted(done)}, open(STATE, 'w', encoding='utf-8'))

    print(f'回写 {written} 条；累计已处理 {len(done)} 条')
    return 0


def cmd_status(args):
    entries = [e for e in parse_po(args.po) if not e.is_header and e.msgid]
    total = len(entries)
    trans = sum(1 for e in entries if e.translated)
    done = set()
    if os.path.exists(STATE):
        done = set(json.load(open(STATE, encoding='utf-8')).get('done', []))
    reviewed = sum(1 for e in entries if key_of(e) in done)
    print(f'{os.path.relpath(args.po, REPO)}')
    print(f'  总条目   {total}')
    print(f'  有译文   {trans}  ({100*trans/total:.1f}%)')
    print(f'  本项目已过 {reviewed}  ({100*reviewed/total:.1f}%)')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--po', default=DEFAULT_PO)
    ap.add_argument('--glossary', default=DEFAULT_GLOSSARY)
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('export')
    p.add_argument('--count', type=int, default=80)
    p.add_argument('--out', required=True)
    p.add_argument('--untranslated-only', action='store_true')
    p.set_defaults(fn=cmd_export)

    p = sub.add_parser('import')
    p.add_argument('translations')
    p.set_defaults(fn=cmd_import)

    p = sub.add_parser('status')
    p.set_defaults(fn=cmd_status)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == '__main__':
    sys.exit(main())
