# Project plan and progress

Read this file first in every session. It is the hand-off between sessions: what we are building, the rules we work by, the build phases, and the **progress marker** that says where we are. Keep the marker current (rule 1).

Everything Claude-specific (this plan, session notes, scratch) lives in `.dev/`. The rest of the repo is the public tutorial.

## 1. Rules for Claude in this repo

1. **Update the progress marker** in section 5 whenever a phase, day or deliverable changes state, and at the end of every working session. Move finished items to "Done", set the "Now" line, list the "Next" items. Never leave the marker describing a past state.
2. **This is a working repo, not a personal log.** No references to the author's career, job changes, interviews, or to anyone reviewing the material. Write everything as a reference architecture and tutorial for its readers.
3. **English only** in all repo files.
4. **Verify against docs, not memory.** Databricks renamed most of this stack in 2026 (Genie Spaces to Genie Agents, DABs to Declarative Automation Bundles, DLT to Lakeflow Spark Declarative Pipelines, Vector Search to AI Search). Every module note states the doc page and "Last updated" date it was checked against. Items marked **[verify]** are unconfirmed until checked in the workspace, which happens when the phase that needs them starts.
5. **Smallest thing that still teaches.** Prefer simplicity; push back only when a simplification would hurt a teaching goal. Ask before widening scope. Stretch items stay stretch until core is done.
6. **Any workspace, no cloud lock-in.** Every core-path feature runs on a standard Databricks workspace with Unity Catalog and serverless compute. The author builds on an Azure workspace; the only cloud-specific value in the repo is `workspace.host` in `databricks.yml`. Free Edition was dropped on 2026-10-02 (it has no on-demand clusters, which developing SDP streaming tables needs); do not reintroduce Free Edition wording.
7. **No Python installs outside `~/.venv`.** Add dependencies to `~/pyproject.toml` and run `uv sync` from `~`. Code that ships to Databricks pins its own versions in the app `requirements.txt` or `pyproject.toml`.
8. **Source of truth is the Markdown in this repo.** Any shared rendering (artifact page, PDF) is regenerated from the file, never edited directly.
9. **Dates are absolute** (2026-10-02, not "tomorrow") in every file, including this one.
10. **Claude files go in `.dev/`.** Keep the root `CLAUDE.md` as a one-line pointer to this file. Session notes, spike logs and scratch go in `.dev/` too; reader-facing docs go in `docs/`.

## 2. What we are building

Public name: **Databricks Genie in Production** (GitHub: `git@github.com:zoltanctoth/databricks-genie-in-production.git`).

Purpose: a production reference architecture for Databricks Genie that doubles as a Udemy or YouTube course for Databricks practitioners new to Genie. Three pillars: semantic layer (Unity Catalog metric views), Genie Agents (curation, benchmarks, operation), productionizing (bundles, apps, MCP orchestrator, evaluation). The build goes deepest on Genie curation and metric views; course polish is a later pass.

Capstone on Inside Airbnb San Francisco data (snapshot 2026-06-14, three files):

| ID | Component | Short description |
|---|---|---|
| C1 | Dataset | `listings.csv.gz`, `calendar.csv.gz`, summary `reviews.csv` uploaded by the student to a UC volume |
| C2 | Pipeline | Serverless Lakeflow SDP: bronze, silver, gold star schema (`dim_listing`, `dim_host`, `fact_calendar`, `fact_review`) plus the listing-grain `fact_listing_activity`, with comments and PK/FK |
| C3 | Metric views | `availability_metrics` (built); `market_metrics`, `review_activity_metrics`, `compliance_metrics` designed in the architecture doc, added only when Agent A curation needs them (D14); deployed by a job SQL task (D5) |
| C4 | Genie Agent A | "San Francisco Market Analyst", Chat mode on `availability_metrics`, `dim_listing`, `dim_host` (no fact exposed twice), full curation, 20+ benchmarks |
| C5 | Genie Agent B | "Host Operations and Compliance", Agent mode on the 32 PDFs in a volume only (generated locally, mirrored on S3) |
| C6 | App 1 | Databricks App on the Genie Conversation API with user authorization |
| C7 | App 2 | Orchestrator agent on Databricks Apps (MLflow AgentServer) consuming both Genie Agents via managed MCP servers |
| C8 | Evaluation | Genie benchmarks per agent; `mlflow.genai.evaluate` for orchestrator routing |
| C9 | Bundle and CI/CD | One bundle, direct engine, `dev` and `prod` targets in one workspace; GitHub Actions (PR validates, `main` deploys dev and tests, `release` deploys prod); Genie JSON promotion via `bundle generate genie-space` |
| C10 | Docs | README, diagram, per-module notes with verification dates |

Full detail, decisions D1 to D15 (D13: dev mode prefixes schemas with `dev_<user>_`; resources reference schemas by `${resources.schemas.<key>.name}`; D14: Agent A on the metric view plus the gold tables that do not repeat its facts, Agent B on the documents; D15: each component goes into the bundle and through CI as it is built, no fixed dates), functional requirements, risk register and open questions: [docs/01-requirements-and-risks.md](../docs/01-requirements-and-risks.md). The build specification (pipeline tables and rules, Genie sources, metric view YAML, orchestration) is [docs/02-architecture.md](../docs/02-architecture.md); read it before writing silver, gold or metric views. Research appendices: [docs/research/](../docs/research/).

Decisions already taken (do not reopen without the author): standard workspace, dev and prod as two bundle targets in it (D1, revised 2026-10-02); San Francisco, not Budapest (D2); Supervisor Agent out, hand-built MCP orchestrator in (D3); metric views via SQL task, not a bundle resource (D5); Genie config in git as generated `.geniespace.json` (D6); apps use on-behalf-of user auth (D7); Model Serving deployment is stretch (D8).

Open decisions: D4 (apps in both targets or prod only, leaning prod-only), D9, D10, D11, D12.

## 3. Where things are

| What | Where |
|---|---|
| Local repo | `~/Documents/dbx/databricks-genie-in-production`, remote `origin` on GitHub; branches `main` (deploys dev through CI) and `release` (deploys prod through CI) |
| Workspace | Azure Databricks, host `adb-7405615411129521.1.azuredatabricks.net`, catalog `genie_reference`, warehouse `Serverless Starter Warehouse`. CLI profiles: `genie-prod-me` (author) and `genie-prod-sp` (service principal `dab_principal`, application ID `47d22b7a-8f16-43cb-93c5-590e5d89e8b9`). Always pass `--profile`; never pick one for the user. |
| Schemas | `airbnb` and `raw` (prod, owned by the service principal); `dev_tothz_*` (author's dev); `dev_dab_principal_*` (CI's dev copy) |
| Bundle | `bundle/`: `databricks.yml`, `scripts.yml`, `resources/` (`schemas.yml`, `airbnb_pipeline.yml`, `setup_workspace.job.yml`, `metric_views.job.yml`, `tests.job.yml`), `src/` (`pipeline/`, `metric_views/`, `tests/`, `setup/`) |
| CI/CD | `.github/workflows/{pr,main,release}.yml`; GitHub environments `ci` and `prod`; as-built notes in `.dev/cicd.md` |
| Requirements and risks | `docs/01-requirements-and-risks.md` (draft v0.4, 2026-10-08) |
| Architecture and build spec | `docs/02-architecture.md` (agent sources in section 2, metric view designs in section 3) |
| Research appendices | `docs/research/{genie-agents,metric-views,bundles,agent-framework,dataset}.md` (2026-10-01) |
| Claude plan, notes, scratch | `.dev/` (this file is `.dev/plan.md`) |
| Databricks courseware for reference | `~/Documents/dbx/` sibling folders (Data Engineering, Spark, GenAI, ML, Advanced DE tracks) |
| Dataset mirror (author-side) | `s3://dbx-data-public/airbnb-sf/`: `listings.csv`, `calendar.csv`, summary `reviews.csv`, CC BY 4.0 `LICENSE.md`, and `documents/` with the 32 PDFs from `tools/generate_documents.py` (sync: `aws s3 sync build/documents s3://dbx-data-public/airbnb-sf/documents/ --profile tz --delete`). Snapshot 2026-06-14, uploaded 2026-10-02. Bucket policy `.dev/s3-bucket-policy.json`: objects public, anonymous listing only under `airbnb-sf/`. Students still download from Inside Airbnb (`docs/research/dataset.md`) |

## 4. Build phases

No fixed dates (dropped 2026-10-08, D15). Each component goes into the bundle and through CI as soon as it is built, not in a final bundling phase.

| # | Phase | State | Exit criteria |
|---|---|---|---|
| 1 | Requirements and research | done | Requirements drafted; research appendices written |
| 2 | Data and pipeline | done | Files in volumes, five gold tables with comments and constraints, PDFs generated |
| 3 | Metric views | reduced (D14) | `availability_metrics` deployed by the `deploy_metric_views` job; more views only when Agent A curation shows a need |
| 4 | CI/CD and tests | done | PR validates, merge to `main` deploys dev and runs the tests, merge to `release` deploys prod; all green on GitHub |
| 5 | Genie Agent A | in progress | Chat mode on metric views and gold tables; curated, 20+ benchmarks, scores recorded per curation step; in the bundle and deployed by CI |
| 6 | Genie Agent B | | Agent mode on the 32 PDFs in the `documents` volume; one benchmark per document; in the bundle and deployed by CI |
| 7 | App 1 | | Databricks App on the Genie Conversation API with user authorization (OBO); in the bundle |
| 8 | Orchestrator app | | Agent on Databricks Apps calling both Genie Agents through managed MCP servers; in the bundle |
| 9 | Evaluation | | Genie benchmarks per agent and `mlflow.genai.evaluate` for orchestrator routing, run by a manual or scheduled workflow (not a merge gate) |
| 10 | Hardening and course outline | | Clean-clone test, module notes, outline mapping the build to lessons |

Stretch (only once core is done): S1 Model Serving deploy, S3 materialized metric view, S4 second city, S5 Genie One walkthrough, S6 SCD2 snapshots. S2 (GitHub Actions) moved into core as phase 4.

## 5. Where we are

<!-- PROGRESS MARKER. Keep this section current (rule 1). Format: Now / Done / Next / Blocked. -->

**Now:** 2026-10-08. Phases 1 to 4 are done (phase 3 reduced to one metric view by D14). Phase 5 is in progress: Agent A (`market_analyst`) is in the bundle with 6 benchmarks and is deployed by CI to both dev copies and to prod (release run 37759964095, PR #5). `main.yml` now runs the agent's benchmarks after deploying (`bundle/scripts/run_genie_eval.py`) and fails below 80% accuracy; After two curation fixes (a general-instruction rule against adding `IS NOT NULL` filters, and the certificate benchmark's missing `stay_type = 'short_term'` filter) the agent scores 6/6 in repeated runs. A 'listings exclude hotels' definition is not in the instruction: the benchmarks no longer encode it, and adding it made Genie drop hotels from questions that never said 'listings' (2/6).

**Done:**
- **Phase 1, requirements and research** (2026-10-01 to 2026-10-08): requirements v0.1 to v0.4, research appendices, architecture doc. D1 revised 2026-10-02 (Free Edition to a standard Azure workspace; Free Edition has no on-demand clusters for developing SDP streaming tables). D14 and D15 on 2026-10-08: agent sources split by type, App 1 kept, each component bundled and deployed by CI as it is built, no fixed dates.
- **Phase 2, data and pipeline** (2026-10-02 to 2026-10-05): dataset mirrored to S3; 32 PDFs generated by `tools/generate_documents.py` (static inputs, not a job task); `setup_workspace` job copies files and PDFs into the target's volumes; `airbnb_pipeline` builds bronze (3 streaming tables), silver (3 materialized views) and gold: `dim_host` 3,499, `dim_listing` 7,332, `fact_calendar` 2,676,180, `fact_review` 434,102, `fact_listing_activity` 7,332, every column commented, PK/FK `RELY`. `fact_listing_activity` reproduces Inside Airbnb's published occupancy for all listings and revenue within $1 for all 5,932 priced ones. Prod managers group as bundle scripts (`scripts.yml`).
- **Phase 3, metric views** (2026-10-07 to 2026-10-08): `availability_metrics` (renamed from `booking_reference` on 2026-10-08) over `fact_calendar` with a snowflake join to `dim_listing` and `dim_host`, deployed by the `deploy_metric_views` job (D5).
- **Phase 4, CI/CD and tests** (2026-10-08): `pr.yml`, `main.yml`, `release.yml` and the `tests` job, all green on GitHub including the first prod release. Prod handed to the service principal. Details and how to switch to federation: `.dev/cicd.md`.

**Findings that still matter:**
- Data: the 2026 calendar export has no price column, and a blocked night is not a booking, so revenue never comes from the calendar. 90 calendar listings and 4,197 review rows have no listing (dropped in silver); 8,790 same-day review repeats are kept. Inside Airbnb's activity windows are per listing, from its own `last_scraped` (two scrape dates exist).
- Bundles: development mode prefixes schemas with `dev_<user>_`, so resources must reference `${resources.schemas.<key>.name}` (D13). `bundle plan -t <target>` lists every action before a deploy; a schema rename is a recreate. No post-deploy hook exists. The catalog cannot be created through the API on this workspace (Default Storage), so it was created in the UI and is not a bundle resource. `run_as` and `grants.principal` take the application ID. The statement API returns HTTP 200 for failed statements. The CLI caches `/Me` under `~/Library/Caches/databricks/<version>/user/`.
- Genie (tested 2026-10-08, CLI 1.19): a metric view source sits in `data_sources.tables`, not `metric_views`. `generate` writes `parent_path` as the user's home folder; leave it unset. Creating a space silently drops column configs for columns that do not exist yet. On create, Genie adds its own join spec from PK/FK constraints, so a join spec in the file is duplicated; the JSON carries no `join_specs` and the FK join works. The `space_id` survives redeploys, and an update overwrites the remote config with the file exactly. Bundle substitution does not run inside a `file_path` JSON, only on YAML values, so the agent's JSON is inline in `serialized_space` with `${var.catalog}.${resources.schemas.schema.name}` names; switching from `file_path` to inline with the same content is not a change in `bundle plan`. Target-level prod `permissions` apply to the Genie space. Planning as the service principal from the author's checkout fails with a state lineage mismatch (local `.databricks/` is the author's); plan from a copy without `.databricks/`. Bundle `scripts` resolve only `${bundle.*}`, `${workspace.*}` and `${var.*}`, not resource fields; `bundle summary` reports a Genie space's ID as `id`. Creating a Genie space fails (403, 'Table ... does not exist') when a source table or metric view is missing, so CI deploys in two passes (2026-10-08): `bundle deploy --select <data-layer resources>`, then the setup, pipeline, metric view and test jobs, then a full `bundle deploy` that adds the agents. A new resource the jobs need must be added to the `--select` list in `main.yml` and `release.yml`; agents and apps stay out of it. Benchmark eval API (CLI 1.19, Beta, tested 2026-10-08): `genie-create-eval-run SPACE_ID --json '{}'` runs every benchmark in the space; `genie-get-eval-run` gives `eval_run_status`, `num_correct`, `num_questions`, `num_needs_review`; `genie-get-eval-result-details` gives `assessment` (GOOD/BAD) and `assessment_reasons`. Six questions take about 80 s. Scores on an unchanged space varied between 4/6 and 5/6. Benchmarks live in `serialized_space.benchmarks` and round-trip through the pull script; the API returns them sorted by `id` descending, so the first pull after hand-adding them reorders them and one more deploy settles the state.
- Metric views: a pipeline rejects `CREATE VIEW ... WITH METRICS`, so they run as job SQL tasks; bare table names in the YAML resolve against the view's own schema (tested 2026-10-07, not documented); in Spark SQL `''` inside a string is two adjacent literals, not an escaped quote; keep metric view files out of `src/pipeline/`, which the pipeline globs.
- CI and identity: whoever deploys first owns the objects; prod is deployed only as the service principal. Reading raw `s3a://` paths needs `SELECT ON ANY FILE` for non-admins (granted to the service principal; listed only under `hive_metastore`). The author is not an account admin, so CI uses an OAuth secret instead of federation.

**Next:**
1. Phase 5, Genie Agent A (sources in `docs/02-architecture.md` section 2: `availability_metrics`, `dim_listing` with its `availability_*` columns hidden, `dim_host`): (a) done on the author's dev target on 2026-10-08 (`resources/market_analyst.genie_space.yml`, `src/genie/market_analyst.geniespace.json`, space `01f1c2f1775e12f8b78e9e2da512a3b6`); R-6 solved the same day (inline `serialized_space`); pull script `bundle/scripts/pull_genie_space.py` written and round-trip tested; still open: commit and let `main.yml` deploy CI's copy; (b) write 20+ benchmarks with gold SQL (`bundle/eval/benchmarks_market.json`), occupancy and revenue checked against the published figures; (b2) benchmark candidate: Superhost vs other listing counts silently drop the 90 listings whose host has a null `is_superhost`; (c) baseline score, then curate in the documented order and record the score after each step; (d) regenerate the JSON, commit, promote through `main` and `release`.
2. Phase 6, Genie Agent B: **[verify]** the "Analyze files in volumes" preview in the workspace (R-1); one benchmark question per PDF (`bundle/eval/benchmarks_host_ops.json`); bundle and CI as for Agent A.
3. Phases 7 to 9 (App 1, orchestrator, evaluation workflow), see section 4. Settle D4 (apps in both targets or prod only) before phase 7.
4. Leftovers, any time: drop the old `booking_reference` views by hand in `dev_tothz_airbnb`, `dev_dab_principal_airbnb` and `airbnb`; `setup_workspace` over HTTPS so the `ANY FILE` grant can be revoked; a bootstrap script for a fresh workspace (catalog grants, deploy, setup run); GitHub repo description and topics.

**Blocked:** nothing. Workload identity federation for CI waits on an account admin; CI uses an OAuth client secret until then.

## 6. Session checklist

At the start: read sections 5 and 4, then only the docs the current phase needs.
At the end: update section 5, and if a decision changed, update the requirements doc and the decisions list in section 2.
