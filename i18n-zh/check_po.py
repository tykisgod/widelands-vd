#!/usr/bin/env python3
"""Widelands 简体中文译文静态校验。

用法:
    python i18n-zh/check_po.py data/i18n/translations/widelands/zh_CN.po
    python i18n-zh/check_po.py --all          # 校验全部 32 个域
    python i18n-zh/check_po.py <po> --glossary i18n-zh/glossary.tsv

退出码 0 表示无 error 级问题。warning 不影响退出码。

设计要点：不依赖 polib 等第三方库，因为本仓库的 CI 与本地环境都只保证
有标准库。po 解析器与 extract_glossary.py 共用同一份实现。
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from collections import Counter

# ---------------------------------------------------------------- po 解析

ESCAPES = {'\\n': '\n', '\\t': '\t', '\\r': '\r', '\\"': '"', '\\\\': '\\'}


def unescape(s: str) -> str:
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


class Entry:
    __slots__ = ('line', 'ctxt', 'msgid', 'msgid_plural', 'msgstrs', 'flags', 'comments')

    def __init__(self, line: int):
        self.line = line
        self.ctxt = ''
        self.msgid = ''
        self.msgid_plural = ''
        self.msgstrs: list[str] = []
        self.flags: list[str] = []
        self.comments: list[str] = []

    @property
    def is_header(self) -> bool:
        return not self.msgid and not self.ctxt

    @property
    def translated(self) -> bool:
        return any(s.strip() for s in self.msgstrs)


def parse_po(path: str):
    """按空行切分条目，返回 Entry 列表。容忍 CRLF。"""
    entries = []
    cur = Entry(0)
    target = None          # 当前续行拼接到哪个字段
    plural_idx = None
    started = False

    def commit():
        nonlocal cur, started, target, plural_idx
        if started:
            entries.append(cur)
        cur = Entry(0)
        started = False
        target = None
        plural_idx = None

    with open(path, encoding='utf-8') as fh:
        for lineno, raw in enumerate(fh, 1):
            s = raw.strip()
            if not s:
                commit()
                continue
            if not started:
                cur.line = lineno
            if s.startswith('#'):
                if s.startswith('#,'):
                    cur.flags += [f.strip() for f in s[2:].split(',')]
                elif s.startswith('#.'):
                    cur.comments.append(s[2:].strip())
                target = None
                continue

            if s.startswith('msgctxt'):
                started, target, payload = True, 'ctxt', s[7:]
            elif s.startswith('msgid_plural'):
                started, target, payload = True, 'msgid_plural', s[12:]
            elif s.startswith('msgid'):
                started, target, payload = True, 'msgid', s[5:]
            elif s.startswith('msgstr['):
                bracket = s.index(']')
                plural_idx = int(s[7:bracket])
                while len(cur.msgstrs) <= plural_idx:
                    cur.msgstrs.append('')
                started, target, payload = True, 'msgstr_n', s[bracket + 1:]
            elif s.startswith('msgstr'):
                if not cur.msgstrs:
                    cur.msgstrs.append('')
                plural_idx = 0
                started, target, payload = True, 'msgstr_n', s[6:]
            elif s.startswith('"'):
                payload = s
            else:
                target = None
                continue

            if target is None:
                continue
            body = payload.strip()
            if not (body.startswith('"') and body.endswith('"') and len(body) >= 2):
                continue
            text = unescape(body[1:-1])
            if target == 'msgstr_n':
                cur.msgstrs[plural_idx] += text
            else:
                setattr(cur, target, getattr(cur, target) + text)
    commit()
    return entries


# ---------------------------------------------------------------- 检查项

# printf 占位符：%s %d %u %1$s %2.1f %% 等
PLACEHOLDER = re.compile(r'%(?:\d+\$)?[-+ #0]*[\d*]*(?:\.[\d*]+)?(?:hh|h|ll|l|L|z|j|t)?[diouxXeEfFgGaAcspn%]')
# Widelands 自有的 bformat 占位符
BFORMAT = re.compile(r'%\d+\$')
CJK = re.compile(r'[㐀-䶿一-鿿豈-﫿]')
ASCII_WORD = re.compile(r"[A-Za-z]{2,}")
# 中文里不该出现的半角标点（占位符与代码标识符旁除外，见 check_punctuation）
HALFWIDTH = {',': '，', ';': '；', '?': '？', '!': '！'}


class Problem:
    def __init__(self, level, path, line, kind, msg, msgid=''):
        self.level = level
        self.path = path
        self.line = line
        self.kind = kind
        self.msg = msg
        self.msgid = msgid

    def __str__(self):
        head = f'{self.path}:{self.line}: {self.level}: [{self.kind}] {self.msg}'
        if self.msgid:
            snippet = self.msgid if len(self.msgid) <= 60 else self.msgid[:57] + '...'
            head += f'\n    msgid: {snippet!r}'
        return head


def check_placeholders(e, path, out):
    """占位符的种类、数量、参数编号必须与原文完全一致。错一个会让游戏崩溃。"""
    sources = [e.msgid] + ([e.msgid_plural] if e.msgid_plural else [])
    # 中文 nplurals=1，单复数共用 msgstr[0]，故取原文占位符的并集作为允许集
    want = Counter()
    for src in sources:
        want |= Counter(PLACEHOLDER.findall(src))

    for i, got_str in enumerate(e.msgstrs):
        if not got_str.strip():
            continue
        got = Counter(PLACEHOLDER.findall(got_str))
        if got == want:
            continue
        missing = want - got
        extra = got - want
        parts = []
        if missing:
            parts.append('缺少 ' + ', '.join(sorted(missing.elements())))
        if extra:
            parts.append('多出 ' + ', '.join(sorted(extra.elements())))
        out.append(Problem('error', path, e.line, 'placeholder',
                           f'msgstr[{i}] 占位符与原文不符：' + '；'.join(parts), e.msgid))

    # 带编号的占位符必须连续覆盖 1..n，否则 bformat 会抛异常
    for i, got_str in enumerate(e.msgstrs):
        nums = sorted({int(m[1:-1]) for m in BFORMAT.findall(got_str)})
        if nums and nums != list(range(1, len(nums) + 1)):
            out.append(Problem('error', path, e.line, 'placeholder-index',
                               f'msgstr[{i}] 位置参数编号不连续：{nums}', e.msgid))


def check_escapes(e, path, out):
    """换行数量必须一致——多一个少一个都会让 UI 布局错位。"""
    for i, got in enumerate(e.msgstrs):
        if not got.strip():
            continue
        src = e.msgid_plural if (e.msgid_plural and i > 0) else e.msgid
        if src.count('\n') != got.count('\n'):
            out.append(Problem('error', path, e.line, 'newline',
                               f'msgstr[{i}] 换行数 {got.count(chr(10))} 与原文 {src.count(chr(10))} 不符',
                               e.msgid))


def check_plural(e, path, out):
    """中文 nplurals=1：有 msgid_plural 的条目只能有 msgstr[0]。"""
    if not e.msgid_plural:
        return
    if len(e.msgstrs) > 1:
        out.append(Problem('error', path, e.line, 'plural',
                           f'中文 nplurals=1，应只有 msgstr[0]，实际有 {len(e.msgstrs)} 个', e.msgid))


def load_keep_english(path):
    """合法保持英文的 msgid 集合。"""
    keep = set()
    if not path or not os.path.exists(path):
        return keep
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.rstrip('\n')
            if line.strip() and not line.startswith('#'):
                keep.add(line)
    return keep


KEEP_ENGLISH: set[str] = set()


def check_untranslated(e, path, out):
    """msgstr 仍是纯英文——漏译或误把原文抄了一遍。"""
    if e.msgid in KEEP_ENGLISH:
        return
    for i, got in enumerate(e.msgstrs):
        got = got.strip()
        if not got:
            out.append(Problem('error', path, e.line, 'empty',
                               f'msgstr[{i}] 为空', e.msgid))
            continue
        if CJK.search(got):
            continue
        # 无 CJK 才继续判断：纯符号/纯占位符/纯数字的条目合法
        stripped = PLACEHOLDER.sub('', got)
        if not ASCII_WORD.search(stripped):
            continue
        # 原文本身就没有英文单词（如 "%s"）则不算漏译
        if not ASCII_WORD.search(PLACEHOLDER.sub('', e.msgid)):
            continue
        out.append(Problem('error', path, e.line, 'untranslated',
                           f'msgstr[{i}] 无中文字符，疑似漏译：{got!r}', e.msgid))


def check_punctuation(e, path, out):
    """中文文案里的半角标点。占位符与英文标识符紧邻处不报。"""
    for i, got in enumerate(e.msgstrs):
        if not CJK.search(got):
            continue
        masked = PLACEHOLDER.sub('\x00', got)
        for pos, ch in enumerate(masked):
            if ch not in HALFWIDTH:
                continue
            prev = masked[pos - 1] if pos else ''
            nxt = masked[pos + 1] if pos + 1 < len(masked) else ''
            # 夹在 ASCII / 占位符之间的半角标点是合理的
            if (prev.isascii() and prev.isalnum()) or (nxt.isascii() and nxt.isalnum()):
                continue
            if prev == '\x00' or nxt == '\x00':
                continue
            out.append(Problem('warning', path, e.line, 'punctuation',
                               f'msgstr[{i}] 中文文案内出现半角 {ch!r}，建议用 {HALFWIDTH[ch]!r}', e.msgid))
            break


def check_trailing_space(e, path, out):
    """首尾空白必须与原文一致——UI 拼接依赖它。"""
    for i, got in enumerate(e.msgstrs):
        if not got.strip():
            continue
        src = e.msgid_plural if (e.msgid_plural and i > 0) else e.msgid
        if (src[:1] == ' ') != (got[:1] == ' ') or (src[-1:] == ' ') != (got[-1:] == ' '):
            out.append(Problem('warning', path, e.line, 'whitespace',
                               f'msgstr[{i}] 首尾空白与原文不一致', e.msgid))


def check_fuzzy(e, path, out):
    if 'fuzzy' in e.flags:
        out.append(Problem('warning', path, e.line, 'fuzzy',
                           'fuzzy 标记未清除，游戏不会使用该译文', e.msgid))


def load_glossary(path):
    """TSV: 英文 <TAB> 中文 <TAB> msgctxt <TAB> 出处 <TAB> 备注"""
    terms = {}
    if not path or not os.path.exists(path):
        return terms
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            if not line.strip() or line.startswith('#'):
                continue
            cols = line.rstrip('\n').split('\t')
            if len(cols) < 2 or not cols[0] or not cols[1]:
                continue
            terms[(cols[0], cols[2] if len(cols) > 2 else '')] = cols[1]
    return terms


def check_glossary(e, path, terms, out):
    """原文整体命中术语表时，译文必须与表一致。"""
    if not terms:
        return
    want = terms.get((e.msgid, e.ctxt)) or terms.get((e.msgid, ''))
    if not want:
        return
    got = e.msgstrs[0] if e.msgstrs else ''
    if got.strip() and got != want:
        out.append(Problem('error', path, e.line, 'glossary',
                           f'与术语表不符：应为 {want!r}，实际 {got!r}', e.msgid))


CHECKS = [check_placeholders, check_escapes, check_plural,
          check_untranslated, check_punctuation, check_trailing_space, check_fuzzy]


def check_file(path, terms, require_complete):
    out = []
    entries = parse_po(path)
    checked = 0
    for e in entries:
        if e.is_header:
            continue
        if not e.translated and not require_complete:
            continue        # 未译条目在补全前不报，避免淹没真实问题
        checked += 1
        for fn in CHECKS:
            fn(e, path, out)
        check_glossary(e, path, terms, out)
    return entries, checked, out


def main():
    ap = argparse.ArgumentParser(description='Widelands 简体中文译文校验')
    ap.add_argument('files', nargs='*', help='po 文件路径')
    ap.add_argument('--all', action='store_true', help='校验全部 32 个域的 zh_CN.po')
    ap.add_argument('--glossary', default='', help='术语表 TSV')
    ap.add_argument('--keep-english', default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'keep-english.txt'),
        help='合法保持英文的 msgid 清单')
    ap.add_argument('--require-complete', action='store_true',
                    help='把未译条目也算作 error（验收阶段用）')
    ap.add_argument('--quiet', action='store_true', help='只输出汇总')
    args = ap.parse_args()

    files = list(args.files)
    if args.all:
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        files += sorted(glob.glob(os.path.join(root, 'data/i18n/translations/*/zh_CN.po')))
    if not files:
        ap.error('未指定文件；用 --all 校验全部域')

    global KEEP_ENGLISH
    KEEP_ENGLISH = load_keep_english(args.keep_english)

    terms = load_glossary(args.glossary)
    if terms:
        print(f'术语表载入 {len(terms)} 条')
    if KEEP_ENGLISH:
        print(f'保持英文清单载入 {len(KEEP_ENGLISH)} 条')
    print()

    total_err = total_warn = total_entries = total_checked = 0
    for path in files:
        entries, checked, problems = check_file(path, terms, args.require_complete)
        errs = [p for p in problems if p.level == 'error']
        warns = [p for p in problems if p.level == 'warning']
        total_err += len(errs)
        total_warn += len(warns)
        total_entries += sum(1 for e in entries if not e.is_header)
        total_checked += checked

        if not args.quiet:
            for p in errs + warns:
                print(p)
        if errs or warns:
            rel = os.path.relpath(path)
            print(f'  -> {rel}: {len(errs)} error, {len(warns)} warning '
                  f'（已检查 {checked} 条译文）\n')

    print(f'=== 共 {len(files)} 个文件，{total_entries} 条，已译 {total_checked} 条 '
          f'| {total_err} error, {total_warn} warning ===')
    return 1 if total_err else 0


if __name__ == '__main__':
    sys.exit(main())
