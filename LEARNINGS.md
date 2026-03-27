# Learnings from V1 Backend Implementation

Documented issues and solutions from the first implementation of the procurement GenAI backend. These should inform the V2 rebuild.

---

## Architecture & Performance

### 1. Agent mode extremely slow (30-150s per query)

The LangGraph ReAct agent made multiple sequential LLM calls via GenAI Hub. A single question like "Which vendors supply lidar sensors?" triggered: 1 reasoning call → 1 search tool → 1 reasoning call → 10 parallel tool calls → 1 final reasoning call = 3 LLM round-trips at 10-100s each.

**Consider for V2:** Fewer tool calls via smarter prompting, parallel tool execution, response caching, or a different agent framework. Evaluate whether LangGraph is the right choice or if a simpler tool-calling loop would suffice.

### 2. Linear router too rigid for multi-faceted questions

The router pipeline (classify intent → retrieve graph context → generate answer) could only handle single-intent queries. Questions like "vendors with high risk AND overdue invoices AND expiring contracts" required an agentic approach.

**Consider for V2:** Design the architecture as agent-first from day one, with the linear pipeline as a fast path for simple queries.

### 3. CF memory: 512M caused OOM

The app crashed on startup with 512M. LangGraph + LangChain + GenAI Hub SDK + HANA driver together need ~200-300M at baseline, leaving no room for query processing.

**Resolution:** 1024M works. Actual usage was ~100M at idle, spiking during agent queries.

---

## SAP GenAI Hub / LLM

### 4. Old SDK deprecated — use Orchestration V2

`generative-ai-hub-sdk` is deprecated. Use `sap-ai-sdk-gen>=6.1.2` instead.

```python
from gen_ai_hub.orchestration_v2 import OrchestrationService
from gen_ai_hub.orchestration_v2.models.config import OrchestrationConfig, ModuleConfig
from gen_ai_hub.orchestration_v2.models.llm import LLMModuleConfig
from gen_ai_hub.orchestration_v2.models.template import Template, PromptTemplatingModuleConfig
from gen_ai_hub.orchestration_v2.models.data_masking import MaskingModuleConfig, MaskingProviderConfig, MaskingMethod, DPIStandardEntity, ProfileEntity
from gen_ai_hub.orchestration_v2.models.content_filter import InputFilteringConfig, OutputFilteringConfig, AzureContentSafety, AzureThreshold
```

The `OrchestrationService` auto-discovers from `AICORE_*` env vars — no manual model deployment needed.

### 5. Model names are vendor-prefixed on AI Core

On SAP AI Core, model names include a vendor prefix:
- `anthropic--claude-4.6-opus` (not `claude-opus-4-6`)
- `azure--gpt-4o` (not `gpt-4o`)

Set via `GENAI_MODEL_NAME` env var.

### 6. Server-side DPI masking info must be explicitly extracted

The Orchestration V2 response has masking details buried in:
```python
result = service.run(config=config)
# result.intermediate_results.input_masking  → GenericModuleResult
# result.intermediate_results.input_filtering → GenericModuleResult
# result.intermediate_results.output_filtering → GenericModuleResult
```

Each `GenericModuleResult` has `.message` (human-readable) and `.data` (structured). You must explicitly read these — they're not surfaced in the main response.

DPI masking supports 15 entity types: PERSON, ORG, EMAIL, PHONE, ADDRESS, USERNAME_PASSWORD, SAP_IDS_INTERNAL, SAP_IDS_PUBLIC, NATIONAL_ID, SSN, PASSPORT, DRIVING_LICENSE, IBAN, CREDIT_CARD_NUMBER, SENSITIVE_DATA.

### 7. Content filtering exceptions have no clean error structure

When content is blocked by Azure Content Safety filters, the SDK raises a generic exception. To detect it:
```python
try:
    result = service.run(config=config)
except Exception as exc:
    if "content_filter" in str(exc).lower() or "filtering" in str(exc).lower():
        # Blocked by content filter
    elif "masking" in str(exc).lower():
        # Blocked by masking
    else:
        raise
```

---

## Agent / LangGraph

### 8. LangGraph agents are stateless between invocations

Each call to `agent.stream({"messages": [...]})` starts fresh. To support follow-up questions ("Which of those have the best quality?"), the client must send the full conversation history:

```python
from langchain_core.messages import AIMessage, HumanMessage

messages = []
for m in history:
    if m["role"] == "assistant":
        messages.append(AIMessage(content=m["content"]))
    else:
        messages.append(HumanMessage(content=m["content"]))
messages.append(HumanMessage(content=current_question))
```

### 9. `agent.stream()` is synchronous — needs async bridge for SSE

LangGraph's `stream()` is a sync generator. To stream events via FastAPI's async `StreamingResponse`:

```python
import asyncio, queue

async def stream_events(agent, question):
    q = queue.Queue()
    loop = asyncio.get_event_loop()

    def run_sync():
        for step in agent.stream({"messages": msgs}, stream_mode="updates"):
            q.put(step)
        q.put(None)  # sentinel

    fut = loop.run_in_executor(None, run_sync)
    while True:
        event = await loop.run_in_executor(None, q.get)
        if event is None:
            break
        yield f"data: {json.dumps(event)}\n\n"
    await fut
```

### 10. History messages must be AIMessage, not raw dicts

LangGraph crashes if you pass `{"role": "assistant", "content": "..."}` as a history message. Must wrap as `AIMessage(content=...)`. Easy bug to miss because it only manifests with conversation history.

### 11. Graph edges not auto-extracted from agent tool results

Agent tools return **formatted text** (e.g., "## Vendor: Hokuyo...") not raw dicts. The edge extraction logic (`_extract_edges_from_result`) that works on router-mode raw dicts doesn't work on formatted text.

**Solution in V1:** Infer edges from tool semantics — e.g., `get_vendors_for_material(MAT-X)` returning VND-Y implies a `SUPPLIES` edge. Store tool call args alongside results, then map `(tool_name, args, result_ids) → edges`.

---

## UI / UX

### 12. Must stream intermediate agent steps — no silent waiting

Users saw "Thinking..." for 2+ minutes with zero feedback. SSE streaming of intermediate steps is essential.

**Event format used:**
```
data: {"event":"step","type":"reasoning","thought":"...","tool_calls":["search_entities"],"step_index":0}
data: {"event":"step","type":"tool_result","tool_name":"search_entities","result_preview":"...","step_index":1}
data: {"event":"answer","answer":"...","sources":[...],"trace":{...}}
data: {"event":"done"}
```

### 13. Graph panel must refresh per query, not accumulate

Accumulating nodes/edges across queries made the graph an unreadable mess after 2-3 queries. Each query should replace the graph entirely.

### 14. Need "New Chat" button

Users had to refresh the browser to start a new conversation. Need a button that clears messages, graph, and trace state.

### 15. Trace panel must show current query data

Without a clear refresh, users couldn't tell if the trace panel was showing data from the current or a previous query.

---

## Deployment

### 16. .cfignore is critical

Without `.cfignore`, CF uploaded 118M including `node_modules/` (104M alone). With proper exclusions, upload dropped to 360K.

Exclude: `node_modules/`, `ui/src/`, `tests/`, `docs/`, `ml/`, `seeds/`, `output/`, `.git/`, `*.ipynb`, `.env`.

### 17. CF python_buildpack needs requirements.txt

Even with `pyproject.toml`, the CF `python_buildpack` needs a `requirements.txt` to install dependencies. Use:
```
-e .[your-extras-here]
```
