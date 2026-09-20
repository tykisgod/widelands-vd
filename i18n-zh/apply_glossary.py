#!/usr/bin/env python3
"""把术语表的裁决结果落到各域的 zh_CN.po 上。

只改整条 msgstr 与术语表不符的条目——即原文整体就是一个术语词条的情况。
句子内部的术语用法不在此列，那属于翻译时的判断，由人处理。

用法:
    python i18n-zh/apply_glossary.py --dry-run     # 只列出将要改什么
    python i18n-zh/apply_glossary.py               # 实际改写
    python i18n-zh/apply_glossary.py <po> [<po>…]  # 限定文件

改写保持原文件的行尾风格（Windows checkout 下为 CRLF），不重排条目顺序，
不触碰注释与 header，因此 diff 只含实际改动的 msgstr 行。
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_po import parse_po, load_glossary                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_GLOSSARY = os.path.join(HERE, 'glossary.tsv')


def escape(s: str) -> str:
    out = s.replace('\\', '\\\\').replace('"', '\\"')
    return out.replace('\n', '\\n').replace('\t', '\\t')


def rewrite(path, terms, dry_run):
    """返回 (改动数, 改动清单)。"""
    entries = parse_po(path)
    targets = {}          # 起始行号 -> 新 msgstr
    changes = []
    for e in entries:
        if e.is_header or not e.translated:
            continue
        want = terms.get((e.msgid, e.ctxt)) or terms.get((e.msgid, ''))
        if not want:
            continue
        got = e.msgstrs[0]
        if got == want:
            continue
        targets[e.line] = want
        changes.append((e.line, e.msgid, e.ctxt, got, want))

    if not targets or dry_run:
        return len(changes), changes

    # 逐行重写：定位每个目标条目的 msgstr 行（含续行），整体替换为单行形式
    with open(path, encoding='utf-8', newline='') as fh:
        lines = fh.readlines()

    newline = '\r\n' if lines and lines[0].endswith('\r\n') else '\n'

    # 找出每个条目起始行之后的第一处 msgstr，连同其续行一并替换
    out = []
    i = 0
    starts = sorted(targets)
    n = len(lines)
    while i < n:
        raw = lines[i]
        stripped = raw.strip()
        if stripped.startswith('msgstr'):
            # 该 msgstr 属于哪个条目：取不大于当前行号的最大起始行
            owner = None
            for s in starts:
                if s <= i + 1:
                    owner = s
                else:
                    break
            if owner is not None and owner in targets:
                # 确认这段 msgstr 尚未处理过
                prefix = 'msgstr[0] ' if stripped.startswith('msgstr[') else 'msgstr '
                out.append(f'{prefix}"{escape(targets[owner])}"{newline}')
                del targets[owner]
                i += 1
                while i < n and lines[i].strip().startswith('"'):
                    i += 1
                continue
        out.append(raw)
        i += 1

    with open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.writelines(out)
    return len(changes), changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--glossary', default=DEFAULT_GLOSSARY)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    files = args.files or sorted(
        glob.glob(os.path.join(REPO, 'data/i18n/translations/*/zh_CN.po')))
    terms = load_glossary(args.glossary)
    print(f'术语表 {len(terms)} 条，待处理 {len(files)} 个文件'
          f'{"（试运行）" if args.dry_run else ""}\n')

    total = 0
    for path in files:
        count, changes = rewrite(path, terms, args.dry_run)
        if not count:
            continue
        total += count
        print(f'{os.path.relpath(path, REPO)}  {count} 处')
        for line, msgid, ctxt, got, want in changes:
            tag = f' [{ctxt}]' if ctxt else ''
            print(f'  :{line}  {msgid}{tag}   {got}  ->  {want}')
        print()

    print(f'=== 共 {total} 处{"待改" if args.dry_run else "已改"} ===')
    return 0


if __name__ == '__main__':
    sys.exit(main())
