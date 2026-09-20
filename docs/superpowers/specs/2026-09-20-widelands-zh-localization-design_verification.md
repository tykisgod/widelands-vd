### C1
Verdict: Confirmed
Evidence: `src/CMakeLists.txt:3` generates the missing file during configuration: `configure_file(.../cmake/datadirversion.cmake .../data/datadirversion)`; `cmake/datadirversion.cmake:1` contains `@WL_VERSION@`; the clean checkout reports `DATADIRVERSION_ABSENT`. `src/wlapplication.cc:1658-1679` loads `datadirversion` unless `--skip_check_datadir_version` is set. When autodetection fails, `src/wlapplication.cc:1740-1747` only executes `log_err(...)`; execution then reaches `src/wlapplication.cc:1768: init_filesystems();`, whose `src/wlapplication.cc:1330` calls `FileSystem::create(datadir_)`. Thus it does not exit cleanly. The reported `0x40` access violation is consistent with this path, though the exact faulting dereference is not proven by these lines alone.
Spec change required: Section 4’s manual command must say `widelands.exe --datadir=<repo>\data --skip_check_datadir_version --language=zh_CN`. Section 4.2 must include `--skip_check_datadir_version`, `--datadir_for_testing=<repo>`, and `--scenario=<repo>\test\maps\plain.wmf`.
Proportionate fix: Documentation-only: copy the already-correct arguments from `i18n-zh/run-zh.ps1:60-64` and `i18n-zh/run-verify.ps1:38-49`. Do not generate or commit a synthetic `data/datadirversion`.

### C2
Verdict: Confirmed
Evidence: The verifier itself is runnable and its launcher is correct: `i18n-zh/run-verify.ps1:39-48` supplies the datadir skip, testing root, scenario, script, language, and failure flags. The spec remains incomplete at `docs/superpowers/specs/2026-09-20-widelands-zh-localization-design.md:120-122`, where those first three required arguments are absent. `src/wlapplication_messages.cc:113-116` says `--script` is valid only with `--scenario`, `--loadgame`, or `--editor`. It is also not headless: `src/wlapplication.cc:405` executes `SDL_Init(SDL_INIT_VIDEO)`, and `src/wlapplication.cc:419-424` constructs and initializes `Graphic`, including display resolution and window mode; `--nosound` only disables audio later at `src/wlapplication.cc:1786-1788`.
Spec change required: Rename “自动化验证（无头）” to “自动化验证（无人值守，仍初始化 SDL 视频与窗口）” and show the exact known-green command, including the scenario fixture, `--datadir_for_testing=<repo>`, and `--skip_check_datadir_version`.
Proportionate fix: Fix the spec wording and command only; no verifier-code change is needed.

### C3
Verdict: Partially confirmed
Evidence: The authoritative grammar is `src/base/format/tree.h:40-75`: `%N%`, or `%[N$][flags][width][.precision]fmt`; flags are only `-`, `+`, `0`; formats are `%%`, `%c`, `%s`, `%b`, `%i/%d/%li/%ld/%lli/%lld`, `%u/%lu/%llu`, `%x/%X`, `%p/%P`, and `%f`. Parser restrictions are enforced at `src/base/format/tree.cc:155-245`. The implemented regex at `i18n-zh/check_po.py:136` does match `%li`, `%1$i`, `%c`, `%i`, and even `%N%`; my original assertion about those forms was wrong. It misses valid `%b` and `%P`. It wrongly accepts space/`#` flags, `*` widths and precisions, `hh/h/L/z/j/t`, `o/e/E/F/g/G/a/A/n`, length modifiers before unsupported types such as `%lx`, index zero, decorated percent forms such as `%1$%`, precision on integers, and extra specifiers on `%c`; it also does not enforce the engine’s no-mixing/no-gap/no-duplicate rules. The requested grep’s top 40 were: `210 %s`, `102 %1$s`, `85 %u`, `77 %2$s`, `68 %d`, `40 %s’`, `27 %1%`, `23 %2%`, `20 %1$s’`, `18 %3$s`, `17 %u)`, `16 %1$u`, `12 %2$s.`, `12 %1$s\n`, `11 %s'`, `10 %2$u`, `10 %2$s)`, `10 %1%:%2%`, `9 %2$s’`, `9 %1%:`, `8 %s\`, `8 %3$u`, `7 %5$s`, `7 %2$s\n`, `6 %s.`, `6 %4$s`, `6 %3$s\n`, `6 %1$s,`, `6 %.2f`, `5 %s)`, `5 %i%%`, `5 %4$u`, `5 %4$s\n`, `5 %3$s)`, `5 %1%)`, `4 %s’.`, `4 %s\n`, `4 %i`, `4 %5$s\n`, `4 %2$s:`. That grep deliberately overcaptures suffix punctuation. Normalized with the validator tokenizer, the catalog contains 37 distinct forms, including `%li` 3 times, `%1$i` 5, `%c` 1, and `%i` 8. At runtime `src/base/format/tree.h:346-350` logs the format error and rethrows; Lua `bformat` converts it to a Lua error at `src/scripting/lua_globals.cc:172-175`. It is a throw-after-log path, not log-and-continue.
Spec change required: Replace the generic “printf placeholder” description with the Widelands `format_impl` grammar above, and state that validation must enforce type-specific restrictions and positional-index rules.
Proportionate fix: Replace the permissive generic printf regex with a small engine-specific tokenizer/parser. My earlier proposal was too broad because four of the allegedly missing forms already worked.

### M1
Verdict: Confirmed
Evidence: Tinygettext does load fuzzy entries by default. `src/third_party/tinygettext/src/po_parser.cpp:41-44` constructs `POParser parser(filename, in, dict)` without overriding the constructor default; `src/third_party/tinygettext/include/tinygettext/po_parser.hpp:48` defines that default as `bool use_fuzzy = true`. The flag is detected at `po_parser.cpp:350-361`, and entries are added when `use_fuzzy || !fuzzy` at `po_parser.cpp:418-435` and `:457-465`. Empty singular `msgstr` is skipped by `else if (!msgstr.empty())` at `:453-474`; plural entries are skipped unless at least one `msgstr[N]` is nonempty at `:384-416`. Obsolete `#~` lines enter the general `while(prefix("#"))` comment loop at `:355-365` and are ignored.
Spec change required: State: “This embedded tinygettext loads `#, fuzzy` translations by default; pilot acceptance therefore requires zero fuzzy entries.” Remove any GNU `msgfmt` assumption.
Proportionate fix: Change `check_po.py:286-289` from a non-failing warning saying “游戏不会使用” to an error saying the game will use it. No parser or runtime change is needed.

### M2
Verdict: Partially confirmed
Evidence: Current command output is `pot entries 2378, po entries 2378, only pot 0, only po 0, obsolete msgid lines 0`; the present catalogs are exactly synchronized. `utils/buildcat.py:569-572` regenerates POT files only; although `do_update_po` exists at `:441-472`, main does not invoke it. `utils/buildcat.py:398-401` shows the actual PO merge operation is `msgmerge`. `utils/merge_and_push_translations.sh:129-172` performs a much larger Transifex pull/push workflow. A plain `git rebase upstream/master` runs none of these tools, but it also does not necessarily leave PO stale if upstream already committed synchronized POT/PO files; my categorical rebase claim was too strong. The fixed number 2,378 remains unsafe because legitimate upstream key additions/removals change it.
Spec change required: Replace acceptance item 1 with: “The `(msgctxt, msgid, msgid_plural)` key set in `zh_CN.po` must equal the current `widelands.pot` key set, and every current PO key must have a nonempty translation; the expected count is derived from the POT.”
Proportionate fix: Add one key-set equality check to `check_po.py`. After a rebase, run it; only on mismatch run `msgmerge --update --no-wrap data/i18n/translations/widelands/zh_CN.po data/i18n/translations/widelands/widelands.pot`. Do not adopt the full Transifex pipeline.

### M3
Verdict: Confirmed
Evidence: `i18n-zh/verify_zh.lua:15-23` defines seven context-free, singular, unformatted anchors, and `:46-49` calls only `_(src)`. Lua exposes `_`, `ngettext`, `pgettext`, `npgettext`, and `string.bformat` at `src/scripting/lua_globals.cc:585-609`. A malformed PO entry does not abort the catalog: `po_parser.cpp:75-84` advances to an empty line and throws `POParserError`, while `:487-489` catches it and continues parsing. Therefore unrelated anchors can pass while a damaged entry is silently skipped. Real usable additions are `pgettext("author_name", "Unknown")` → `未知` from `zh_CN.po:1265-1267`; `ngettext("%u missing add-on", "%u missing add-ons", 2):bformat(2)` → `2 缺少插件` from `:830-832`; and `npgettext("unit_narrow", "%1%d", "%1%d", 2):bformat(2)` → `2天` from `:11252-11255`.
Spec change required: Say that the end-to-end verifier covers singular, contextual, plural, contextual-plural, and formatted lookup paths, while static validation remains responsible for whole-catalog integrity.
Proportionate fix: Add exactly those three anchors. They cover `pgettext`, `ngettext`, `npgettext`, and `bformat`; a larger combinatorial suite is unnecessary.

### M4
Verdict: Confirmed but over-engineered
Evidence: `utils/file_utils.py:41-47` reads comma-delimited quoted CSV. `utils/glossary_checks.py:211-235` expects Transifex columns `term`, `comment` or `notes`, `pos`, `translation_<locale>` or `<locale>`, and `comment_<locale>` or `notes_<locale>`; for Chinese it lowercases the locale at `:438-439`, so the applicable columns are normally `translation_zh_cn` and `comment_zh_cn`. It requires Translate Toolkit/`po2csv` at `:7-18` and `:451-454`, plus Hunspell at `:10-14` and `:119-153`. `utils/generate_glossary.py:204-221` additionally uses `poterminology` and `po2csv`. By contrast, `i18n-zh/check_po.py:292-305` intentionally loads five-column TSV, and `:308-318` performs dependency-free exact `(msgid,msgctxt)` checks.
Spec change required: Replace “复用上游 `utils/glossary_checks.py`” with “试点使用 `check_po.py` 内置的 TSV 术语检查；上游 Transifex CSV/Hunspell 工具不纳入试点。”
Proportionate fix: Keep the local TSV implementation. Converting the pilot glossary and installing Translate Toolkit/Hunspell would be heavier than the problem warrants; my incompatibility finding was correct, but adapting the upstream tool would be over-engineering.

### M5
Verdict: Partially confirmed
Evidence: Exact-name inventory is: `tribes/zh_CN.po:89-91` Amazon `Fortress`→`哨所`; `:557-559` Barbarian `Citadel`→`堡垒`; `:593-595` Barbarian `Fortress`→`哨所`; `:629-631` Barbarian `Sentry`→`岗哨`; `:809-811` Empire `Fortress`→`哨所`; `:881-883` Empire `Sentry`→`岗哨`; `:953-955` Frisian `Fortress`→`哨所`; and `widelands/zh_CN.po:11451-11452` uncontextual `Fortress`→empty. The building script explicitly executes `push_textdomain("tribes")` and `pgettext("barbarians_building", "Fortress")` at `data/tribes/buildings/militarysites/barbarians/fortress/init.lua:1-8`. Registration maps `register.lua` to the corresponding `init.lua` at `src/logic/map_objects/description_manager.cc:73-104`; loading executes that script at `:246-279`; tribe loading calls it through `src/logic/map_objects/tribes/tribe_descr.cc:586-600`. The build grid then displays `descr.descname()` at `src/ui/game/fieldaction.cc:100-124`. Therefore, yes: changing only `widelands/zh_CN.po` leaves the build-menu label as `哨所`. However, the current spec already fixes the original scope contradiction at `docs/...design.md:50-63`, explicitly adding targeted cross-domain terminology corrections and citing these exact lines.
Spec change required: none
Proportionate fix: Already applied in the spec. The minimal implementation is to correct the four contextual `Fortress` keys in `tribes/zh_CN.po` according to the approved military-building glossary; the whole tribes domain need not be retranslated.

### M6
Verdict: Confirmed
Evidence: Raw-file inventory over every `<...>` occurrence is 71 occurrences and 14 distinct constructs: `<n>` 16, `<name>` 14, `<reason>` 12, `<msg>` 8, `<br>` 5, `<user>` 4, `<Widelands Home Directory>` 2, `<message>` 2, `<n units>` 2, `<user|game>` 2, plus four one-off header email/address constructs. Classification: paired rich-text tags: none; void rich-text tag: `<br>` 5; non-markup metavariables/comments/header metadata: the other 66. Restricting the inventory to parsed msgid/msgid_plural/msgstr content gives 48 occurrences: `<name>` 14, `<reason>` 12, `<msg>` 8, `<br>` 4, `<user>` 4, and two each of `<Widelands Home Directory>`, `<message>`, and `<user|game>`. The renderer supports paired `rt/div/p/font/link` and void `br/space/vspace/img`: `src/graphic/text/rt_parse.cc:280-287`, `:341-360`, `:380-407`, `:448-455`, `:505-512`, `:554-594`; handlers are registered at `src/graphic/text/rt_render.cc:1869-1884`. Damaged structure throws `SyntaxError` during parsing at `rt_parse.cc:111-121` or `RenderError` for unknown tags at `rt_render.cc:1880-1884`; some widgets catch and fall back, while paths such as tooltip rendering do not.
Spec change required: Replace generic “标签配对” with: “Only recognized Widelands rich-text tags are markup; angle-bracket command metavariables are not tags. In this pilot, nonempty translations must preserve the source’s `<br>` count.”
Proportionate fix: Add a whitelist-based `<br>` count check and ignore all other angle constructs for this catalog. A general XML/HTML tag-pairing validator would produce false positives.

### M7
Verdict: Confirmed but over-engineered
Evidence: No workflow triggers from a push to branch `zh-CN`, and no workflow has a tag-push trigger. `.github/workflows/build.yaml:5-9` accepts pull requests and pushes only to `master` or `protected/*`. `build_appimage.yaml`, `build_clang_tidy.yaml`, `build_codecheck.yaml`, `build_macos.yaml`, `build_testsuite.yaml`, `build_windows.yaml`, `build_windows_arm.yaml`, `build_windows_msvc.yaml`, and `pre-build_checks.yaml` are `workflow_call` only. `check_vcpkg.yaml:5-9` is manual/weekly; `clean_prerelease.yaml:2-7` is manual; `i18n.yaml:5-12` is manual/scheduled and its job is restricted to `widelands/widelands`. Artifact-uploading reusable workflows therefore do not run from that branch push. The release-posting job is additionally restricted to the official repository’s master at `build.yaml:138-147`, and Transifex synchronization is restricted at `i18n.yaml:12`. Thus the accidental public-fork push/tag risk is zero in the current workflows.
Spec change required: Change the non-goal at `docs/...design.md:71` to: “试点只产出并验证译文；是否以及如何制作独立分发包，在试点验收后决定。”
Proportionate fix: Do not add packaging, release artifacts, version pinning, or deployment CI to this pilot. A one-sentence deferral is sufficient; my earlier distribution recommendation was over-engineered.

### M8
Verdict: Rejected
Evidence: Read-only checks report `ROOT_CLAUDE=False` and `rg --files -g 'CLAUDE.md'` returns no matches, so the factual absence is confirmed. But no source, build, test, or repository rule makes `CLAUDE.md` mandatory, and the task can be assessed directly from the code and current design document. No substantiated blocker follows from its absence.
Spec change required: none
Proportionate fix: None. Mentioning the missing file as a review limitation was not useful and should be dropped.

### SUMMARY

C1 Confirmed  
C2 Confirmed  
C3 Partial  
M1 Confirmed  
M2 Partial  
M3 Confirmed  
M4 Overengineered  
M5 Partial  
M6 Confirmed  
M7 Overengineered  
M8 Rejected

M1 matters most among the still-open findings because the runtime loads fuzzy translations while the current validator states the exact opposite and does not fail acceptance.
