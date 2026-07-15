# Backend — AI Command Center

FastAPI-based backend for the 8-agent orchestration system.

## Directory Structure

```
backend/
├── src/
│   ├── main.py              # FastAPI app initialization
│   ├── api/                 # API routes
│   │   └── routes.py        # Endpoints: /, /api/execute, /api/history
│   ├── core/                # Configuration & middleware
│   │   ├── config.py        # Env vars, logging setup
│   │   ├── constants.py     # Agent prompts, metadata
│   │   └── middleware.py    # Security headers, CORS
│   ├── services/            # Business logic
│   │   ├── llm.py           # NVIDIA NIM API wrapper
│   │   ├── drive.py         # Google Drive integration
│   │   ├── logging.py       # JSON log + JSON extraction
│   │   └── orchestrator.py  # Task execution logic
│   ├── schemas/             # Pydantic models
│   │   └── models.py        # UserInput, ExecuteResponse, etc.
│   └── agents/              # Agent system (future expansion)
├── tests/                   # pytest unit tests
├── requirements.txt         # Python dependencies
└── Dockerfile               # Container build
```

## Running Locally

### Prerequisites
- Python 3.10+
- NVIDIA NIM API key
- Google Drive setup (optional)

### Installation

```bash
cd backend
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` from root and fill in your credentials:

```bash
cp ../.env.example ../.env
# Edit .env with your NVIDIA_NIM_API_KEY, GAS_WEB_APP_URL, and FOLDER_IDs
```

### Start Server

```bash
# From backend/ directory
python -m src.main

# Or using uvicorn directly
uvicorn src.main:app --reload --port 7860
```

Dashboard will be available at `http://localhost:7860`

## Running Tests

```bash
pytest tests/ -v
```

## Docker

```bash
docker build -t ai-command-center .
docker run -p 7860:7860 --env-file ../.env ai-command-center
```

## Key Modules

### `src/core/config.py`
- Loads environment variables
- Sets up logging
- Verifies required configs at startup

### `src/core/constants.py`
- `AGENT_PROMPTS`: System prompts for Claudia + 7 specialists
- `AGENTS`: Agent metadata (roles, folder keys)
- `SPECIALIST_AGENTS`: List of specialist agents (excludes Claudia)

### `src/services/orchestrator.py`
- Main execution flow for `/api/execute` endpoint
- Claudia decision parsing
- Agent task delegation & execution

### `src/services/logging.py`
- `extract_json()`: Robust JSON parsing from LLM responses
- `add_json_log()`: Append to daily activity log

## Future Improvements

- [ ] Async task execution (currently sequential)
- [ ] Agent class abstraction for better extensibility
- [ ] Specialist agent files (zara.py, maya.py, etc.)
- [ ] Request/response caching
- [ ] Agent performance metrics
- [ ] Rate limiting & retry logic
