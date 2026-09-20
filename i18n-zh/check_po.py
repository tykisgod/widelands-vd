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
    __slots__ = ('line', 'ctxt', 'msgid', 'msgid_plural', 'msgstrs',
                 'flags', 'comments', 'ref')

    def __init__(self, line: int):
        self.line = line
        self.ctxt = ''
        self.msgid = ''
        self.msgid_plural = ''
        self.msgstrs: list[str] = []
        self.flags: list[str] = []
        self.comments: list[str] = []      # #. 译者注释
        self.ref: list[str] = []           # #: 源码位置

    @property
    def is_header(self) -> bool:
        return not self.msgid and not self.ctxt

    @property
    def translated(self) -> bool:
        return any(s.strip() for s in self.msgstrs)

    @property
    def key(self) -> tuple:
        """gettext 的条目身份：上下文 + 单数原文 + 复数原文。"""
        return (self.ctxt, self.msgid, self.msgid_plural)


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
                elif s.startswith('#:'):
                    cur.ref.append(s[2:].strip())
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

MSG_FLAGS = '-+0'
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


class FormatSpec:
    """一个格式说明符。kind 为 None 表示 %N% 形式（只声明参数位，不声明类型）。"""
    __slots__ = ('raw', 'index', 'kind')

    def __init__(self, raw, index, kind):
        self.raw = raw
        self.index = index
        self.kind = kind


def parse_format_string(s):
    """按 Widelands 自有文法解析，返回 (specs, errors)。

    文法见 src/base/format/tree.h:40-75，约束实现在 tree.cc:155-245：

        %N%
      或
        % [N$] [flags] [width] [.precision] fmt

    与标准 printf 的差异，每一条都会影响校验：
      * %N% 是"第 N 个参数"，不是字面百分号。本项目目录里大量使用
        （%1% 出现 27 次、%2% 23 次、%1%:%2% 10 次）
      * 编号与不编号的占位符不能混用；编号 1 起，不得有空缺或重复
      * flags 只有 - + 0，且 - 与 0 不能并用
      * 支持 %b（布尔）与 %P；不支持 %o %e %E %g %G %a %A %n
      * 整数、十六进制、指针不得带精度；%c 不得带任何修饰
    """
    specs = []
    errors = []
    i = 0
    n = len(s)
    while True:
        j = s.find('%', i)
        if j < 0:
            break
        i = j + 1
        if i >= n:
            errors.append("以孤立的 '%' 结尾")
            break
        if s[i] == '%':          # %% 字面百分号，不占参数
            i += 1
            continue

        start = j
        k = i
        while k < n and s[k].isdigit():
            k += 1

        if k > i and k < n and s[k] == '%':      # %N%
            specs.append(FormatSpec(s[start:k + 1], int(s[i:k]), None))
            i = k + 1
            continue

        index = None
        if k > i and k < n and s[k] == '$':
            index = int(s[i:k])
            i = k + 1

        flags = ''
        while i < n and s[i] in MSG_FLAGS:
            flags += s[i]
            i += 1
        width = ''
        while i < n and s[i].isdigit():
            width += s[i]
            i += 1
        precision = None
        if i < n and s[i] == '.':
            i += 1
            digits = ''
            while i < n and s[i].isdigit():
                digits += s[i]
                i += 1
            if not digits:
                errors.append(f"{s[start:i]!r}：'.' 后缺少数字")
                continue
            precision = int(digits)

        ell = 0
        while i < n and s[i] == 'l':
            ell += 1
            i += 1
        if i >= n:
            errors.append(f'{s[start:]!r}：格式说明符不完整')
            break

        ch = s[i]
        i += 1
        raw = s[start:i]

        if '-' in flags and '0' in flags:
            errors.append(f"{raw!r}：'-' 与 '0' 不能并用")

        if ell:
            if ch not in 'diu':
                errors.append(f"{raw!r}：'l' 之后只能是 d/i/u")
                continue
        if ch == '%':
            errors.append(f'{raw!r}：字面百分号不接受编号或修饰，应写作 %%')
            continue
        if ch == 'c':
            if flags or width or precision is not None:
                errors.append(f'{raw!r}：%c 不能带任何修饰')
            kind = 'c'
        elif ch in 'sb':
            if '+' in flags or '0' in flags:
                errors.append(f"{raw!r}：%{ch} 不能带 '+' 或 '0'")
            kind = ch
        elif ch in 'di':
            if precision is not None:
                errors.append(f'{raw!r}：整数不能带精度')
            kind = 'int'
        elif ch == 'u':
            if precision is not None:
                errors.append(f'{raw!r}：整数不能带精度')
            kind = 'uint'
        elif ch in 'xX':
            if precision is not None:
                errors.append(f'{raw!r}：整数不能带精度')
            kind = ch
        elif ch in 'pP':
            if precision is not None:
                errors.append(f'{raw!r}：指针不能带精度')
            kind = ch
        elif ch == 'f':
            kind = 'f'
        else:
            errors.append(f'{raw!r}：不支持的格式类型字符 {ch!r}')
            continue

        specs.append(FormatSpec(raw, index, kind))

    numbered = [sp for sp in specs if sp.index is not None]
    if numbered and len(numbered) != len(specs):
        errors.append('编号与不编号的占位符不能混用')
    if numbered:
        idxs = [sp.index for sp in numbered]
        uniq = sorted(set(idxs))
        if len(uniq) != len(idxs):
            dup = sorted({x for x in idxs if idxs.count(x) > 1})
            errors.append(f'参数编号重复：{dup}')
        elif uniq != list(range(1, len(uniq) + 1)):
            errors.append(f'参数编号有空缺或不从 1 起：{uniq}')

    return specs, errors


def mask_specs(s, fill=''):
    """把格式说明符替换掉，便于判断"剩下的文字"是否像英文、标点是否合规。

    %% 也一并处理：它是字面百分号，不该被当成待翻译的英文内容。
    """
    specs, _ = parse_format_string(s)
    out = s
    for sp in sorted(specs, key=lambda x: -len(x.raw)):
        out = out.replace(sp.raw, fill)
    return out.replace('%%', fill)


def arg_signature(specs):
    """参数位 -> 类型。不编号的按从左到右枚举，使重排序的译文能正确比对。"""
    sig = {}
    if any(sp.index is not None for sp in specs):
        for sp in specs:
            if sp.index is not None and sig.get(sp.index) is None:
                sig[sp.index] = sp.kind
    else:
        for pos, sp in enumerate(specs, 1):
            sig[pos] = sp.kind
    return sig


def check_placeholders(e, path, out):
    """占位符必须与原文引用同一组参数，且自身合乎文法。

    损坏的占位符不是"显示错乱"而已：格式引擎记录日志后**重新抛出**
    （tree.h:346-350），经 lua_globals.cc:172-175 转为 Lua 错误，会中断
    当前流程。
    """
    src_specs, src_errors = parse_format_string(e.msgid)
    if e.msgid_plural:
        # 中文 nplurals=1，msgstr[0] 对应的语义取单复数原文的并集
        pl_specs, _ = parse_format_string(e.msgid_plural)
        if len(pl_specs) > len(src_specs):
            src_specs = pl_specs
    want = arg_signature(src_specs)

    for i, got_str in enumerate(e.msgstrs):
        if not got_str.strip():
            continue
        got_specs, errors = parse_format_string(got_str)
        for msg in errors:
            out.append(Problem('error', path, e.line, 'placeholder-syntax',
                               f'msgstr[{i}] {msg}', e.msgid))
        got = arg_signature(got_specs)

        if set(got) != set(want):
            missing = sorted(set(want) - set(got))
            extra = sorted(set(got) - set(want))
            parts = []
            if missing:
                parts.append('缺少参数位 ' + ', '.join(map(str, missing)))
            if extra:
                parts.append('多出参数位 ' + ', '.join(map(str, extra)))
            out.append(Problem('error', path, e.line, 'placeholder',
                               f'msgstr[{i}] 与原文引用的参数不一致：'
                               + '；'.join(parts), e.msgid))
            continue

        for idx in sorted(want):
            a, b = want[idx], got[idx]
            if a is not None and b is not None and a != b:
                out.append(Problem('error', path, e.line, 'placeholder-type',
                                   f'msgstr[{i}] 参数 {idx} 的类型由 {a} 变为 {b}',
                                   e.msgid))


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
        # 无 CJK 才继续判断：纯符号/纯占位符/纯标记的条目合法。
        # 标记必须一并剥掉，否则 "%1$s<br>（%2$s）" 会因 "br" 被当成英文单词
        # 而误判为漏译。
        stripped = TAG_RE.sub('', mask_specs(got))
        if not ASCII_WORD.search(stripped):
            continue
        # 原文本身就没有英文单词（如 "%s"）则不算漏译
        if not ASCII_WORD.search(mask_specs(e.msgid)):
            continue
        out.append(Problem('error', path, e.line, 'untranslated',
                           f'msgstr[{i}] 无中文字符，疑似漏译：{got!r}', e.msgid))


def check_punctuation(e, path, out):
    """中文文案里的半角标点。占位符与英文标识符紧邻处不报。"""
    for i, got in enumerate(e.msgstrs):
        if not CJK.search(got):
            continue
        masked = mask_specs(got, '\x00')
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


# Widelands 富文本渲染器实际认识的标签。其余尖括号构造（<name>、<reason>、
# <msg>、<user> 等）是命令行元变量或占位说明，不是标记，必须忽略——否则
# 通用的"标签配对"规则会在本目录上产生大量误报（实测 48 处尖括号构造里
# 只有 4 处是真标记）。
#   成对：rt_parse.cc:280-287,341-360,380-407,448-455,505-512,554-594
#   注册：rt_render.cc:1869-1884
RICHTEXT_TAGS = ('rt', 'div', 'p', 'font', 'link', 'br', 'space', 'vspace', 'img')
TAG_RE = re.compile(r'</?([A-Za-z][A-Za-z0-9_-]*)\b[^>]*>')


def check_markup(e, path, out):
    """真标记的数量必须与原文一致。

    结构被破坏不是小事：rt_parse.cc:111-121 会抛 SyntaxError，未知标签则由
    rt_render.cc:1880-1884 抛 RenderError；部分控件会捕获并降级，但工具提示
    等路径不会。
    """
    def tally(s):
        c = Counter()
        for name in TAG_RE.findall(s):
            low = name.lower()
            if low in RICHTEXT_TAGS:
                c[low] += 1
        return c

    src = tally(e.msgid)
    if e.msgid_plural:
        src |= tally(e.msgid_plural)
    if not src:
        return

    for i, got in enumerate(e.msgstrs):
        if not got.strip():
            continue
        dst = tally(got)
        if dst == src:
            continue
        diffs = []
        for name in sorted(set(src) | set(dst)):
            if src[name] != dst[name]:
                diffs.append(f'<{name}> 原文 {src[name]} 处、译文 {dst[name]} 处')
        out.append(Problem('error', path, e.line, 'markup',
                           f'msgstr[{i}] 富文本标记数量不符：' + '；'.join(diffs),
                           e.msgid))


def check_fuzzy(e, path, out):
    """fuzzy 译文会被游戏当作正式译文显示给玩家——这与 gettext 的常识相反。

    Widelands 运行时直接解析 .po，没有 msgfmt 那一步，所以"msgfmt 默认丢弃
    fuzzy"的保护在这里不存在：
      po_parser.hpp:48       POParser(..., bool use_fuzzy = true)
      po_parser.cpp:41-45    静态 parse() 用三参构造，use_fuzzy 恒为 true
      po_parser.cpp:418,459  if (use_fuzzy || !fuzzy) —— 短路，fuzzy 标记失效
      dictionary_manager.cpp:165  调三参版本，其 use_fuzzy 成员是死字段
    fuzzy 是 msgmerge basedon 相似旧串的猜测，原样显示比留空回退英文更糟，
    因此定为 error 而非 warning。
    """
    if 'fuzzy' in e.flags:
        out.append(Problem('error', path, e.line, 'fuzzy',
                           'fuzzy 译文会被游戏原样显示（tinygettext use_fuzzy '
                           '默认 true），必须核对后清除该标记', e.msgid))


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
          check_untranslated, check_punctuation, check_trailing_space,
          check_markup, check_fuzzy]


def count_obsolete(path):
    """'#~' 废弃条目。运行时无风险（tinygettext 当普通注释整块忽略，
    po_parser.cpp:355），但它是"上游删过串、此 po 被合并过"的信号。"""
    n = 0
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            if line.lstrip().startswith('#~'):
                n += 1
    return n


def check_pot_sync(po_path, pot_path, po_entries, out):
    """po 与 pot 的键集必须双向一致。

    这取代了"条目数等于某个固定数字"的验收方式。固定数字只能抓住四种
    失效里的一种：上游增删串而未做 key 级合并时，po 的条目数和非空率都
    不变，验收静默通过，但新串在运行时全部回退英文。
    """
    if not os.path.exists(pot_path):
        out.append(Problem('error', po_path, 0, 'pot-missing',
                           f'找不到 pot 文件：{pot_path}'))
        return

    pot_keys = {e.key for e in parse_po(pot_path) if not e.is_header}
    po_keys = {e.key for e in po_entries if not e.is_header}

    only_pot = pot_keys - po_keys
    only_po = po_keys - pot_keys

    for key in sorted(only_pot)[:20]:
        out.append(Problem('error', po_path, 0, 'pot-sync',
                           f'pot 中存在但 po 缺失（运行时会回退英文）：'
                           f'ctxt={key[0]!r}', key[1]))
    if len(only_pot) > 20:
        out.append(Problem('error', po_path, 0, 'pot-sync',
                           f'……另有 {len(only_pot) - 20} 条 pot 独有键未列出'))

    for key in sorted(only_po)[:20]:
        out.append(Problem('error', po_path, 0, 'pot-sync',
                           f'po 中存在但 pot 已无（死键，上游已删除）：'
                           f'ctxt={key[0]!r}', key[1]))
    if len(only_po) > 20:
        out.append(Problem('error', po_path, 0, 'pot-sync',
                           f'……另有 {len(only_po) - 20} 条 po 独有键未列出'))

    n = count_obsolete(po_path)
    if n:
        out.append(Problem('warning', po_path, 0, 'obsolete',
                           f'存在 {n} 行 "#~" 废弃条目；运行时被忽略，'
                           f'但说明此文件被合并过，建议清理'))

    if not only_pot and not only_po:
        print(f'  pot 键集比对通过：{len(pot_keys)} 条，双向无差集')


def check_file(path, terms, require_complete, pot_path=''):
    out = []
    entries = parse_po(path)
    checked = 0
    if pot_path:
        check_pot_sync(path, pot_path, entries, out)
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
    ap.add_argument('--pot', default='',
                    help='对应的 .pot 文件；比对 (msgctxt, msgid, msgid_plural) '
                         '键集是否双向一致。--all 时自动按同目录推导')
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

    total_err = total_warn = total_entries = total_checked = total_translated = 0
    for path in files:
        pot = args.pot
        if not pot and args.all:
            # 同目录下的 <域名>.pot
            domain = os.path.basename(os.path.dirname(path))
            candidate = os.path.join(os.path.dirname(path), domain + '.pot')
            pot = candidate if os.path.exists(candidate) else ''
        entries, checked, problems = check_file(path, terms, args.require_complete, pot)
        errs = [p for p in problems if p.level == 'error']
        warns = [p for p in problems if p.level == 'warning']
        total_err += len(errs)
        total_warn += len(warns)
        total_entries += sum(1 for e in entries if not e.is_header)
        total_translated += sum(1 for e in entries if not e.is_header and e.translated)
        total_checked += checked

        if not args.quiet:
            for p in errs + warns:
                print(p)
        if errs or warns:
            rel = os.path.relpath(path)
            print(f'  -> {rel}: {len(errs)} error, {len(warns)} warning '
                  f'（已检查 {checked} 条译文）\n')

    pct = 100 * total_translated / total_entries if total_entries else 0
    print(f'=== 共 {len(files)} 个文件，{total_entries} 条，已译 {total_translated} 条 '
          f'({pct:.1f}%)，已检查 {total_checked} 条 '
          f'| {total_err} error, {total_warn} warning ===')
    return 1 if total_err else 0


if __name__ == '__main__':
    sys.exit(main())
