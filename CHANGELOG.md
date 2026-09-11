# Changelog

## 0.3.0 — 2026-09-11

### Highlights
- **Field-regression pipeline**: new `field-regression` skill turns field analysis into
  regression assets — business scenarios (`scenarios.yaml`), per-scenario API cases with
  DB seed data (`cases/*.json`), idempotent seed SQL release files (`oss/*_seed.sql`),
  and triggers the apifox skill for automated API regression.

### CLI
- `usage-trace` now also writes a machine-readable chain JSON
  (default `.usage-trace/<keyword>-chain.json`, override with `--json-out`)
- Column-level field→table mapping: `field_columns` in chain JSON and graph
- Table schema extraction (`table_schemas` / node `columns`): DDL `CREATE TABLE`,
  JPA/`@TableName` fields, SQLAlchemy `Column`/`mapped_column`/`Mapped[]`/`Table()`,
  EF Core properties, INSERT column lists
- Enum / constant detection (`src/enums.py`): Java/Python/C# enums, Chinese labels
  from constructor args, per-value usage sites (if / switch / assignment) and
  trigger/scenario text (`src/semantics.py`)
- Method/API Chinese titles from Javadoc, `//` / `#` comments, Python docstrings,
  and Spring/HTTP mappings; chain-scenario purpose on main paths

### Report
- Panels: 链路场景, 字段 → 表列, 涉及表 (all columns + highlighted match),
  枚举 / 固定取值 (label + usage scenario + trigger)
- Graph nodes show method or `GET /path` plus Chinese title when known
- Drag-to-resize left/right panes (double-click splitter to reset)
- Persona switcher documented: 资深 / 初级 / PM (NodeInfo detail only)

### Packaging & ops
- Plugin manifests bumped to `0.3.0` with new triggers (生成字段用例, 字段回归, 打通上线SQL)
- Plan doc: `docs/field-regression-plan.md`

## Unreleased

### Packaging & ops
- End-user path is **marketplace / local plugin install** (Codex, Claude Code, Cursor)
- Natural language like `分析当前项目的 orderId` auto-triggers the skill
- Missing CLI is installed by the skill via `pip install git+https://github.com/ddsyw/usage-trace.git`
- Maintainer `install-skill.sh` also installs the CLI by default (`--skip-cli` to opt out)
- Cursor install docs include Windows PowerShell and macOS/Linux steps
- Removed deprecated `scripts/install-claude-agent.sh` and `docs/claude-code-agent.md`

## 0.2.0 — 2026-07-22

### Highlights
- **P1** tree-sitter engine + incremental `ProjectIndex` (Java)
- **P2** Understand-Anything style offline HTML report (search, theme, persona, NodeInfo)
- **P3** multi-platform packaging: Codex / Claude Code / Cursor plugins, unified `scripts/install.sh`, skill symlink install, optional pre-commit sync hooks
- **P4** multi-language foundation: Python (SQLAlchemy) and C# (EF Core) parsers, profiles, table extraction

### Analysis
- Layer path classification uses path segments (avoids false Service hits on module names)
- Group methods by class in graph layout / report frames
- Improved discovery (camelCase boundaries, plurals)
- Table extraction: MyBatis / JPA / raw SQL / Java SQL strings; SQLAlchemy `__tablename__` + `query/select`; EF Core `[Table]` / `ToTable` / `DbSet` / `FromSqlRaw`
- Profile-scoped `source_exts` so monorepos only index the active language
- Auto profile detection scores by source counts for mixed repos

### Packaging & ops
- Skill-first (no Claude Code subagent)
- `scripts/install.sh` (`cli` / `skill` / `hooks` / `sync`)
- Marketplace manifests for Codex, Claude Code, Cursor
- Docs: `docs/skill-install.md`, dual-language README

### Breaking / notes
- Report output defaults under `.usage-trace/`
- Index cache version bumped with multi-language source sets
- Requires `tree-sitter`, `tree-sitter-java`, `tree-sitter-python`, `tree-sitter-c-sharp`

## 0.1.x — prior
- Initial Java/Spring CLI pipeline and Codex skill packaging

