#!/usr/bin/env python3
"""把上游 widelands/widelands 的改动同步进本 fork 的 zh-CN 分支。

    python i18n-zh/sync-upstream.py            # 只看有什么要同步，不改工作区
    python i18n-zh/sync-upstream.py --apply    # 真的做合并，改动留在工作区不提交
    python i18n-zh/sync-upstream.py --apply --commit

为什么是 merge 不是 rebase
==========================
zh-CN 领先上游的提交里有 36 个改过 zh_CN.po，涉及 31 个文件。rebase 会把这
36 个提交逐个重放到新的上游之上，上游只要动过同一批文件，冲突就要解 36 次；
而且 rebase 重写历史，公开的默认分支必须 force-push，别人克隆过的副本全废。
merge 只有一个合并点，冲突解一次，不重写历史。

还有一条：`--ours` / `--theirs` 在 rebase 期间的含义与平时相反（ours 是被
rebase 到的上游，theirs 才是本方）。选反了会直接销毁全部译文。merge 里两者
是直觉含义——ours 就是 zh-CN 本方——这个坑自动消失。

.po 不能做行级三方合并
======================
上游本地不跑 msgmerge，合并发生在 Transifex 服务端（utils/buildcat.py 里带
msgmerge 的函数是无调用者的死代码，真实链路在 merge_and_push_translations.sh）。
fork 拿不到这一步，所以必须自己补做 **key 级合并**：

    新 pot 的键集  +  本方 po 的译文  ->  新 po

只按键匹配，不做行级 diff，也不做模糊匹配（--nofuzzymatching）。上游新增的
串会成为空条目，由 check_po.py 报出来，等人来翻译；上游删掉的串自动消失。

冲突处理策略（确定性，不需要人判断）
====================================
    */zh_CN.po              取本方  —— 译文是我们的产出
    */*.pot                 取上游  —— pot 是 buildcat.py 从源码自动生成的
    translation_stats.conf  取本方  —— 之后由 update_stats.py 重算
    其他任何文件冲突         中止    —— 说明上游改了我们也改过的代码，要人看
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TRANSLATIONS = os.path.join(REPO, 'data', 'i18n', 'translations')
LOCALE = 'zh_CN'
UPSTREAM = 'upstream/master'   # 可用 --upstream 覆盖，便于自测


def git(*args, check=True, quiet=False):
    r = subprocess.run(['git', '-C', REPO, *args],
                       capture_output=True, text=True, encoding='utf-8')
    if check and r.returncode != 0:
        if not quiet:
            sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f'git {" ".join(args)} 失败（退出码 {r.returncode}）')
    return r


def out(*args):
    return git(*args).stdout.strip()


def domains():
    """返回 (域名, pot 路径, po 路径)，以工作区现有目录为准。"""
    for name in sorted(os.listdir(TRANSLATIONS)):
        d = os.path.join(TRANSLATIONS, name)
        if not os.path.isdir(d):
            continue
        yield name, os.path.join(d, name + '.pot'), os.path.join(d, LOCALE + '.po')


def find_pot2po():
    exe = shutil.which('pot2po')
    if exe:
        return [exe]
    # Windows 上 pip 装的脚本常常不在 PATH 里
    cand = os.path.join(os.path.dirname(sys.executable), 'Scripts', 'pot2po.exe')
    if os.path.exists(cand):
        return [cand]
    try:
        subprocess.run([sys.executable, '-m', 'translate.tools.pot2po', '--version'],
                       capture_output=True, check=True)
        return [sys.executable, '-m', 'translate.tools.pot2po']
    except Exception:
        raise SystemExit(
            '找不到 pot2po。key 级合并靠它完成，先装：\n'
            '    python -m pip install translate-toolkit')


def survey():
    """看上游有什么新东西。返回落后的提交数。"""
    if UPSTREAM.startswith('upstream/'):
        git('fetch', 'upstream', '--quiet')
    behind = int(out('rev-list', '--count', f'HEAD..{UPSTREAM}'))
    ahead = int(out('rev-list', '--count', f'{UPSTREAM}..HEAD'))
    print(f'zh-CN 相对 {UPSTREAM}：落后 {behind} 个提交，领先 {ahead} 个')
    if not behind:
        print('已是最新，无需同步。')
        return 0

    base = out('merge-base', 'HEAD', UPSTREAM)
    print(f'\n上游新提交（{behind} 个，最近 15 条）：')
    for line in out('log', '--oneline', '-15', f'{base}..{UPSTREAM}').splitlines():
        print('  ' + line)

    i18n = out('diff', '--name-only', f'{base}..{UPSTREAM}',
               '--', 'data/i18n').splitlines()
    pots = [f for f in i18n if f.endswith('.pot')]
    print(f'\n其中动到 data/i18n 的文件 {len(i18n)} 个，pot {len(pots)} 个')
    if pots:
        print('pot 有变动 —— 需要做 key 级合并，可能有新串要翻译：')
        for f in pots[:10]:
            print('  ' + f)
    return behind


def resolve_conflicts():
    """按确定性策略解冲突。有策略覆盖不到的冲突就中止。"""
    conflicted = [l[3:] for l in out('status', '--porcelain').splitlines()
                  if l[:2] in ('UU', 'AA', 'UD', 'DU', 'AU', 'UA', 'DD')]
    if not conflicted:
        return

    print(f'\n冲突 {len(conflicted)} 个文件，按策略处理：')
    unexpected = []
    for f in conflicted:
        if f.endswith(f'/{LOCALE}.po'):
            git('checkout', '--ours', '--', f)      # merge 里 ours = zh-CN 本方
            git('add', '--', f)
            print(f'  取本方  {f}')
        elif f.endswith('.pot'):
            git('checkout', '--theirs', '--', f)
            git('add', '--', f)
            print(f'  取上游  {f}')
        elif f.endswith('translation_stats.conf'):
            git('checkout', '--ours', '--', f)
            git('add', '--', f)
            print(f'  取本方  {f}（稍后重算）')
        else:
            unexpected.append(f)

    if unexpected:
        print('\n以下冲突没有既定策略，说明上游改了我们也改过的东西，需要人看：')
        for f in unexpected:
            print('  ' + f)
        print('\n工作区停在合并中间状态。处理完后 git add 再 git commit，'
              '或者 git merge --abort 回退。')
        raise SystemExit(2)


def untranslated_map():
    """每个域的未译 msgid 集合。用来算出上游这次新加了哪些串。"""
    sys.path.insert(0, HERE)
    import importlib
    cp = importlib.import_module('check_po')
    importlib.reload(cp)
    result = {}
    for name, _pot, po in domains():
        if not os.path.exists(po):
            continue
        miss = set()
        for e in cp.parse_po(po):
            if e.is_header:
                continue
            if not (e.msgstrs and e.msgstrs[0].strip()):
                miss.add((e.ctxt or '', e.msgid))
        result[name] = miss
    return result


def drop_obsolete(po):
    """删掉 "#~" 废弃条目。pot2po 会把上游删掉的串留成注释，运行时被忽略，
    但会一次次累积下去，本仓库原本一条都没有。"""
    text = io.open(po, encoding='utf-8').read()
    blocks = text.split('\n\n')
    kept = [b for b in blocks
            if not any(l.startswith('#~') for l in b.splitlines())]
    if len(kept) == len(blocks):
        return 0
    io.open(po, 'w', encoding='utf-8', newline='\n').write(
        '\n\n'.join(kept).rstrip('\n') + '\n')
    return len(blocks) - len(kept)


def key_merge(pot2po):
    """用新 pot 的键集重建每个域的 zh_CN.po，保留本方译文。"""
    print('\nkey 级合并（新 pot 键集 + 本方译文）：')
    changed = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, pot, po in domains():
            if not os.path.exists(pot):
                print(f'  跳过  {name}（上游已删除该域的 pot）')
                continue
            if not os.path.exists(po):
                print(f'  新域  {name}（上游新增，将生成全空的 {LOCALE}.po）')
            dst = os.path.join(tmp, name + '.po')
            cmd = pot2po + ['--nofuzzymatching', '-i', pot, '-o', dst]
            if os.path.exists(po):
                cmd += ['-t', po]
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding='utf-8', errors='replace')
            if r.returncode != 0 or not os.path.exists(dst):
                sys.stderr.write(r.stdout + r.stderr)
                raise SystemExit(f'pot2po 在域 {name} 上失败')
            before = open(po, encoding='utf-8').read() if os.path.exists(po) else ''
            after = open(dst, encoding='utf-8').read()
            if after != before:
                shutil.copyfile(dst, po)
                changed.append(name)
    print(f'  {len(changed)} 个域的 {LOCALE}.po 有变化'
          + ('：' + ', '.join(changed) if changed else ''))

    dropped = sum(drop_obsolete(po) for n, _p, po in domains()
                  if os.path.exists(po) and (only is None or n in only))
    if dropped:
        print(f'  清掉 {dropped} 条 "#~" 废弃条目（上游已删除的串）')
    return changed


def main():
    global UPSTREAM
    ap = argparse.ArgumentParser(description='同步上游改动到 zh-CN')
    ap.add_argument('--apply', action='store_true',
                    help='真的执行合并（默认只勘察不改动）')
    ap.add_argument('--commit', action='store_true',
                    help='合并并校验通过后自动提交')
    ap.add_argument('--all-domains', action='store_true',
                    help='对全部 32 个域重跑 key 合并（默认只处理 pot 有变化的域）')
    ap.add_argument('--upstream', default=UPSTREAM,
                    help=f'要同步的上游 ref（默认 {UPSTREAM}）；自测时可指向本地分支')
    args = ap.parse_args()
    UPSTREAM = args.upstream

    behind, changed_domains = survey()
    if not behind:
        return 0
    if not args.apply:
        print('\n（这是勘察模式，没有改动任何东西。加 --apply 真的做合并。）')
        return 0

    if out('status', '--porcelain'):
        raise SystemExit('工作区不干净，先提交或清理再同步。')

    pot2po = find_pot2po()
    before_missing = untranslated_map()

    print(f'\n合并 {UPSTREAM} …')
    r = git('merge', '--no-commit', '--no-ff', UPSTREAM, check=False)
    print(r.stdout.strip() or r.stderr.strip())
    resolve_conflicts()

    # pot 无条件取上游：它是从源码自动生成的产物，本 fork 从不修改。
    # 没冲突时 merge 已经带过来了，这一步是兜底。
    git('checkout', UPSTREAM, '--', 'data/i18n/translations', check=False, quiet=True)
    git('checkout', 'HEAD', '--', f'data/i18n/translations/*/{LOCALE}.po',
        check=False, quiet=True)

    key_merge(pot2po, None if args.all_domains else changed_domains)

    print('\n重算 translation_stats.conf …')
    subprocess.run([sys.executable, os.path.join(HERE, 'update_stats.py')],
                   cwd=REPO, check=False)

    after_missing = untranslated_map()
    new_strings = []
    for name, miss in after_missing.items():
        for key in sorted(miss - before_missing.get(name, set())):
            new_strings.append((name, key))
    if new_strings:
        print(f'\n上游新增了 {len(new_strings)} 条待翻译的串：')
        for name, (ctxt, msgid) in new_strings[:20]:
            tag = f'[{ctxt}] ' if ctxt else ''
            print(f'  {name}: {tag}{msgid[:70]}')
        if len(new_strings) > 20:
            print(f'  …… 另有 {len(new_strings) - 20} 条')
    else:
        print('\n上游没有新增待翻译的串。')

    print('\n校验 …')
    # 必须带 --require-complete：check_po.py 默认跳过未译条目，
    # 不带这个开关的话上游新增的空条目会静默通过。
    check = subprocess.run(
        [sys.executable, os.path.join(HERE, 'check_po.py'),
         '--all', '--require-complete', '--quiet'],
        cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print(check.stdout.strip()[-800:])

    git('add', '-A')
    if check.returncode != 0:
        print('\n校验没过。若只是上面列出的新串没翻，翻完再提交即可；'
              '若是别的 error，先看具体报告。')
        print('改动已 git add。')
        return 1

    if args.commit:
        git('commit', '-m',
            f'Merge {UPSTREAM} into zh-CN\n\n'
            f'按 key 级合并重建各域 {LOCALE}.po，pot 取上游，'
            f'translation_stats.conf 重算。校验 0 error。')
        print('\n已提交：' + out('log', '--oneline', '-1'))
    else:
        print('\n改动已 git add，未提交。确认无误后 git commit。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
