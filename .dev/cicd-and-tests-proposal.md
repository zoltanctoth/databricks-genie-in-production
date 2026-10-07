# CI/CD and test proposal (2026-10-07, not yet decided)

Status: proposal. Four open decisions at the end. CI/CD is implemented by hand once they are settled; this file is the input for that session.

## CI/CD: GitHub Actions with the Databricks CLI and workload identity federation

Pattern from the Databricks GitHub Actions page (Azure docs checked 2026-10-07; `docs/research/bundles.md` cites the same page dated 2026-09-11): `databricks/setup-cli@<pinned version>`, then `databricks bundle validate|deploy|run -t <target>`.

Authentication: workload identity federation (`DATABRICKS_AUTH_TYPE: github-oidc` plus `DATABRICKS_CLIENT_ID`, no secrets stored in GitHub). A federation policy on the service principal limits who may sign in as it, for example subject `repo:zoltanctoth/databricks-genie-in-production:environment:prod`. Creating the policy is an account-level command (`databricks account service-principal-federation-policy create`) and needs a Databricks account admin (R-17). Fallback: OAuth M2M with a client secret stored as a GitHub environment secret.

Docs: https://learn.microsoft.com/en-us/azure/databricks/dev-tools/ci-cd/github and https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/provider-github

| Workflow | Trigger | Steps | Signs in as |
|---|---|---|---|
| `pr.yml` | pull request to `main` | Static checks, `bundle validate --strict` for both targets, `bundle plan -t prod` written to the PR job summary; deploy to `dev`, run `setup_workspace`, `airbnb_pipeline`, `deploy_metric_views`, tests job | CI service principal |
| `deploy-prod.yml` | push to `main` | `bundle deploy -t prod`, run `airbnb_pipeline`, `deploy_metric_views`, tests job as smoke test | prod service principal `47d22b7a-…`, GitHub environment `prod` |

Design choices:
- Two service principals: a CI one for PR deploys and the existing prod one, so a PR can never write to prod schemas. One service principal with two federation policies is the simpler alternative.
- PRs deploy to the existing `dev` target as the CI service principal. Development mode prefixes names with the deploying identity, so CI gets isolated `dev_<sp>_*` schemas without a third target (D1 unchanged). `concurrency:` stops two PRs running at once.
- The first prod deploy (Next 1) happens through CI, so the prod service principal owns every prod resource and nobody deploys prod from a laptop.
- `bundle plan -t prod` in the PR shows every create, change, recreate and delete before merge (a schema rename is a recreate). Optional: fail on `delete` unless the PR has a label.
- A `prod` GitHub environment gives a required-reviewer gate and limits which workflows can use the prod federation policy.

## Tests in four layers

1. **Static, every PR, no workspace:** `bundle validate --strict` for both targets; `ruff`; a pytest that extracts the YAML from `src/metric_views/*.sql`, parses it and checks every dimension and measure has `comment`, `display_name` and `synonyms` (FR-4 agent metadata); unit tests for `tools/generate_documents.py`, in particular that `classify_license()` matches `license_status` in `silver_listings`.
2. **Pipeline expectations:** `CONSTRAINT ... EXPECT (...) ON VIOLATION FAIL UPDATE` on keys and required columns in silver and gold, plain `EXPECT` for soft rules. Results appear in the pipeline event log; runs in CI and prod.
3. **Tests job in the bundle** (`resources/tests.job.yml`, SQL tasks on the warehouse, each check fails through `raise_error()` / `assert_true()`): the 2026-10-05 acceptance checks as regression tests (gold row counts, `estimated_nights_l365d` equals the published value for all listings, review windows match the listings file, revenue within $1, no orphan foreign keys, every column commented via `information_schema`); metric view checks (each view exists; `MEASURE(...)` equals hand-written SQL on gold, for example `availability_ratio` by neighbourhood against a plain `AVG` over `fact_calendar`). The same job is the post-deploy smoke test in prod.
4. **Evaluations, not PR-gating** (cost, non-deterministic): Genie benchmarks once Days 6 to 8 produce them (running them through the API is **[verify]**), and `mlflow.genai.evaluate` for orchestrator routing. Manual or nightly workflow that records scores.

SQL tasks rather than pytest with Databricks Connect for layer 3: the tests are about tables and views, they reuse the `warehouse_id` variable, and the results are visible in the Jobs UI.

## Open decisions

1. **Account admin:** can account-level federation policies be created on this Azure account? If not, OAuth M2M with a secret.
2. **Service principals:** a separate CI one (recommended) or one shared?
3. **PR integration run:** full run (setup, pipeline, metric views, tests; a few minutes of serverless per PR) on every PR, or static checks on PRs with the full run on merge and on demand?
4. **Scope:** CI/CD is stretch item S2 (Day 11 rule). Doing it now moves S2 into core while three of four metric views and the Genie Agent work (Days 6 to 8) are still ahead. Now, or after the metric views?

Once decided: record S2's status in the plan and requirements, then order the work as federation policy, CI service principal, workflows, tests job, prod first deploy through CI.
