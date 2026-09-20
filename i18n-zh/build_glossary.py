#!/usr/bin/env python3
"""从高完成度域抽取术语，套用人工裁决，生成 i18n-zh/glossary.tsv。

数据来源是 tribes / world / win_conditions 三个域已有的成熟译文——
它们是建筑名、货物名、工人名、地形名的权威出处。主 UI 里出现的每个游戏
名词都必须与之一致，否则玩家会在建造菜单和经济面板看到同一事物的两个名字。

但"源域内部自洽"不等于"正确"，故所有裁决集中在 corrections.tsv，由人工
逐条复核后覆盖抽取结果。

用法:
    python i18n-zh/build_glossary.py            # 生成 glossary.tsv
    python i18n-zh/build_glossary.py --report   # 只打印统计与冲突，不写文件
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_po import parse_po                                   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TRANSLATIONS = os.path.join(REPO, 'data', 'i18n', 'translations')

# 完成度高、且内容确实是术语的域。
#
# 刻意不含 maps：该域装的是地图标题（"彗星岛"、"阿斯托里亚 2.R"），是专有
# 名词而非术语。把它们纳入会用地图名去约束其他域——实测 Atoll 作为地图名
# 被译作"环状珊瑚岛"，随即误伤了主 UI 里作为随机地图地形类型的同名条目。
SOURCE_DOMAINS = ('tribes', 'world', 'win_conditions')

# corrections.tsv 中把中文写成这个值，表示将该词条排除出术语表。
EXCLUDE_MARKER = '-'

CORRECTIONS = os.path.join(HERE, 'corrections.tsv')
OUTPUT = os.path.join(HERE, 'glossary.tsv')


def is_term(en: str) -> bool:
    """术语 = 短名词短语。排除句子、带占位符的模板、带标记的富文本。"""
    if not en or len(en) > 60:
        return False
    if '%' in en or '<' in en or '\n' in en:
        return False
    if re.search(r'[.!?;:]\s|[.!?]$', en):
        return False
    return len(en.split()) <= 6


def load_corrections():
    """人工裁决表。列：英文 / 中文 / msgctxt / 理由。

    msgctxt 留空表示对该英文的所有上下文生效。
    """
    rows = {}
    if not os.path.exists(CORRECTIONS):
        return rows
    with open(CORRECTIONS, encoding='utf-8') as fh:
        for line in fh:
            if not line.strip() or line.startswith('#'):
                continue
            cols = line.rstrip('\n').split('\t')
            if len(cols) < 2 or not cols[0]:
                continue
            en = cols[0]
            zh = cols[1]
            ctxt = cols[2] if len(cols) > 2 else ''
            why = cols[3] if len(cols) > 3 else ''
            rows[(en, ctxt)] = (zh, why)
    return rows


def extract():
    """返回 {(en, ctxt): {zh: [域名]}}。"""
    terms = {}
    for domain in SOURCE_DOMAINS:
        path = os.path.join(TRANSLATIONS, domain, 'zh_CN.po')
        if not os.path.exists(path):
            print(f'  跳过缺失的域：{domain}', file=sys.stderr)
            continue
        for e in parse_po(path):
            if e.is_header or not e.translated:
                continue
            en, zh = e.msgid, e.msgstrs[0]
            if not en or not zh or not is_term(en):
                continue
            slot = terms.setdefault((en, e.ctxt), {})
            slot.setdefault(zh, []).append(domain)
    return terms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true', help='只统计，不写文件')
    args = ap.parse_args()

    terms = extract()
    corrections = load_corrections()

    rows = []
    conflicts = []
    corrected = 0
    excluded = 0
    for (en, ctxt), variants in sorted(terms.items()):
        if len(variants) > 1:
            conflicts.append((en, ctxt, variants))

        fix = corrections.get((en, ctxt)) or corrections.get((en, ''))
        if fix and fix[0] == EXCLUDE_MARKER:
            excluded += 1
            continue
        if fix:
            zh, note = fix
            sources = 'corrections'
            corrected += 1
        else:
            # 采信被最多域佐证的译法
            zh, doms = max(variants.items(), key=lambda kv: (len(set(kv[1])), len(kv[1])))
            sources = ','.join(sorted(set(doms)))
            note = ''
        rows.append((en, zh, ctxt, sources, note))

    # 裁决表里可能有抽取结果中不存在的词条（主 UI 通用术语），一并收入
    known = {(r[0], r[2]) for r in rows}
    for (en, ctxt), (zh, note) in sorted(corrections.items()):
        if zh == EXCLUDE_MARKER:
            continue
        if (en, ctxt) not in known and not any(r[0] == en for r in rows):
            rows.append((en, zh, ctxt, 'corrections', note))
            corrected += 1

    print(f'抽取 {len(terms)} 条，人工裁决覆盖 {corrected} 条，排除 {excluded} 条，'
          f'源域内部冲突 {len(conflicts)} 条，输出 {len(rows)} 条')
    for en, ctxt, variants in conflicts[:20]:
        desc = ' | '.join(f'{z}({",".join(sorted(set(d)))})' for z, d in variants.items())
        print(f'  冲突 {en}{" [" + ctxt + "]" if ctxt else ""} -> {desc}')

    if args.report:
        return 0

    rows.sort(key=lambda r: (r[0].lower(), r[2]))
    with open(OUTPUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# Widelands 简体中文术语表——由 build_glossary.py 生成，请勿手工编辑。\n')
        fh.write('# 要改译名请改 i18n-zh/corrections.tsv 后重新生成。\n')
        fh.write('# check_po.py --glossary 会据此校验全部 32 个域的一致性。\n')
        fh.write('#\n')
        fh.write('# 英文\t中文\tmsgctxt\t出处\t备注\n')
        for en, zh, ctxt, src, note in rows:
            fh.write(f'{en}\t{zh}\t{ctxt}\t{src}\t{note}\n')
    print(f'已写入 {OUTPUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
