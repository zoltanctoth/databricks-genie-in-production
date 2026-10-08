# CI/CD as built (2026-10-08)

GitHub Actions with the Databricks CLI, kept minimal for teaching: validation, integration testing, promotion. All three stages ran green on GitHub on 2026-10-08, including the first prod release. Reader-facing summary: README, "CI/CD".

## Flow

| Trigger | Workflow | GitHub environment | What runs |
|---|---|---|---|
| Pull request to `main` | `.github/workflows/pr.yml` | `ci` | `bundle validate --strict` for `dev` and `prod`; `bundle plan -t prod` written to the run summary |
| Push to `main` | `.github/workflows/main.yml` | `ci` | `bundle deploy -t dev`, then `bundle run` of `setup_workspace`, `airbnb_pipeline`, `deploy_metric_views`, `tests` |
| Push to `release` | `.github/workflows/release.yml` | `prod` | The same chain on `prod`; the tests are the smoke test |

Promotion: a pull request from `main` to `release`. `release` is protected. CLI pinned to `databricks/setup-cli@v1.19.0` (the local CLI version). `bundle deploy` in CI has no `--auto-approve`, so a delete or recreate fails the run and needs a human.

## Identity

- One service principal, `dab_principal` (application ID `47d22b7a-8f16-43cb-93c5-590e5d89e8b9`, numeric ID `146863530177899`), signs in for both environments. In `dev` it gets its own copy: `dev_dab_principal_raw`, `dev_dab_principal_airbnb`, jobs `[dev dab_principal] ...`.
- Sign-in today: OAuth M2M. GitHub environments `ci` and `prod` each hold variables `DATABRICKS_HOST` (full `https://` URL) and `DATABRICKS_CLIENT_ID`, and secret `DATABRICKS_CLIENT_SECRET`. `prod` allows only the `release` branch. Secrets expire; rotate them.
- Prod is deployed only as the service principal: by `release.yml`, or as break-glass with `databricks bundle deploy -t prod --profile genie-prod-sp` from a clean `release` worktree (`git worktree add ../genie-release release`). Whoever deploys first owns the schemas, volumes and pipeline, and only an admin can change that later.
- `prod` sets `run_as` to the service principal. It fixes the runtime identity only; deploy-time ownership is decided by who deploys.

One-time grants and fixes, done 2026-10-08:

- `USE CATALOG` and `CREATE SCHEMA` on `genie_reference` for the service principal.
- `GRANT SELECT ON ANY FILE TO <application ID>`: `setup_workspace` reads a raw `s3a://` path, which needs this legacy privilege; workspace admins have it implicitly, the service principal did not. The grant lives in the `hive_metastore` scope, so `SHOW GRANTS ON ANY FILE` lists it only with `hive_metastore` as the current catalog.
- Prod objects first deployed by a human were handed to the service principal (schema and volume owner, pipeline `IS_OWNER`). Before that, the release failed with "User does not have MANAGE on Schema" and "Only admins can change pipeline owners".

## Target: workload identity federation (needs an account admin)

The author is a workspace admin, not an account admin (the account console shows only the workspace picker), so federation waits. To switch:

1. An account admin creates two federation policies on numeric ID `146863530177899` (`databricks account service-principal-federation-policy create`), issuer `https://token.actions.githubusercontent.com`, audience the account ID `e8493620-2b42-4f8f-bc56-41f1af52aad0`, subjects:
   - `repo:zoltanctoth@445752/databricks-genie-in-production@1400199154:environment:ci`
   - `repo:zoltanctoth@445752/databricks-genie-in-production@1400199154:environment:prod`
2. In each workflow's `env`, replace the secret line with `DATABRICKS_AUTH_TYPE: github-oidc` and add `id-token: write` to `permissions`.
3. Delete the client secret.

The repository was created after GitHub's 2026-07-15 switch, so its `sub` claim uses numeric IDs (checked through `GET /repos/.../actions/oidc/customization/sub`); the `repo:<org>/<repo>:...` form in the Databricks docs would not match. Docs checked 2026-10-08: learn.microsoft.com/azure/databricks/dev-tools/auth/provider-github (updated 2026-10-05), .../auth/oauth-federation-policy (updated 2026-10-02).

## Tests

- **PR:** `bundle validate --strict` for both targets.
- **Main and release:** the chain itself (pipeline and metric view job must succeed), then the `tests` job: `bundle/src/tests/gold_and_metric_views.sql`, SQL task on the warehouse, one `assert_true()` per check. Minimum row counts, foreign key integrity, every gold column commented, and `MEASURE(availability_ratio)` by neighbourhood equal to a hand-written `AVG` over `fact_calendar`.
- **Out of CI (phase 9):** Genie benchmarks and `mlflow.genai.evaluate`, on a manual or scheduled workflow, not a merge gate.

## Gotchas

- Local dry runs as the service principal must use a clean copy without `bundle/.databricks/`; otherwise the CLI reuses the developer's local state and reads `dev_<user>_*` as the service principal (403).
- `setup_workspace` runs on every `main` and `release` run; it is idempotent and fills empty volumes on a first deploy.
- Old objects after a rename (for example the metric view `booking_reference`, renamed to `availability_metrics` on 2026-10-08) are dropped by hand; the bundle carries no cleanup statements.
