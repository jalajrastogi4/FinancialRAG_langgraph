# Deep Finance Research Agent

A production-grade multi-agent LangGraph system for automated financial research and analysis using SEC filings and live market data.

## 🎯 Overview

Deep Finance Research Agent is an intelligent system that autonomously researches complex financial queries by:
- Breaking down questions into thematic research areas
- Deploying parallel researcher agents with tool budgets and rate limiting
- Retrieving data from SEC filings (10-K, 10-Q, 8-K) via hybrid search (dense + sparse embeddings)
- Fetching live market data through Yahoo Finance MCP integration
- Synthesizing comprehensive reports with verification and retry logic

## 🏗️ Architecture

```
User Query → Planner → Plan Writer → Fanout
                                        ↓
                            [Researcher 1, 2, 3...] (Parallel)
                                        ↓
                                    Verifier
                                    ↓     ↓
                            Retry Fanout  Editor → Final Report
```

### Key Components

- **Planner**: Analyzes query complexity and generates thematic research questions
- **Researcher Agents**: Execute focused research with tool budgets and rate limiting
- **Verifier**: Validates task completion and triggers retries for failures
- **Editor**: Synthesizes all research into a comprehensive final report

## 🚀 Features

### Production-Ready Capabilities
- ✅ **Parallel Execution**: Up to 3 concurrent researchers with configurable concurrency
- ✅ **Tool Budget Management**: Per-researcher budget enforcement (5 hybrid searches, 2 live queries)
- ✅ **Thread-Safe Rate Limiting**: Double-checked locking pattern for concurrent tool access
- ✅ **Retry Logic**: Automatic retry with exponential backoff (max 2 retries per theme)
- ✅ **Timeout Protection**: 300s timeout per research task with graceful degradation
- ✅ **State Persistence**: SQLite checkpointing for conversation continuity

### Observability & Monitoring
- ✅ **Langfuse Integration**: Full tracing across graph, nodes, agents, and tools
- ✅ **Structured Logging**: Context-aware logs with thread_id, user_id, theme_id
- ✅ **Error Tracking**: Comprehensive exception logging with stack traces
- ✅ **Routing Visibility**: Debug logs for all graph routing decisions

### Data Retrieval
- ✅ **Hybrid Search**: Combines dense (Gemini embeddings) + sparse (BM25) retrieval
- ✅ **Metadata Filtering**: LLM-powered filter extraction (company, year, quarter, doc type)
- ✅ **Live Market Data**: Yahoo Finance MCP for real-time stock prices and news
- ✅ **Document Processing**: Docling-based PDF → Markdown conversion with table/image extraction

## 📊 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Framework** | LangGraph (state machine), LangChain (agents) |
| **LLM** | Google Gemini 2.0 Flash |
| **Vector Store** | Qdrant Cloud (hybrid search) |
| **Embeddings** | Gemini Embedding 001 + BM25 |
| **Observability** | Langfuse (tracing), Loguru (logging) |
| **Persistence** | SQLite (checkpoints) |
| **External APIs** | Yahoo Finance MCP (live data) |

## 🛠️ Setup

### Prerequisites
- Python 3.10+
- Qdrant Cloud account
- Google AI API key
- Langfuse account (optional, for tracing)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd FinancialRAG_Project

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create `.envs/.env.local`:

```env
# Google AI
GOOGLE_API_KEY=your_google_api_key

# Qdrant
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_URL=https://your-cluster.qdrant.io

# Langfuse (optional)
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# Graph Configuration
MAX_PARALLEL_RESEARCHERS=3
HYBRID_SEARCH_TOOL_CALLS_PER_RESEARCHER=5
LIVE_FINANCE_RESEARCHER_TOOL_CALLS_PER_RESEARCHER=2
```

## 🎮 Usage

### Basic Example

```python
from graph.run import run_graph

run_graph(
    query="Analyze Amazon's financial performance in 2023 and 2024",
    thread_id="thread_001",
    user_id="user_001"
)
```

### Output Structure

```
agent_files/
└── user_001/
    └── thread_001/
        ├── research_plan.md          # Thematic questions
        ├── researcher/
        │   ├── a3f9c2_theme.md       # Theme 1 research
        │   ├── a3f9c2_sources.txt    # Theme 1 sources
        │   ├── b7e4d1_theme.md       # Theme 2 research
        │   └── ...
        └── report.md                  # Final synthesized report
```

## 📈 Performance Characteristics

- **Latency**: ~60-120s for complex queries (3-5 themes, parallel execution)
- **Throughput**: Handles 3 concurrent researchers per query
- **Cost**: ~$0.10-0.30 per complex query (Gemini Flash pricing)
- **Accuracy**: Hybrid search retrieval @ k=5 with metadata filtering

## 🔧 Configuration Options

### Graph Settings (`core/config.py`)

```python
MAX_RETRIES_PER_THEME = 2              # Retry failed research tasks
MAX_PARALLEL_RESEARCHERS = 3            # Concurrent researcher agents
MAX_RESEARCH_TASK_TIMEOUT_SEC = 300    # Timeout per researcher
HYBRID_SEARCH_TOOL_CALLS_PER_RESEARCHER = 5   # Budget per researcher
LIVE_FINANCE_RESEARCHER_TOOL_CALLS_PER_RESEARCHER = 2
```

### Rate Limiting

- **Hybrid Search**: 2 queries/second (configurable in `agents/researcher_agent.py`)
- **Live Finance**: 1 query/second (external API protection)

## 🧪 Example Queries

```python
# Historical financial analysis
"What were Apple's revenue trends across segments in 2022-2023?"

# Multi-company comparison
"Compare AWS vs Azure revenue growth in 2023"

# Live + historical hybrid
"Analyze Tesla's Q3 2024 performance vs historical trends"

# Complex multi-dimensional
"Evaluate Amazon's profitability metrics, cash flow, and segment performance in 2023-2024"
```

## 📁 Project Structure

```
FinancialRAG_Project/
├── agents/              # Agent definitions (researcher, editor)
├── core/                # Config, logging, observability
├── graph/               # LangGraph nodes, routing, state
│   └── nodes/           # Individual graph nodes
├── ingestion/           # PDF processing & Qdrant ingestion
├── persistence/         # Checkpoint management
├── prompts/             # System prompts for agents
├── tools/               # RAG tools, file tools, rate limiters
├── data/                # Processed markdown files
├── agent_files/         # Per-user/thread research outputs
└── results_outputs/     # Sample outputs for demonstration
```

## 🔍 Key Design Decisions

### 1. Tool Budget Scope
- **Per-Researcher Budgets**: Each parallel researcher gets independent budget allocation
- **Rationale**: Prevents one researcher from exhausting shared budget
- **Trade-off**: Total cost = per_researcher_budget × num_researchers

### 2. State Management
- **Merge Function**: Custom `merge_research_tasks` for parallel task updates
- **Immutable Budgets**: Budgets in config, not state (prevents mutation issues)
- **Thread Safety**: Double-checked locking for rate limiters

### 3. Error Handling
- **Graceful Degradation**: Researchers continue even if tools fail
- **Partial Failures**: Editor proceeds with available research
- **Comprehensive Logging**: Full stack traces + structured context

