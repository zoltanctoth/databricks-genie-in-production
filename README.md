# Databricks Genie in Production

[![Dev tests](https://github.com/zoltanctoth/databricks-genie-in-production/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/zoltanctoth/databricks-genie-in-production/actions/workflows/main.yml)
[![Prod smoke tests](https://github.com/zoltanctoth/databricks-genie-in-production/actions/workflows/release.yml/badge.svg?branch=release)](https://github.com/zoltanctoth/databricks-genie-in-production/actions/workflows/release.yml)

A production reference architecture and hands-on tutorial for Databricks AI/BI Genie. You build a complete, deployable Genie stack on a standard Databricks workspace: a semantic layer with Unity Catalog metric views, two curated Genie Agents with benchmarks, a Databricks App on the Genie API, a custom orchestrator agent over MCP, and dev/prod deployment with Declarative Automation Bundles.

Written for Databricks practitioners who know SQL, Python and Unity Catalog but are new to Genie. Every step is reproducible on any Databricks workspace with Unity Catalog and serverless compute, on any cloud.

> **Status:** work in progress. The live progress marker is in [.dev/plan.md](.dev/plan.md#5-where-we-are). The build runs 2026-10-02 to 2026-10-15.

## What you will build

```mermaid
flowchart LR
  subgraph Student["Your laptop"]
    DL[Download Inside Airbnb<br/>San Francisco, 3 files]
    CLI[databricks CLI<br/>bundle deploy / run]
  end

  subgraph WS["Databricks workspace (one workspace, two bundle targets)"]
    direction TB
    VOL[(UC Volume: raw files)]
    PDFVOL[(UC Volume: generated PDFs)]
    subgraph PIPE["Lakeflow Spark Declarative Pipeline (serverless)"]
      B[bronze] --> S[silver] --> G[gold star schema<br/>comments + PK/FK]
    end
    MV[Metric views<br/>mv_market, mv_review_activity]
    JOB[Lakeflow Job<br/>pipeline -> metric view DDL -> PDF gen]
    GA[Genie Agent A<br/>SF Market Analyst<br/>Chat mode]
    GB[Genie Agent B<br/>Host Ops and Compliance<br/>Agent mode + PDFs]
    APP1[Databricks App 1<br/>Genie chat via Conversation API<br/>user authorization]
    APP2[Databricks App 2<br/>Orchestrator agent<br/>MLflow AgentServer + MCP]
    MCP[Managed Genie MCP servers]
    MLF[MLflow 3<br/>traces, evaluate]
    WH[(Serverless SQL warehouse)]
  end

  DL --> VOL
  CLI -->|bundle| PIPE & JOB & GA & GB & APP1 & APP2
  VOL --> B
  G --> MV
  JOB --> PIPE & MV & PDFVOL
  MV --> GA & GB
  G --> GA & GB
  PDFVOL --> GB
  GA & GB --> WH
  APP1 -->|Genie API, OBO| GA
  APP2 --> MCP --> GA & GB
  APP2 --> MLF
```

The three pillars, and what each module teaches:

| Pillar | What you build | What you learn |
|---|---|---|
| **Semantic layer** | Four-table gold star schema with comments and PK/FK constraints; two metric views with snowflake joins, composed measures and window measures | Why curation starts in Unity Catalog, why Databricks puts metric views under Genie, and where the approach stops |
| **Genie Agents** | Agent A (Chat mode) over metric views; Agent B (Agent mode) over tables plus PDFs in a volume; 20+ benchmarks each | How a Genie Agent produces an answer, what each curation feature does to quality, how to measure and operate it |
| **Productionizing** | One bundle with `dev` and `prod` targets; Genie JSON promotion workflow; a Genie chat app; an orchestrator agent consuming both Genie Agents over MCP, evaluated with MLflow 3 | How Genie goes from a workspace toy to a deployed, versioned, monitored component |

## Repository layout

```
README.md                          # this file
.dev/plan.md                       # working plan and live progress marker
docs/
  01-requirements-and-risks.md     # requirements, decisions, two-week plan, risk register
  research/                        # source-cited research appendices (Genie, metric views,
                                   # bundles, agent framework, dataset), verified 2026-10-01
bundle/
  databricks.yml                   # bundle, variables, dev and prod targets
  bootstrap.yml                    # one-command bootstrap script (catalog, grants, deploy, data copy)
  resources/                       # one YAML file per resource: schemas, pipeline, jobs
  src/                             # pipeline code, setup notebook
```

Genie JSON, apps and evaluation code land under `bundle/` as the build progresses. The target layout is in [docs/01-requirements-and-risks.md, section 7.5](docs/01-requirements-and-risks.md#75-bundle-layout).

## Start here

1. Read [docs/01-requirements-and-risks.md](docs/01-requirements-and-risks.md) for the architecture, decisions and plan.
2. Check [.dev/plan.md](.dev/plan.md#5-where-we-are) for what is built and what is next.
3. The research appendices in [docs/research/](docs/research/) hold the detailed findings with source URLs and page dates. Re-verify anything dated before you build on it; Databricks renamed half of this stack in 2026.

## Deploying the bundle

Every target deploys as a human (or CI) identity; in `prod` the jobs and the pipeline run as a service principal that gets least-privilege grants declared in the bundle. Three one-time prerequisites per workspace:

1. **Catalog.** The catalog named by `var.catalog` is shared by all targets, so the bundle never owns it. The bootstrap script creates it with `CREATE CATALOG IF NOT EXISTS`. On a classic workspace where the account has Default Storage enabled, that statement fails with "Metastore storage root URL does not exist"; create the catalog once in Catalog Explorer with **Use default storage** ticked, and the script then passes.
2. **Service principal.** Create one, put its application ID in the `prod` target's `service_principal` variable, and give yourself the **Service Principal User** role on it so you may deploy jobs that run as it. Its grants are in `databricks.yml` (schema level) and `bootstrap.yml` (catalog level); you grant nothing by hand.
3. **SQL warehouse.** `bootstrap.yml` looks up a warehouse by name for its SQL statements. Change the name if your workspace has no `Serverless Starter Warehouse`.

Then, per target:

```bash
databricks bundle run bootstrap -t dev --profile <your-profile>
```

The script runs the SQL above, deploys, and runs the `setup_workspace` job that copies the source files into the target's raw volume. Bundles have no post-deploy hook; a named script invoked after deploy is the canonical substitute. Re-running is safe: every step is idempotent.

Pass `--profile` explicitly. If your shell exports `DATABRICKS_CLIENT_ID` for a service principal, a bare `bundle deploy` silently deploys as that principal, which then owns the schemas and lacks the catalog grants described above.

## GitHub metadata

Suggested repository description:

> Production reference architecture and hands-on tutorial for Databricks AI/BI Genie: metric views as the semantic layer, Genie Agents with benchmarks and evaluation, Databricks App on the Genie API, MCP orchestration, and dev/prod deployment with Declarative Automation Bundles.

Suggested topics: `databricks`, `genie`, `ai-bi`, `text-to-sql`, `metric-views`, `unity-catalog`, `mcp`, `reference-architecture`, `tutorial`.

## Data attribution

Data: Inside Airbnb (insideairbnb.com), San Francisco snapshot 2026-06-14, licensed under CC BY 4.0. Modified: filtered, cleansed and aggregated for teaching. Students download the raw files themselves; this repository redistributes only derived artifacts.
