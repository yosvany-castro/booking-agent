# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a production-ready FastAPI template for building AI agent applications with **LangGraph** integration. It combines FastAPI for async REST APIs with LangGraph for stateful, multi-step AI agent workflows, along with comprehensive observability, persistence, and long-term memory capabilities.

## Essential Commands

### Development

```bash
# Install dependencies
make install

# Run server (choose environment)
make dev          # Development with hot reload
make staging      # Staging environment
make prod         # Production with uvloop

# Code quality
make lint         # Check code with ruff
make format       # Format code with ruff

# Clean up
make clean        # Remove venv and cache files
```

### Docker

```bash
# Build and run for specific environment
make docker-build-env ENV=development
make docker-run-env ENV=development
make docker-logs ENV=development
make docker-stop ENV=development

# Full stack (API + Prometheus + Grafana)
make docker-compose-up ENV=development
make docker-compose-down ENV=development
```

### Model Evaluation

```bash
# Run evaluations (see evals/ directory)
make eval ENV=development              # Interactive mode
make eval-quick ENV=development        # Quick mode with defaults
make eval-no-report ENV=development    # Skip report generation
```

### Testing

```bash
# Run tests (uses pytest)
pytest                    # All tests
pytest -m "not slow"      # Skip slow tests
pytest path/to/test.py    # Single test file
pytest -k test_name       # Specific test by name
```

## Architecture

### Core Application Flow

1. **Request Entry**: FastAPI endpoints in `app/api/v1/` receive requests
2. **Middleware Pipeline**:
   - `LoggingContextMiddleware` binds request context (request_id, session_id, user_id)
   - `MetricsMiddleware` tracks request metrics for Prometheus
   - Rate limiting via `slowapi` decorator on each endpoint
3. **LangGraph Agent Workflow**:
   - `LangGraphAgent` orchestrates multi-step AI workflows using StateGraph
   - States are persisted in PostgreSQL via `AsyncPostgresSaver`
   - LLM calls flow through `LLMService` with automatic retries and circular fallback
4. **Response**: Streaming or complete responses returned to client

### LangGraph State Management

The agent workflow uses a StateGraph with these key nodes:
- **chat node**: Main LLM interaction, decides whether to call tools or end
- **tool_call node**: Executes tools and returns results back to chat
- **State persistence**: Checkpointed in PostgreSQL for conversation continuity

State flows: `chat` → `tool_call` → `chat` → `END`

### LLM Service with Circular Fallback

`LLMService` (in `app/services/llm.py`) provides automatic retry and fallback:
1. Attempts call with current model (3 retries with exponential backoff)
2. On total failure, switches to next model in registry (circular)
3. Continues through all models until success or all fail
4. Models: gpt-5-mini, gpt-5, gpt-5-nano, gpt-4o, gpt-4o-mini

**Key insight**: This ensures high availability even when specific models are unavailable or rate-limited.

### Long-Term Memory System

Uses **mem0ai** with **pgvector** for semantic memory:
- Memories are automatically extracted from conversations
- Stored per user_id with vector embeddings
- Retrieved via semantic search during chat to provide context
- Updates happen in background (non-blocking) after response is sent

**Integration points**:
- Memory retrieval: Before LLM call in `_chat()` node
- Memory update: After response via `asyncio.create_task()`

### Authentication Flow

JWT-based authentication with session management:
1. User registers/logs in via `/api/v1/auth/login`
2. JWT token + session created and returned
3. Protected endpoints use `get_current_session` dependency
4. Session ID used for LangGraph thread persistence and logging context

### Environment-Specific Configuration

Uses environment files in priority order:
1. `.env.{environment}.local` (local overrides, gitignored)
2. `.env.{environment}` (development, staging, production)
3. `.env.local` (fallback local)
4. `.env` (fallback default)

Set environment via `APP_ENV=development|staging|production` or use Makefile commands.

## Key Patterns & Conventions

### Imports
**All imports must be at the top of the file** - never add imports inside functions or classes. This is a strict project rule.

### Logging
- Use structlog for all logging
- Event names: `lowercase_with_underscores`
- **Never use f-strings** in log events - pass variables as kwargs
- Always bind context: `logger.info("event", session_id=id, user_id=uid)`
- Use `logger.exception()` for exceptions (preserves tracebacks)

```python
# Correct
logger.info("user_login_successful", user_id=user.id, session_id=session.id)

# Wrong
logger.info(f"User {user.id} logged in")
```

### Retry Logic
Always use **tenacity** library for retries:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_external_api():
    ...
```

### Rate Limiting
All endpoints must have rate limiting decorators:

```python
@router.post("/chat")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat(request: Request, data: ChatRequest):
    ...
```

Rate limits are configured in settings per endpoint.

### LangGraph Integration
- Define state schemas with Pydantic models in `app/schemas/graph.py`
- Use `Command` objects to control flow between nodes
- Always include Langfuse `CallbackHandler` in config for observability
- Implement streaming with `astream(stream_mode="messages")`

### Database Operations
- All database operations must be async
- Use SQLModel for ORM (combines SQLAlchemy + Pydantic)
- Connection pooling is managed globally
- Health checks verify DB connectivity

### Error Handling
- Handle errors at beginning of functions (early returns)
- Use `HTTPException` with appropriate status codes
- Never swallow exceptions silently
- In production, log and degrade gracefully when possible

### Caching Strategy
**Only cache successful responses** - never cache errors. This is a strict rule to prevent propagating failures.

## Project Structure Deep Dive

```
app/
├── api/v1/              # API routes with rate limiting
│   ├── auth.py          # JWT authentication endpoints
│   ├── chatbot.py       # Chat endpoints (standard + streaming)
│   └── api.py           # Router aggregation
├── core/
│   ├── config.py        # Environment-specific config with .env loading
│   ├── logging.py       # Structlog setup with context binding
│   ├── metrics.py       # Prometheus metrics definitions
│   ├── middleware.py    # LoggingContext & Metrics middleware
│   ├── limiter.py       # Rate limiter configuration
│   ├── langgraph/
│   │   ├── graph.py     # LangGraphAgent class (main workflow)
│   │   └── tools/       # Agent tools (e.g., DuckDuckGo search)
│   └── prompts/
│       ├── __init__.py  # Prompt loader
│       └── system.md    # System prompts for agents
├── models/              # SQLModel database models (User, Session, Thread)
├── schemas/             # Pydantic schemas for API and graph state
│   ├── auth.py          # Auth request/response schemas
│   ├── chat.py          # Chat message schemas
│   └── graph.py         # GraphState definition for LangGraph
├── services/
│   ├── database.py      # Database service with async operations
│   └── llm.py           # LLMService with retry & circular fallback
├── utils/               # Utility functions for message processing
└── main.py              # FastAPI app entry with lifespan context
```

```
evals/                   # Model evaluation framework
├── evaluator.py         # Core evaluation logic
├── main.py              # CLI for running evaluations
├── helpers.py           # Utility functions
├── metrics/prompts/     # Evaluation criteria as .md files
└── reports/             # Generated JSON evaluation reports
```

## Important Implementation Details

### Lifespan Context
Use `@asynccontextmanager` for startup/shutdown (not `@app.on_event`):

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup")
    yield
    logger.info("application_shutdown")

app = FastAPI(lifespan=lifespan)
```

### LangGraph Checkpointing
- Uses `AsyncPostgresSaver` for state persistence
- Checkpoint tables: defined in `settings.CHECKPOINT_TABLES`
- Shared connection pool with main database
- Clear history: `DELETE FROM checkpoint_tables WHERE thread_id = ?`

### Streaming Responses
- Use `graph.astream(stream_mode="messages")` for token-level streaming
- Yield individual tokens via `AsyncGenerator[str, None]`
- Update memory in background after stream completes
- Use `sync_to_async` for getting final state snapshot

### Memory Updates
Memory updates are non-blocking:

```python
asyncio.create_task(
    self._update_long_term_memory(user_id, messages, metadata)
)
```

This prevents blocking the response while memories are being processed.

## Testing & Evaluation

### Running Tests
- Tests use pytest framework
- Markers: `@pytest.mark.slow` for long-running tests
- Test files: `test_*.py` or `*_test.py` pattern
- Use `httpx` for async HTTP testing

### Model Evaluation
- Custom metrics defined as markdown files in `evals/metrics/prompts/`
- Evaluator fetches traces from Langfuse
- Reports include success rates, metric performance, trace details
- Interactive CLI with rich formatting and progress bars

## Observability

### Langfuse Integration
All LLM operations are traced via Langfuse `CallbackHandler`:
- Passed in `config["callbacks"]` for graph execution
- Includes metadata: user_id, session_id, environment, debug flag
- Accessible at configured `LANGFUSE_HOST`

### Prometheus Metrics
Key metrics exported:
- HTTP request duration and count
- Rate limit hits
- LLM inference duration (labeled by model)
- Database health status

Access metrics at `/metrics` endpoint.

### Grafana Dashboards
Pre-configured dashboards for:
- API performance (latency, throughput)
- Rate limiting statistics
- Database performance
- System resource usage

Access Grafana at `http://localhost:3000` (default admin/admin).

## Security Considerations

- Never hardcode secrets - use environment variables
- JWT tokens expire per `ACCESS_TOKEN_EXPIRE_MINUTES`
- CORS configured via `settings.ALLOWED_ORIGINS`
- Input validation via Pydantic models on all endpoints
- Rate limiting protects against abuse
- Database queries use parameterized statements (SQLModel ORM)

## Common Pitfalls to Avoid

1. **Don't use blocking I/O** - everything must be async
2. **Don't skip rate limiting** on new endpoints
3. **Don't use f-strings in logs** - breaks structured logging filters
4. **Don't cache errors** - only cache successful responses
5. **Don't forget Langfuse callbacks** - required for LLM observability
6. **Don't modify state directly** - use Command objects in LangGraph
7. **Don't add imports inside functions** - strict top-of-file rule

## Dependencies Reference

Core stack:
- **FastAPI** - Web framework with async support
- **LangGraph** - Agent workflow orchestration with state graphs
- **LangChain** - LLM abstraction and tools
- **Langfuse** - LLM observability and tracing
- **mem0ai** - Long-term memory with semantic search
- **PostgreSQL + pgvector** - Database and vector storage
- **SQLModel** - ORM combining SQLAlchemy + Pydantic
- **structlog** - Structured logging
- **tenacity** - Retry logic with exponential backoff
- **slowapi** - Rate limiting
- **prometheus-client** - Metrics collection
- **uvloop** - High-performance event loop (production)

Refer to `pyproject.toml` for complete dependency list and versions.
