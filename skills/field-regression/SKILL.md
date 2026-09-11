---
name: field-regression
description: >
  Field-level regression pipeline: trace a field's call chain with usage-trace,
  extract business scenarios, generate per-scenario API test cases and DB seed
  data, assemble idempotent seed SQL release files (OSS 上线文件) for the field's
  table, and trigger the apifox skill for automated API regression. ALWAYS use
  this skill when the user asks to generate test cases for a field or run a
  field regression — including prompts like "给 storeNo 生成回归用例",
  "生成字段用例", "字段回归", "打通上线SQL", "生成造数SQL", "字段回归流水线",
  "为 orderId 创建用例数据并回归", "create field regression cases",
  "generate seed SQL", "run field regression".
---

# field-regression

Turn a field's usage analysis into regression assets. Pipeline:

```
① usage-trace chain JSON  →  ② scenarios.yaml  →  ③ cases/*.json
                                                       │
⑤ apifox skill regression  ←  ④ oss/*_seed.sql (OSS 上线文件)
```

Division of labor: **CLI is deterministic** (chain JSON, field→table.column
mapping); **you (the agent) do the semantic work** (scenario naming, case data
values); the **apifox skill** (already installed) executes API regression.

## Prerequisites

- `usage-trace` CLI available (`usage-trace --help`); if missing install once:
  ```bash
  python3 -m pip install -U "git+https://github.com/ddsyw/usage-trace.git"
  ```
- An apifox skill for API regression is assumed available in this environment.

## Workflow

### Step 1 — Trace the field (deterministic)

```bash
usage-trace --keyword "<keyword>" --root "<target>" --profile auto --depth 4
```

Outputs (always both):

- `.usage-trace/<keyword>-report.html` — human report
- `.usage-trace/<keyword>-chain.json` — machine input for the steps below

Read `<keyword>-chain.json`. Key fields:

- `usages` — usage sites (file/line/layer/occurrence_type/snippet)
- `nodes` / `edges` — call-chain graph (`kind: unit|table`, `layer`)
- `db_statements` — resolved SQL statements (`linked` = in traced chain)
- `field_columns` — **field → table.column evidence**; non-empty means the
  field is backed by a database column
- `table_schemas` — all columns of involved tables (from DDL / entity / ORM)
- `field_enums` — related enum/constant values, Chinese labels, and per-value
  usage sites (`usages[].scenario` / `trigger` / `method`)
- `scenarios` / `main_paths` — CLI-inferred chain purpose, entry API, tables
  (use as the skeleton; refine names in the user's language)

### Step 2 — DB-field gate

- `field_columns` non-empty → proceed with all steps; set `db_backed: true`.
- `field_columns` empty → **degrade**: produce scenarios.yaml with
  `db_backed: false`, still write cases/*.json (API-level only), **skip Step 4**
  (no seed SQL), and tell the user the field has no direct DB column evidence.

### Step 3 — Business scenarios → `.usage-trace/<keyword>/scenarios.yaml`

Derive one scenario per distinct business usage of the field: group by entry
point (Controller/API node in `main_paths`/`nodes`) crossed with operation type
(query/create/update/delete from `db_statements.op`). Name scenarios in the
user's language. Schema:

```yaml
keyword: storeNo
db_backed: true
field_tables:            # aggregated from field_columns
  - table: t_order
    columns: [store_no]
    ops: [select, insert]
scenarios:
  - id: query_order_by_store        # ascii id, used as file name
    name: 按门店查询订单
    entry: "GET /api/orders?storeNo={storeNo}"   # inferred from Controller nodes
    operation: query                 # query|create|update|delete
    read_write: R                    # R|W|RW
    chain: "OrderController.listByStore → OrderService.findByStoreNo → OrderMapper.selectByStoreNo → t_order.store_no"
    tables:
      - {table: t_order, columns: [store_no], op: select}
    preconditions: ["store_no=S0001 为有效门店"]
    notes: ""
```

Rules: scenario ids stable and unique; every scenario's `chain` must come from
real `nodes`/`edges` (cite real quals, do not invent); include one normal case
per scenario plus boundary cases (empty value / nonexistent value / max length)
when the code shows validation or branching on the field.

### Step 4 — Case data → `.usage-trace/<keyword>/cases/<scenario_id>.json`

One JSON per case (a scenario may yield several cases, suffix `-1`, `-2`, ...).
Values must be **realistic** and consistent with `db_seed` and field semantics
inferred from usages. Schema:

```json
{
  "scenario_id": "query_order_by_store",
  "case_id": "query_order_by_store-1",
  "title": "按门店查询订单-正常",
  "request": {
    "method": "GET",
    "url": "/api/orders",
    "query": {"storeNo": "S0001"},
    "body": {},
    "headers": {"Content-Type": "application/json"}
  },
  "asserts": [
    {"type": "status", "expect": 200},
    {"type": "jsonpath", "path": "$.data[0].storeNo", "expect": "S0001"}
  ],
  "db_seed": {
    "t_order": [
      {"id": 900001, "order_no": "UT20260911001", "store_no": "S0001", "status": "PAID"}
    ]
  },
  "db_assert": {"table": "t_order", "where": "store_no = 'S0001'", "expect_rows_gte": 1}
}
```

- `db_seed` rows must cover the columns seen in `db_statements.sql` /
  entity mappings (respect NOT NULL columns visible in code/SQL).
- Seed ids use the `900xxx` range to avoid colliding with real data.
- `db_assert` is optional (omit for pure-read flows with no state change).

### Step 5 — Seed SQL release file → `.usage-trace/<keyword>/oss/`

Assemble one OSS 上线文件 per physical table from all cases' `db_seed`:

`oss/<YYYYMMDD>_<keyword>_<table>_seed.sql` (date = today, keyword lower snake).

File convention (custom, idempotent, replay-safe):

```sql
-- ============================================================
-- usage-trace field-regression seed SQL (OSS 上线文件)
-- keyword   : storeNo
-- table     : t_order
-- scenarios : query_order_by_store, create_order_with_store
-- generated : 2026-09-11 (by field-regression skill / usage-trace v0.3.0)
-- note      : idempotent inserts (NOT EXISTS guard); ids in 900xxx test range
-- ============================================================

-- scenario: query_order_by_store (case query_order_by_store-1)
INSERT INTO t_order (id, order_no, store_no, status)
SELECT 900001, 'UT20260911001', 'S0001', 'PAID'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM t_order WHERE id = 900001);
```

Rules: one `INSERT ... SELECT ... WHERE NOT EXISTS` per seed row keyed on the
primary key (or the most unique column visible); group rows under a comment
naming scenario + case; never `DROP`/`DELETE`/`UPDATE` existing business data;
string values properly quoted/escaped.

### Step 6 — Automated regression (apifox skill)

Trigger the **existing apifox skill** (do not reimplement API execution):

- Input: the cases directory `.usage-trace/<keyword>/cases/` plus any
  environment info the user provided (base URL / env name).
- Wait for its result, then write a summary to
  `.usage-trace/<keyword>/regression-result.json`:

```json
{
  "keyword": "storeNo",
  "ran_at": "2026-09-11T10:00:00Z",
  "total": 6,
  "passed": 5,
  "failed": 1,
  "failures": [{"case_id": "query_order_by_store-2", "reason": "expect 200 got 404"}]
}
```

If the apifox skill is unavailable in this environment, stop after Step 5 and
tell the user which command/artifacts are ready for manual regression.

## Final summary to user

- scenario count and list (id + name + entry)
- field → table.column evidence (from `field_columns`)
- artifacts paths: `scenarios.yaml`, `cases/`, `oss/*_seed.sql`,
  `regression-result.json` (if ran)
- regression pass rate when available

## Notes

- Never fabricate chain nodes, tables, or columns not present in
  `<keyword>-chain.json`; when uncertain, mark the scenario `notes` field.
- Large chains: work scenario-by-scenario instead of loading everything at once.
- The HTML report (`.usage-trace/<keyword>-report.html`) is for the human; the
  chain JSON is for you — do not parse the HTML.

## Docs

- Plan: `docs/field-regression-plan.md`
- English: `README.md`
- Chinese: `README-CN.md`
