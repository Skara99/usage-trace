# usage-trace

[中文文档](README-CN.md)

`usage-trace` is a coding-agent **plugin + skill** for tracing a field or
identifier through Java, Python, or C# codebases. After installing the plugin in
Codex / Claude Code / Cursor, ask naturally:

```text
分析当前项目的 orderId
```

The skill auto-matches, ensures the local CLI is available, and writes a single
offline HTML report covering usage sites, call chains, related tables, column
mapping, chain scenarios, and enum values.

## Features

- Search keyword usages with generated naming variants.
- Build a caller/callee graph around matched methods.
- Classify layers such as Controller, Service, Repository, Entity, SQL, Table,
  and package/path-based layers.
- Resolve database table access from language-specific sources (MyBatis, JPA,
  SQLAlchemy, EF Core, raw SQL, string SQL, and more).
- Map the keyword to physical table columns (`field_columns`) and extract the
  table's full column list (`table_schemas`) from DDL / entities / ORM models.
- Detect related enums and constants (`field_enums`), including Chinese labels
  and per-value usage scenarios / triggers.
- Infer method/API Chinese titles and chain-scenario purpose from comments,
  Javadoc/docstrings, and Spring/HTTP mappings (`src/semantics.py`).
- Emit a machine-readable chain JSON for downstream automation.
- Field-regression pipeline skill: business scenarios, API test cases with DB
  seed data, idempotent seed SQL release files, and apifox-skill regression.
- Render a single self-contained offline HTML report (resizable side panes,
  资深/初级/PM personas).
- Marketplace plugins for Codex / Claude Code / Cursor with auto skill matching.
- Support Java, Python, and C# through `--profile auto`.
- Keep `codex-find` as a compatibility command while using `usage-trace` as the
  primary name.

## Install (plugin only)

### Codex

```bash
codex plugin marketplace add ddsyw/usage-trace --ref main
codex plugin add usage-trace@usage-trace
```

Or open `/plugins` in Codex and install from the `usage-trace` marketplace.

### Claude Code

```text
/plugin marketplace add ddsyw/usage-trace
/plugin install usage-trace@usage-trace
```

### Cursor

Local plugin install (recommended today):

**Windows PowerShell** (from this repository root):

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.cursor\plugins\local\usage-trace" | Out-Null
Copy-Item -Recurse -Force ".\plugins\usage-trace\*" "$env:USERPROFILE\.cursor\plugins\local\usage-trace\"
```

**macOS / Linux / Git Bash**:

```bash
mkdir -p ~/.cursor/plugins/local/usage-trace
cp -R plugins/usage-trace/. ~/.cursor/plugins/local/usage-trace/
```

Confirm:

```text
~/.cursor/plugins/local/usage-trace/.cursor-plugin/plugin.json
~/.cursor/plugins/local/usage-trace/skills/usage-trace/SKILL.md
```

Or follow Cursor Marketplace submission docs for the packaged plugin.

## Use (auto skill trigger)

In the target project, ask in plain language — no need to name the skill:

```text
分析当前项目的 orderId
```

```text
查找 storeNo 字段项目使用情况，生成报告并总结调用链和表
```

```text
Trace userId usage, call chain, and related tables
```

The agent should:

1. Load the `usage-trace` skill automatically
2. If `usage-trace` is missing, install the CLI once:
   ```bash
   python3 -m pip install -U "git+https://github.com/ddsyw/usage-trace.git"
   ```
3. Run:
   ```bash
   usage-trace --keyword orderId --root . --profile auto --depth 4
   ```
4. Summarize `.usage-trace/orderId-report.html`

## What the agent runs (CLI reference)

```bash
usage-trace --keyword <identifier> --root <project> [options]
```

- `--keyword`: required keyword or field name, for example `orderId`.
- `--root`: required target project root (`.` for current project).
- `--profile`: language profile. Default is `auto`; profiles include
  `java-spring`, `java-generic`, `python-sqlalchemy`, `python-generic`,
  `csharp-ef`, `csharp-generic`.
- `--depth`: call-chain depth. Default is `4`; the code applies a hard cap.
- `--max-nodes`: maximum graph nodes rendered in the report. Default is `300`.
- `--variants`: comma-separated extra keyword variants to search.
- `--out`: optional output HTML path. Default is `.usage-trace/<keyword>-report.html`
  in the current directory.
- `--json-out`: optional chain JSON path. Default is
  `.usage-trace/<keyword>-chain.json` (usages, graph, SQL, `field_columns`,
  `table_schemas`, `field_enums`, `scenarios` — machine input for
  `field-regression`).

Compatibility command:

```bash
codex-find --keyword orderId --root /path/to/your/project
```

## Report contents

The generated HTML report includes:

- a summary of matched usage counts and table counts
- an interactive layered call-chain dashboard with a default main-path view,
  left-side layer tabs, group frames, search, pan, zoom, and click-to-focus
  neighborhood highlighting
- graph node labels: method name or HTTP API (`GET /api/orders`), plus a
  Chinese title when a comment/Javadoc/docstring is present
- **链路场景**: what each main path does, entry API, call chain, and table
- **字段 → 表列**: keyword → physical column evidence
- **涉及表**: all resolved columns of each table, with the traced column highlighted
- **枚举 / 固定取值**: enum/constant names, values, Chinese labels, usage
  scenarios, and how each value is triggered (`if` / `switch` / assignment)
- drag-to-resize left/right panes (double-click a splitter to reset)
- persona switcher (资深 / 初级 / PM) for NodeInfo detail level
- Understand-Anything-style graph metadata: node type, complexity, tags,
  weighted edges, architecture layers, guided tour steps
- usage-site details, SQL diagnostics, truncation / inferred-edge notes

The report is a single offline HTML file with no external HTTP assets.

### Persona (资深 / 初级 / PM)

These buttons only change the **right-hand node detail** panel:

| | 资深 (default) | 初级 | PM |
|---|---|---|---|
| Summary / Chinese title / purpose | yes | yes | yes |
| Related tables / SQL | yes | yes | yes |
| Callers / callees | clickable | names only | hidden |
| Method source | yes | yes | hidden |
| Complexity | `simple/moderate/complex` | `简单/中等/复杂` | hidden |

## Support matrix

- Java/Spring:
  - keyword usage tracing
  - controller/service/repository/entity layer classification
  - MyBatis XML and annotation SQL
  - JPA repository/entity table mappings
  - raw SQL files and Java SQL string literals
- Plain Java:
  - keyword usage tracing
  - call-chain graph
  - package/path-based layer classification
  - MyBatis XML mapper SQL
  - raw SQL files and Java SQL string literals
- Python (SQLAlchemy / generic):
  - keyword usage + call-chain tracing (tree-sitter-python)
  - `__tablename__` / `Table()` / `Column()` / `mapped_column` / `Mapped[]`
  - SQL string table hints; enum classes (`class X(Enum)`)
- C# (EF Core / generic):
  - keyword usage + call-chain tracing (tree-sitter-c-sharp)
  - `[Table]` / `ToTable` / `DbSet` and SQL string table hints
  - `enum` member values

## Debug pipeline

The single `usage-trace` command orchestrates these phases:

1. `src/discover.py`: discover keyword usage sites
2. `src/trace.py`: build the call graph
3. `src/tables.py`: resolve database tables, columns, and schemas
4. `src/graph.py`: prune and layout graph nodes
5. `src/enums.py` + `src/semantics.py`: enum values, Chinese titles, chain scenarios
6. `src/render.py`: render the offline HTML report + write `*-chain.json`

These scripts remain available for debugging individual phases.

## Field-regression pipeline (v0.3.0)

The `field-regression` skill (shipped in the same plugin) turns a field's
analysis into regression assets. Trigger naturally:

```text
给 storeNo 生成回归用例并打通上线SQL
```

Pipeline:

1. `usage-trace` writes `<keyword>-chain.json` including `field_columns`
   (field → table.column evidence)
2. Agent derives business scenarios → `.usage-trace/<keyword>/scenarios.yaml`
3. Agent writes per-scenario API cases with `db_seed` rows →
   `.usage-trace/<keyword>/cases/*.json`
4. Idempotent seed SQL release files (OSS 上线文件) →
   `.usage-trace/<keyword>/oss/YYYYMMDD_<keyword>_<table>_seed.sql`
5. Triggers the existing apifox skill for automated API regression and writes
   `regression-result.json`

When `field_columns` is empty the pipeline degrades to API-level cases only
(no seed SQL). Design doc: `docs/field-regression-plan.md`.

## Development

```bash
git clone https://github.com/ddsyw/usage-trace.git
cd usage-trace
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m ruff check .
python3 -m compileall -q src tests
```

Smoke test:

```bash
python3 src/usage_trace.py \
  --keyword storeNo \
  --root tests/fixtures/java-spring
```

Maintainer helpers (not required for end users):

```bash
bash scripts/install.sh          # local skill dirs + editable CLI
bash scripts/install.sh sync     # sync thin plugin SKILL.md
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Project layout

```text
.agents/plugins/marketplace.json   Codex repo marketplace
.codex-plugin/plugin.json          Root Codex plugin manifest
.claude-plugin/                    Claude Code plugin + marketplace
.cursor-plugin/                    Cursor plugin + marketplace
docs/skill-install.md              Plugin install and usage guide
plugins/usage-trace/               Thin multi-platform plugin wrapper
profiles/                          analysis profiles (java/python/csharp)
scripts/                           Maintainer install/sync scripts
skills/usage-trace/SKILL.md        Skill definition (synced into plugin)
skills/field-regression/SKILL.md   Field-regression pipeline skill
src/                               CLI and analysis phases
templates/report.html.tmpl         offline report template
tests/                             Unit, integration, and fixture tests
```

## Limitations

- The call graph is static and heuristic; reflection, runtime proxies, dynamic
  SQL generation, and complex dependency injection may require manual review.
- Very large projects may need a lower `--max-nodes` value or narrower keyword
  variants to keep reports readable.