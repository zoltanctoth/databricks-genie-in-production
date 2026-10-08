# Course notes

Raw material for turning the build into lessons (phase 10). Each entry is something that happened during the build and is worth teaching: what we did, what broke or surprised us, the numbers, and the lesson. Add to it as each phase finishes; the course outline is written from this file, the plan and the architecture doc.

## Module: Genie Agent A, from UI to bundle (phase 5, 2026-10-08)

### Create in the UI, then generate
- The fastest start is a throwaway space in the UI, then `databricks bundle generate genie-space --existing-id <id> --key <key>`. The generated YAML needs edits before the first deploy: delete `parent_path` (it is the author's home folder, so CI and prod would fail or write there), set the title (dev mode adds `[dev <user>]` itself), write the description by hand (Genie writes a long one that promises columns you plan to hide).
- Pick the resource key once. The key ties the bundle's state to the space; renaming it after the first deploy deletes the space and creates a new one with a new `space_id` and no history. Same for `parent_path`. The title can change freely.
- Pitfall seen live: the UI table picker lists `dev_tothz_airbnb` and `dev_dab_principal_airbnb` next to each other; adding a table from the wrong dev schema gives a permission error on the next save.
- A metric view source goes under `data_sources.tables` in the JSON, not `metric_views`.

### Per-target table names (the one real design problem)
- The Genie JSON holds fully qualified table names, and this bundle has three copies of the schema (author dev, CI dev, prod). Bundle `${...}` substitution runs only on YAML values, not inside a `file_path` JSON (tested: the plan sent the text unchanged).
- Fix: put the JSON inline as `serialized_space: |` in the resource YAML with `${var.catalog}.${resources.schemas.schema.name}.<table>`. Use the resource reference, not `${var.schema}`, because only the resource carries the `dev_<user>_` prefix. Switching from `file_path` to inline with the same content is no change in `bundle plan`.
- Verify per target with `bundle plan -t <target> -o json` before deploying anything.
- Consequence: `generate --force` no longer fits, so `bundle/scripts/pull_genie_space.py` pulls UI edits back: reads the space through the API, turns literal names back into variables (plain and backticked forms), rewrites only the `serialized_space` block. Bundle `scripts:` cannot do this: they resolve only `${bundle.*}`, `${workspace.*}`, `${var.*}`, not `space_id`.

### What the Genie API does on create and update
- Create silently drops column configs for columns that do not exist yet (seen when a metric view column was renamed before the view was rebuilt).
- Create fails (403, "Table ... does not exist") when a source table or metric view is missing.
- On create, Genie adds its own join spec from PK/FK constraints; a join spec in the file is then duplicated. We removed `join_specs` from the JSON and the FK join still worked. Teaching point: declare PK/FK `RELY` in gold and let Genie derive joins.
- Update replaces the whole config with the file: anything curated in the UI and not pulled is gone on the next deploy. Workflow: change in UI, pull, review `git diff`, commit, deploy.
- The `space_id` survives redeploys. Target-level `permissions` apply to the space.
- The UI configure panel does not refresh; it showed "Filters (0)" for a filter the API returned until the page was reloaded.
- UI naming in 2026: SQL expressions (filters, measures, fields, joins, example queries) are under Configure → Examples; Configure → Instructions holds only the General Instructions text (one block, `text_instructions` allows one item). "Fields" replaced "Dimensions" in the UI; the JSON key is still `sql_snippets.expressions`.

### Column configs
- Format assistance samples values so Genie knows formats and casing; entity matching builds a value dictionary so "mission" becomes `Mission`. The UI defaults turn format assistance on almost everywhere and entity matching on every string column, including free text (`description`, `host_about`, `listing_url`), which wastes the entity-matching budget.
- Curated: entity matching on low and medium cardinality categories users name (`neighbourhood`, `room_type`, `property_type`, `stay_type`, `license_status`, `host_size_band`, `host_type`); format assistance on dates and booleans; nothing on IDs and numbers; exclude the duplicate availability columns, coordinates and URLs (one fact, one place).
- Found while reviewing the generated configs: the metric view said `neighborhood`, the gold table `neighbourhood`. One concept, two names in one agent. Renamed the dimension, kept "neighborhood" as a synonym.

### Benchmarks
- How many: question types × failure modes (wrong source, wrong filter value, wrong definition, wrong grain, wrong aggregation, NULL handling, should refuse). The count follows from the grid; 100/N points per question sets the resolution. We kept 6 for Agent A (D16): enough to teach the method, at the cost of a gate where one wrong answer is 17 points.
- Chat-mode scoring rules (docs "Test and monitor a Genie Agent", 2026-09-17): different row order is Good; extra columns are Bad; missing rows or columns are Bad. An LLM judge only labels why a result is Bad (`LLM_JUDGE_MISSING_OR_INCORRECT_FILTER` and so on).
- Gold SQL rules learned the hard way: only the columns asked for (Genie's helpful `listing_count` made answers Bad), no `ROUND`, fixed `ORDER BY`, and the gold must answer exactly the question's wording. Three gold bugs turned up: a certificate question whose gold lost its `stay_type = 'short_term'` filter (Genie was right, the benchmark wrong); a Superhost-vs-regular question whose gold included the new 'Unknown' group the question never asked about; the first benchmarks were written in the throwaway space by mistake.
- Run-to-run variation: the same unchanged space scored 4/6 and 5/6 on consecutive runs. Read score changes smaller than one question as noise.
- Benchmarks live in `serialized_space.benchmarks`, deploy with the space, and round-trip through the pull script. The API returns them sorted by `id` descending.

### Curation steps and their scores (6 benchmarks)
| Step | Score |
|---|---|
| Column configs and UC metadata only | 4/6 to 5/6 |
| General instruction "Output": only the requested measures plus grouping columns, no extra counts | 4/6 (the remaining failures were a gold bug and NULL filtering) |
| Added "listings exclude hotels" definition | 2/6: Genie dropped hotels from questions that never said "listings". Reverted. Lesson: a definition in free text overreaches; the benchmarks had also dropped that rule |
| Added rule: no `IS NOT NULL` filters unless asked (Genie's `nightly_price IS NOT NULL` removed 1,400 unpriced listings from the review average) + fixed the certificate gold | 6/6, repeated |
| Metric view `host_type` gets 'Unknown' for the 90 hosts with no Superhost status | 5/6 until the gold was limited to the two groups the question names, then 6/6 |
- Lesson worth a slide: ask "would I want this rule if no benchmark existed?" The output-columns rule passes (the orchestrator parses results); a rule written only to satisfy a benchmark is gaming the scorer.
- A filter snippet (`NOT dim_listing.is_hotel`, display name "listings") was tried and removed by the author; Genie generated its `instruction` text (WHEN_TO_USE, SCOPE_TABLES, RISK_IF_MISUSED) automatically.

### NULLs: one fact, one definition
- `host_type` was `IF(is_superhost, 'Superhost', 'Not Superhost')`; `IF` with a NULL condition returns the second branch, so 90 listings with unknown status counted as "Not Superhost" in the metric view while table queries dropped them. Two paths, two answers. Fixed with `CASE ... ELSE 'Unknown'` (3,817 + 3,425 + 90 = 7,332 listings).

### Benchmarks in CI
- `bundle/scripts/run_genie_eval.py`: `genie-create-eval-run SPACE_ID --json '{}'` runs every benchmark (CLI 1.19, Beta); poll `genie-get-eval-run`; details per result give `assessment` and `assessment_reasons`. About 80 s for 6 questions. Writes a Markdown table to the GitHub job summary and fails below 80%.
- Only dev is evaluated; a release is a merge of a `main` commit that passed.
- The gate did its job on day one: it failed the build at 67% and pointed straight at a gold bug and a NULL-filter habit.

### CI ordering
- A Genie space cannot be created before its tables exist, and the metric views are built by a job that runs after deploy. Both dev CI and the first prod release failed on this. Fix: deploy in two passes, `bundle deploy --select <data-layer resources>`, run setup, pipeline, metric views and tests, then a full `bundle deploy` that adds the agents. New data-layer resources must be added to the `--select` list in both workflows. The docs say `--select` is "not intended for use in production"; here every run still ends with a full deploy.
- A push that did not trigger a workflow run happened once; `gh workflow run main.yml --ref main` starts it by hand.
- Planning as the service principal from the author's checkout fails with a state lineage mismatch (`.databricks/` holds the author's state); plan from a copy without it.

### Genie benchmarks vs MLflow evaluation
- Genie benchmarks are unit tests for one agent with fixed scoring rules and a UI review loop; `mlflow.genai.evaluate` is the integration test for code around the agents (routing, answer composition, traces, custom scorers). Reuse benchmark questions as a slice of the orchestrator dataset labelled with the expected agent; if they pass in Genie but fail through the orchestrator, the fault is in routing.
