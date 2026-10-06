# Project plan and progress

Read this file first in every session. It is the hand-off between sessions: what we are building, the rules we work by, the two-week plan, and the **progress marker** that says where we are. Keep the marker current (rule 1).

Everything Claude-specific (this plan, session notes, scratch) lives in `.dev/`. The rest of the repo is the public tutorial.

## 1. Rules for Claude in this repo

1. **Update the progress marker** in section 5 whenever a phase, day or deliverable changes state, and at the end of every working session. Move finished items to "Done", set the "Now" line, list the "Next" items. Never leave the marker describing a past state.
2. **This is a working repo, not a personal log.** No references to the author's career, job changes, interviews, or to anyone reviewing the material. Write everything as a reference architecture and tutorial for its readers.
3. **English only** in all repo files.
4. **Verify against docs, not memory.** Databricks renamed most of this stack in 2026 (Genie Spaces to Genie Agents, DABs to Declarative Automation Bundles, DLT to Lakeflow Spark Declarative Pipelines, Vector Search to AI Search). Every module note states the doc page and "Last updated" date it was checked against. Items marked **[verify]** in the requirements doc are unconfirmed until the Day 1 spike proves them in the target workspace.
5. **Smallest thing that still teaches.** Prefer simplicity; push back only when a simplification would hurt a teaching goal. Ask before widening scope. Stretch items stay stretch until core is done (Day 11 rule).
6. **Any workspace, no cloud lock-in.** Every core-path feature runs on a standard Databricks workspace with Unity Catalog and serverless compute. The author builds on an Azure workspace; the only cloud-specific value in the repo is `workspace.host` in `databricks.yml`. Free Edition was dropped on 2026-10-02 (it has no on-demand clusters, which developing SDP streaming tables needs); do not reintroduce Free Edition wording.
7. **No Python installs outside `~/.venv`.** Add dependencies to `~/pyproject.toml` and run `uv sync` from `~`. Code that ships to Databricks pins its own versions in the app `requirements.txt` or `pyproject.toml`.
8. **Source of truth is the Markdown in this repo.** Any shared rendering (artifact page, PDF) is regenerated from the file, never edited directly.
9. **Dates are absolute** (2026-10-02, not "tomorrow") in every file, including this one.
10. **Claude files go in `.dev/`.** Keep the root `CLAUDE.md` as a one-line pointer to this file. Session notes, spike logs and scratch go in `.dev/` too; reader-facing docs go in `docs/`.

## 2. What we are building

Public name: **Databricks Genie in Production** (GitHub: `git@github.com:zoltanctoth/databricks-genie-in-production.git`).

Purpose: a production reference architecture for Databricks Genie that doubles as a Udemy or YouTube course for Databricks practitioners new to Genie. Three pillars: semantic layer (Unity Catalog metric views), Genie Agents (curation, benchmarks, operation), productionizing (bundles, apps, MCP orchestrator, evaluation). The two-week build goes deepest on Genie curation and metric views; course polish is a later pass.

Capstone on Inside Airbnb San Francisco data (snapshot 2026-06-14, three files):

| ID | Component | Short description |
|---|---|---|
| C1 | Dataset | `listings.csv.gz`, `calendar.csv.gz`, summary `reviews.csv` uploaded by the student to a UC volume |
| C2 | Pipeline | Serverless Lakeflow SDP: bronze, silver, gold star schema (`dim_listing`, `dim_host`, `fact_calendar`, `fact_review`) plus the listing-grain `fact_listing_activity`, with comments and PK/FK |
| C3 | Metric views | `market_metrics`, `availability_metrics`, `review_activity_metrics`, `compliance_metrics`, optional parameterized `market_metrics_eur`; deployed by a job SQL task |
| C4 | Genie Agent A | "San Francisco Market Analyst", Chat mode, full curation, 20+ benchmarks |
| C5 | Genie Agent B | "Host Operations and Compliance", Agent mode, tables plus 32 PDFs in a volume (generated locally, mirrored on S3) |
| C6 | App 1 | Databricks App on the Genie Conversation API with user authorization |
| C7 | App 2 | Orchestrator agent on Databricks Apps (MLflow AgentServer) consuming both Genie Agents via managed MCP servers |
| C8 | Evaluation | Genie benchmarks per agent; `mlflow.genai.evaluate` for orchestrator routing |
| C9 | Bundle | One bundle, direct engine, `dev` and `prod` targets in one workspace, Genie JSON promotion via `bundle generate genie-space` |
| C10 | Docs | README, diagram, per-module notes with verification dates |

Full detail, decisions D1 to D13 (D13: dev mode prefixes schemas with `dev_<user>_`; resources reference schemas by `${resources.schemas.<key>.name}`), functional requirements, risk register and open questions: [docs/01-requirements-and-risks.md](../docs/01-requirements-and-risks.md). The build specification (pipeline tables and rules, Genie sources, metric view YAML, orchestration) is [docs/02-architecture.md](../docs/02-architecture.md); read it before writing silver, gold or metric views. Research appendices: [docs/research/](../docs/research/).

Decisions already taken (do not reopen without the author): standard workspace, dev and prod as two bundle targets in it (D1, revised 2026-10-02); San Francisco, not Budapest (D2); Supervisor Agent out, hand-built MCP orchestrator in (D3); metric views via SQL task, not a bundle resource (D5); Genie config in git as generated `.geniespace.json` (D6); apps use on-behalf-of user auth (D7); Model Serving deployment is stretch (D8).

Open decisions: D4 (apps in both targets or prod only, leaning prod-only), D9, D10, D11, D12.

## 3. Where things are

| What | Where |
|---|---|
| Local repo | `~/Documents/dbx/databricks-genie-in-production`, remote `origin` on GitHub |
| Workspace | Azure Databricks, host `adb-7405615411129521.1.azuredatabricks.net`. CLI profiles: `genie-prod-me` (user login) and `genie-prod-sp` (service principal for `prod` `run_as`). Always pass `--profile`; never pick one for the user. |
| Bundle | `bundle/` (`databricks.yml`, `resources/pipeline.yml`, `src/pipeline/`, `src/setup/`); targets `dev` (default) and `prod` |
| Requirements and risks | `docs/01-requirements-and-risks.md` (draft v0.2, 2026-10-01) |
| Research appendices | `docs/research/{genie-agents,metric-views,bundles,agent-framework,dataset}.md` |
| Claude plan, notes, scratch | `.dev/` (this file is `.dev/plan.md`) |
| Databricks courseware for reference | `~/Documents/dbx/` sibling folders (Data Engineering, Spark, GenAI, ML, Advanced DE tracks) |
| Target bundle layout | requirements doc section 7.5 (`databricks.yml`, `resources/`, `src/`, `eval/`) |
| Dataset mirror (author-side) | `s3://dbx-data-public/airbnb-sf/` (plain `listings.csv`, `calendar.csv`, summary `reviews.csv`, a CC BY 4.0 `LICENSE.md`, and `documents/` with the 32 Genie PDFs regenerated by `tools/generate_documents.py` and synced with `aws s3 sync build/documents s3://dbx-data-public/airbnb-sf/documents/ --profile tz --delete`; San Francisco snapshot 2026-06-14, uploaded 2026-10-02 with AWS profile `tz`). Bucket policy (`.dev/s3-bucket-policy.json`, applied 2026-10-02): every object publicly readable, anonymous listing allowed only under `airbnb-sf/`, bucket ACL private. Students still download from Inside Airbnb; see the republishing note in `docs/research/dataset.md` |

## 4. The two-week plan (2026-10-02 to 2026-10-15)

| Day | Date | Phase | Exit criteria |
|---|---|---|---|
| 0 | Oct 1 | Requirements and research | Requirements v0.2 drafted; research appendices written |
| 1 | Oct 2 | Feasibility spike in the target workspace | Every **[verify]** item has a go/no-go; fallbacks chosen for red items |
| 2 to 3 | Oct 3 to 4 | Data and pipeline | FR-1 to FR-3, FR-13 pass: files in volume, four gold tables, comments and constraints, PDFs generated |
| 4 to 5 | Oct 5 to 6 | Metric views | FR-4 passes: two views with agent metadata, snowflake join, window measure, SQL task deploy |
| 6 to 8 | Oct 7 to 9 | Genie Agents | FR-5, FR-6 pass: both agents curated, 20+ benchmarks each, scores recorded per curation step |
| 9 to 10 | Oct 10 to 11 | Serving | FR-8 to FR-10 pass: App 1 with OBO, App 2 with MCP, MLflow traces, small eval set |
| 11 to 12 | Oct 12 to 13 | Bundles | FR-7, FR-11, FR-12 pass: Genie JSON generated, dev and prod deploy from clean clone |
| 13 | Oct 14 | Hardening and buffer | Clean-clone test passes; module notes written; success criteria in requirements 3.2 checked |
| 14 | Oct 15 | Course outline | Outline document maps the build to modules and lessons |

Stretch (only if core is done by Day 11): S1 Model Serving deploy, S2 GitHub Actions, S3 materialized metric view, S4 second city, S5 Genie One walkthrough, S6 SCD2 snapshots.

## 5. Where we are

<!-- PROGRESS MARKER. Keep this section current (rule 1). Format: Now / Done / Next / Blocked. -->

**Now:** 2026-10-05, Days 2 to 3 (data and pipeline). Bronze (three SQL files) and silver (three materialized views) written and bundle-validated for dev and prod; `files` and `documents` volumes declared. Not yet deployed or run. Next is the setup job (copy CSVs and PDFs into the volumes), then a first pipeline run on dev, then gold. Earlier state: bundle identity model settled (human deploys, prod runs as a service principal); `bootstrap.yml` script, per-target schemas and prod grants written and config-validated; catalog `genie_reference` created by hand in the Azure workspace. Bronze SDP tables written, not yet deployed or run. The 32 Genie PDFs generated and mirrored to `s3://dbx-data-public/airbnb-sf/documents/` (FR-13 done).

**Done:**
- 2026-10-05: Bronze rewritten as three SQL files (`bronze_listings.py` notebook removed; it used the Beta `:source_path` parameter syntax that the bundle never defined, and `%run` of a config notebook that does not exist). All three read `${source_path}` from the pipeline `configuration`. Silver written as three materialized views: `silver_listings` (typed, latest scrape per listing, 13 null columns dropped, `license_status` matching `classify_license()` in the PDF generator, `stay_type`, `is_hotel`, published occupancy and revenue kept for validation), `silver_calendar` and `silver_reviews` (typed, semi join on `silver_listings` drops the 90 orphan listings and 4,197 orphan review rows; same-day review repeats kept). D13 decided after a wrong first version: development mode already prefixes schemas (`dev_tothz_raw`, `dev_tothz_airbnb` exist in the workspace from the first dev deploy), so the variable override was reverted the same day. The real defect was `source_path` built from `${var.source_schema}`, which in dev pointed at prod's schema; it is now built from `${resources.schemas.source_schema.name}`. `files` and `documents` volume resources added to `schemas.yml`. Finding: `databricks bundle plan -t <target>` shows the exact add/change/recreate/delete actions and `bundle summary -o json` shows the deployed names per state; a schema rename is always a recreate.
- 2026-10-05: Architecture doc `docs/02-architecture.md` written from the data profile and the docs. Key findings: Inside Airbnb's `estimated_occupancy_l365d` reproduces as `LEAST(255, reviews_l365d * 2 * GREATEST(minimum_nights, 5.5))` (99.9 percent exact) and revenue as nights times price (100 percent), so a listing-grain `fact_listing_activity` gold table carries the only genuine multi-table metric and every revenue benchmark has a published gold answer. Revenue from the calendar dropped (no price column; blocked is not booked). Metric views renamed to `<subject>_metrics` per the skill convention; `compliance_metrics` added for Agent B (94 unregistered short-term non-hotel listings, 1,834 entire homes over 90 estimated nights). Volume layout settled: `raw.files/airbnb-sf/` for CSVs, `raw.documents` for the PDFs. Requirements 7.1 to 7.4, D2, R-18 corrected; D13 (dev gold schema) opened.
- 2026-10-05: Local copy of the three CSVs plus `LICENSE.md` downloaded from `s3://dbx-data-public/airbnb-sf/` into `data/` (git-ignored; `data/**` also in the bundle `sync.exclude`). Profile of the 2026-06-14 San Francisco snapshot: `listings.csv` 7,332 rows x 90 columns (13 columns entirely null, including `host_since`, `instant_bookable`, `neighbourhood_group_cleansed`, `host_response_*`; `price` is `$1,234.00` text, null for 19.1 percent; 36 `neighbourhood_cleansed` values; 3,499 hosts; `license` set for 66.3 percent; two scrape dates 2026-06-14 and 2026-06-22). `calendar.csv` 2,709,030 rows x 5 columns (`listing_id`, `date`, `available`, `minimum_nights`, `maximum_nights`): **no `price` or `adjusted_price` column** in this file, 365 rows per listing, 7,422 listing ids of which 90 are not in `listings.csv`. `reviews.csv` 438,299 rows x 2 columns (`listing_id`, `date`), 2009-05-03 to 2026-06-21, 4,197 rows for listing ids missing from `listings.csv`, 8,790 exact duplicate rows (same listing, same day).
- 2026-10-05: Group management as bundle scripts. Layout: `bundle/scripts.yml` declares the entry points (`create_group`, `add_group_member`, `setup_manager_group`) and the `prod_managers_group_name` variable; bodies live in `bundle/scripts/*.sh` (run from the bundle root, excluded from sync). `bundle run <script>` rejects positional arguments (CLI v1.19.0), so `GROUP_MEMBER=<email>` is the input and defaults to the deploying identity. Group `prod_managers` created in the workspace and the deploying user added; prod target's CAN_MANAGE names the group. Finding: the CLI caches `/Me` under `~/Library/Caches/databricks/<version>/user/`; group membership added after that cache fills makes the "permissions section should include the current identity" recommendation fire until the cache file is deleted.
- 2026-10-02: Workspace bootstrap designed and written. Findings: (a) bundles have no post-deploy hook, so `scripts.bootstrap` (catalog SQL, USE CATALOG grant, deploy, `setup_workspace` run) is the one-command entry point; (b) the Azure workspace is a classic workspace in a Default Storage account, so neither the API nor SQL can create a catalog (`Metastore storage root URL does not exist`; CLI issue databricks/cli#4513 closed not-planned 2026-05-20), the catalog was created once in the UI and is not a bundle resource; (c) a shared catalog must not be owned by two targets' state, so only per-target schemas are resources; (d) the statement API returns HTTP 200 for failed statements, the script inspects the body; (e) `run_as.service_principal_name` and `grants.principal` take the application ID (run-as docs 2026-09-11). Deployer owns the schemas; the SP `47d22b7a-…` gets USE CATALOG (script) plus schema grants in the prod target override. README gained a "Deploying the bundle" section.
- 2026-10-02: D1 revised. Moved from Free Edition to a standard (Azure) workspace because Free Edition has no on-demand clusters for developing SDP streaming tables. Free Edition wording removed from README, requirements (now v0.3), this plan and `bundle/databricks.yml` (`free` target deleted). Research appendices keep their Free Edition findings under a header note saying they no longer constrain the design.
- 2026-10-01: Research appendices written (Genie Agents, metric views, bundles, agent framework, dataset), all source-cited.
- 2026-10-01: Requirements and risk register v0.1, then v0.2 (simplified to four gold tables, San Francisco chosen over Budapest).
- 2026-10-02: Dataset mirrored to `s3://dbx-data-public/airbnb-sf/` (plain CSV plus CC BY 4.0 `LICENSE.md`), bucket policy set; confirmed a serverless notebook reaches S3 over s3a.
- 2026-10-02: FR-13 done. `tools/generate_documents.py` (fpdf2 and matplotlib in `~/.venv`) renders 32 PDFs from the CSVs in about 5 seconds: 10 neighbourhood market reports, 20 host house-rules sheets (synthetic rules, real counts; the 2026 file has no `house_rules` column), 1 regulation summary verified against sfplanning.org and sf.gov on 2026-10-02, 1 data dictionary. 1.5 MB total, largest 65 KB. Synced to `s3://dbx-data-public/airbnb-sf/documents/`, public read confirmed. Decision: PDFs are static inputs beside the CSVs, not a job task.
- 2026-10-02: Bundle wired (`include`, `catalog`/`schema`/`source_path` variables), `resources/pipeline.yml` (serverless, `airbnb_pipeline`), three bronze streaming tables in `src/pipeline/` using Auto Loader `read_files` with all-string columns and ingestion metadata; `bundle validate` OK against the dev workspace.
- 2026-10-01: Public name and GitHub metadata chosen; README reworked to tutorial-first; `.dev/plan.md` created as the session hand-off; personal and review-process references removed from all docs.

**Next:**
0. Recreate `scripts/bootstrap.sh` (catalog, `setup_manager_group`, deploy, setup job) and document `setup_manager_group` in the README deploy section. Note: `experimental.immutable_folder: true` in `databricks.yml` makes `bundle validate -t prod` fail with two unresolved `${resources.internal_immutable_snapshots...}` path errors on CLI v1.19.0; validation is clean without it.
1. Add `resources/setup_workspace.job.yml` (serverless notebook task) and parameterize `src/setup/setup_workspace.py` with `base_parameters` (`cloud_source`, `target_volume`) instead of `%run ../import_config`; add a `files` volume resource in the raw schema. Until then the last line of the bootstrap script fails after a successful deploy.
2. `databricks bundle run bootstrap -t dev --profile genie-prod-me`, then `bundle run airbnb_pipeline`; confirm three bronze tables, zero rescued rows in `bronze_listings`, row counts 7,332 / 2,709,030 / 438,299.
3. Day 1 spike: run the remaining **[verify]** checklist items from requirements section 11 in the workspace; log the go/no-go table in `.dev/spike-day1.md` and fold confirmed facts into `docs/`.
4. Silver and gold SQL per `docs/02-architecture.md` section 1: three silver materialized views (typing, orphan-dropping expectations, `license_status`, `stay_type`, `is_hotel`), then `dim_listing`, `dim_host`, `fact_calendar`, `fact_review`, `fact_listing_activity` with comments and PK/FK. Acceptance: `fact_listing_activity.estimated_nights_l365d` equals `dim_listing.published_occupancy_l365d` for at least 99.9 percent of listings; `fact_review` has 434,102 rows.
5. Have the setup notebook copy the CSVs and `documents/` into the `files` and `documents` volumes (resources already declared), and write one benchmark question per PDF into `eval/benchmarks_host_ops.json`.
6. Set the GitHub repo description and topics from the README.

**Blocked:** nothing.

## 6. Session checklist

At the start: read sections 5 and 4, then only the docs the day's phase needs.
At the end: update section 5, and if a decision changed, update the requirements doc and the decisions list in section 2.
