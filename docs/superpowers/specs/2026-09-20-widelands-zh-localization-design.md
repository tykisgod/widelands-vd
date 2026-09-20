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

**主体：`widelands` 主 UI 域，全面重译**

- 2,378 条 / 11,927 英文词
- 其中 190 条带 `msgctxt` 消歧、65 条复数形式、463 条含 printf 占位符
- 已译的 1,312 条一并重过，以统一术语与语气

选择"全面重译"而非"只补空缺"，是因为现有译文的术语不一致（add-on 附件/插件）与错译（Fortress→哨所）会在同一屏界面上同时出现，只补空缺无法消除。

**附带：跨域的术语定点修正**

只改 `widelands` 一个域达不到术语统一的目标。以 `Fortress` 为例：

```
data/tribes/buildings/militarysites/barbarians/fortress/init.lua:1
    push_textdomain("tribes")
data/tribes/buildings/militarysites/barbarians/fortress/init.lua:8
    descname = pgettext("barbarians_building", "Fortress")
```

建造菜单显示的建筑名来自 **`tribes` 域**、上下文 `barbarians_building`，即 `data/i18n/translations/tribes/zh_CN.po:593-595` 的"哨所"。四个部族各有一条（`:90` amazons、`:594` barbarians、`:810` empire、`:954` frisians），全部误译为"哨所"。而试点主体范围内的 `widelands/zh_CN.po:11451` 那条 msgstr 本身是空的。**只修 `widelands` 域，玩家在游戏里看到的名字不会有任何变化。**

因此试点范围追加一项：**凡术语表收录的词条，在任何域中出现的译文都必须与表一致**。这不是把 `tribes` 等域整域纳入重译，而是由术语表驱动的定点修正——`check_po.py --all --glossary` 会把全部 32 个域中与术语表冲突的条目列出来，逐条改正即可。改动量由术语表规模决定，边界明确且可枚举。

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
    --skip_check_datadir_version `
    --language=zh_CN
```

`--skip_check_datadir_version` 不可省略：`data/datadirversion` 由 cmake 从模板 `cmake/datadirversion.cmake`（内容为 `@WL_VERSION@`）在构建期生成，源码 checkout 里不存在，而 `checkdatadirversion`（`src/wlapplication.cc:1657-1684`）会因此判定 datadir 无效。

**另有一个必须写明的陷阱**：`--fullscreen` 是"存在即生效"的开关（`src/wlapplication.cc:1934` 用 `check_commandline_flag` 读取），写成 `--fullscreen=false` 会被判为非法参数，游戏静默早退。

**不要直接双击 `widelands.exe`**：daily 构建的 zip 只含可执行文件，不含 `data/`。找不到任何有效 datadir 时，`src/wlapplication.cc:1739-1746` 只记录错误却**不退出**，随后继续执行并解引用空指针，表现为「0x… 指令引用了 0x0000000000000040 内存，该内存不能为 read」。本项目已实地踩中一次。

**改一条译文 → 重启游戏 → 立即可见**。无需 msgfmt、MSVC、vcpkg 或任何构建依赖。

daily 构建与工作区 master 之间可能存在数日偏差；若校验脚本报告 msgid 与二进制期望不符，则将工作区切至 daily 对应的 commit。

### 4.1 CRLF 风险（已排除）

Windows 上 `core.autocrlf=true`，且 `.gitattributes` 的 `* text=auto` 只对 `.cc/.h/.lua/.py` 强制 LF，**`.po` 不在其列**，因此工作区的 po 文件以 CRLF 落盘（本地 378,019 字节 vs 版本库 365,689 字节，差额 12,330 正好等于行数）。

经源码确认此路径安全：`src/third_party/tinygettext/src/unix_file_system.cpp:53` 用 `new std::ifstream(filename)` 以**文本模式**打开（未加 `std::ios::binary`），Windows CRT 自动将 CRLF 归一为 LF；`src/base/i18n.cc` 未替换 tinygettext 的 filesystem，走的就是该默认实现。提交时 autocrlf 会转回 LF，版本库不受污染（`git status` 对未修改的 po 文件为干净可证）。

### 4.2 自动化验证（无人值守，非无头）

**措辞澄清**：这条路径是**无人值守**的，不是无头的。即使加了 `--nosound`，进程仍会初始化 SDL 视频并创建窗口、初始化 OpenGL（实跑日志里有完整的 GRAPHICS REPORT）。它不需要人盯着，但需要一个可用的图形环境，不能在纯文本的 CI 容器里跑。

`regression_test.py:174-183` 给出了可用的调用形态。实测可行的完整命令为：

```
widelands.exe --datadir=<repo>/data
              --skip_check_datadir_version
              --datadir_for_testing=<repo>
              --homedir=<tmp>
              --scenario=<repo>/test/maps/plain.wmf
              --script=<repo>/i18n-zh/verify_zh.lua
              --language=zh_CN --nosound --fail-on-lua-error --fail-on-errors
```

三个参数缺一不可，原因各不相同：

- `--scenario`：`--script` 只在游戏内执行。`script_to_run_` 的消费点全部位于进入游戏之后（`src/wlapplication.cc:842/933/982/1014/1042`），不配合 scenario / loadgame / editor / template 模式则根本不会被调用。`test/maps/plain.wmf` 是现成的最小夹具。
- `--datadir_for_testing=<repo>`：`plain.wmf` 引用了仓库内的自定义测试部族资源，路径按仓库根解析；缺此参数会因找不到 `idle_1` 动画而致命退出。
- `--skip_check_datadir_version`：同 §4 所述。

脚本侧要点：Lua 里 `_` 是 gettext 函数，**不要用 `for _, v in ipairs(...)` 遍历**，否则局部变量会遮蔽它，报 `attempt to call a number value`。已在 `verify_zh.lua` 中规避。

验证失败时以 `error()` 抛出，由 `--fail-on-lua-error` 转为非零退出码；`i18n-zh/run-verify.ps1` 封装了上述全部细节并回显结果。

这条路径验证的是**端到端真实加载链路**（tinygettext 解析 → 字典命中 → 运行时返回），比静态 po 校验强得多。人工截图验收仍保留，用于检查字体缺字与按钮溢出这类静态检查覆盖不到的视觉问题。

**已知局限**：当前 7 条锚点只覆盖 `_()`，未覆盖 `pgettext` / `ngettext` / 含占位符的条目；且 tinygettext 跳过单条坏条目时其余锚点仍会通过，故本验证只能证明"加载链路通"，不能证明"整份目录无损"。整份目录的完整性由 `check_po.py --pot` 保证，两者互补。

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
| 未译残留 | msgstr 为纯 ASCII 英文单词；`i18n-zh/keep-english.txt` 收录 OpenGL / Linux / `%.2f MB` / Page Up 这类合法保持英文的条目 | 全量 |
| 标点一致性 | 全角/半角使用符合约定 | 全量 |
| 首尾空白 | 与原文一致（UI 拼接依赖它） | 全量 |
| **fuzzy 标记** | **判为 error，见下** | 全量 |
| **pot 键集** | **与 `<域名>.pot` 双向比对，兼报 `#~` 废弃条目** | 全量 |
| 术语符合性 | 命中术语表的原文，其译文须与表一致 | 依术语表 |
| 富文本标记 | 标签配对 | 见 §7.2 |

脚本只用 Python 标准库（不依赖 polib——本机既无 gettext 工具链也无 translate-toolkit），对全部 32 个域通用，后续阶段直接复用。

### 7.1 fuzzy 必须判为 error

这一条与 gettext 的常识相反，因此单列说明。

Widelands **运行时直接解析 `.po`，没有 msgfmt 环节**，所以"msgfmt 默认丢弃 fuzzy 条目"的保护在这里不存在：

```
po_parser.hpp:48            POParser(..., bool use_fuzzy = true)   ← 默认实参
po_parser.cpp:41-45         静态 parse() 用三参构造，从不覆盖该默认值
po_parser.cpp:418, 459      if (use_fuzzy || !fuzzy)  ← 短路，fuzzy 标记完全失效
dictionary_manager.cpp:165  调三参版本，其自身的 use_fuzzy 成员是死字段
```

fuzzy 译文是 msgmerge 基于相似旧串的猜测，会被**原样显示给玩家**，比留空回退英文更糟。故判为 error 而非 warning——warning 不影响退出码，会让 fuzzy 条目无声通过验收。

相较之下另两类条目是安全的，无需专门设计：空 msgstr 不入字典，查询时回退英文原文（`dictionary.cpp:126-137`）；`#~` 废弃条目被 `po_parser.cpp:355` 的 `while(prefix("#"))` 当普通注释整块忽略。后者仍作为 warning 报出，因为它是"此文件被合并过"的有用信号。

## 8. 验收标准

试点完成的定义，五项全部满足：

1. 下述命令零 error：

   ```
   python i18n-zh/check_po.py data/i18n/translations/widelands/zh_CN.po \
          --pot data/i18n/translations/widelands/widelands.pot \
          --glossary i18n-zh/glossary.tsv --require-complete
   ```

   即同时成立：po 与 pot 的 `(msgctxt, msgid, msgid_plural)` 键集双向无差集；每条 msgstr 非空；无 `fuzzy` 标记；占位符、换行、复数形式、术语一致性全部通过。

   **条目总数由 pot 推导，不写死。** 早先版本用的"2,378 条全部有译文"是不安全的判据：上游增删串而未做 key 级合并时，po 的条目数与非空率都不变，验收静默通过，但新增串在运行时全部回退英文，覆盖率实际下降却毫无信号。2,378 这个数字降级为现状描述——截至 pot 的 `POT-Creation-Date: 2026-09-07`，本域共 2,378 条，已有上游译文 1,312 条，需补译 1,066 条。

2. `python i18n-zh/check_po.py --all --glossary i18n-zh/glossary.tsv` 中，`glossary` 类 error 为零——确保术语表词条在全部 32 个域的译文一致（见 §2 的跨域定点修正）
3. `i18n-zh/run-verify.ps1` 退出码为 0（端到端加载校验）
4. `i18n-zh/glossary.tsv` 定稿并通过 Codex 评审
5. **游戏内实跑截图确认**：主菜单、选项菜单、单人战役列表、建造菜单、经济面板五处中文显示正常，无缺字方块、无按钮文本溢出。建造菜单须专门确认军事建筑名（岗哨 / 关卡 / 塔楼 / 要塞 / 堡垒）已按术语表显示

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
| 上游持续更新英文条目 | 译文过时、新串静默回退英文 | 见 §10.1——单纯 rebase 是错的 |

### 10.1 与上游同步：不能只靠 rebase

原方案里"定期 rebase upstream/master"这一句是错的，必须展开。

根因是**上游本地根本不跑 msgmerge**——合并发生在 Transifex 服务端。`utils/buildcat.py` 的 `__main__` 只再生 `.pot`；其中含 `msgmerge` 的 `do_buildpo()` / `do_update_po()` 无任何调用者，是遗留死代码。真实链路在 `utils/merge_and_push_translations.sh:158-172`：再生 pot → `tx push -s` → `tx pull -a -f` 把服务端合并好的 `.po` 拉回。

fork 拿不到这一步。于是 rebase 时，上游会同时带来新 `widelands.pot` 和已被 Transifex 合并过的新 `zh_CN.po`，而本 fork 也重写了同一个 378 KB 文件，必然大面积冲突，且三种常规解法都错：

- `--ours`（保住译文）→ 键集停留在旧 pot，上游新增串在 po 里没有条目，运行时全部回退英文；而文件本身条目数与非空率均未变，**验收静默通过，覆盖率却已下降**。最危险，因为毫无信号。
- `--theirs`（接受上游）→ 键集正确，但 msgstr 变回上游旧译文，**本 fork 全部译文成果丢失**。
- 手工逐块解冲突 → 2,378 条目、378 KB，冲突块覆盖大半个文件，既不可行也不可靠。

根因是把 `.po` 当普通文本做行级三方合并。`.po` 是按 key 索引的数据文件，正确操作是 **key 级合并**。

正确步骤：

```bash
git fetch upstream
git rebase upstream/master
#   zh_CN.po 冲突一律取 ours，不要手工解
git checkout --ours data/i18n/translations/widelands/zh_CN.po
git add    data/i18n/translations/widelands/zh_CN.po
git rebase --continue

# pot 是 buildcat.py 从源码自动生成的产物，本 fork 从不修改，直接取上游
git checkout upstream/master -- data/i18n/translations/widelands/widelands.pot

# 关键一步：补做 Transifex 没帮我们做的 key 级合并
pot2po --nofuzzymatching \
  -t data/i18n/translations/widelands/zh_CN.po \
  -i data/i18n/translations/widelands/widelands.pot \
  -o data/i18n/translations/widelands/zh_CN.po

# 门禁
python i18n-zh/check_po.py data/i18n/translations/widelands/zh_CN.po \
  --pot data/i18n/translations/widelands/widelands.pot --require-complete
```

选 `pot2po`（translate-toolkit）而非 `msgmerge` 的理由：纯 Python，`pip install translate-toolkit` 即可；本机实测 `msgmerge` / `msgfmt` / `msgattrib` / `xgettext` **全部未安装**，在 Windows 上部署 gettext 二进制是额外负担；translate-toolkit 已是上游开发依赖（`utils/validate_translations.sh:60` 的 `pofilter` 同属该包）。`--nofuzzymatching` 让变更串以**空 msgstr** 返回而非 fuzzy 猜测，从源头消掉 §7.1 的风险。

注意 translate-toolkit 本机当前亦未安装，需要时再 `pip install`。若不愿引入该依赖，可基于 `check_po.py` 现成的 `parse_po()` 写约 40 行的 `i18n-zh/sync_po.py`（按 pot 顺序重建 po、键命中则搬运旧 msgstr、未命中留空、header 保留我方的）——本项目用不到 msgmerge 的模糊匹配、引用注释更新、`--previous` 等能力。**此工具在上游实际发生变动前不预先编写。**

当前状态：pot 与 po 实测完全同步（2,378 条双向无差集、零 fuzzy、零废弃条目，两者 `POT-Creation-Date` 同为 `2026-09-07`），daily 二进制 `1.4~git1 (216a91e@master)` 与工作区 HEAD 一致。**这是前瞻性风险，不是现存缺陷，不阻塞试点翻译。**
