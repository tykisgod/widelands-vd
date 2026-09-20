import sys
sys.path.insert(0, 'i18n-zh')
from check_po import parse_format_string, arg_signature

cases = [
    ('%s',            'ok 1 个无编号 string'),
    ('%1$s and %2$s', 'ok 编号 1,2'),
    ('%1%:%2%',       'ok Widelands 专有 %N% 形式'),
    ('%i%%',          'ok 整数 + 字面百分号'),
    ('%.2f',          'ok 浮点带精度'),
    ('%li',           'ok 长整型'),
    ('%b',            'ok 布尔（旧正则漏掉）'),
    ('%P',            'ok 大写指针（旧正则漏掉）'),
    ('%1$s %s',       'ERR 编号与不编号混用'),
    ('%1$s %3$s',     'ERR 编号有空缺'),
    ('%1$s %1$s',     'ERR 编号重复'),
    ('%.2d',          'ERR 整数不能带精度'),
    ('%-0s',          'ERR - 与 0 不能并用'),
    ('%5c',           'ERR %c 不能带修饰'),
    ('%o',            'ERR 不支持的类型 o'),
    ('%lx',           'ERR l 之后只能是 d/i/u'),
]
for s, note in cases:
    specs, errs = parse_format_string(s)
    sig = arg_signature(specs)
    status = 'ERR: ' + '; '.join(errs) if errs else f'OK  sig={sig}'
    print(f'  {s:<16} {status:<50} <- {note}')

print()
print('重排序应视为等价：')
a, _ = parse_format_string('%s costs %d')
b, _ = parse_format_string('%2$d 元买 %1$s')
print('  原文 sig =', arg_signature(a))
print('  译文 sig =', arg_signature(b))
print('  一致 ->', arg_signature(a) == arg_signature(b))
