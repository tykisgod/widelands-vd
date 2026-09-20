# Widelands 简体中文版

[Widelands](https://www.widelands.org/) 是一款自由开源的即时战略游戏，有单人战役
和多人模式，灵感来自《工人物语 II》（Settlers II™），但内容与深度远超其上。

本仓库是它的**简体中文本地化分支**，不是上游官方仓库。

## 完成度

| 范围 | 条目 | 已译 |
|---|---:|---:|
| 主界面（`widelands` 域） | 2,378 | **100%** |
| 17 个战役与教程剧本 | 2,507 | **100%** |
| 部族百科全书 | 2,339 | **100%** |
| 全部 32 个文本域 | **9,772** | **100%** |

静态校验 **0 error / 0 warning**（占位符、复数、标点、术语一致性、富文本标记、
与 pot 的键集比对等 9 项检查），实机加载验证 10/10 通过。

## 怎么玩

游戏程序和中文数据是**分开的两部分**，必须一起用。

### 1. 拿到游戏程序

从上游的 [latest 发布页](https://github.com/widelands/widelands/releases/tag/latest)
下载对应平台的 daily 构建，解压到任意目录。

> ⚠️ 这个 zip 里**只有可执行文件，没有 `data/` 目录**。直接双击
> `widelands.exe` 会闪一下就没反应——Widelands 找不到数据目录时不报错退出，
> 而是记一条日志继续跑，随后空指针崩溃。必须按下面的方式指定数据目录。

### 2. 拿到中文数据

```bash
git clone -b zh-CN https://github.com/tykisgod/widelands-vd.git
```

### 3. 启动

**Windows**——把 `widelands.exe` 和仓库的路径填进下面这行，存成 `.cmd` 双击即可
（注意批处理文件要存成 **GBK/ANSI** 编码，存成 UTF-8 的话中文注释会被 cmd.exe
读成乱码、把命令行解析搞崩）：

```bat
start "" "C:\路径\widelands.exe" "--datadir=C:\路径\widelands-vd\data" --skip_check_datadir_version --language=zh_CN
```

**Linux / macOS**：

```bash
./widelands --datadir=/路径/widelands-vd/data --skip_check_datadir_version --language=zh_CN
```

`--skip_check_datadir_version` 是必需的：源码检出里没有构建时才会生成的
`data/datadirversion`。

改完 `.po` 重启游戏即生效，**不需要编译**——Widelands 运行时用 tinygettext
直接读 `.po`，没有 msgfmt 环节。

## 译文是怎么做的

**全面重译，而非只补空缺。** 原有译文存在术语不一致与错译，只补空缺无法消除。
举几个实际改掉的：

| 原译 | 问题 | 现译 |
|---|---|---|
| `Fortress` → 哨所 | "哨所"的语义正是驻军 2 人的 `Sentry` | 要塞 |
| `Out of Fields` → 场地之外 | 把 "out of"（用尽）读成了"在……之外" | 田地已耗尽 |
| `Ferry` → 艄公 | 游戏里 Ferry 是船本身，不是划船的人 | 渡船 |
| `Food Preserver` → 食品仓库 | 这座建筑做定额口粮，既不存货也不是仓库 | 食物加工房 |
| `Charcoal Burner` → 烧炭弟 | 错字 | 烧炭工 |
| `add-on` → 附件／插件 | 同一概念两种说法 | 附加内容 |

术语由 1,548 条的术语表约束，凡收录的词条在任何域中都必须一致；每一处改动的
理由都记在 [`i18n-zh/corrections.tsv`](i18n-zh/corrections.tsv)。

**刻意保留原文的两处**，都不是漏译：

- 帝国百科里的 52 条拉丁语引文——上游注释明写 `DO NOT TRANSLATE`，游戏中紧随
  其后显示的就是它的译文
- 弗里西亚战役二中帝国总督的拉丁语台词——下一句台词正是"有人听得懂他在说
  什么吗？"，译出来这个包袱就毁了

## 署名

**tyk (Variables Digital)** &lt;tyk@varsdigital.com&gt; — 项目发起与主持，术语裁决，最终定稿
**Claude Code (Anthropic)** — 译文撰写、工具开发
**Codex (OpenAI)** — 设计文档与术语表评审

译文由 AI 辅助完成，全部经人工裁决与实机验收后定稿。之所以写明，是因为公开
发布的译文理应让使用者知道它是怎么来的。

### 建立在前人工作之上

本项目**不是**从零开始。开始时 zh_CN 已有 3,400 条译文，出自：

> Frank Tang (roadt) · luojie-dune · royweiluo · Susie Shi · XIA ·
> GunChleoc · Hao Hu · Roy Luo · liu lizhi

`tribes`、`world`、`win_conditions` 三个域的成熟译文是术语表的**权威来源**——
建筑名、物品名、工人名、地形名全部沿用其既有译法，只在有据可查的错译处才改动。
署名一律追加，从未替换或删除任何既有译者。

## 与上游的关系

- `zh-CN`（默认分支）：中文版，领先上游若干个翻译提交
- `master`：与上游逐字节一致的纯镜像，从不落本方提交

本分支**不向上游回馈**。Widelands 官方译文走 Transifex，直接提交 `.po` 的 PR
通常不被接收；本项目的产出是独立发布的中文版。

上游同步由 [`i18n-zh/sync-upstream.py`](i18n-zh/sync-upstream.py) 完成，每周自动
检查一次。用 merge 而非 rebase，且 `.po` 走 key 级合并而非行级三方合并——原因
见 [`i18n-zh/README.md`](i18n-zh/README.md#与上游同步)。

## 译文有问题？

欢迎提 [issue](https://github.com/tykisgod/widelands-vd/issues)，也可以直接写信
到上面的邮箱。翻译流程、术语表、校验工具的说明都在
[`i18n-zh/README.md`](i18n-zh/README.md)。

## 许可

译文与 `i18n-zh/` 下的工具同 Widelands 本体，采用 **GPL-2.0 或任何更新版本**。
Widelands 本体版权归 Widelands Development Team 所有，部分素材采用各类
Creative Commons 许可，详见对应目录。
