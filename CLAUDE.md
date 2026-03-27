# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project

GenAI Q&A backend for SAP procurement data. Provides natural-language querying over a procurement knowledge graph stored in SAP HANA Cloud, with answers generated via SAP GenAI Hub (AI Core Orchestration V2).

**This is a fresh rebuild** — see `LEARNINGS.md` for issues from V1 that should inform design decisions.

## Sibling Repos

| Repo | Purpose |
|------|---------|
| `procurement-data-generator` | Generates the procurement dataset (29 tables, ~10K rows) and deploys to HANA Cloud |
| `procurement-ui` | React frontend for chat, graph visualization, and trace display |

## Data Source: HANA Cloud

The backend queries data in HANA Cloud under the `PROCUREMENT` schema.

### Relational Tables (29)

See `docs/DATA_MODEL.md` for the full schema. Key tables:

| Domain | Tables |
|--------|--------|
| Org | company_code, purchasing_org, plant, cost_center |
| Master | material_master, vendor_master, contract_header, source_list |
| Transactional | po_header, po_line_item, gr_header, invoice_header, payment |

### Knowledge Graph Views

The graph workspace (`scripts/graph/create_graph_workspace.sql`) defines:

- **10 vertex views**: V_VENDOR, V_MATERIAL, V_PLANT, V_CATEGORY, V_PURCHASE_ORDER, V_CONTRACT, V_INVOICE, V_GOODS_RECEIPT, V_PAYMENT, V_PURCHASE_REQ
- **14 edge views**: E_SUPPLIES, E_ORDERED_FROM, E_CONTAINS_MATERIAL, E_UNDER_CONTRACT, E_INVOICED_FOR, E_RECEIVED_FOR, E_PAYS, E_BELONGS_TO_CATEGORY, E_CATEGORY_PARENT, E_LOCATED_AT, E_HAS_CONTRACT, E_REQUESTED_MATERIAL, E_INVOICED_BY_VENDOR, E_PAID_TO_VENDOR
- **Unified views**: V_ALL_VERTICES, E_ALL_EDGES
- **Graph workspace**: PROCUREMENT_KG

Entity ID prefixes: `VND-` (vendor), `MAT-` (material), `PO-` (purchase order), `CTR-` (contract), `INV-` (invoice), `GR-` (goods receipt), `PAY-` (payment), `PR-` (purchase requisition), plant codes (SG01, MY01, VN01), category codes (ELEC, MECH, etc.).

## SAP GenAI Hub (AI Core Orchestration V2)

**SDK**: `sap-ai-sdk-gen>=6.1.2` — uses `OrchestrationService` from `gen_ai_hub.orchestration_v2`

**Key imports:**
```python
from gen_ai_hub.orchestration_v2 import OrchestrationService
from gen_ai_hub.orchestration_v2.models.config import OrchestrationConfig, ModuleConfig
from gen_ai_hub.orchestration_v2.models.llm import LLMModuleConfig
from gen_ai_hub.orchestration_v2.models.template import Template, PromptTemplatingModuleConfig
from gen_ai_hub.orchestration_v2.models.data_masking import MaskingModuleConfig, MaskingProviderConfig, MaskingMethod, DPIStandardEntity, ProfileEntity
from gen_ai_hub.orchestration_v2.models.content_filter import InputFilteringConfig, OutputFilteringConfig, AzureContentSafety, AzureThreshold
```

**Model naming**: Vendor-prefixed on AI Core, e.g. `anthropic--claude-4.6-opus` (not `claude-opus-4-6`).

**No manual deployment needed** — `OrchestrationService` auto-discovers from `AICORE_*` env vars.

## Query Patterns

See `docs/GRAPHRAG_QUERY_PATTERNS.md` for all 22 router patterns and agent mode reference.

## Demo Scenarios

See `docs/DEMO_SCENARIOS.md` for 3 persona-driven storylines with step-by-step query sequences.

## Environment Variables

```bash
# Graph backend
GRAPH_BACKEND=hana          # or "networkx" for local dev with CSV

# HANA Cloud
HANA_HOST=                  # SQL endpoint (e.g. xxxx.hana.prod-ap10.hanacloud.ondemand.com)
HANA_PORT=443
HANA_USER=DBADMIN
HANA_PASSWORD=
HANA_SCHEMA=PROCUREMENT

# SAP GenAI Hub (AI Core)
AICORE_AUTH_URL=            # OAuth token URL from AI Core service key
AICORE_CLIENT_ID=           # OAuth client ID
AICORE_CLIENT_SECRET=       # OAuth client secret
AICORE_RESOURCE_GROUP=default
AICORE_BASE_URL=            # AI Core API base URL
GENAI_MODEL_NAME=anthropic--claude-4.6-opus  # Vendor-prefixed model name
```

## Cloud Foundry Deployment

```bash
# Build + deploy
bash scripts/deploy_to_cf.sh

# Set secrets (first deploy only)
cf set-env procurement-graphrag HANA_HOST <value>
cf set-env procurement-graphrag HANA_PASSWORD <value>
cf set-env procurement-graphrag AICORE_AUTH_URL <value>
cf set-env procurement-graphrag AICORE_CLIENT_ID <value>
cf set-env procurement-graphrag AICORE_CLIENT_SECRET <value>
cf set-env procurement-graphrag AICORE_BASE_URL <value>
cf set-env procurement-graphrag GENAI_MODEL_NAME anthropic--claude-4.6-opus
cf restage procurement-graphrag
```

**Memory**: 1024M minimum (512M causes OOM with LangGraph + LangChain + SDK).

## Graph Workspace Deployment

```bash
# Deploy vertex/edge views + GRAPH WORKSPACE to HANA Cloud
python scripts/graph/deploy_graph.py

# Preview only
python scripts/graph/deploy_graph.py --dry-run

# SQL-only (no graph engine needed)
python scripts/graph/deploy_graph.py --no-graph
```
