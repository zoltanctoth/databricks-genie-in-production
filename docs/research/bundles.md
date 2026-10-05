> Research appendix. Compiled 2026-10-01 from the official Databricks docs and cited sources by a research agent; every fact carries its source URL and the page "Last updated" date. Re-verify anything dated before you build on it.
>
> Platform note (2026-10-02): the build moved from Databricks Free Edition to a standard workspace (decision D1 in `docs/01-requirements-and-risks.md`). Free Edition limits quoted below are kept as research and no longer constrain the design.

# Declarative Automation Bundles (ex-DABs) — research notes, 2026-10-01

Scope: one workspace, `dev` + `prod` targets, deploying: SDP medallion pipeline, Lakeflow job, UC metric views, 2 Genie Agents, 1 Databricks App, 1 custom-agent serving endpoint.

## 1. Bundles today

- **Name**: "Declarative Automation Bundles (formerly known as Databricks Asset Bundles)", renamed **March 16, 2026**. CLI commands and YAML keys unchanged.
- **CLI**: minimum documented v0.218.0, but this stack needs **>= 1.3.0** (Genie, direct default). Latest release **v1.19.0 (2026-09-30)**; weekly cadence.
- **Engines**: `terraform` (legacy) and `direct` (Go SDK, no Terraform). Direct is **GA since CLI 1.3.0 (June 10, 2026)** and the default ("default value is `direct`", reference page). Since **1.14.0** Terraform bundles auto-migrate after a clean dry-run; opt out via `bundle.engine: terraform`. Docs: "the Terraform deployment engine will soon be disabled."
- **Direct-only resources** (direct page, Sep 17, 2026): cluster policies, UC catalogs, external locations, UC secrets, **Genie spaces**, instance pools, AI Search endpoints, MCP services, model provider services, model services, Postgres snapshot schedules. `lifecycle.started` (apps/clusters/warehouses) is direct-only. `pipeline.cascade_on_destroy` (CLI 1.12.0) is direct-only.
- **Direct-engine semantics that bite**: state is `.databricks/bundle/<target>/resources.json` (local config snapshot, synced to workspace). **Removing a field from YAML reverts it to the server default** (Terraform left it unchanged). `bundle plan -o json` gives per-field diffs; `bundle deploy --plan plan.json` replays an approved plan.
- Python for bundles is GA (CLI 0.275.0) but **not supported in the workspace UI editor**; stay YAML.

## 2. Resource-by-resource (resources page, last updated Sep 17, 2026)

Supported top-level keys relevant here: `pipelines`, `jobs`, `genie_spaces`, `apps`, `model_serving_endpoints`, `dashboards`, `schemas`, `volumes`, `sql_warehouses`. **No metric-view resource exists.** Every resource supports `lifecycle: {prevent_destroy}` and `permissions` (except schemas/volumes, which use `grants`).

**pipelines** — keys: `name`, `catalog`, `schema` (`target` deprecated), `serverless`, `development`, `continuous`, `channel`, `libraries` (`notebook.path`, `file.path`, `glob`), `root_path`, `configuration`, `parameters`, `environment`, `event_log`, `run_as`, `tags`, `cascade_on_destroy`. Free Edition => `serverless: true`, no `clusters`.

**jobs** — keys: `name`, `tasks`, `environments` (required for serverless tasks), `schedule`/`trigger`/`continuous`, `parameters`, `max_concurrent_runs`, `run_as`, `email_notifications`, `tags`. Tasks: `pipeline_task.pipeline_id: ${resources.pipelines.X.id}`; `sql_task` with `file.path`, `query.query_id`, `alert`, `dashboard` — **`warehouse_id` is Required**; `notebook_task.notebook_path`. `git_source` discouraged.

**genie_spaces** (CLI 1.3.0, direct-only) — full key list: `title` (optional override), `description`, `warehouse_id` (**Required**), `serialized_space` (**Required** unless `file_path`), `file_path` (local `*.geniespace.json`; takes precedence over `serialized_space`), `parent_path` (defaults to `${workspace.resource_path}`), `permissions` (levels `CAN_VIEW`, `CAN_RUN`, `CAN_EDIT`, `CAN_MANAGE`), `lifecycle`. Output substitution `${resources.genie_spaces.<key>.space_id}` (used by bundle-examples `app_with_genie_space`).
`.geniespace.json` format (docs example): `{"version": 2, "config": {"sample_questions": [{"id": "<32 hex>", "question": ["..."]}]}, "data_sources": {"tables": [{"identifier": "cat.sch.tbl", "column_configs": [{"column_name": "..."}]}]}, "instructions": {"text_instructions": [{"id": "<32 hex>", "content": ["..."]}]}}`. Table identifiers are fully qualified literals.
**Export an existing agent**: `databricks bundle generate genie-space --existing-id <space-id>` (space ID is in URL `.../genie/rooms/<id>` or Configure > About). Writes `resources/<key>.genie_space.yml` + `src/<key>.geniespace.json` (bundle-commands page, Sep 25, 2026). Re-sync after UI edits: `databricks bundle generate genie-space --resource <key> --force [--watch]`. UI edits do **not** flow back automatically; deploy detects remote drift and asks to overwrite. **Genie spaces are not bindable** (`bundle deployment bind` list: jobs, pipelines, schemas, volumes, registered_models, quality_monitors, plus clusters/dashboards/model_serving_endpoints per release notes) — generate = template, deploy = new space with new ID. History: GitHub issue databricks/cli#3008 opened 2025-06-06 ("blocked until there is a public API"), closed 2026-06-10 via PR #5282, shipped in v1.3.0.

**apps** (CLI 0.239.0) — keys: `name` (lowercase alnum + hyphens, unique in workspace), `source_code_path`, `description`, `config` (`command`, `env` list; `value_from: <resource-name>` injects IDs), `resources` list (each with `name`, `description`, and one of `genie_space{name, space_id, permission: CAN_VIEW|CAN_EDIT|CAN_MANAGE|CAN_RUN}`, `serving_endpoint{name, permission: CAN_QUERY|CAN_MANAGE|CAN_VIEW}`, `sql_warehouse{id, permission: CAN_USE|CAN_MANAGE|IS_OWNER}`, `job`, `secret`, `uc_securable`, `database`, `postgres`, `experiment`, `app`), `compute_size`, `user_api_scopes`, `permissions` (`CAN_USE`, `CAN_MANAGE`), `lifecycle.started` (direct-only), `git_repository`/`git_source`. Generate from existing: `bundle generate app --existing-app-name X [--bind]`.

**model_serving_endpoints** — keys: `name` (required, unique per workspace, alnum/dash/underscore), `config.served_entities[]` (`entity_name` = UC model `cat.sch.model`, `entity_version`, `workload_size`, `scale_to_zero_enabled`, `workload_type`, `environment_vars`), `config.traffic_config.routes[]` (`served_model_name`, `traffic_percentage`), `ai_gateway` (external/PT only), `tags`, `description`, `email_notifications`, `telemetry_config` (CLI 1.6.0), `budget_policy_id`, `route_optimized`, `permissions`. Bindable since 0.247.0. **`run_as` is not supported; an error occurs if an MSE is in a bundle where `run_as` is configured** (run-as page, Sep 11, 2026).

**dashboards** (0.232.0) — `display_name`, `file_path` (`*.lvdash.json`) or `serialized_dashboard`, `warehouse_id`, `parent_path`, `embed_credentials`, `dataset_catalog`/`dataset_schema` (0.283.0, per-target parameterisation), `permissions`. Deploy errors if remote JSON drifted (`--force` overwrites); `bundle generate dashboard --existing-id ... --watch`.

**schemas** — `catalog_name`, `name`, `comment`, `properties`, `storage_root`, `grants[]{principal, privileges}`. "The owner of a schema resource is always the deployment user ... `run_as` ... will be ignored." Bindable.

**volumes** (0.236.0) — `catalog_name`, `schema_name`, `name`, `volume_type` (MANAGED|EXTERNAL), `storage_location`, `grants`. Not prefixed in development mode — add `${bundle.target}` yourself. Cannot be `artifact_path` until it exists.

**Metric views** — no resource (community thread 2026-07-25: "there is no metric view resource in Asset Bundles today"). Pattern: `CREATE OR REPLACE VIEW cat.sch.mv WITH METRICS LANGUAGE YAML AS $$ ... $$` in a `.sql` file run by a job `sql_task` (`file.path`, `warehouse_id`, `parameters: {catalog, schema}`), wrapped in `USE CATALOG IDENTIFIER(:catalog)` + `EXECUTE IMMEDIATE` because `source:` in the YAML must be a fully-qualified literal. Metric view YAML `version: 1.1` uses `fields`/`measures`/`joins`/`parameters`. Deployment becomes **deploy, then `bundle run metric_views_ddl -t <target>`**, upstream of the Genie agents that reference the views by FQN.

## 3. Dev/prod in ONE workspace

- **Targets**: `targets.<name>` with `default: true` on one; `mode`, `presets`, `variables`, `workspace.{host,root_path,...}`, `run_as`, per-target `resources` overrides. Same `workspace.host` for both targets is fine; isolation comes from `root_path`, names, and UC catalog/schema.
- **`mode: development`** (deployment-modes page, Sep 11, 2026): prefixes names with `[dev ${workspace.current_user.short_name}]` (Genie titles too — blog confirms "[dev <name>] Demo NYC Taxi Space"), tags `dev`, sets pipelines `development: true`, pauses all schedules/triggers, allows concurrent job runs, disables the deployment lock. Volumes and files are not prefixed. **Correction 2026-10-05:** schemas ARE prefixed, with `dev_<short_name>_` (brackets are not valid in a schema name); observed in the target workspace as `genie_reference.dev_tothz_raw`. Reference schemas through `${resources.schemas.<key>.name}` so dependent paths pick up the prefix.
- **`mode: production`**: validates pipelines `development: false`; optional `git.branch` check (`--force` to bypass); if `run_as` is not a service principal it validates that `root_path`/`artifact_path`/`state_path` are not user-specific and that `run_as` + `permissions` are explicit. Use `workspace.root_path: /Workspace/Shared/.bundle/${bundle.name}/${bundle.target}` (or any non-user path) for prod. Tip: `immutable_folder` for tamper-proof prod.
- **Presets** (reference page, Sep 17, 2026): `name_prefix`, `pipelines_development`, `trigger_pause_status` (PAUSED|UNPAUSED), `jobs_max_concurrent_runs`, `source_linked_deployment`, `tags`, `artifacts_dynamic_version`. Presets override mode; per-resource settings override presets.
- **Catalog/schema**: `variables.catalog`/`schema` with per-target values (e.g. one catalog, `dev_`/`prod_` schemas) fed into `pipelines.X.catalog/schema`, sql_task `parameters`, `dashboards.X.dataset_catalog/dataset_schema`. **The Genie JSON cannot take variables** — `data_sources.tables[].identifier` are literals ("the table identifiers inside the JSON must resolve", blog). Options: per-target `file_path` override to a second JSON; per-target inline `serialized_space`; or a pre-deploy tokenising script.
- **`run_as` constraints** (run-as page): only `user_name` or `service_principal_name`; "Non-admins can only set this field to their own email"; if deploy identity != run_as identity "only jobs and pipelines are supported"; **MSE forbids any `run_as`**. => For this stack do **not** set top-level `run_as`; deployer = runner. Set `run_as` only at job/pipeline level if ever needed.
- **Free Edition specifics** (limitations page, Sep 29, 2026): serverless only; **"One SQL warehouse, limited to a 2X-Small"** => dev and prod share one `warehouse_id` (single `lookup` variable); **"One active pipeline per pipeline type"** => dev and prod pipelines cannot run simultaneously; **"Max of 5 concurrent job tasks per account"**; **"Up to 3 Databricks Apps per account"**, auto-stopped after 24h (dev + prod app = 2 of 3); serving: "Limits on the number of active endpoints", no GPU/PT; "One workspace and one metastore per account"; **"No access to the account console or account-level APIs"**; login limited to email OTP / Google / Microsoft. Workspace-level service principals do exist (Apps auto-create one, visible under Settings > Identity & Access per a Databricks employee, 2026-04-07), and docs let workspace admins add SPs and OAuth secrets from workspace settings — but nothing confirms manual SP creation on Free Edition.

## 4. CI/CD

- Official pattern (ci-cd/github page, Sep 11, 2026): `databricks/setup-cli@<version>` then `databricks bundle validate|deploy|run -t <target>` with `working-directory`. Auth via env: PAT (`DATABRICKS_HOST` + `DATABRICKS_TOKEN` from secrets), OAuth M2M (`DATABRICKS_CLIENT_ID` + `DATABRICKS_CLIENT_SECRET`), or **GitHub OIDC federation** (`DATABRICKS_AUTH_TYPE: github-oidc`, `DATABRICKS_CLIENT_ID`, no secret) — recommended.
- Free Edition reality: OIDC federation needs an account-console federation policy => **not available**. OAuth M2M needs a workspace-level SP + OAuth secret (workspace admins can create both per docs; unverified on Free Edition). **User PAT is the fallback** (`DATABRICKS_TOKEN`), with `run_as` omitted. Local dev: OAuth U2M via `databricks auth login`.
- Zero-secret alternative: "bundles in the workspace" UI (GA Oct 2025) deploys from a Git folder inside the (single) workspace; needs serverless (fine).
- Flow: PR -> `bundle validate -t dev` + `bundle plan -t prod`; merge -> `bundle deploy -t prod`, `bundle run metric_views_ddl -t prod`, `bundle run medallion_job -t prod`.

## 5. Gaps / gotchas

1. **Genie IDs are not stable across recreate.** Not bindable; redeploying under the same `parent_path`+title overwrites and yields a new `space_id`, wiping chat history/system-table continuity. Changing `parent_path` or key forces recreation. Deploy prod once, then only update.
2. **Genie JSON drift**: UI edits don't flow back; always `generate --resource <key> --force` before `deploy`; never hand-edit prod.
3. **`warehouse_id` required** on genie_spaces/dashboards/sql_task; on Free Edition it is one shared warehouse — use `variables.warehouse_id.lookup.warehouse: "<name>"` once (lookup supports warehouse, job, pipeline, dashboard, cluster, cluster_policy, instance_pool, metastore, notification_destination, query, alert, service_principal).
4. **Direct engine reverts removed fields to defaults** — be explicit.
5. **No `run_as` anywhere** because of the serving endpoint; schema owner is always the deployer.
6. **Dev-mode prefix** `[dev x]` vs serving-endpoint/app names that only allow `[a-z0-9-_]`: sanitisation undocumented; use explicit `name: agent-${bundle.target}`.
7. **Pipeline concurrency**: "one active pipeline per pipeline type" — a dev run while prod runs will fail/queue.
8. **App 24h auto-stop** on Free Edition; `lifecycle.started: true` starts it on deploy but will not keep it alive.
9. **Permission levels differ per type** (jobs CAN_VIEW/CAN_MANAGE_RUN/CAN_MANAGE/IS_OWNER; pipelines CAN_VIEW/CAN_RUN/CAN_MANAGE/IS_OWNER; apps CAN_USE/CAN_MANAGE; Genie CAN_VIEW/CAN_RUN/CAN_EDIT/CAN_MANAGE; dashboards CAN_READ/CAN_RUN/CAN_EDIT/CAN_MANAGE). Top-level `permissions` merge additively.
10. A Sep-2026 community report says dashboard `default_catalog/default_schema` "do not work for metric views anymore" — unverified; test.
11. `bundle deploy --select` (1.2.0) is "not intended for use in production".

## 6. Facts verified / open questions

**Verified (URL — "Last updated")**
- https://docs.databricks.com/aws/en/dev-tools/bundles/ — Sep 11, 2026
- https://docs.databricks.com/aws/en/dev-tools/bundles/resources — Sep 17, 2026
- https://docs.databricks.com/aws/en/dev-tools/bundles/settings — Sep 11, 2026
- https://docs.databricks.com/aws/en/dev-tools/bundles/deployment-modes — Sep 11, 2026
- https://docs.databricks.com/aws/en/dev-tools/bundles/reference — Sep 17, 2026
- https://docs.databricks.com/aws/en/dev-tools/bundles/direct — Sep 17, 2026
- https://docs.databricks.com/aws/en/dev-tools/bundles/python/ — Sep 11, 2026
- https://docs.databricks.com/aws/en/dev-tools/bundles/workspace — Sep 11, 2026
- https://docs.databricks.com/aws/en/dev-tools/ci-cd/github — Sep 11, 2026
- https://docs.databricks.com/aws/en/dev-tools/bundles/run-as — Sep 11, 2026
- https://docs.databricks.com/aws/en/dev-tools/cli/bundle-commands — Sep 25, 2026
- https://docs.databricks.com/aws/en/dev-tools/bundles/job-task-types — Sep 11, 2026
- https://docs.databricks.com/aws/en/dev-tools/bundles/variables — Sep 14, 2026
- https://docs.databricks.com/aws/en/dev-tools/bundles/permissions — Sep 11, 2026
- https://docs.databricks.com/aws/en/release-notes/dev-tools/bundles — Sep 11, 2026; https://github.com/databricks/cli/releases (v1.19.0, 2026-09-30)
- https://docs.databricks.com/aws/en/getting-started/free-edition-limitations — Sep 29, 2026
- https://docs.databricks.com/aws/en/uc-semantics/metric-views/tpch-example — Sep 11, 2026
- https://community.databricks.com/t5/data-engineering/can-i-deploy-a-metric-view-using-dabs/td-p/164061 — 2026-07-24
- https://www.advancinganalytics.co.uk/blog/genie-in-a-bundle — 16 June 2026
- https://github.com/databricks/cli/issues/3008 — closed 2026-06-10 (PR #5282)
- https://github.com/databricks/bundle-examples/tree/main/knowledge_base (genie_space_nyc_taxi, app_with_genie_space)
- https://community.databricks.com/t5/databricks-free-edition-help/free-edition-apps-failed-to-create-app-service-principal-due-to/td-p/153625 — 2026-04-07

**Open questions**
- Can a Free Edition workspace admin manually create a service principal + OAuth secret (for M2M CI auth)? No doc confirms; test in Settings > Identity and access.
- Are PATs enabled by default on Free Edition workspaces? Likely yes, unverified.
- How does `mode: development` prefix names of apps/serving endpoints that disallow spaces/brackets?
- Does `serialized_space` (inline string) get `${var.*}` substitution, which would solve per-target catalog names in the Genie JSON?
- Does "one active pipeline per pipeline type" block a second *defined* pipeline or only a second *running* one?
- Does `dashboards.dataset_catalog/dataset_schema` work with metric-view datasets (community report says no)?

## Skeleton `databricks.yml`

```yaml
bundle:
  name: genie_ref_arch
  engine: direct                      # required for genie_spaces (default >= CLI 1.3.0)

include:
  - resources/*.yml                   # pipeline, job, genie_space x2, app, serving endpoint, schema

variables:
  catalog:      {description: UC catalog}
  schema:       {description: UC schema (gold/metric views)}
  warehouse_id:                       # Free Edition: the single 2X-Small warehouse
    lookup: {warehouse: "Serverless Starter Warehouse"}

workspace:
  host: https://dbc-xxxxxxxx.cloud.databricks.com

targets:
  dev:
    default: true
    mode: development                 # [dev <user>] prefix, paused schedules, pipelines development=true
    variables: {catalog: workspace, schema: dev_gold}
  prod:
    mode: production
    workspace:
      root_path: /Workspace/Shared/.bundle/${bundle.name}/${bundle.target}
    # no run_as: forbidden with model_serving_endpoints; deployer = runner
    variables: {catalog: workspace, schema: prod_gold}
    resources:
      genie_spaces:
        sales_agent: {file_path: ../src/sales_agent.prod.geniespace.json}   # FQNs differ per target
        ops_agent:   {file_path: ../src/ops_agent.prod.geniespace.json}
```

```yaml
# resources/genie.yml (dev default; prod overrides file_path above)
resources:
  genie_spaces:
    sales_agent:
      title: Sales Agent
      warehouse_id: ${var.warehouse_id}
      file_path: ../src/sales_agent.geniespace.json
      permissions: [{level: CAN_RUN, group_name: users}]
# app.yml: resources: [{name: genie, genie_space: {name: Sales Agent, space_id: ${resources.genie_spaces.sales_agent.space_id}, permission: CAN_RUN}},
#   {name: agent, serving_endpoint: {name: agent-${bundle.target}, permission: CAN_QUERY}}]
# job.yml: pipeline_task.pipeline_id: ${resources.pipelines.medallion.id};
#   sql_task: {file: {path: ../sql/metric_views.sql}, warehouse_id: ${var.warehouse_id}, parameters: {catalog: ${var.catalog}, schema: ${var.schema}}}
```
