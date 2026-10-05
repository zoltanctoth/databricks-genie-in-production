> Research appendix. Compiled 2026-10-01 from the official Databricks docs and cited sources by a research agent; every fact carries its source URL and the page "Last updated" date. Re-verify anything dated before you build on it.
>
> Platform note (2026-10-02): the build moved from Databricks Free Edition to a standard workspace (decision D1 in `docs/01-requirements-and-risks.md`). Free Edition limits quoted below are kept as research and no longer constrain the design.

# Unity Catalog metric views — research note (official docs, as of 2026-10-01)

## 1. What "Unity Catalog semantics" covers; where metric views fit; GA status

The `uc-semantics` overview (Sep 11, 2026) lists four components:
- **Metric views** — "Reusable SQL objects that define and govern business KPIs"; UC securables with standard privileges; "the core implementation of Unity Catalog semantics".
- **Domains and subdomains** — business-aligned grouping of assets for the Discover page.
- **Pages** — governed rich-text business-concept pages "for people and Genie One to reference as an authoritative source" (domain, body with `@` asset tags, related assets).
- **Certification and deprecation** — flags; certification "steers Genie One toward the assets your organization vouches for".

Together these form "the human-modeled layer of the Genie Ontology", merged by Genie One with inferred context. No "semantic model" or "UC functions as metrics" object exists under `uc-semantics`; SQL functions appear only as agent-scoped Genie "trusted assets".

**History / GA:** Introduced in DBR 16.4. Blog (Apr 2, 2026): "Unity Catalog Business Semantics is now GA"; at that date the UI editor was "Public Preview" and materialization "currently in Preview". Databricks is "open sourcing the core Metric View implementation in Apache Spark OSS" (SPARK-54119), with "Unity Catalog OSS v0.5" support "coming soon", and joined the Open Semantic Interchange initiative. The Spark 4.2 blog confirms: "Spark 4.2 introduces metric views, bringing a native semantic layer to Spark SQL."

## 2. Anatomy: YAML spec

Top-level keys (yaml-reference, Sep 17, 2026): `version` (spec `0.1`|`1.1`), `comment`, `source` (any table-like UC asset incl. another metric view, or a SQL query), `parameters`, `filter` (applied to all queries), `joins`, `fields` (alias `dimensions`, which the UI emits), `measures`, `materialization`.

- **joins**: `name`, `source`, `on` (`source.` = metric view source; unprefixed = joined table) or `using: [cols]`, nested `joins` (snowflake), `cardinality: many_to_one` (default) | `one_to_many` (DBR 18.1+), `rely: {at_most_one_match: true}` (unvalidated; wrong assertion gives wrong SUM/COUNT).
- **fields**: `name`, `expr` (scalar; source columns, join columns via dot path like `customer.nation.n_name`, or earlier fields), `comment`, `display_name` (≤255 chars), `synonyms` (≤10 × 255 chars), `format`. Wildcards (DBR 18.2+): `source.*`, `customer.* EXCEPT (id)`, `<t>.<struct>.*`; no `name`/metadata on wildcards.
- **measures**: `name`, `expr` (aggregate; may use `FILTER (WHERE …)`, fields, earlier measures via `MEASURE(x)`, parameters), same metadata keys, plus `window: [{order, range, semiadditive, offset}]`.
- **parameters** (DBR 18.2+): `name`, `data_type`, optional `default` (castable, no subquery; once one default is set, all later params need one). Usable anywhere a constant is valid, incl. window `range`/`offset`.
- **format**: `type: number|currency|percentage|byte|date|date_time`; `decimal_places {type: max|exact|all, places}`, `currency_code`, `hide_group_separator`, `abbreviation: none|compact|scientific`, `date_format`, `time_format`, `leading_zeros`.
- Agent metadata requires DBR 17.3 + spec 1.1; under 1.1, `#` YAML comments are stripped on save and `ALTER VIEW` drops UC comments not carried in YAML `comment` fields.

Compact example (condensed from the create page and TPC-H tutorial):

```yaml
version: 1.1
comment: Orders KPIs for sales analysis
source: samples.tpch.orders
parameters:
  - {name: discount, data_type: double, default: 0}
joins:
  - name: customer
    source: samples.tpch.customer
    'on': source.o_custkey = customer.c_custkey
    rely: {at_most_one_match: true}
    joins:
      - name: nation
        source: samples.tpch.nation
        'on': customer.c_nationkey = nation.n_nationkey
filter: source.o_orderdate >= '1995-01-01'
fields:
  - {name: order_date, expr: o_orderdate, display_name: Order Date}
  - {name: order_month, expr: "DATE_TRUNC('MONTH', order_date)", display_name: Order Month}
  - name: order_status
    expr: "CASE o_orderstatus WHEN 'O' THEN 'Open' WHEN 'P' THEN 'Processing' WHEN 'F' THEN 'Fulfilled' END"
    synonyms: [status, fulfillment status]
  - {name: market_segment, expr: customer.c_mktsegment, synonyms: [segment, industry]}
  - {name: customer_nation, expr: customer.nation.n_name, display_name: Country}
measures:
  - {name: order_count, expr: COUNT(DISTINCT o_orderkey), display_name: Order Count}
  - name: total_revenue
    expr: SUM(o_totalprice)
    display_name: Total Revenue
    synonyms: [revenue, sales]
    format: {type: currency, currency_code: USD, decimal_places: {type: exact, places: 2}}
  - {name: discounted_revenue, expr: SUM(o_totalprice * (1 - discount))}
  - {name: avg_order_value, expr: MEASURE(total_revenue) / MEASURE(order_count), synonyms: [AOV]}
  - {name: open_order_revenue, expr: "SUM(o_totalprice) FILTER (WHERE o_orderstatus = 'O')", synonyms: [backlog]}
  - name: t7d_customers
    expr: COUNT(DISTINCT o_custkey)
    window: [{order: order_date, range: trailing 7 day, semiadditive: last}]
```

## 3. Query semantics

- Every measure must be wrapped in `MEASURE(...)` (alias `AGG`, DBR 18.1+); no `SELECT *`. Typical: `SELECT order_month, MEASURE(total_revenue) FROM mv GROUP BY ALL`; `WHERE` on fields is allowed.
- Joins are pruned per query ("the fact and dimension tables needed for the specific query"). Star: source = fact, dims via LEFT OUTER JOIN, many-to-one; many-to-many "selects the first matching row". Snowflake: nested `joins`. `one_to_many`: source is the dimensional spine, facts aggregate at their own grain without fan-out; fields cannot reference one-to-many columns; one aggregate cannot span sources (arithmetic between aggregates is fine); subtrees cannot mix cardinalities; siblings aggregate separately then blend; multi-fact models use a bridge source.
- **Window measures**: `order`, `range: current|cumulative|trailing N unit|leading N unit|all` (unitless N on a dense integer index, DBR 19), `inclusive|exclusive` (DBR 18.1), `semiadditive: first|last` (used when `order` is not grouped), `offset` (e.g. `-12 month`, DBR 18.1). Date-hierarchy fields must be built on the order *field*, not the source column.
- **Composability**: measures reference earlier measures via `MEASURE()`; a metric view can be another's `source`; wildcards import its measures.
- **Parameterized**: `FROM mv(discount => 0.15)` (named), `FROM mv(0.15)` (positional), `FROM mv()`/`FROM mv` (defaults).
- **Cannot**: "Metric views cannot be directly joined with other tables at query time" — wrap in a CTE, then join. No `SELECT *`, no data profiling; string fields are always STRING; ARRAY/MAP must be flattened in the source query and may not appear in joined tables.
- `DESCRIBE TABLE EXTENDED mv AS JSON` returns the YAML and per-column agent metadata; `Type` = `METRIC_VIEW`.

## 4. Materialization

- Top-level `materialization:` block: `schedule` (MV schedule syntax; no `TRIGGER ON UPDATE`; omitted = manual only), `mode: relaxed` (only mode), `materialized_views: [{name, type: aggregated|unaggregated, dimensions, measures, cluster_by, partition_by}]`; one `unaggregated` per view.
- Databricks creates a **managed serverless Lakeflow pipeline** per metric view; initial update on creation, later edits do not trigger refresh; manual refresh via `REFRESH MATERIALIZED VIEW <mv>` (DBR 18.0) or the pipeline UI; incremental where possible; billed as Lakeflow serverless DBUs.
- Automatic rewrite: exact match → rollup match (single additive aggregate: SUM/COUNT/MIN/MAX/BIT_*/BOOL_*; no DISTINCT, window or multi-aggregate measures; no rollup with one_to_many joins) → unaggregated match → source. Verify with `EXPLAIN EXTENDED` or the query profile. Relaxed mode skips freshness checks, so rewritten and non-rewritten queries can differ in freshness.
- **Requirements**: "Your workspace must have serverless compute enabled to run Lakeflow pipelines"; DBR 17.3+. Not allowed with parameters, RLS/column masks/ABAC, invoker-dependent expressions (`current_user()`), group ownership, or owner changes after creation. Blog (Apr 2026): "currently in Preview".
- **Free Edition** (Sep 29, 2026): serverless-only (prerequisite met) but "One active pipeline per pipeline type", one 2X-Small warehouse, 5 concurrent job tasks. Since each materialized metric view owns a pipeline, realistically at most one, competing with any other pipeline. Non-materialized metric views are unconstrained.

## 5. How Genie consumes metric views; why recommended

- Genie Agents accept "up to 50 tables, views, or metric views" and need a pro/serverless warehouse. Best practices: "Metric views are particularly effective for Genie Agents because they pre-define metrics, dimensions, and aggregations. This approach helps you stay within the limit, simplifies your data model, and can improve Genie's response accuracy." Also: "pre-join or de-normalize tables using views or metric views."
- "Synonyms are automatically imported to help Genie better discover and understand available fields and measures"; dashboards auto-apply `MEASURE()` and use display names/formats. The serialized agent config has a dedicated `data_sources.metric_views[]` list.
- GA blog rationale: "Genie spaces can be created directly on top of Metric Views, which means every natural-language query Genie answers is grounded in governed, deterministic definitions, not inferred logic… Genie is no longer hallucinating metrics; it's resolving them from a single source of truth."
- Genie One chat searches Genie Agents first, then "dashboards, queries, and metric views"; Genie Ontology combines "modeled context you govern in Unity Catalog semantics, such as metric views, domains, and Pages" with inferred context. Reverse paths: "Export a Genie Agent as a metric view"; promote dashboard logic to a metric view. Genie One/Agents usage is free through Jan 31, 2027.

## 6. Create / deploy in CI/CD

- **SQL DDL**: `CREATE [OR REPLACE] [TEMPORARY] VIEW name [(col COMMENT …)] WITH METRICS LANGUAGE YAML [COMMENT …] AS $$ <yaml> $$`; `ALTER VIEW name AS $$ full yaml $$` (full replace); `DROP VIEW`; `GRANT SELECT`. Needs UC, DBR 16.4+, SELECT on sources, CREATE TABLE + USE SCHEMA, USE CATALOG.
- **Catalog Explorer**: UI editor (Fields/Measures/Joins/Filter/Materializations/Parameters, Builder or Custom expressions, Preview), `<>` YAML editor, Genie Code authoring, `/importBI` import of Tableau/Power BI model files. Only the owner edits; transfer ownership to a group for collaboration (not for materialized views).
- **Bundles**: The bundle `resources` reference (Sep 17, 2026) has `genie_space`, `dashboard`, `job`, `pipeline`, `schema`, `volume`… but **no metric-view resource**. The community blog (Nov 13, 2025) confirms: "Metric Views are not a supported resource with DABs, so they need to be deployed using a SQL statement." Its pattern (`databricks-dab-examples/knowledge-base/metric-views`): one job of SQL-warehouse notebook tasks (`dim_*` → `fct_*` → `metv_*` → `dashboard_task`) with job parameters `catalog`/`schema` from bundle variables; each `metv_*` notebook runs `USE CATALOG IDENTIFIER(:catalog)`, concatenates `:catalog || '.' || :schema` into the YAML (fully-qualified `source`/join names are required) and runs the DDL via `EXECUTE IMMEDIATE`. Dashboards are native `dashboards:` resources; Genie Agents are `genie_spaces` resources (CLI 1.3.0+, direct deployment engine, `.geniespace.json`).
- **Terraform**: no `databricks_metric_view` resource in the provider's `docs/resources` listing (checked Oct 1, 2026); deploy via SQL instead.

## 7. Limits, gotchas, compute

- **Compute**: DBR 16.4 minimum; 17.3 agent metadata/snowflake/TEMPORARY/materialization/JDBC-ODBC; 18.0 BI compat mode + `REFRESH MATERIALIZED VIEW`; 18.1 one_to_many/`offset`/inclusive-exclusive/`rely`; 18.2 parameters + wildcards; 19 numeric-index windows. SQL warehouses auto-track the latest DBSQL version. Genie Agents need a pro or serverless warehouse.
- **Spec**: `version` is `0.1` or `1.1`; `#` comments stripped under 1.1; `ALTER VIEW` drops UC comments not in YAML; ≤10 synonyms, ≤255 chars each.
- **Silent-wrong-answer traps**: unvalidated `rely.at_most_one_match`; many-to-many picks first row; CHAR padding lost; date hierarchy defined on source column breaks window measures; non-dense numeric index.
- **Query**: `MEASURE()` mandatory, no `SELECT *`, no direct joins, no data profiling.
- **Materialization**: blocked by parameters/RLS/CLM/ABAC/invoker functions/group ownership; freshness varies by rewrite path; Lakeflow DBU cost; Free Edition allows one pipeline per type.
- **BI**: Power BI compat mode removed by Microsoft (April 2026) — use Native query + `MEASURE()` or a wrapper view. OpenSharing of metric views is Beta.

## 8. Facts verified / open questions

**Facts verified** (all docs.databricks.com/aws/en/ unless noted; dates = "Last updated"):
- `uc-semantics/` (Sep 11, 2026): four components; "human-modeled layer of the Genie Ontology".
- `uc-semantics/metric-views/`, `/create` (Sep 11): DDL, prerequisites, UI/Genie Code/wildcards.
- `/feature-availability` (Sep 17): per-DBR feature matrix, spec versions.
- `/query` (Sep 11): MEASURE/AGG, no SELECT *, CTE-then-join, consumer tools.
- `/basic-modeling`, `/joins` (Sep 11): sources, arrays, star/snowflake/one_to_many rules, rely.
- `/advanced-techniques` (Sep 17): window measures, offset, composability.
- `/use-parameters` (Sep 11): TVF syntax, DBR 18.2, no materialization with params.
- `/materialization` (Sep 11): pipeline, serverless requirement, rewrite, restrictions, billing.
- `uc-semantics/agent-metadata` (Sep 11): display names, synonyms limits, format spec, Genie synonym import.
- `/yaml-reference` (Sep 17): grammar, parameters, materialization fields, YAML 1.1 upgrade.
- `/tpch-example`, `/manage`, `/bi-tools` (Sep 11): full example; permissions/ALTER/ownership/OpenSharing Beta; BI patterns.
- `sql/language-manual/sql-ref-syntax-ddl-create-view`: `WITH METRICS` grammar, DESCRIBE output.
- `genie-agents/set-up`, `/best-practices`, `/concepts`; `genie-one/chat` (Sep 17): 50-object limit, warehouse requirement, metric-view recommendation, export-to-metric-view, Genie Ontology.
- `getting-started/free-edition-limitations` (Sep 29): serverless only, one pipeline per type.
- `dev-tools/bundles/resources` (Sep 17): no metric-view resource; `genie_space` exists.
- databricks.com/blog/redefining-semantics-data-layer-future-bi-and-ai (Apr 2, 2026): GA; SPARK-54119; UC OSS v0.5; materialization in Preview. databricks.com/blog/introducing-apache-spark-42: metric views in Spark 4.2.
- community.databricks.com/t5/technical-blog/how-to-deploy-metric-views-with-dabs/ba-p/138432 (Nov 13, 2025) + github.com/databricks-solutions/databricks-dab-examples (knowledge-base/metric-views): EXECUTE IMMEDIATE pattern, job YAML.
- `release-notes/product/2026/april`: Power BI compat mode removed; Google Sheets connector GA.

**Open questions:**
- Has a native bundle or Terraform resource for metric views shipped since Sep 17, 2026? None found (Terraform check was a filename grep of `docs/resources`).
- Preview/GA status of materialization and the UI editor after April 2026 (no preview badges in docs, no explicit GA note).
- Release status and parity of Spark 4.2 OSS metric views / UC OSS v0.5.
- Genie Ontology authority-scoring details (linked page not found on AWS docs).
