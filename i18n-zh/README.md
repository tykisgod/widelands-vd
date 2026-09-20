# Widelands 简体中文本地化

本目录是 [Widelands](https://www.widelands.org/) 简体中文译文的工作区，
包含术语表、校验工具与验收脚本。

## 署名

**tyk (Variables Digital)** — 项目发起与主持，术语裁决，最终定稿
**Claude Code (Anthropic)** — 译文撰写、工具开发
**Codex (OpenAI)** — 设计文档与术语表评审

本项目的译文由 AI 辅助完成，全部经人工裁决与实机验收后定稿。之所以写明，
是因为公开发布的译文理应让使用者知道它是怎么来的。

### 建立在前人工作之上

本项目**不是**从零开始。开始时 zh_CN 已有 3,400 条译文，出自：

> Frank Tang (roadt) · luojie-dune · royweiluo · Susie Shi · XIA ·
> GunChleoc · Hao Hu · Roy Luo · liu lizhi

其中 `tribes`（84%）、`world`（98%）、`win_conditions`（86%）三个域的成熟
译文，是本项目术语表 1,300 个词条的**权威来源**——建筑名、货物名、工人名、
地形名全部沿用他们的既有译法，只在有据可查的错译处才改动（见
`corrections.tsv` 每条的理由）。没有这批积累，术语一致性无从谈起。

署名一律追加，从未替换或删除任何既有译者。

## 当前状态

| 范围 | 条目 | 已译 |
|---|---:|---:|
| `widelands` 主 UI 域 | 2,378 | **2,378（100%）** |
| 全部 32 个域 | 9,772 | 4,466（45.7%） |

主 UI 域为**全面重译**，而非只补空缺——现有译文存在术语不一致
（`add-on` 同时译作"附件"与"插件"）与错译（`Fortress` 译作"哨所"，而
"哨所"的语义正是驻军 2 人的 `Sentry`），只补空缺无法消除。

尚未完成：17 个战役与教程剧本（约 2,200 条）、`tribes_encyclopedia`
百科全书（2,314 条）、以及其余零散补漏。

## 快速上手

```powershell
# 以中文启动游戏（改完 .po 重启即生效，无需编译）
.\i18n-zh\run-zh.ps1

# 无人值守的译文加载验证
.\i18n-zh\run-verify.ps1
```

```bash
# 静态校验
python i18n-zh/check_po.py data/i18n/translations/widelands/zh_CN.po \
       --pot data/i18n/translations/widelands/widelands.pot \
       --glossary i18n-zh/glossary.tsv --require-complete

# 全部 32 个域
python i18n-zh/check_po.py --all --glossary i18n-zh/glossary.tsv
```

**不要直接双击 `widelands.exe`。** 官方 daily 构建的 zip 只含可执行文件，
不含 `data/`；Widelands 找不到 datadir 时只记录错误却不退出
（`src/wlapplication.cc:1739`），随后空指针崩溃。必须通过上面的脚本启动。

## 文件说明

| 文件 | 用途 |
|---|---|
| `corrections.tsv` | **唯一可人工编辑的术语裁决表**，每条附理由 |
| `glossary.tsv` | 由 `build_glossary.py` 生成，请勿手工编辑 |
| `build_glossary.py` | 从高完成度域抽取术语，套用裁决 |
| `apply_glossary.py` | 把术语裁决落到全部 32 个域 |
| `check_po.py` | 静态校验：占位符、换行、复数、漏译、标点、术语、pot 键集、富文本标记、fuzzy |
| `batch.py` | 翻译批次的导出与回写 |
| `show_batch.py` | 批次的紧凑视图 |
| `verify_zh.lua` / `run-verify.ps1` | 端到端加载验证（覆盖 `_()`、`pgettext`、`ngettext`） |
| `run-zh.ps1` | 以中文启动游戏 |
| `screenshot.ps1` | 视觉验收抓屏 |
| `update_stats.py` | 重算 `translation_stats.conf` 的词数统计 |
| `keep-english.txt` | 合法保持英文的 msgid（OpenGL、Ctrl、`%.2f MB` 等） |
| `STYLE.md` | 术语之外的译文规范 |
| `batches/` | 各批次的原文与译文，便于追溯 |

## 几个容易踩的技术前提

- Widelands 运行时用 tinygettext **直接读 `.po`**，没有 msgfmt 环节
- 因此 **fuzzy 条目会被原样显示给玩家**（`po_parser.hpp:48` 的
  `use_fuzzy` 默认为 `true` 且从不被覆盖），`check_po.py` 将其判为 error
- 占位符文法是 Widelands 自有的（`src/base/format/tree.h:40-75`），
  `%N%` 是"第 N 个参数"而非字面百分号，且编号与不编号不得混用
- 与上游同步不能只靠 `git rebase`，需补做 key 级合并，详见设计文档
  `docs/superpowers/specs/2026-09-20-widelands-zh-localization-design.md` §10.1

## 许可

译文与本目录下的工具同 Widelands 本体，采用 **GPL-2.0 或任何更新版本**。
Widelands 本体版权归 Widelands Development Team 所有。
