> Research appendix. Compiled 2026-10-01 from the official Databricks docs and cited sources by a research agent; every fact carries its source URL and the page "Last updated" date. Re-verify anything dated before you build on it.

# Research note: Databricks Genie Agents (official docs, read 2026-10-01)

Sources: docs.databricks.com/aws/en pages ("Last updated" Sep 11–30, 2026) and databricks.com/product/pricing/genie (modified Aug 20, 2026). Nothing below is from memory.

## 1. What a Genie Agent is today

- **Naming.** "Genie Agents were formerly known as Genie Spaces" (all pages). "Agent mode was formerly known as Research Agent" (concepts). "Genie One was previously known as Databricks One." The REST API still uses `/api/2.0/genie/spaces/{space_id}`; the Share dialog still says "Embed space".
- **Genie family.** *Genie Agents*: domain-specific, author-curated NL-to-SQL chat over Unity Catalog data. *Genie One*: simplified business-user UI; its Chat routes a question first to a matching Genie Agent, then to dashboards/queries/metric views, and can connect Google Drive, SharePoint, GitHub, Glean, Atlassian. *Genie Code*: developer coding/data assistant; also embedded in Genie Agents to propose context at creation, debug wrong answers, analyze usage and benchmark runs.
- **Chat mode (default).** Structured data only; "cannot answer questions about unstructured data such as PDFs". One read-only SQL query on the agent's warehouse → summary, result table, optional visualization. Verified answers ("trusted assets") exist only here.
- **Agent mode.** Multi-step: research plan, several SQL queries, iteration, report with citations/visualizations/tables, PDF export, "Answer now" to stop early. Only Agent mode reads volume files and uploaded PDFs. No cross-Geo needed in Americas, Europe, AU/NZ/JP; elsewhere cross-Geo required. Separate streaming "Agent mode APIs".
- **Inspect (Public Preview).** Per-response re-check of generated SQL with verification sub-queries.
- Compound AI system; prompts wrapped in English, so non-English responses may come back in English.

## 2. How Genie generates answers

Concepts page components: **Unity Catalog table metadata** (names, descriptions, PK/FK), **column names/descriptions** (relevance-filtered), **knowledge store context** incl. column sample values, **example SQL queries** (relevance-filtered), **SQL functions** (all attached), **Instructions** (the "General instructions" text), **prompt/response history** (oldest trimmed at token limit). Only sources attached under **Configure > Sources** are queried, even if instructions name other tables.

UI concepts (tune-quality page):
- **Configure > Examples tab**: example queries, **Filters**, **Measures**, **Fields** (together "SQL expressions"), **Joins**. API: `example_question_sqls`, `sql_snippets.{filters,measures,expressions}`, `join_specs`.
  - **Example SQL queries** (recommended): title = typical user phrasing; static or **parameterized** (`:param`; String/Date/Date and Time/Decimal/Integer; comment). Optional **Usage guidance**. Exact parameterized match in Chat mode = **verified answer**.
  - **SQL functions**: UC scalar or table-valued; Genie cannot read/modify the body; users need `EXECUTE`.
  - **SQL expressions**: Name, Code, Synonyms, Instructions. Filter = boolean; Measure = aggregation; Field = row-level expression. Applied "exactly as written".
  - **Joins**: tables, condition (or SQL expression), relationship many-to-one / one-to-many / one-to-one (API adds many-to-many via `--rt=FROM_RELATIONSHIP_TYPE_<X>--`). UC PK/FK auto-imported.
- **Configure > Text tab**: **General instructions**, one global block (API: max 1 `text_instructions`); docs say use "only as a last resort".
- **Configure > Sources**: per-table **Description** override (Reset → UC comment); per-column **Description**, **Synonyms**, hide/show; **Advanced settings** = **Prompt matching**:
  - **Format assistance** (API `get_example_values`): representative values, sampled with the author's permissions, shared with all users.
  - **Entity matching** (API `build_value_dictionary`; troubleshooting page still says "Value dictionaries"): curated distinct values for string columns; **120 columns/agent, 1,024 values/column, 127 chars**; stored in workspace storage bucket; blocked on row-filtered/masked tables, must be disabled manually on views over them; column kebab → **Refresh prompt matching**. Filters on such columns become drop-downs.
- **Knowledge store** = agent-scoped descriptions, synonyms, joins, SQL expressions, prompt-matching settings; never writes to UC. **Knowledge mining** suggests measures/filters/fields/joins from author thumbs-ups or CSV downloads.
- Allowed sources: managed/external/foreign tables, views, metric views, materialized views; metric views and pre-joined views recommended.

## 3. Curation workflow and quality tuning

- Create → Genie Code auto-launches and proposes descriptions/examples; can build an agent from a domain description. **Review Suggested Queries** mines popular workspace queries the author can view.
- Settings: Title, Default warehouse, Tags (incl. governed), Thumbnail, Markdown Description, **Common questions**. Kebab: **Clone** (tables, settings, instructions, examples, functions; not chats/monitor data), **Export to metric view**, **Assign certification** (Certified/Deprecated via `system.certification_status`).
- Response loop: "Is this correct?" → **Yes / Fix it (Submit, or Submit and try again) / Request review**. Editors: **Show code**, edit SQL, **Add as instruction**, **Add as benchmark**, Refresh data, Regenerate. "Genie does not automatically learn or change its behavior in response to feedback."
- **Monitor tab** (CAN MANAGE): all Q&A with filters; **Weekly digest**; **Analyze Agent Usage** (Genie Code, last 6 months, cited); full conversations visible when sharing = **Reviewable by agent managers** (default for new conversations; Private shows prompts only); delete conversations; audit-log events.
- **Benchmarks**: **500/agent**, each runs as a new conversation. Chat-mode scoring vs a SQL Answer (exact SQL, same rows, order-insensitive, 4-sig-digit numerics = Good; empty/error, extra columns, differing single cell = Bad; ≤5,000 rows compared); no SQL Answer → manual review. Agent-mode runs: LLM judge + optional **Evaluation note**. Evaluations tab keeps history; result sets 1 week. Recommend 2–4 phrasings/question; API page: ≥5 example SQL, ≥5 benchmarks.
- Best practices: start small, "aim for five or fewer tables", domain-expert author, SQL expressions > example SQL > text, no conflicting instructions, explicit clarification rules, summaries via heading "Instructions you must follow when providing summaries", deploy with **Declarative Automation Bundles**, structured user testing. Dashboard filters don't carry into manually linked agents.

## 4. Files in volumes and file upload (PDF-relevant)

**Analyze files in volumes (Beta; volumes page, Sep 24 2026).** Admin toggle **Analyze Files in Volumes with Genie Agents** (Previews page).
- Up to **10 volumes/agent**, whole volume only; add a **Description** (drives retrieval).
- **Agent mode only**; retrieves relevant content, reasons with tables, cites to page level (Beta); also via Agent mode APIs.
- Users need **READ VOLUME** plus **both Workspace access and Databricks SQL access entitlements** (consumer-only/SQL-only/account-only users excluded). Always the asking user's permissions.
- **Without content search**: **500 files/volume** (TXT/MD exempt; >500 → error), types **PDF, JPG, JPEG, PNG, TIFF, TIF, DOC, DOCX, PPT, PPTX**, **10 MB/file**, **≤5 files per question**; unsupported/oversized files ignored.
- **With content search** (recommended; Beta): enable per volume in Catalog Explorer (CAN MANAGE), manual **Sync now** (no auto-reindex). **10,000 files/volume, skips >50 MB**, same types, **100 indexed volumes/workspace**, **managed volumes only** (no external volumes, no workspace-bound catalogs). Needs Lakebase, `ai_parse_document`, Foundation Model APIs; no cross-Geo in Sydney, Tokyo, Frankfurt, Ireland, London, N. Virginia, Ohio, Oregon; not GovCloud/FedRAMP. Billing: ingestion = AI Functions, serving = Lakebase CUs (2–12, scale-to-zero after 3 idle days), plus Genie reasoning.
- Cannot read Google Drive/SharePoint files; no web search.

**Upload a file (Sep 17 2026).** CSV/Excel Public Preview; PDF Beta (toggles **Genie - Upload File**, **Upload Local PDFs to Genie Agents**; needs **Upload data using the UI** and Partner-powered AI). 25 files/conversation. CSV/Excel <200 MB, <100 columns. PDF: Agent mode, <20 MB, ≤100 pages, **≤15,000 characters**, UI only, conversation-scoped, not in compliance-security-profile workspaces. Stored in a hidden user+agent UC managed volume; uploader-only access.

## 5. Limits and sizing

| Item | Limit |
|---|---|
| Tables/views/metric views per agent | 50 (recommend ≤5) |
| Instructions | 100/agent (each example query, each function, whole General instructions block = 1) |
| Knowledge store snippets | 200/agent (table descriptions + joins + SQL expressions) |
| Entity matching | 120 columns, 1,024 values/column, 127 chars |
| Conversations / messages | 200,000 per agent / 10,000 per conversation |
| Benchmarks | 500/agent |
| Volumes | 10/agent |
| Timeouts | SQL >5 min and messages >30 min cancelled |
| Results | CSV ≈1 GB; results persist 7 days |
| API serialized_space | strings ≤25,000 chars, arrays ≤10,000, 1 text instruction |
| Token limit | warning, then messaging blocked; mitigate by hiding columns, pruning examples |

Compute: pro or serverless SQL warehouse (serverless recommended). Partner-powered AI features must be on at account and workspace level.

## 6. Sharing, permissions, embedding, auth

- **Two credentials**: warehouse access uses the **embedded compute credentials of the last author who saved the warehouse**; data access uses the **end user's UC identity** (row filters/masks per user; query history attributed to the user). If that author leaves the workspace, queries fail until a CAN EDIT user re-saves the warehouse.
- Author: DBSQL entitlement, CAN USE warehouse, SELECT on data, CAN EDIT+ (creator gets CAN MANAGE). Consumer: consumer access or DBSQL entitlement, SELECT on data, CAN VIEW/CAN RUN (identical abilities: ask, feedback, upload). CAN EDIT adds instructions/questions/tables; CAN MANAGE adds monitor, permissions, delete, others' conversations. Agents inherit folder permissions; share to users/groups/"All account users"; OpenSharing for external parties; users must be workspace members.
- **Embedding**: iframe; admin configures allowed embedding surfaces; author needs CAN MANAGE; Share > **Embed space**; end users must sign in to Databricks and hold agent + data access; add `allow="clipboard-write"`; embedded users cannot edit config.
- **API auth**: OAuth U2M for interactive, OAuth M2M service principal otherwise (SP needs data + warehouse permissions, is billed). Management APIs import/export `serialized_space` for CI/CD. Multi-agent systems can call a Genie Agent with **on-behalf-of-user** downscoped tokens (off by default, admin-enabled; MLflow ≥2.22.1; Databricks Apps recommended for broader scopes).

## 7. Pricing, billing, Free Edition

- Pricing page: **Genie One and Genie Agents "PROMOTION – FREE UNTIL JAN 31, 2027"**; from **Feb 1, 2027** every user gets **150 DBUs/month free**, then **$0.070/DBU**, compute billed separately. Genie Code billed since **July 8, 2026** (25% off until Jan 31, 2027, same allowance). Genie Ontology free until Jan 31, 2027, "price coming soon". 150 DBUs ≈ $10.50 (US East).
- **Service principals**: no allowance, no promotion, "their usage is billed". UI and API share one 150 DBU pool per named user.
- SKUs: billed = **Serverless Real-Time Inference** (`billing_origin_product='GENIE'`); free = **GENIE_FREE_USAGE** (since July 20, 2026); `usage_metadata.genie.surface` ∈ GENIE_CODE/GENIE_ONE/GENIE_AGENTS. Budgets: Unity Gateway + tag `databricks-product: genie`, one budget for all Genie products, shared + per-user thresholds, alert/block (approximate), never removes free allowance, LLM usage only.
- Volumes: reasoning billed as Genie usage; content search adds AI Functions ingestion + Lakebase serving.
- **Free Edition**: limitations page (Sep 29 2026) does not list Genie Agents or Genie One as unsupported (only Knowledge Assistant, R/Scala, etc.); one 2X-Small serverless SQL warehouse exists. The overview mentions Genie for dashboards and Genie Code. No explicit availability statement; Free Edition has **no account console**, while Partner-powered AI and cross-Geo are account-admin settings.

## 8. Facts verified / open questions

**Verified** (base `https://docs.databricks.com/aws/en/`):
- `genie-agents/concepts` (Sep 11) – naming, context components, Chat vs Agent mode, Inspect, two credentials, regions.
- `genie-agents/set-up` (Sep 24) – 50 tables, 200k/10k, warehouse types, ACL levels, clone/export/certify.
- `genie-agents/tune-quality` (Sep 11) – 100 instructions, 200 snippets, tabs, entity-matching limits, joins, SQL expressions, knowledge mining.
- `genie-agents/monitor` (Sep 17) – feedback, Monitor tab, 500 benchmarks, scoring rules.
- `genie-agents/best-practices` (Sep 11) – ≤5 tables, instruction hierarchy, DABs.
- `genie-agents/volumes` (Sep 24), `volumes/content-search` (Sep 17) – all file limits, entitlements, regions, billing.
- `genie-agents/file-upload` (Sep 17) – 25 files, PDF 20 MB/100 pages/15,000 chars.
- `genie-agents/embed` (Sep 11), `genie-agents/troubleshooting` (Sep 25), `genie-agents/talk-to-genie` (Sep 11), `genie-agents/conversation-api` (Sep 30).
- `security/auth/access-control/` – ACL matrix, CAN VIEW = CAN RUN.
- `agents/custom-agents/model-serving/multi-agent-genie` (Sep 11) and `.../agent-authentication-model-serving` (Sep 21) – OBO.
- `genie-one/` (Sep 18), `genie-one/chat` (Sep 17), `genie-code/` (Sep 23) – positioning, external sources, promo note.
- `genie/budgets`, `genie/consumption-guide`, `genie/monitor-cost`, `genie/genie-cost-budgets-faq` (all Sep 11) – billing, SKUs, SP exclusion.
- `getting-started/free-edition-limitations` (Sep 29); https://www.databricks.com/product/pricing/genie (Aug 20) – promo dates, 150 DBU, $0.070/DBU.

**Open questions (not stated in docs):**
- Whether Genie Agents, Agent mode and the volumes Beta are enabled in Free Edition, and how account-level toggles are handled there.
- Character/page limits for PDFs read from volumes (only uploaded PDFs have the 15,000-char cap); how content is chunked without content search.
- DBU consumption per Chat-mode vs Agent-mode message; no per-request rate table published.
- Actual token-limit size; "workspace-specific limits" for tables via API.
- Whether Inspect, Agent mode or volume reasoning cost extra after Feb 1, 2027 beyond standard LLM metering.
- Embedded-iframe auth beyond "users are prompted to authenticate" (no SSO/OBO detail).
- Content-search auto-sync (currently manual **Sync now** only).
