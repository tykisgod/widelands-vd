- [Critical] The zero-build command cannot run from a clean checkout: `data/datadirversion` is build-generated and absent, while `--datadir` rejects a missing or mismatched file (`src/wlapplication.cc:1656-1695`). Checking out the daily commit does not generate it; use `--skip_check_datadir_version` or provision the exact file.

- [Critical] The §4.2 verifier is not runnable as shown. `--script` executes only with a scenario/load/editor mode, and `i18n-zh/verify_zh.lua` is outside the mounted `data/` tree. Specify a fixture, `--datadir_for_testing=<repo>`, success/exit handling, and game shutdown. SDL video is still initialized, so this is unattended rather than truly headless.

- [Critical] Placeholder validation does not cover Widelands’ actual format grammar. The stated 463-entry inventory misses valid forms including `%li`, `%1$i`, `%c`, and `%i`; the grammar also supports `%N%`, length modifiers, and additional specifiers (`src/base/format/tree.h:40-75`). A damaged placeholder can cause runtime failure.

- [Moderate] Validation never compares `(msgctxt, msgid, msgid_plural)` keys against `widelands.pot`, rejects fuzzy entries, or defines obsolete-entry handling. Tinygettext loads fuzzy translations by default, so the fixed “2,378 nonempty entries” criterion can pass stale or incomplete catalogs after upstream changes. Rebase alone is not a safe `msgmerge` workflow.

- [Moderate] Representative `_()` calls do not exercise `pgettext`, `ngettext`, `npgettext`, formatting, or actual UI call sites. They therefore cannot detect the claimed binary/catalog mismatch, and tinygettext can log and skip an invalid entry while unrelated anchors still pass.

- [Moderate] `glossary.tsv` is incompatible with `utils/glossary_checks.py`: that tool expects a comma-delimited Transifex schema, has no `msgctxt` support, and requires `po2csv`/Hunspell. An adapter or replacement checker and dependency setup are missing.

- [Moderate] The pilot boundary contradicts the terminology goal. The acknowledged `Fortress → 哨所` errors remain in four contextual `tribes` entries, while only the generic `widelands` entry is in scope. Targeted corrections to source domains are required to achieve consistency.

- [Moderate] Rich-text validation cannot be deferred: the pilot catalog already contains `<br>` plus command metavariables such as `<msg>` and `<name>`. A generic tag-pairing rule will either miss real markup or misclassify metavariables.

- [Moderate] The stated independent Chinese distribution has no packaging, branch CI, release artifact, version-pinning, or update workflow. The proposed hard-coded local launcher and upstream daily binary only define a developer test setup.

- [Moderate] [Uncertain] No root `CLAUDE.md` exists in this checkout, so compliance with the requested project coding standards cannot be assessed.
