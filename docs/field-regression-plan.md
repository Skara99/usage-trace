# 字段级回归流水线规划（usage-trace v0.3.0）

> 状态：CLI / skill 骨架已落地（v0.3.0）。报告侧后续又补了表结构、枚举取值、链路场景、可拖拽侧栏。
> 日期：2026-09-11
> 范围：CLI 增强 + 新 skill `field-regression` + 插件同步 + 文档

## 1. 背景与目标

现有 `usage-trace` 止步于"分析报告"：字段用法、调用链、涉及的表。
实际需求是把分析结果**变现为测试资产**，形成闭环流水线：

```
用户(Cursor): "给 storeNo 生成回归用例并打通上线SQL"
      │
      ▼
[field-regression skill] 编排 5 步
      ├─① usage-trace CLI: 输出链路 JSON + 列级 字段→表.列 映射（确定性）
      ├─② LLM 整理业务场景 → scenarios.yaml
      ├─③ LLM 按场景生成用例数据 → cases/*.json（接口用例 + db_seed）
      ├─④ 组装字段所在表(tb)的新增造数 SQL → oss/ 上线文件
      └─⑤ 触发已有 apifox skill 自动回归 → 汇总结果
```

关键决策（已确认）：

| 决策点 | 结论 |
|--------|------|
| 架构 | 新建独立 `field-regression` skill；`usage-trace` skill 保持纯分析 |
| 分工 | LLM 为主做场景提取与用例数据生成；CLI 只做确定性部分（链路 JSON、列级映射） |
| tb 含义 | 字段所在的数据库表；"打通新增 SQL" = 为该表生成造数 INSERT 上线文件 |
| OSS 上线文件 | 本次按自定义规范生成（溯源注释头 + 幂等 INSERT），后续可对齐内部规范 |
| apifox 回归 | 已有独立 skill；本流水线只定义触发点与输入输出契约 |

## 2. 现状差距

| 需求环节 | v0.2.0 现状 | 缺口 |
|---------|------------|------|
| ① 字段→链路 | 已有（usage sites + 调用链 + 分层） | 缺机器可读 JSON 输出（只有 HTML） |
| ② 判定字段对应 DB 字段 | 只有表级解析（MyBatis/JPA/MP/SQLAlchemy/EF） | 缺**列级**确认：字段是否命中 SQL 列 / Entity 映射 |
| ③ 业务场景整理 | 无 | 全新：LLM 基于链路 JSON 提取场景 |
| ④ 用例数据生成 | 无 | 全新：LLM 按场景生成接口用例 + db_seed |
| ⑤ tb 新增 SQL（OSS 上线文件） | 无 | 全新：造数 SQL 组装规范 |
| ⑥ apifox 回归 | 已有独立 skill（假定可用） | 只需触发点 + 结果汇总 |

## 3. Phase 1 — CLI 增强（确定性部分）

### 3.1 列级映射 `field_columns`（src/tables.py）

在 `resolve_tables()` 汇总完 `db_statements` 之后追加一步：

- 输入：`db_statements`（含 `sql` / `tables` / `op` / `source` / `statement_id`）、关键字变体列表
- 变体来源：复用 `discover.keyword_variants(keyword)`（storeNo → storeNo/store_no/STORE_NO/…，最长优先）
- 匹配规则（保守，避免误报）：
  1. **SQL 列位置匹配**：在语句文本中找 `\b<variant>\b`（word-boundary，大小写不敏感），
     且变体出现在列语法位置：`WHERE`/`AND`/`ON`/`SET`/`IF`/`GROUP BY`/`ORDER BY` 之后、
     `INSERT INTO ... (cols)` 列清单内、`SELECT <variant>` 投影内
  2. 简化实现：直接 word-boundary 匹配 SQL 文本即可（变体已含 snake/camel 形态，
     `#{storeNo}` 参数占位同样视为"语句使用该字段"的证据）
  3. 命中后按语句的 `tables` 展开为 `(table, column)` 对；若语句无表则跳过
- 去重键：`(table, column, op, statement_id)`
- 产出写入 `graph["field_columns"]`：

```json
[{
  "table": "t_order",
  "column": "store_no",
  "variant": "store_no",
  "op": "select",
  "source": "mybatis_xml",
  "statement_id": "com.example.mapper.OrderMapper.findByStoreNo",
  "sql": "SELECT * FROM t_order WHERE store_no = #{storeNo}",
  "file": "src/main/resources/mapper/OrderMapper.xml"
}]
```

- 排序：`(table, column, op)` 稳定排序，SQL 截断到 400 字符
- **判定规则**：`field_columns` 非空 ⇒ 字段对应数据库字段（skill 据此决定走 ③④⑤）
- `resolve_tables()` 签名增加可选参数 `keyword_variants: list[str] | None = None`，
  向后兼容（默认 None = 不做列级映射，独立 phase-3 调试入口行为不变）

### 3.2 链路 JSON 输出（src/usage_trace.py）

- 新增 CLI 参数 `--json-out <path>`；不传时默认写 `.usage-trace/<keyword>-chain.json`（与报告同目录）
- `run()` 组装 chain JSON（在 `prune_and_layout` 之后、`render` 之前）：

```json
{
  "keyword": "storeNo",
  "meta": {"project": "...", "language": "java-spring", "generated_at": "...", "depth": 4},
  "usages": [{"file": "...", "line": 12, "layer": "Controller", "hit": "param", "text": "...", "class": "OrderController"}],
  "nodes": [{"id": "...", "kind": "unit|table", "label": "...", "layer": "...", "qual": "...", "col": 1, "row": 0}],
  "edges": [{"from": "...", "to": "...", "kind": "call", "confidence": "confirmed", "op": "..."}],
  "db_statements": [{"source": "...", "op": "...", "tables": ["t_order"], "sql": "...", "statement_id": "...", "linked": true}],
  "field_columns": [ ... ],
  "main_paths": [ ... ],
  "counts": {"usages": 12, "nodes": 30, "tables": 2, "field_columns": 3}
}
```

- nodes 只保留 LLM 需要的字段（id/kind/label/layer/qual/col/row），
  edges 保留 from/to/kind/confidence/op
- 该 JSON 是 `field-regression` skill 的**唯一机器输入**

### 3.3 报告展示（src/render.py）

- 报告摘要区新增"字段→表列"区块：`{{FIELD_COLUMNS_HTML}}`
- 列：表 / 列名 / 操作 / 来源 / 语句 ID；空时显示"未发现该字段直接对应数据库列"

### 3.4 测试

- `test_tables.py`：fixtures(java-spring) 上断言 `t_order / store_no / mybatis_xml` 命中；
  无关字段（如 `OrderService`）不产生误报；`keyword_variants=None` 向后兼容
- `test_cli.py`：`run()` 产出 chain.json；`--json-out` 自定义路径生效；
  `counts.field_columns` 正确；usages/nodes/edges/db_statements 结构字段齐备

## 4. Phase 2 — 新 skill `field-regression`

### 4.1 文件位置

- `skills/field-regression/SKILL.md`（源）
- `plugins/usage-trace/skills/field-regression/SKILL.md`（同步副本，内容一致）

### 4.2 SKILL.md 要素

- frontmatter `name: field-regression`，description 含中英触发词：
  `生成字段用例`、`字段回归`、`打通上线SQL`、`生成造数SQL`、`字段回归流水线`、
  `create field regression cases`、`generate seed SQL`
- 依赖声明：第一步调用 `usage-trace` CLI；第五步调用**已有的 apifox skill**（不做其内部实现）

### 4.3 工作流（写入 SKILL.md，LLM 可执行）

1. **链路分析**：`usage-trace --keyword <K> --root . --profile auto --depth 4`
   → 读 `.usage-trace/<K>-chain.json`
2. **DB 字段判定**：`field_columns` 非空？
   - 空 → 降级：只输出链路摘要与场景草稿（scenarios.yaml 的 `db_backed: false`），跳过 ④
3. **场景整理** → `.usage-trace/<K>/scenarios.yaml`：

```yaml
keyword: storeNo
db_backed: true
field_tables: [{table: t_order, columns: [store_no], ops: [select, insert]}]
scenarios:
  - id: query_order_by_store
    name: 按门店查询订单
    entry: "GET /api/orders?storeNo={storeNo}"     # 从 Controller 节点推断
    operation: query                                 # query|create|update|delete
    read_write: R / W / RW
    chain: "OrderController.listByStore → OrderService.findByStoreNo → OrderMapper.selectByStoreNo → t_order.store_no"
    tables: [{table: t_order, columns: [store_no], op: select}]
    preconditions: ["store_no 存在有效门店记录"]
    notes: ""
```

4. **用例数据** → `.usage-trace/<K>/cases/<scenario_id>.json`（平台无关、字段贴近 apifox 导入格式）：

```json
{
  "scenario_id": "query_order_by_store",
  "title": "按门店查询订单-正常",
  "request": {"method": "GET", "url": "/api/orders", "query": {"storeNo": "S0001"}},
  "headers": {"Content-Type": "application/json"},
  "asserts": [{"type": "status", "expect": 200}, {"type": "jsonpath", "path": "$.data[0].storeNo", "expect": "S0001"}],
  "db_seed": {
    "t_order": [
      {"id": 900001, "order_no": "UT20260911001", "store_no": "S0001", "status": "PAID"}
    ]
  },
  "db_assert": {"table": "t_order", "where": "store_no = 'S0001'", "expect_rows_gte": 1}
}
```

5. **OSS 上线文件** → `.usage-trace/<K>/oss/<YYYYMMDD>_<K>_<table>_seed.sql`
   - 自定义规范：头部溯源注释（关键字/表/场景/生成时间/工具版本）；
     每场景一段；INSERT 前存在性守卫（`INSERT ... SELECT ... WHERE NOT EXISTS`）保证幂等；
     数值来自各场景 `db_seed`
6. **回归**：调用已有 apifox skill，传 `cases/` 目录 + 基础环境信息；
   等待结果 → 汇总通过率/失败用例，回写 `.usage-trace/<K>/regression-result.json`

### 4.4 降级路径

- `field_columns` 为空：不生成造数 SQL 与上线文件，明确告知用户"字段未直接命中数据库列"
- apifox skill 不可用：止步于 ④，输出待执行说明

## 5. Phase 3 — 插件同步与版本

- 六份 plugin.json（root/thin × codex/claude/cursor）版本 `0.2.0+codex.*` → `0.3.0+codex.<ts>` 统一 bump
- description / defaultPrompt 增补新触发词（`生成字段用例`、`字段回归` 等），三平台同步
- `test_skill_def.py` 扩展：
  - 新 skill 存在、frontmatter 合法、含中英触发词
  - 源/副本内容一致
  - SKILL.md 含关键契约字面量（`chain.json`、`scenarios.yaml`、`cases/`、`oss/`、`db_seed`、apifox）

## 6. Phase 4 — 文档

- README.md / README-CN.md：新增"字段回归流水线"章节（架构图、快速示例、文件契约）
- AGENTS.md：pipeline 与 conventions 增补 field-regression skill 说明
- docs/skill-install.md：新 skill 的触发示例

## 7. 测试与验证

```bash
python3 -m pytest            # 全量单测（含新增 CLI/skill 测试）
python3 -m ruff check .      # lint
python3 -m compileall -q src tests
python3 src/usage_trace.py --keyword storeNo --root tests/fixtures/java-spring
# → 检查 .usage-trace/storeNo-chain.json：field_columns 含 t_order.store_no
```

## 8. 风险与边界

| 风险 | 缓解 |
|------|------|
| 列级匹配误报（字段名恰好是 SQL 关键字/别名） | word-boundary + 变体最长优先 + 保守语句来源（仅已解析 db_statements） |
| 动态 SQL（MyBatis `<if>`）列不确定 | 记录原始 SQL 片段，LLM 场景整理时人工可见 |
| 用例数据与真实库表结构不匹配 | db_seed 由 LLM 基于 SQL/Entity 定义生成；上线文件带存在性守卫可重放 |
| apifox skill 契约变化 | 触发点只传 cases 目录 + 环境信息，适配层留在 apifox skill 侧 |
| 大项目 LLM 上下文膨胀 | chain.json 已剪枝（max-nodes 上限后输出），场景整理分批进行 |
