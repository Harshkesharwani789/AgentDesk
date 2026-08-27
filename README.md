# AgentDesk

> **AI-Powered Customer Support Resolution Platform** — Go beyond answering questions. Resolve tickets end-to-end.

[![CI](https://github.com/Harshkesharwani789/AgentDesk/actions/workflows/ci.yml/badge.svg)](https://github.com/Harshkesharwani789/AgentDesk/actions)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-agent-purple.svg)

---

## 🎯 What is AgentDesk?

**AgentDesk** is an intelligent customer-support resolution system that combines a **hybrid-retrieval RAG copilot** (semantic + BM25 + cross-encoder reranking, with citations) with a **LangGraph resolution agent** capable of:

- 🔍 Looking up order statuses
- ❌ Cancelling orders
- 💰 Processing refunds with **human-in-the-loop approval** for amounts above a configurable threshold
- 🚨 Escalating to human agents when needed
- 📚 Answering knowledge-base questions with grounded citations

The human-approval gate uses `langgraph.interrupt()` with `SqliteSaver` checkpointing — the graph **literally cannot proceed** without a recorded human decision, and approvals survive process restarts.

---

## 📊 Results at a Glance

### Agent Performance (30 Scripted Scenarios)

Full table + failure analysis: [`results/agent_eval.md`](results/agent_eval.md)

| Metric | Value |
|---|---|
| Task Success Rate | **97%** (29/30) |
| Tool-Call Accuracy | 93% |
| Escalation Correctness | 97% |
| Grounded-Citation Rate | 75% |
| Avg Reply-Quality Score | 3.40 / 5 |

### Retrieval Quality (RAGAS)

Full table: [`results/ragas.md`](results/ragas.md)

| Mode | Reranker | Faithfulness | Answer Relevancy | Context Precision | Context Recall |
|---|---|---|---|---|---|
| semantic | ✗ | 0.85 | 0.70 | 0.90 | 0.84 |
| hybrid | ✗ | 0.86 | 0.70 | 0.93 | 0.85 |
| hybrid | ✓ | 0.82 | 0.55 | **1.00** | 0.87 |

> **Note:** Adding the reranker raises context precision to a perfect 1.00 but slightly lowers faithfulness — reranking optimizes *which* chunks get retrieved, not what the LLM does with them.

---

## 🏗️ Architecture

```text
                    User (Web UI at /, or POST /chat directly)
                                      |
                                      v
                    +--------------------------------------+
                    |       LangGraph Resolution Agent       |
                    |  understand -> ask | act(<=4) -> guard  |
                    |         -> respond | escalate           |
                    |  brain: Groq llama-3.3-70b-versatile    |
                    |  fallback: Gemini (logged failover)     |
                    +---------------+----------------------+-+
                                    |                       |
                    +---------------v------+   +------------v-----------+
                    | kb_search             |   | order_lookup            |
                    | (hybrid + rerank      |   | cancel_order            |
                    | retrieval pipeline)   |   | refund_initiate*         |
                    +---------------+------+   | escalate_to_human        |
                                    |          +------------+-----------+
                                    v                        v
                    +--------------------------+   +------------------------+
                    | Retrieval Layer           |   | Order Management        |
                    | Chroma + BGE embeddings   |   | SQLite + SQLAlchemy     |
                    | BM25 + RRF + reranker     |   | Seeded, 5% failures     |
                    +--------------------------+   +------------------------+

  * refund above config.agent.refund_approval_cap -> interrupt() -> checkpointed
    -> GET/POST /approvals -> approve/reject -> graph resumes from checkpoint
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Groq API key (required)
- Gemini API key (required for agent fallback + eval harness)

### Installation

```bash
# Clone the repository
git clone https://github.com/Harshkesharwani789/AgentDesk.git
cd AgentDesk

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
PYTHONPATH=src pip install --no-cache-dir -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY and GEMINI_API_KEY

# Build retrieval index (~10 min, one-time)
PYTHONPATH=src python scripts/build_index.py

# Start the server
PYTHONPATH=src python scripts/run_api.py
```

Open `http://localhost:8000` for the web UI with **Ask** and **Resolve** tabs.

---

## 💡 Usage Examples

### Copilot Flow (Ask Tab — `POST /query`)

Ask a support question → hybrid retrieval + rerank → grounded answer with citations.

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I cancel my order?", "mode": "hybrid", "use_reranker": true}'
```

### Resolution Flow (Resolve Tab — `POST /chat`)

Describe what you need → agent classifies intent, calls tools, and resolves.

```bash
# Check order status
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What'\''s the status of order 5?"}'

# Process a refund (auto-approved if below cap)
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Refund order 8, it arrived damaged"}'

# Manage approvals
curl http://127.0.0.1:8000/approvals
curl -X POST http://127.0.0.1:8000/approvals/<approval_id> \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

---

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| **Language** | Python 3.12 |
| **Backend** | FastAPI (`/query`, `/chat`, `/approvals`) |
| **Frontend** | Vanilla HTML/CSS/JS — no React/Gradio/Streamlit |
| **Agent** | LangGraph (StateGraph, interrupt/Command, SqliteSaver) |
| **Retrieval** | BAAI/bge-small-en-v1.5 + ChromaDB, BM25, RRF, cross-encoder reranker |
| **LLMs** | Groq llama-3.3-70b (agent + RAG), Gemini flash-lite (fallback) |
| **Database** | SQLAlchemy + SQLite |
| **Evaluation** | RAGAS (retrieval) + custom scenario harness (agent) |
| **CI/CD** | GitHub Actions, Docker, Render |

---

## 📁 Project Structure

```text
AgentDesk/
├── config/agentdesk.yaml         # Single source of config
├── data/raw/                     # Bitext support dataset
├── evals/                        # 30-scenario agent eval harness
├── results/                      # Generated eval results (never hand-written)
├── scripts/                      # Build index, seed orders, run API, run evals
├── src/agentdesk/
│   ├── agent/                    # LangGraph graph, tools, prompts, runtime
│   ├── orders/                   # SQLAlchemy models, DB session, seed, client
│   ├── llm/                      # Unified Groq+Gemini client, dev cache
│   ├── api/                      # FastAPI app + static UI mount
│   ├── ingestion/                # Data ingestion pipeline
│   ├── retrieval/                # Hybrid RAG stack
│   ├── generation/               # Response generation
│   └── webui/static/             # Hand-built frontend
├── tests/                        # Unit & integration tests
├── Dockerfile
├── render.yaml
└── requirements.txt
```

---

## 🧪 Testing

```bash
# Fast deterministic tests (no model downloads needed)
PYTHONPATH=src python -m pytest tests/ -m "not requires_index" -q

# Full test suite (needs built index)
PYTHONPATH=src python -m pytest tests/ -q

# Run retrieval evaluation
PYTHONPATH=src python scripts/run_evaluation.py

# Run 30-scenario agent evaluation
PYTHONPATH=src:. python scripts/run_agent_evals.py
```

### Key Test Files

| Test | What it proves |
|---|---|
| `test_agent_restart_resume.py` | Approval interrupt survives process restart |
| `test_orders_idempotency.py` | Duplicate refund calls produce exactly one refund |
| `test_agent_tools.py` | Tool-level coverage (cancel, refund, escalate, kb) |
| `test_agent_graph.py` | Graph-level flow coverage |
| `test_hybrid.py` | RRF ordering correctness |

---

## 🎨 Design Decisions

- **Hand-built frontend** — Full API decoupling, no build step, no extra runtime dependency
- **LangGraph over hand-rolled agent** — Explicit, testable routing; each node independently unit-testable
- **SQLite for everything** — Zero external infra for portfolio deployment; swap boundary already defined
- **Code-enforced approval gate** — `interrupt()` makes it impossible to bypass, unlike prompt-only guardrails
- **Three distinct eval models** — No model grades its own homework; task success is a direct DB assertion
- **Dedicated eval API key** — Prevents eval batches from exhausting the live demo's daily quota

---

## ⚠️ Limitations

- Knowledge base uses the public Bitext benchmark dataset (not proprietary data)
- Render free tier: ephemeral filesystem loses DB on restart (fine for demo, reseeds automatically)
- Groq free tier: 100k tokens/day for 70b model; dedicated eval key mitigates
- Not currently deployed (exceeds 512MB RAM cap on Render free tier)
- No authentication on endpoints (acceptable for portfolio demo)
- Cold Docker builds are slow (~10 min for index baking)

---

## 🔮 Future Improvements

- [ ] Persistent disk / Postgres for orders + checkpoints
- [ ] Auth + rate limiting on `/chat` and `/approvals`
- [ ] OpenTelemetry tracing for agent tool calls
- [ ] Interactive eval dashboard (replacing static markdown tables)
- [ ] Streaming responses for real-time UX
- [ ] Multi-tenant support with isolated agent sessions

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ by Harsh using LangGraph, FastAPI, and hybrid RAG
</p>
