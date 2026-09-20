#!/usr/bin/env python3
"""把导出的批次以紧凑形式打印，供翻译时阅读。

只显示真正影响译法的信息：原文、复数原文、msgctxt、译者注释、界面位置、
术语表命中、现有译文。注释与原文都不截断——截断会导致误译。
"""
import json
import sys

path = sys.argv[1]
start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
end = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9

data = json.load(open(path, encoding='utf-8'))
for it in data[start:end]:
    print(f"{it['key']} {it['msgid']!r}")
    if it.get('msgid_plural'):
        print(f"    复数 {it['msgid_plural']!r}")
    if it.get('msgctxt'):
        print(f"    ctxt {it['msgctxt']}")
    if it.get('note'):
        print(f"    注释 {it['note']}")
    if it.get('ui'):
        print(f"    界面 {it['ui']}")
    if it.get('terms'):
        print(f"    术语 {'; '.join(it['terms'])}")
    if it.get('current'):
        print(f"    现译 {it['current']!r}")
print(f'--- 共 {len(data[start:end])} 条 ---')
