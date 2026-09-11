# AGENTS.md

usage-trace is a Python CLI that traces a keyword's full usage across Java/Spring, Python, or C# codebases and produces a single offline HTML report. End users install it as a coding-agent **plugin + skill** for Codex / Claude Code / Cursor; natural-language prompts like `分析当前项目的 orderId` should auto-load the skill.

## Quick start (dev)

```bash
python3 -m pip install -e ".[dev]"
usage-trace --keyword storeNo --root tests/fixtures/java-spring
```

Report lands at `.usage-trace/<keyword>-report.html`; chain JSON at `.usage-trace/<keyword>-chain.json`.

## Commands

```bash
# tests
python3 -m pytest

# lint
python3 -m ruff check .

# compile check
python3 -m compileall -q src tests

# smoke test
python3 src/usage_trace.py --keyword storeNo --root tests/fixtures/java-spring
```

## Pipeline (src/)

A single `usage-trace` run orchestrates these phases in order:

1. `discover.py` — find keyword usage sites in the target project
2. `trace.py` — build the caller/callee call-chain graph
3. `tables.py` — resolve involved database tables, column mapping (`field_columns`), and table schemas (`table_schemas`)
4. `graph.py` — prune and layout the graph (node cap, layer assignment, grouping)
5. `enums.py` + `semantics.py` — enum/constant values, Chinese titles, chain scenarios, enum-value usage sites
6. `render.py` — emit the offline HTML report from `templates/report.html.tmpl` and write `*-chain.json`

`usage_trace.py` is the orchestrator entry point. `common.py` holds shared helpers (profile loading, graph structure). `understand_rules.py` defines the Understand-Anything-style graph rules. Profiles live in `profiles/`.

Since v0.3.0 every run also writes `.usage-trace/<keyword>-chain.json` (usages, graph, SQL, `field_columns`, `table_schemas`, `field_enums`, `scenarios`; override with `--json-out`). The `field-regression` skill consumes it: scenarios (`scenarios.yaml`) → API cases with `db_seed` (`cases/*.json`) → idempotent seed SQL release files (`oss/*_seed.sql`) → apifox-skill regression. Plan: `docs/field-regression-plan.md`.

## Project layout

```
src/                    CLI and analysis phases
profiles/               analysis profiles (java-*, python-*, csharp-*)
templates/              HTML report template
tests/                  unit tests, e2e tests, and fixture projects
skills/                 Skill definitions (usage-trace, field-regression)
.codex-plugin/          Codex plugin manifest
.claude-plugin/         Claude Code plugin + marketplace manifests
.cursor-plugin/         Cursor plugin + marketplace manifests
plugins/usage-trace/    thin multi-platform plugin wrapper for marketplace install
.agents/plugins/        Codex repo marketplace manifest
scripts/                maintainer install/sync helpers
docs/                   guides (skill-install.md)
```

## Operations

- **End users:** install the marketplace plugin, then ask in natural language (e.g. `分析当前项目的 orderId`). Skill auto-matches; CLI is installed via pip from GitHub if missing.
- Field-regression pipeline: prompts like `给 storeNo 生成回归用例并打通上线SQL` trigger the `field-regression` skill (chain JSON → scenarios → cases with `db_seed` → OSS seed SQL → apifox regression).
- Ops guide: `docs/skill-install.md`.
- Maintainer helpers: `bash scripts/install.sh` (local skill dirs + editable CLI), `bash scripts/install.sh sync`.
- Keep `skills/usage-trace/SKILL.md` and `plugins/usage-trace/skills/usage-trace/SKILL.md` in sync.
- Keep `skills/field-regression/SKILL.md` and `plugins/usage-trace/skills/field-regression/SKILL.md` in sync.

## Conventions

- Keep changes scoped to the module being touched; don't refactor unrelated code.
- The report must be a single offline HTML file with no external HTTP assets.
- When editing plugin.json or SKILL.md, keep platform copies in sync:
  - Codex: root `.codex-plugin/` and `plugins/usage-trace/.codex-plugin/`
  - Claude Code: root `.claude-plugin/` and `plugins/usage-trace/.claude-plugin/`
  - Cursor: root `.cursor-plugin/` and `plugins/usage-trace/.cursor-plugin/`
  - Skill: `skills/usage-trace/SKILL.md` and `plugins/usage-trace/skills/usage-trace/SKILL.md`
  - Skill: `skills/field-regression/SKILL.md` and `plugins/usage-trace/skills/field-regression/SKILL.md`
  - Keep `version` identical across all plugin manifests.
- Description / defaultPrompt fields should include Chinese auto-trigger phrases such as `分析当前项目的 orderId`, `查找字段使用情况`, `追踪调用链`, `生成字段用例`, `字段回归`, `打通上线SQL`.
- `codex-find` is a backwards-compatible alias for `usage-trace`; both map to the same entry point.