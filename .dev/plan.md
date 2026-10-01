# Project plan and progress

Read this file first in every session. It is the hand-off between sessions: what we are building, the rules we work by, the two-week plan, and the **progress marker** that says where we are. Keep the marker current (rule 1).

Everything Claude-specific (this plan, session notes, scratch) lives in `.dev/`. The rest of the repo is the public tutorial.

## 1. Rules for Claude in this repo

1. **Update the progress marker** in section 5 whenever a phase, day or deliverable changes state, and at the end of every working session. Move finished items to "Done", set the "Now" line, list the "Next" items. Never leave the marker describing a past state.
2. **This is a working repo, not a personal log.** No references to the author's career, job changes, interviews, or to anyone reviewing the material. Write everything as a reference architecture and tutorial for its readers.
3. **English only** in all repo files.
4. **Verify against docs, not memory.** Databricks renamed most of this stack in 2026 (Genie Spaces to Genie Agents, DABs to Declarative Automation Bundles, DLT to Lakeflow Spark Declarative Pipelines, Vector Search to AI Search). Every module note states the doc page and "Last updated" date it was checked against. Items marked **[verify]** in the requirements doc are unconfirmed until the Day 1 spike proves them on Free Edition.
5. **Smallest thing that still teaches.** Prefer simplicity; push back only when a simplification would hurt a teaching goal. Ask before widening scope. Stretch items stay stretch until core is done (Day 11 rule).
6. **Free Edition first.** Every core-path feature must work on Databricks Free Edition. The Azure workspace is a fallback for demos only.
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
| C2 | Pipeline | Serverless Lakeflow SDP: bronze, silver, gold star schema (`dim_listing`, `dim_host`, `fact_calendar`, `fact_review`) with comments and PK/FK |
| C3 | Metric views | `mv_market`, `mv_review_activity`, optional parameterized `mv_market_eur`; deployed by a job SQL task |
| C4 | Genie Agent A | "San Francisco Market Analyst", Chat mode, full curation, 20+ benchmarks |
| C5 | Genie Agent B | "Host Operations and Compliance", Agent mode, tables plus generated PDFs in a volume |
| C6 | App 1 | Databricks App on the Genie Conversation API with user authorization |
| C7 | App 2 | Orchestrator agent on Databricks Apps (MLflow AgentServer) consuming both Genie Agents via managed MCP servers |
| C8 | Evaluation | Genie benchmarks per agent; `mlflow.genai.evaluate` for orchestrator routing |
| C9 | Bundle | One bundle, direct engine, `dev` and `prod` targets in one workspace, Genie JSON promotion via `bundle generate genie-space` |
| C10 | Docs | README, diagram, per-module notes with verification dates |

Full detail, decisions D1 to D12, functional requirements, risk register and open questions: [docs/01-requirements-and-risks.md](../docs/01-requirements-and-risks.md). Research appendices: [docs/research/](../docs/research/).

Decisions already taken (do not reopen without the author): Free Edition primary (D1); San Francisco, not Budapest (D2); Supervisor Agent out, hand-built MCP orchestrator in (D3); metric views via SQL task, not a bundle resource (D5); Genie config in git as generated `.geniespace.json` (D6); apps use on-behalf-of user auth (D7); Model Serving deployment is stretch (D8).

Open decisions: D4 (three-app quota vs two apps times two targets, leaning prod-only apps), D9, D10, D11, D12.

## 3. Where things are

| What | Where |
|---|---|
| Local repo | `~/Documents/dbx/databricks-genie-in-production`, remote `origin` on GitHub |
| Requirements and risks | `docs/01-requirements-and-risks.md` (draft v0.2, 2026-10-01) |
| Research appendices | `docs/research/{genie-agents,metric-views,bundles,agent-framework,dataset}.md` |
| Claude plan, notes, scratch | `.dev/` (this file is `.dev/plan.md`) |
| Databricks courseware for reference | `~/Documents/dbx/` sibling folders (Data Engineering, Spark, GenAI, ML, Advanced DE tracks) |
| Target bundle layout | requirements doc section 7.5 (`databricks.yml`, `resources/`, `src/`, `eval/`) |

## 4. The two-week plan (2026-10-02 to 2026-10-15)

| Day | Date | Phase | Exit criteria |
|---|---|---|---|
| 0 | Oct 1 | Requirements and research | Requirements v0.2 drafted; research appendices written |
| 1 | Oct 2 | Feasibility spike on Free Edition | Every **[verify]** item has a go/no-go; fallbacks chosen for red items |
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

**Now:** Day 0, 2026-10-01. Requirements and research phase complete; build starts 2026-10-02 with the Day 1 spike.

**Done:**
- 2026-10-01: Research appendices written (Genie Agents, metric views, bundles, agent framework, dataset), all source-cited.
- 2026-10-01: Requirements and risk register v0.1, then v0.2 (simplified to four gold tables, San Francisco chosen over Budapest).
- 2026-10-01: Public name and GitHub metadata chosen; README reworked to tutorial-first; `.dev/plan.md` created as the session hand-off; personal and review-process references removed from all docs.

**Next:**
1. Set the GitHub repo description and topics from the README (repo exists and is pushed).
2. Day 1 spike (2026-10-02): run the **[verify]** checklist from requirements section 11 on Free Edition; log the go/no-go table in `.dev/spike-day1.md` and fold confirmed facts into `docs/`.

**Blocked:** nothing.

## 6. Session checklist

At the start: read sections 5 and 4, then only the docs the day's phase needs.
At the end: update section 5, and if a decision changed, update the requirements doc and the decisions list in section 2.
