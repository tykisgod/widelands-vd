# Widelands 简体中文本地化

本目录是 [Widelands](https://www.widelands.org/) 简体中文译文的工作区，
包含术语表、校验工具与验收脚本。

## 署名

**tyk (Variables Digital)** &lt;tyk@varsdigital.com&gt; — 项目发起与主持，术语裁决，最终定稿
**Claude Code (Anthropic)** — 译文撰写、工具开发
**Codex (OpenAI)** — 设计文档与术语表评审

译文有问题或有更好的译法，欢迎提 issue，也可以直接写信到上面的地址。

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
| 17 个战役与教程剧本 | 2,507 | **2,507（100%）** |
| `tribes_encyclopedia` 百科全书 | 2,339 | **2,339（100%）** |
| 全部 32 个域 | 9,772 | **9,772（100%）** |

`check_po.py` 全域 **0 error / 0 warning**。

主 UI 域为**全面重译**，而非只补空缺——现有译文存在术语不一致
（`add-on` 同时译作"附件"与"插件"）与错译（`Fortress` 译作"哨所"，而
"哨所"的语义正是驻军 2 人的 `Sentry`），只补空缺无法消除。同样的整理
也做到了其余各域：`Out of Fields` 被误读成"场地之外"、`Ferry`（船）
被译成"艄公"（划船的人）、`Food Preserver`（做口粮的作坊）被译成
"食品仓库"等，均已订正并记入 `corrections.tsv`。

刻意保留原文的两处：帝国百科里 52 条拉丁语引文（原文注释明写
`DO NOT TRANSLATE`，游戏中紧随其后就是它的译文），以及弗里西亚战役二
中帝国总督的拉丁语台词（下一句台词正是"有人听得懂他在说什么吗？"）。
见 `keep-english.txt`。

## 快速上手

```powershell
# 以中文启动游戏（改完 .po 重启即生效，无需编译）
.\i18n-zh\run-zh.ps1

# 无人值守的译文加载验证
.\i18n-zh\run-verify.ps1
```

```bash
# 全部 32 个域（--all 会自动带上 Widelands 文法、术语表与保持英文清单）
python i18n-zh/check_po.py --all

# 单个域，并与 pot 比对键集
python i18n-zh/check_po.py data/i18n/translations/widelands/zh_CN.po \
       --grammar widelands --glossary i18n-zh/glossary.tsv \
       --keep-english i18n-zh/keep-english.txt \
       --pot data/i18n/translations/widelands/widelands.pot --require-complete
```

**`--grammar widelands` 不能省。** 默认的 `printf` 文法会把 `%1%` 当成
字面百分号放过去，整类占位符从此不再被检查，而校验仍报 0 error。

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
| `sync-upstream.py` | 同步上游改动（merge + key 级合并 + 校验） |
| `keep-english.txt` | 合法保持英文的 msgid（OpenGL、Ctrl、`%.2f MB` 等） |
| `STYLE.md` | 术语之外的译文规范 |
| `batches/` | 各批次的原文与译文，便于追溯 |

## 几个容易踩的技术前提

- Widelands 运行时用 tinygettext **直接读 `.po`**，没有 msgfmt 环节
- 因此 **fuzzy 条目会被原样显示给玩家**（`po_parser.hpp:48` 的
  `use_fuzzy` 默认为 `true` 且从不被覆盖），`check_po.py` 将其判为 error
- 占位符文法是 Widelands 自有的（`src/base/format/tree.h:40-75`），
  `%N%` 是"第 N 个参数"而非字面百分号，且编号与不编号不得混用
- 与上游同步不能只靠 `git rebase`，需补做 key 级合并，见下一节

## 与上游同步

```bash
python i18n-zh/sync-upstream.py            # 只看上游有什么新东西，不改工作区
python i18n-zh/sync-upstream.py --apply    # 真的合并，改动 git add 但不提交
```

`.github/workflows/zh_sync_check.yaml` 每周一自动跑一次：有新东西就把同步
结果推到 `sync/upstream-<日期>` 分支并开 issue。**刻意不自动开 PR**——上游
的 `build.yaml` 在 `pull_request` 上触发，其中只有 appimage / dev_release
两个 job 带 `github.repository == 'widelands/widelands'` 守卫，其余会实打实
地在本 fork 上跑整套构建矩阵。推到 `sync/` 分支不触发任何东西（`build.yaml`
的 push 过滤是 `[master, protected/*]`）。要跑 CI 时由人手动开 PR。

### 为什么是 merge 不是 rebase

zh-CN 领先上游的提交里有 36 个改过 `zh_CN.po`，涉及 31 个文件。rebase 会
逐个重放这 36 个提交，上游只要动过同一批文件，冲突就要解 36 次；而且 rebase
重写历史，公开的默认分支必须 force-push，别人克隆过的副本全废。merge 只有
一个合并点，冲突解一次。

附带好处：`--ours` / `--theirs` 在 rebase 期间含义与平时相反（ours 是被
rebase 到的上游），选反了直接销毁全部译文；merge 里是直觉含义，这个坑消失。

### `.po` 不做行级合并

上游本地不跑 msgmerge，合并发生在 Transifex 服务端（`utils/buildcat.py` 里
带 msgmerge 的函数是无调用者的死代码，真实链路在
`utils/merge_and_push_translations.sh:158-172`）。fork 拿不到这一步，必须自己
补 **key 级合并**：新 pot 的键集 + 本方译文 → 新 po（`pot2po
--nofuzzymatching`）。上游新增的串成为空条目，上游删掉的串自动消失。

合并后的文件策略与有没有冲突无关——实测上游改了 `zh_CN.po` 时 git 报的是
`Auto-merging`，按行级三方合并"成功"、压根不产生冲突，上游的旧译文会静默
混进来。所以脚本一律：`zh_CN.po` 恢复本方版本、`*.pot` 取上游，再做 key 合并。

### 校验必须带 `--require-complete`

`check_po.py:762` 默认跳过未译条目（翻译期是对的，否则几千条空串全报错）。
但同步场景下恰恰相反：上游新增的串是空条目，不带这个开关会**静默通过**，
条目数和非空率都看不出异常，覆盖率却已经掉了。`sync-upstream.py` 内部已经
带上，手动跑校验时别忘。

## 许可

译文与本目录下的工具同 Widelands 本体，采用 **GPL-2.0 或任何更新版本**。
Widelands 本体版权归 Widelands Development Team 所有。
