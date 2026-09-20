#!/usr/bin/env python3
"""重算 data/i18n/translation_stats.conf 里 zh_CN 的词数统计。

游戏的选项界面会显示"XX 的翻译已完成 N%"，数据取自该文件。上游用
translate-toolkit 的 pocount 生成，本机没有该依赖，故按同一口径自行计算：

    Total Source Words       全部 msgid 的源词数
    Translated Source Words  有译文的条目的 msgid 源词数

先用 --check 核对能否复现该文件里现有的 [global] total，口径一致才改写。

用法:
    python i18n-zh/update_stats.py --check    # 只比对口径，不改文件
    python i18n-zh/update_stats.py            # 改写 zh_CN 一节
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_po import parse_po                                   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TRANSLATIONS = os.path.join(REPO, 'data', 'i18n', 'translations')
STATS = os.path.join(REPO, 'data', 'i18n', 'translation_stats.conf')

WORD = re.compile(r"[^\s]+")


def count_words(text: str) -> int:
    """pocount 按空白切分计词。"""
    return len(WORD.findall(text))


def tally(locale: str):
    total = translated = 0
    pattern = os.path.join(TRANSLATIONS, '*', f'{locale}.po')
    files = sorted(glob.glob(pattern))
    for path in files:
        for e in parse_po(path):
            if e.is_header or not e.msgid:
                continue
            n = count_words(e.msgid)
            if e.msgid_plural:
                n += count_words(e.msgid_plural)
            total += n
            if e.translated:
                translated += n
    return len(files), total, translated


def read_stats():
    section = None
    data = {}
    with open(STATS, encoding='utf-8') as fh:
        for line in fh:
            s = line.strip()
            if s.startswith('[') and s.endswith(']'):
                section = s[1:-1]
            elif '=' in s and section:
                k, v = s.split('=', 1)
                data.setdefault(section, {})[k.strip()] = v.strip()
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='只比对口径，不改文件')
    ap.add_argument('--locale', default='zh_CN')
    args = ap.parse_args()

    existing = read_stats()
    declared_total = int(existing.get('global', {}).get('total', 0))
    declared_tr = int(existing.get(args.locale, {}).get('translated', 0))

    n_files, total, translated = tally(args.locale)
    drift = abs(total - declared_total) / declared_total * 100 if declared_total else 0

    print(f'{args.locale}：{n_files} 个域')
    print(f'  本脚本算得 total       = {total}')
    print(f'  文件中声明 global.total = {declared_total}  （相差 {drift:.1f}%）')
    print(f'  本脚本算得 translated  = {translated}  ({100*translated/total:.1f}%)')
    print(f'  文件中现有 translated  = {declared_tr}  ({100*declared_tr/declared_total:.1f}%)')

    if drift > 3:
        print('\n口径与上游不一致（total 相差超过 3%），不改写文件。', file=sys.stderr)
        return 1
    if args.check:
        return 0

    with open(STATS, encoding='utf-8', newline='') as fh:
        lines = fh.readlines()
    out = []
    in_section = False
    changed = False
    for line in lines:
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            in_section = (s == f'[{args.locale}]')
        elif in_section and s.startswith('translated'):
            nl = '\r\n' if line.endswith('\r\n') else '\n'
            out.append(f'translated={translated}{nl}')
            changed = True
            continue
        out.append(line)

    if not changed:
        print(f'未找到 [{args.locale}] 一节的 translated 项', file=sys.stderr)
        return 1

    with open(STATS, 'w', encoding='utf-8', newline='') as fh:
        fh.writelines(out)
    print(f'\n已更新：{declared_tr} -> {translated}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
