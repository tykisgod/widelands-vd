# Widelands 简体中文本地化 — 设计文档

日期：2026-09-20
仓库：`tykisgod/widelands-vd`（fork 自 `widelands/widelands`，GPL-2.0）
状态：试点阶段已批准

## 1. 背景

Widelands 是一款 C++/SDL2 的中世纪定居者建造类 RTS，采用 gettext 国际化，译文由 Transifex 管理。

简体中文的**基础设施已完整存在**，无需任何改造：

- `data/i18n/locales.lua:267` 已注册 `zh_CN`，显示名"简体中文"，字体集 `cjk`
- `data/i18n/fonts.lua:46` 的 `cjk` 字体集指向内置的文泉驿微米黑 `MicroHei/wqy-microhei.ttc`
- po 头部 `Plural-Forms: nplurals=1; plural=0;` 对中文配置正确

缺的只是译文本身。全量统计 32 个翻译域的 zh_CN 完成度：

| 指标 | 数值 |
|---|---|
| 总条目 | 9,772 |
| 已译 | 3,400（**34.8%**） |
| 未译 | 6,372（约 8.07 万英文词） |

分布极不均衡：`world` 98.1%、`tribes` 84.4%、`win_conditions` 85.7%、`maps` 83.0% 基本可用；而 `tribes_encyclopedia` 仅 1.1%（2,314 条未译 / 2.18 万词），17 个战役与教程剧本多数为 0%，`widelands` 主 UI 域 55.2%。

现有译文质量参差，已确认的问题类型：

| 原文 | 现有译文 | 问题 |
|---|---|---|
| `%1$s or %2$s` | `%1$s or %2$s` | 连接词 "or" 未翻译 |
| `No AI` | `没有人工智能` | 生硬直译 |
| `New Objectives` | `一些新的目标` | 凭空增译 |
| `%1$s, %2$s` | `%1$s,%2$s` | 半角逗号，与其他条目不一致 |
| `add-on`（`zh_widelands.po:805` / `:832`） | 附件 / 插件 | 同一术语两种译法 |
| `Fortress`（四个部族全部） | 哨所 | 与 `Sentry`→"岗哨" 语义重叠；Fortress 是大型军事建筑，非哨所 |

## 2. 目标与范围

### 试点范围（本文档覆盖）

**仅 `widelands` 主 UI 域，全面重译**：

- 2,378 条 / 11,927 英文词
- 其中 190 条带 `msgctxt` 消歧、65 条复数形式、463 条含 printf 占位符
- 已译的 1,312 条一并重过，以统一术语与语气

选择"全面重译"而非"只补空缺"，是因为现有译文的术语不一致（add-on 附件/插件）与错译（Fortress→哨所）会在同一屏界面上同时出现，只补空缺无法消除。

### 验收后再决定的范围（不在本文档内）

其余 31 个域，按优先级：战役与教程剧本（约 2,200 条 / 4.5 万词）、`tribes_encyclopedia`（2,314 条 / 2.18 万词）、零散补漏。

### 非目标

- **不回馈上游**。Widelands 官方译文走 Transifex，直接提交 `.po` 的 PR 通常不被接收。本项目的产出是独立发布的中文版分发。
- **不改动 C++ 源码、不改动游戏逻辑、不新增 UI 字符串。**
- **不做繁体中文**（`zh_TW` 当前近乎空白，属未来独立议题）。

## 3. 仓库与分支

```
tykisgod/widelands-vd          fork 自 widelands/widelands，公开，GPL-2.0
  └─ 分支 zh-CN                 译文工作分支
E:\dpp_new\widelands-vd        本地工作区
  ├─ origin    → tykisgod/widelands-vd
  └─ upstream  → widelands/widelands
```

克隆使用 `--filter=blob:none`（惰性拉取 blob）而非 `--depth 1`：保留完整提交历史以便后续 rebase 上游新增的英文条目，同时避免拉取 3.1 GB 的历史二进制资源。工作区仍需完整 checkout（约 1 GB），因为运行游戏需要 `data/` 下的全部资源。

本项目新增文件统一放在仓库根目录的 `i18n-zh/`，与上游路径隔离，保证 diff 清晰：

```
i18n-zh/
  glossary.tsv        术语表（英文 / 中文 / 上下文 / 出处 / 备注）
  check_po.py         译文校验脚本
  run-zh.ps1          本地测试启动脚本
  README.md           使用说明与安装指引
```

## 4. 本地测试环境（零编译）

**关键发现：Widelands 运行时通过 tinygettext 直接读取 `.po` 源文件，不需要 msgfmt 编译成 `.mo`，也不需要编译 C++。**

证据链：

- `src/wlapplication.cc:1388` — localedir 默认为 `<datadir>/i18n/translations`
- `src/wlapplication.cc:1651` — 支持 `--localedir=<path>`
- `src/wlapplication.cc:1764` — 支持 `--language=<code>`
- `src/base/i18n.cc:239` — `textdomain_cache_key(domain, ldir)` 返回 `ldir + "/" + domain`
- `src/base/i18n.cc:62` — `tinygettext::DictionaryManager::add_directory(dir)` 在该目录下按 `<lang>.po` 匹配

因此实际读取路径为 `<datadir>/i18n/translations/<域名>/zh_CN.po`，即我们工作区里的源文件本身。

测试方式：使用官方 daily 构建的 Windows 便携版（`Widelands-daily-mingw-Release-x64.zip`，32 MB，仅含可执行文件与 DLL，不含游戏数据），用 `--datadir` 指向本地工作区：

```powershell
# i18n-zh/run-zh.ps1
& E:\dpp_new\widelands-run\widelands.exe `
    --datadir=E:\dpp_new\widelands-vd\data `
    --language=zh_CN
```

**改一条译文 → 重启游戏 → 立即可见**。无需 msgfmt、MSVC、vcpkg 或任何构建依赖。

daily 构建与工作区 master 之间可能存在数日偏差；若校验脚本报告 msgid 与二进制期望不符，则将工作区切至 daily 对应的 commit。

### 4.1 CRLF 风险（已排除）

Windows 上 `core.autocrlf=true`，且 `.gitattributes` 的 `* text=auto` 只对 `.cc/.h/.lua/.py` 强制 LF，**`.po` 不在其列**，因此工作区的 po 文件以 CRLF 落盘（本地 378,019 字节 vs 版本库 365,689 字节，差额 12,330 正好等于行数）。

经源码确认此路径安全：`src/third_party/tinygettext/src/unix_file_system.cpp:53` 用 `new std::ifstream(filename)` 以**文本模式**打开（未加 `std::ios::binary`），Windows CRT 自动将 CRLF 归一为 LF；`src/base/i18n.cc` 未替换 tinygettext 的 filesystem，走的就是该默认实现。提交时 autocrlf 会转回 LF，版本库不受污染（`git status` 对未修改的 po 文件为干净可证）。

### 4.2 自动化验证（无头）

`regression_test.py:174-183` 揭示了一条无 GUI 的自动化路径：

```
widelands.exe --verbose --datadir=<dir> --homedir=<tmp> --nosound \
              --fail-on-lua-error --fail-on-errors --language=zh_CN --script=<lua>
```

游戏内 Lua 可调用 `print()`，且 `test/scripting/lunit.lua` 提供断言框架。据此编写 `i18n-zh/verify_zh.lua`：取一组有代表性的 msgid，经 `_()` 取译文后打印，脚本侧比对是否为预期中文且非英文原文。

这条路径验证的是**端到端真实加载链路**（tinygettext 解析 → 字典命中 → 运行时返回），比静态 po 校验强得多，且可在每批译文产出后无人值守运行。人工截图验收仍保留，用于检查字体缺字与按钮溢出这类静态检查无法覆盖的视觉问题。

## 5. 术语表

术语表是全部译文的地基，必须在翻译开始前完成并通过评审。

**数据来源**：`tribes`（84.4%）、`world`（98.1%）、`maps`（83.0%）、`win_conditions`（85.7%）四个高完成度域共 1,770 条成熟译文。它们是建筑名、货物名、工人名、地形名的权威出处——主 UI 中出现的每个游戏名词都必须与之一致，否则玩家会在建造菜单与经济面板看到同一事物的两个名字。

**已完成的抽取**：以"短名词短语"为筛选条件（≤6 词、无占位符、无句末标点），从上述四域抽出 **1,355 条词条，四域之间零冲突**，说明这批译文内部自洽，可作为基准。

**仍需人工裁决的部分**：

1. 四域**内部自洽不等于正确**。已发现 `Fortress`→"哨所" 与 `Sentry`→"岗哨" 语义重叠的错译。军事建筑体系（Sentry / Blockhouse / Outpost / Barrier / Tower / Fortress / Citadel / Castle）需整体复核其规模序列与中文对应。
2. 四大部族专名的风格定调：Barbarians（巴巴里安）、Empire（帝国）、Atlanteans（亚特兰蒂斯）、Frisians（弗里西亚）、Amazons（亚马逊）。
3. 主 UI 通用术语（add-on、ware、economy、warehouse、ship、expedition、port space 等）在四域中未出现或出现不全，需新增并定稿。

**产出**：`i18n-zh/glossary.tsv`，列为 `英文 / 中文 / msgctxt / 出处域 / 备注`。定稿前交由 Codex 评审。

**机器校验**：复用上游 `utils/glossary_checks.py`，并在 `check_po.py` 中加入术语符合性检查。

## 6. 翻译流水线

按源码位置（po 文件的 `#:` 注释）分组，每批约 80 条，串行推进。

**为何串行而非并行分片**：术语与语气一致性是本次的核心诉求。串行让后续批次能持续参照前批已确立的译法，并在发现更好译法时向前回溯修订。并行分片虽快，但即使有术语表约束，句式语气仍会出现可察觉的断层。

每批的输入上下文包含：

- `msgid` 原文
- `msgctxt` 消歧上下文（190 条有）
- `#.` 译者注释（上游为易混淆条目提供的说明）
- `#:` 源码位置（用以判断该字符串出现在哪个界面）
- 术语表中命中的词条

**翻译约定**：

- 复数条目仅填 `msgstr[0]`（中文 `nplurals=1`）
- 占位符 `%s` / `%1$s` / `%2.1f%%` 原样保留，包括参数编号
- 转义序列 `\n` `\"` `\\` 原样保留
- 中文文案内使用全角标点；但占位符与英文代码标识符周围保持半角
- UI 按钮、菜单项求短；提示与说明文字求清晰完整
- 保留上游 po 头部的译者署名历史，并在 `Last-Translator` 追加本项目标识

每批产出后立即运行 `check_po.py`，不过不放行。

## 7. 校验脚本 `i18n-zh/check_po.py`

| 检查项 | 说明 | 影响范围 |
|---|---|---|
| 占位符完整性 | `%s` / `%1$s` / `%2.1f%%` 的种类、数量、参数编号与原文逐一比对 | 463 条；错一个会导致游戏崩溃或显示错乱 |
| 转义序列 | `\n` `\"` `\\` 与原文一致 | 全量 |
| 复数形式 | 有 `msgid_plural` 的条目必须且只能有 `msgstr[0]` | 65 条 |
| 未译残留 | msgstr 为纯 ASCII 英文单词（排除纯占位符/纯符号条目） | 全量 |
| 标点一致性 | 全角/半角使用符合约定 | 全量 |
| 术语符合性 | 命中术语表的原文，其译文须与表一致 | 依术语表 |
| 富文本标记 | 标签配对（为后续战役剧本阶段预留） | 试点阶段不触发 |
| 可解析性 | 用 polib 完整解析，确保 tinygettext 能正确读取 | 全文件 |

脚本对全部 32 个域通用，后续阶段直接复用。

## 8. 验收标准

试点完成的定义，五项全部满足：

1. `data/i18n/translations/widelands/zh_CN.po` 的 2,378 条全部有译文
2. `check_po.py` 对该文件零报错（静态校验）
3. `verify_zh.lua` 无头运行通过（端到端加载校验）
4. `i18n-zh/glossary.tsv` 定稿并通过 Codex 评审
5. **游戏内实跑截图确认**：主菜单、选项菜单、单人战役列表、建造菜单、经济面板五处中文显示正常，无缺字方块、无按钮文本溢出

验收后由用户决定是否推进到其余 31 个域。

## 9. 评审机制

用户已指定：所有中间评审环节交由 Codex CLI（GPT）执行，不再逐项征询用户。适用于本设计文档、术语表定稿、以及各批次译文的质量复核。

## 10. 风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 克隆约 1 GB，耗时长 | 起步慢 | 后台执行，期间并行建术语表（已完成） |
| daily 构建与 master 有数日偏差 | msgid 不匹配 | 校验脚本报错时将工作区切至 daily 对应 commit |
| CJK 字体缺字 | 显示方块 | 文泉驿微米黑已内置；实跑阶段专项检查 |
| 中文按钮文本溢出 | 界面错乱 | 截图验收逐屏检查；UI 类条目从严控制长度 |
| 现有译文中潜藏更多错译 | 术语表被污染 | 术语表不盲信四域现状，逐条复核后交 Codex 评审 |
| 上游持续更新英文条目 | 译文过时 | 保留完整 git 历史，定期 rebase upstream/master |
