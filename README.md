# ✈️ WanderBot — Multi-Agent Travel Orchestrator (LangGraph + MCP)

> A **supervisor-driven multi-agent** travel planner built with **LangGraph**. Specialist agents fetch live data through **MCP (Model Context Protocol)** servers — including a **custom Weather MCP server** — and a **human-in-the-loop** step lets the user approve or revise the itinerary before it is finalised.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-1C3C3C)
![MCP](https://img.shields.io/badge/MCP-FastMCP-6E56CF)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Checkpointer-316192?logo=postgresql&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-gpt--oss--20b-F55036)

<!-- TODO: add a screenshot/GIF of the UI: query → draft itinerary → approve → final plan -->

---

## ✨ Highlights

- 🧭 **Supervisor agent** – reads the request, extracts **trip constraints** (destination, origin, duration, budget, style) and **dynamically selects** only the specialist agents needed.
- 🛡️ **Input guardrail** – blocks non-travel / harmful requests before any tool is called (fails open on parser errors so valid requests are never lost).
- 🔌 **MCP-based tools** – Tavily (remote), AviationStack (stdio) and a **custom FastMCP weather server**, all loaded through `langchain-mcp-adapters`' **`MultiServerMCPClient`**.
- 🙋 **Human-in-the-Loop (HITL)** – the graph **pauses with `interrupt()`**; the user approves or sends feedback, and the run **resumes with `Command(resume=...)`**.
- 💾 **Persistent state** – **PostgreSQL checkpointer (`PostgresSaver`)** keyed by `thread_id`, so a paused plan survives restarts.
- 🧩 **Graceful degradation** – every MCP call is wrapped; if a live tool fails, the agent falls back to clearly-labelled general guidance instead of crashing.
- 🔭 **Observability** – **LangSmith** tracing hooks included.

---

## 🏗️ System Architecture

![WanderBot system architecture](assets/architecture.png)

## 🧠 Agent Workflow (LangGraph)

![WanderBot LangGraph agent workflow](assets/agent-workflow.png)

> Agents are visited in a fixed order (`flight → hotel → weather → budget → itinerary`), but the **supervisor decides which ones run** — e.g. a "weather in Goa in July?" query skips flights, hotels and budget. The **itinerary agent always runs**.

---

## 🔄 From Python Functions to MCP Tools

WanderBot was built in two stages — a good example of refactoring toward a **standard tool protocol**:

![From Python functions to MCP tools](assets/functions-to-mcp.png)

| | Stage 1 – Functions | Stage 2 – MCP |
|---|---|---|
| Tool access | Imported Python functions | Discovered at runtime via **MCP** (`client.get_tools()`) |
| Coupling | Agent code tied to each API client | Agent only knows **tool name + arguments** |
| Reuse | Project-only | Any MCP-compatible client can reuse the servers |
| Transports | n/a | **HTTP** (Tavily), **stdio** (Aviation, Weather) |

The LangGraph **node signatures did not change** — only the tool layer behind them did, which is exactly the benefit MCP is meant to deliver.

---

## 🤖 Agents & Tools

| Agent | What it does | Tools / MCP |
|---|---|---|
| 🧭 **Supervisor** | Input **guardrail**, JSON-based **routing**, trip-constraint extraction. Falls back to the full pipeline if parsing fails. | LLM |
| ✈️ **Flight Agent** | Fetches airport and airline reference data, then asks the LLM for likely route, airlines, duration, fare range and booking advice. | `aviationstack` MCP → `list_airports`, `list_airlines` |
| 🏨 **Hotel Agent** | Live search for hotels / neighbourhoods. | `tavily` MCP → `tavily_search` |
| 🌦️ **Weather Agent** | LLM extracts the destination city, then pulls **current weather + forecast**. | **Custom** `weather` MCP → `get_current_weather`, `get_forecast` |
| 💰 **Budget Agent** | Cost categories, risk areas, saving tips, feasibility. | LLM |
| 🗺️ **Itinerary Agent** | Merges all results into a **draft** day-by-day plan. | LLM |
| 🙋 **Human Approval** | Pauses the graph and waits for approve / feedback. | LangGraph `interrupt()` |
| ✅ **Final Agent** | Produces the polished response (Trip Summary, Flights, Hotels, Weather, Itinerary, Budget, Recommendations). | LLM |

### 🛠️ Custom Weather MCP Server
`custom_weather_mcp_server.py` is built with **FastMCP** and exposes two tools over **stdio**:

| Tool | Returns |
|---|---|
| `get_current_weather(city)` | temperature, feels-like, humidity, condition, wind speed |
| `get_forecast(city)` | next five 3-hour forecast entries (time, temp, condition) |

It is launched automatically as a subprocess by `mcp_client.py`.

---

## 🔌 API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Web UI |
| `POST` | `/api/travel` | Start a run `{ "message": "...", "thread_id": null }` → returns draft itinerary + `requires_approval: true` |
| `POST` | `/api/travel/approve` | Resume a paused run `{ "thread_id": "...", "approved": true/false, "feedback": "..." }` |
| `GET` | `/health` | Health check |

**Human-in-the-loop flow**
```
POST /api/travel          →  draft itinerary + thread_id  (graph paused)
POST /api/travel/approve  →  { approved: false, feedback: "make it cheaper" }
                          →  final plan with feedback applied
```

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | **LangGraph** (`StateGraph`, conditional edges, `interrupt`, `Command`) |
| LLM | **Groq** · `openai/gpt-oss-20b` via `langchain-groq` |
| Tool protocol | **MCP** · `FastMCP`, `langchain-mcp-adapters` (`MultiServerMCPClient`) |
| External data | Tavily · AviationStack · OpenWeatherMap |
| Backend | **FastAPI**, Uvicorn, Pydantic, `nest_asyncio` |
| State / persistence | **PostgreSQL** + `langgraph-checkpoint-postgres` |
| Frontend | Jinja2 templates + static HTML/CSS/JS |
| Observability | LangSmith |

## 📁 Project Structure
```
├── app.py                         # FastAPI app + REST endpoints
├── backend.py                     # LangGraph graph: supervisor, agents, HITL, checkpointer
├── mcp_client.py                  # MultiServerMCPClient + async MCP helper functions
├── custom_weather_mcp_server.py   # Custom FastMCP weather server (stdio)
├── tools/                         # Original function-based tools (Stage 1)
├── templates/  static/            # Web UI
├── test.py  mcp_version_test.py   # Experiments / MCP checks
└── requirements.txt
```

---

## 🚀 Getting Started

**Prerequisites:** Python 3.11, a running **PostgreSQL** instance, [`uv`](https://docs.astral.sh/uv/) (provides `uvx` for the Aviation MCP server).

```bash
git clone https://github.com/saichavan10/WanderBot-AI-Enterprise-Multi-Agent-Travel-Orchestrator.git
cd WanderBot-AI-Enterprise-Multi-Agent-Travel-Orchestrator

conda create -n travel python=3.11 -y
conda activate travel
pip install -r requirements.txt
```

Create a `.env` file (never commit it):

```env
GROQ_API_KEY=...
TAVILY_API_KEY=...
AVIATIONSTACK_API_KEY=...
OPENWEATHER_API_KEY=...
DATABASE_URL=postgresql://user:password@localhost:5432/wanderbot
LANGSMITH_API_KEY=...        # optional – tracing
```

Run:

```bash
python app.py
```
Open **http://127.0.0.1:8000**

---

## ⚠️ Known Limitations
- Flight data is **airport/airline reference data** — the app does **not** return live ticket prices and says so in its output.
- Agents run **sequentially**; flight/hotel/weather could be parallelised for lower latency.
- Free-tier APIs are rate-limited.

## 🗺️ Roadmap
- Run independent agents **in parallel** (LangGraph fan-out)
- **Streaming** responses to the UI
- Run MCP servers as **remote HTTP services** instead of local subprocesses
- Dockerise (app + Postgres via Docker Compose) and add CI
- Unit tests for the supervisor's routing and guardrail

## 👤 Author
**Saish Chavan** · [LinkedIn](https://www.linkedin.com/in/saish-chavan) · saishchavan154@gmail.com