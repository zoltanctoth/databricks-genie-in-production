> Research appendix. Compiled 2026-10-01 from the official Databricks docs and cited sources by a research agent; every fact carries its source URL and the page "Last updated" date. Re-verify anything dated before you build on it.
>
> Platform note (2026-10-02): the build moved from Databricks Free Edition to a standard workspace (decision D1 in `docs/01-requirements-and-risks.md`). Free Edition limits quoted below are kept as research and no longer constrain the design.

# Genie as a tool in Databricks agents — research notes (verified 2026-10-01)

Sources: docs.databricks.com (AWS), databricks.com pricing/blog, github.com/databricks (app-templates, databricks-ai-bridge), PyPI. "Last updated" dates quoted from the pages.

## 0. Headline findings (change the architecture picture)

1. **Databricks now recommends Databricks Apps, not Model Serving, for new custom agents.** Both `deploy-agent` (Sep 15, 2026) and `multi-agent-genie` (Sep 11, 2026) carry an info box: "For new use cases, Databricks recommends deploying agents on Databricks Apps". The old `generative-ai/agent-framework/*` URLs 301 to `agents/custom-agents/*`; Model Serving pages now live under `agents/custom-agents/model-serving/` and `query-agent` calls them "legacy agents hosted on Model Serving".
2. **Agent Bricks Supervisor Agent and Knowledge Assistant are closed to new customers.** Pricing page (modified Sep 30, 2026) footnote 2 and FAQ: "KA and SA are no longer available to new customers; existing customers can continue using them. For document Q&A and multi-agent use cases, we recommend customers use Genie Agents." The docs page (Sep 11, 2026) does **not** yet say this. The separate "Supervisor API" (Beta) is deprecated with EOL Sep 30, 2026 (page dated Sep 29, 2026).
3. **"Genie Space" is renamed "Genie Agent"**; MCP server URL and SDK identifiers still use `space_id`.
4. **Genie is exposed via a managed MCP server** (`/api/2.0/mcp/genie/{genie_space_id}`), and this is how the official multi-agent app template consumes it — not via `GenieAgent`.

## 1. Three ways to serve Genie

### (a) Genie Conversation API from a Databricks App
- **What**: App (Streamlit/Dash/Node/AppKit) calls `POST /api/2.0/genie/spaces/{id}/start-conversation`, `.../messages`, polls, fetches `query-result`. Chat mode (stateful) and Agent mode APIs (GA since 2026, per release notes) available. Official template: `appkit-genie` (React/TS AppKit with "Genie" plugin) in `databricks/app-templates`; also `*-data-app-obo-user` templates.
- **Auth**: App service principal (auto-created, `DATABRICKS_CLIENT_ID/SECRET` injected) **or** user authorization (OBO) via `user_api_scopes: [genie, sql]` — token forwarded in `x-forwarded-access-token`. Genie itself splits credentials: SQL runs on the warehouse with **author-embedded compute credentials**; **data access is evaluated as the end user** (row filters/column masks apply; users need no warehouse permission) (concepts, Sep 11, 2026).
- **Deployed**: one App (serverless). Sizes: Medium 2 vCPU/6 GB 0.5 DBU/h, Large 4 vCPU/12 GB 1 DBU/h, XLarge 12 vCPU/48 GB 3 DBU/h (Sep 25, 2026). Billed per hour while running.
- **Cost drivers**: app compute hours + Genie usage (serverless SQL on the warehouse). Release note Sep 24, 2026: **service-principal Genie usage is billed at standard Genie PAYG pricing and excluded from the per-user free allowance** — favors OBO.
- **Free Edition**: Apps "Up to 3 per account; auto-stop 24 h after start/redeploy"; one 2X-Small SQL warehouse (Sep 29, 2026). Genie not listed as unsupported. **Verified feasible.**
- **Maturity**: GA (Conversation API; Agent-mode APIs GA Jul 2026). Simplest, fewest moving parts.

### (b) Custom agent with Genie as a tool
Two deployment targets:
- **(b1) Databricks Apps (recommended path)**: MLflow `AgentServer` (FastAPI, `/responses` endpoint) + `ResponsesAgent` schema; templates `agent-openai-agents-sdk`, `agent-openai-agents-sdk-multiagent`, `agent-langgraph`, `agent-langgraph-advanced`; Genie consumed via managed MCP server. Auth: service principal with `genie_space` resource `CAN_RUN` in `databricks.yml`, or OBO via `user_api_scopes: [genie]` + `get_user_workspace_client()` inside handlers. Only Medium/Large app sizes supported for agents. Query with `DatabricksOpenAI(...).responses.create(model=f"apps/{app_name}")`; OAuth only (no PAT).
- **(b2) Model Serving (Public Preview, "legacy")**: `mlflow.pyfunc.log_model(..., resources=[DatabricksGenieSpace(...)])` → UC registry → `agents.deploy()` (needs MLflow ≥3.1.3, `databricks-agents` ≥1.1.0). Auto-provisions endpoint, short-lived creds for declared resources, Review App, real-time tracing, production monitoring (beta), inference tables. CPU endpoint; `scale_to_zero_enabled=True` supported. OBO: `AuthPolicy(SystemAuthPolicy, UserAuthPolicy(api_scopes=[...]))`, MLflow ≥2.22.1, workspace-admin opt-in; Genie is an OBO-supported resource.
- **Cost drivers**: app hours or serving-endpoint hours + LLM tokens (FMAPI) + Genie SQL compute. Tracing to MLflow experiment (storage).
- **Free Edition**: Model Serving "limits on number of active endpoints, no GPU, no provisioned throughput" (exact count not published) — (b2) **plausible but unverified**; (b1) uses the 3-app quota — **verified feasible on paper**.
- **Maturity**: ResponsesAgent/MLflow 3 GA; managed MCP servers Public Preview; MCP-in-custom-agents Public Preview; Apps agent path is the current default.

### (c) Agent Bricks Supervisor Agent
- **What**: no-code supervisor over up to 50 subagents (Genie Agents, published dashboards, KA endpoints, serving endpoints, UC functions/tables/volumes, AI Search indexes, other Supervisors, web search, MCP servers/Services, custom MCP apps, custom agents on Apps); built-in sandboxed code execution; ALHF (questions + guidelines) for improvement; long-running tasks via checkpoint/continuation.
- **Auth**: built-in OBO — end users need explicit access to each subagent (Genie: access to the agent and its UC objects); supervisor ends/redirects conversations the user cannot satisfy.
- **Deployed**: a managed agent endpoint (serverless), queryable from Playground/REST; permissions Can Manage / Can Query.
- **Cost**: **$0.070/DBU** for the supervisor (Serverless Real-time Inference SKU) **plus** every subagent at native price (Genie → serverless SQL).
- **Free Edition**: Jun 17, 2026 blog says "Agent Bricks" added to Free Edition, but Free Edition limitations (Sep 29, 2026) list **Knowledge Assistant as unsupported**, and the pricing page says SA is closed to new customers. **Treat as unavailable for a new Free Edition account; unverified in-product.**
- **Maturity**: GA Feb 10, 2026, but now in "existing customers only" mode → **do not base a new reference architecture on it.**

## 2. Code-level specifics for (b)

**Packages (PyPI, 2026-10-01)**: `databricks-ai-bridge 0.22.0` (2026-09-18; requires `mlflow-skinny>=3.10.1`, `databricks-sdk>=0.49`; extras `agent-server`, `memory`), `databricks-langchain 0.20.0` (2026-06-10; requires `langchain>=1.0.0`, `databricks-mcp>=0.5.1`, `langchain-mcp-adapters`), `databricks-openai 0.17.1` (2026-08-20; requires `openai-agents>=0.5.0`, `databricks-mcp>=0.4.0`, `mlflow>=3.10.1`), `databricks-mcp 0.9.2`, `databricks-agents 1.12.0`, `mlflow 3.16.1`. Template `agent-openai-agents-sdk-multiagent/pyproject.toml` pins `databricks-openai>=0.13.0`, `databricks-agents>=1.9.3`, `mlflow>=3.10.0`, `openai-agents>=0.4.1`, Python ≥3.11.

**GenieAgent (databricks_langchain/genie.py, main)** — a factory returning a `RunnableLambda`, not a class:
```python
def GenieAgent(genie_space_id, genie_agent_name: str = "Genie", description: str = "",
               include_context: bool = False, message_processor: Optional[Callable] = None,
               client: Optional[WorkspaceClient] = None, return_pandas: bool = False)
# input: {"messages": [...], "conversation_id": optional} ->
# {"messages": [AIMessage(name="query_result"), ...], "conversation_id": str, ["dataframe": pd.DataFrame]}
```
Backed by `databricks_ai_bridge.genie.Genie(space_id, client=None, truncate_results=False, return_pandas=False)` with `ask_question(question, conversation_id=None) -> GenieResponse(result, query, description, conversation_id, suggested_questions, text_attachment_content)`; polls every 0.5 s up to 500 iterations (~250 s); truncates markdown results to 20 000 tokens when `truncate_results=True`. All calls `@mlflow_trace`d (span type AGENT/PARSER). Default prompt concatenates the full chat history, prefixed "I will provide you a chat history, where your name is {name}…" — use `message_processor` to send only the last turn.

**Genie via MCP in the official App template (`agent_server/agent.py`)**:
```python
from databricks_openai.agents import McpServer
McpServer(url=build_mcp_url(f"/api/2.0/mcp/genie/{space_id}"), name="Genie")
agent = Agent(name=..., model="databricks-claude-sonnet-4-5", mcp_servers=[...], tools=[...])
@invoke()  # from mlflow.genai.agent_server
async def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse: ...
@stream()
async def stream_handler(request) -> AsyncGenerator[ResponsesAgentStreamEvent, None]: ...
```
`get_user_workspace_client()` = `WorkspaceClient(token=headers["x-forwarded-access-token"], auth_type="pat")`; must be called inside handlers (falls back silently to the SP if header missing — verify with a `whoami` tool). LangGraph equivalent: `DatabricksMultiServerMCPClient([DatabricksMCPServer(name, url, workspace_client)])` → `create_react_agent(ChatDatabricks(endpoint=...), tools)`.

**ResponsesAgent (MLflow)**: subclass `mlflow.pyfunc.ResponsesAgent`, implement `predict(ResponsesAgentRequest) -> ResponsesAgentResponse` and optionally `predict_stream(...) -> Generator[ResponsesAgentStreamEvent]`; helpers `create_text_output_item()`, `create_function_call_item()`; stream `response.output_text.delta` then `response.output_item.done` with the same `item_id`; `custom_inputs`/`custom_outputs` supported. Signature inferred automatically.

**Model Serving resource declaration (notebook `langgraph-multiagent-genie`)**:
```python
from mlflow.models.resources import (DatabricksFunction, DatabricksGenieSpace,
    DatabricksServingEndpoint, DatabricksSQLWarehouse, DatabricksTable)
resources = [DatabricksServingEndpoint(endpoint_name=LLM), DatabricksGenieSpace(genie_space_id=sid),
             DatabricksSQLWarehouse(warehouse_id=wid), DatabricksTable(table_name="c.s.t")]
mlflow.pyfunc.log_model(name="agent", python_model="agent.py", resources=resources, pip_requirements=[...])
agents.deploy(UC_MODEL_NAME, version, deploy_feedback_model=False)
```
Passthrough requires endpoint creator to hold `Can Run` on the Genie Agent (MLflow ≥2.17.1), `Use Endpoint` on the warehouse, SELECT on tables; "if your genie space uses embedded credentials you do not have to add" warehouse/tables. OBO variant: `WorkspaceClient(credentials_strategy=ModelServingUserCredentials())` passed as `client=` to `GenieAgent`, plus `auth_policy=AuthPolicy(system_auth_policy=SystemAuthPolicy(resources=[...]), user_auth_policy=UserAuthPolicy(api_scopes=[...]))`.

**Apps resource declaration (`databricks.yml`)**:
```yaml
resources:
  - name: 'genie_space'
    genie_space: { space_id: '<id>', permission: 'CAN_RUN' }   # UI values: Can view/run/edit/manage
  - name: 'experiment'
    experiment: { experiment_id: '<id>', permission: 'CAN_EDIT' }
user_api_scopes: [genie, sql]     # only for OBO
```
Downstream grants must be added too (tables, warehouse, UC functions). App name must start with `agent-` to appear under Agents.

**MLflow 3 tracing**: `mlflow.openai.autolog()` / `mlflow.langchain.autolog()`; `MLFLOW_TRACKING_URI=databricks`, `MLFLOW_EXPERIMENT_ID` via `value_from: experiment`; `mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})` for sessions. On Model Serving, traces go to the active experiment (Git-folder experiments break real-time tracing).

## 3. Supervisor Agent details
- **Create**: Agents → Create Agent → Supervisor Agent (UI); SDK (Beta): `w.supervisor_agents.create_supervisor_agent(SupervisorAgent(display_name, description, instructions))`, `create_tool(parent="supervisor-agents/<id>", tool=Tool(tool_type="knowledge_assistant", ...))`, `update_tool` (mask: description only), `delete_tool`.
- **Requirements**: serverless, UC, Model Serving, serverless budget policy with nonzero budget, supported region; ≥1 subagent.
- **Limits**: ≤50 agents/tools; AI Search subagents Delta Sync only; web search needs `databricks-gpt-5` allowlisted, not in Enhanced Security workspaces; long-running continuation cannot span a single tool/model call that exceeds the API timeout.
- **Pricing**: $0.070/DBU + subagents at native prices.
- **Regions (AWS, Sep 2026 table)**: Supervisor ✓ in ap-northeast-1⥂, ap-northeast-2⥂, ap-south-1, ap-southeast-1⥂, ap-southeast-2⥂, ca-central-1, eu-central-1, eu-west-1, eu-west-2, eu-west-3, sa-east-1, us-east-1, us-east-2, us-west-2; not in ap-southeast-3, us-gov-west-1, us-west-1 (⥂ = cross-geo routing required).
- **Status**: GA Feb 2026; **closed to new customers per pricing page (Sep 30, 2026)**.

## 4. MCP
- **Managed servers (Public Preview, Sep 21, 2026)**: Genie One `…/ai-gateway/mcp-services/system.ai.genie_one_mcp` (scope `ai-gateway`); **Genie Agent `…/api/2.0/mcp/genie/{genie_space_id}` (scope `genie`)**; AI Search `…/api/2.0/mcp/ai-search/{c}/{s}/{index}` (`ai-search`); Databricks SQL `…/api/2.0/mcp/sql` (`sql`); UC functions `…/api/2.0/mcp/functions/{c}/{s}/{fn}` (`unity-catalog`, incl. `system.ai.python_exec`). Pricing: Genie → serverless SQL; UC functions → serverless general compute.
- **Guidance**: "For analytics use cases, start with the Genie One MCP server" (semantic layer via Genie Ontology) over raw SQL MCP.
- **Consumption**: `databricks_mcp.DatabricksMCPClient(server_url, workspace_client).list_tools()/call_tool()`; `databricks_openai.agents.McpServer`; `databricks_langchain.DatabricksMCPServer/DatabricksMultiServerMCPClient`. Auth: local OAuth profile, SP, or OBO (`ModelServingUserCredentials` on serving; forwarded token on Apps). External MCP Services via Unity Gateway need `user_api_scopes: [ai-gateway]` + `EXECUTE`. Discover servers in workspace under AI Gateway → MCPs.

## 5. Evaluation and monitoring
- **MLflow 3 GenAI eval**: `mlflow.genai.evaluate(data=..., predict_fn=..., scorers=[...])`; built-in judges `RelevanceToQuery, Safety, RetrievalGroundedness, Correctness, Guidelines, ExpectationsGuidelines, ToolCallCorrectness`; multi-turn `ConversationCompleteness, ConversationalGuidelines, ConversationalSafety`; custom judges/code scorers. Datasets: `mlflow.genai.datasets.create_dataset(uc_table_name=...)` backed by UC (needs serverless Spark locally), populated from traces. UI: Traces tab → Evaluate → run scorers. Template ships `evaluate_agent.py` using `ConversationSimulator` + scorers against the `@invoke` function.
- **Production monitoring (Beta, Sep 15, 2026)**: `scorer.register(); scorer.start(sampling_config=ScorerSamplingConfig(sample_rate=0.7))`; ≤20 scorers per experiment; job runs as the registering user; needs serverless budget policy; UC-stored traces require `mlflow.monitoring.sqlWarehouseId` tag.
- **Genie-specific**: Genie **benchmarks** (≤500 questions/agent; Chat mode compares result sets vs gold SQL with graded ratings; Agent mode uses an LLM judge + optional evaluation note; Genie Code analyzes runs) measure **SQL/answer accuracy of the Genie Agent itself**; MLflow eval measures the **orchestrating agent** (routing, tool-call correctness, answer quality). Use both: benchmarks for the Genie layer, `ToolCallCorrectness`/`Correctness` with expectations for the wrapper. Genie Monitor tab: usage trends, feedback, reviewable conversations, 6-month summaries.
- **Free Edition**: MLflow experiments/tracing and evaluate run on serverless — no stated restriction; production monitoring needs a serverless budget policy (likely default) — **unverified**; Review App not supported for Apps-hosted agents (use labeling sessions).

## 6. Databricks Apps
- **Templates** (`databricks/app-templates`): `appkit-genie`, `agent-openai-agents-sdk`, `agent-openai-agents-sdk-multiagent` (Genie via MCP + app/serving-endpoint subagents), `agent-langgraph`, `agent-langgraph-advanced`, `agent-langchain-ts`, `agent-migration-from-model-serving`, `*-chatbot-app`, `*-data-app-obo-user`, `mcp-server-hello-world`, `e2e-chatbot-app`. All ship `databricks.yml`, `AGENTS.md`, `evaluate_agent.py`, chat UI.
- **Auth**: App authorization (dedicated, non-reusable SP; all users share permissions) vs User authorization (OBO; scopes `sql`, `genie`, `model-serving`, `ai-gateway`, …; token scoped to the hosting workspace; first visit shows consent prompt; scope cache up to 5 min; restart existing apps after first enabling). Both configurable in UI or `databricks.yml`; `Can Manage` on resource and app required to attach. Apps-based agents support more OBO scopes than Model Serving.
- **Deploy**: `databricks bundle validate/deploy` then `databricks bundle run <app>` (deploy alone does not restart). Query over OAuth only.
- **Free Edition**: 3 apps/account, 24 h auto-stop, serverless only, restricted egress domains, no SSO/SCIM, non-commercial.

## 7. Facts verified (URL → fact)
- https://docs.databricks.com/aws/en/agents/custom-agents/author-agent (Sep 15, 2026) — Apps-first authoring, AgentServer, `user_api_scopes: [genie]`, Medium/Large only.
- https://docs.databricks.com/aws/en/agents/custom-agents/model-serving/deploy-agent (Sep 15, 2026) — `agents.deploy`, MLflow ≥3.1.3, Apps recommendation banner.
- https://docs.databricks.com/aws/en/agents/custom-agents/model-serving/multi-agent-genie (Sep 11, 2026) — Public Preview; LangGraph + DSPy notebooks.
- https://docs.databricks.com/aws/en/notebooks/source/generative-ai/langgraph-multiagent-genie.html — `GenieAgent`, `DatabricksGenieSpace`, `langgraph-supervisor==0.0.30`.
- https://docs.databricks.com/aws/en/agents/custom-agents/model-serving/agent-authentication-model-serving (Sep 21, 2026) — passthrough table, OBO resources, `AuthPolicy`.
- https://docs.databricks.com/aws/en/agents/custom-agents/agent-authentication (Sep 11, 2026) — `genie_space`/`CAN_RUN` yml, `get_user_workspace_client`.
- https://docs.databricks.com/aws/en/agents/custom-agents/multi-agent-apps (Sep 11, 2026) — Genie subagent via MCP, `CAN_RUN`.
- https://docs.databricks.com/aws/en/agents/agent-bricks/multi-agent-supervisor (Sep 11, 2026) — subagents, limits, SDK.
- https://docs.databricks.com/aws/en/agents/agent-bricks/supervisor-api (Sep 29, 2026) — deprecated, EOL Sep 30, 2026.
- https://www.databricks.com/product/pricing/agent-bricks (modified Sep 30, 2026) — $0.070/DBU; KA/SA closed to new customers.
- https://www.databricks.com/blog/whats-coming-next-free-edition (Jun 17, 2026) — Agent Bricks in Free Edition.
- https://docs.databricks.com/aws/en/getting-started/free-edition-limitations (Sep 29, 2026) — 3 apps, KA unsupported, endpoint limits.
- https://docs.databricks.com/aws/en/agents/mcp-tools/managed-mcp (Sep 21, 2026) — Genie MCP URL/scopes/pricing.
- https://docs.databricks.com/aws/en/agents/mcp-tools/use-mcp-in-agents (Sep 11, 2026) — client code.
- https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/ (Sep 16, 2026), /evaluate-app (Sep 15), /concepts/judges/ (Sep 15), /production-monitoring (Sep 15, Beta).
- https://docs.databricks.com/aws/en/genie-agents/monitor (Sep 17, 2026) — benchmarks; /concepts (Sep 11) — credential split, Agent mode; /conversation-api (Sep 30, 2026).
- https://docs.databricks.com/aws/en/ai-bi/release-notes/2026 — SP Genie billing (Sep 24, 2026), Agent-mode API GA.
- https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth (Sep 28, 2026), /compute-size (Sep 25), /resources (Sep 11).
- https://docs.databricks.com/aws/en/resources/feature-region-support — Supervisor region column.
- https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli (Sep 29, 2026) — `databricks-agentbricks` Beta, `agent.toml`.
- github.com/databricks/databricks-ai-bridge (`integrations/langchain/src/databricks_langchain/genie.py`, `src/databricks_ai_bridge/genie.py`); github.com/databricks/app-templates (`agent-openai-agents-sdk-multiagent/agent_server/agent.py`, `databricks.yml`, `pyproject.toml`).

## Open questions
- Exact Free Edition cap on active Model Serving endpoints (docs say only "limits on the number").
- Whether a brand-new Free Edition account can still create a Supervisor Agent (pricing says closed to new customers; docs silent) — needs in-product check.
- Whether production monitoring (Beta) and UC-backed evaluation datasets work on Free Edition (budget policy, serverless Spark).
- Model Serving OBO: the exact `api_scopes` string for Genie is not shown in the scraped excerpt (managed-MCP page uses `genie`); confirm in the OBO resource table.
- `databricks-openai` has no `GenieAgent`; Genie via OpenAI Agents SDK is MCP-only (confirmed by template and 404 on `databricks_openai/genie.py`).
- Supervisor/KA future: pricing FAQ points to "Genie Agents" for multi-agent use cases; no docs yet describe Genie Agents orchestrating other agents beyond UC-function tools and volumes.
