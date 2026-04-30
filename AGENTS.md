# Repository Guidelines

## Project Structure & Module Organization
- Source code lives in `src/` (e.g., `src/core/`, `src/rag_store/`, `src/services/`, `src/config/`).
- Entry points: `main.py` (CLI) and `src/app.py` (app orchestration).
- Tests mirror source layout in `tests/` (e.g., `tests/test_core/`, `tests/test_rag_store/`).
- Supporting assets: `data/`, `docs/`, `setup_chromadb/` (ChromaDB scripts), `docker_deployment/`.

## Build, Test, and Development Commands
- Install deps: `uv sync` (add `--group dev` for dev tools).
- Run app: `uv run python main.py`.
- Run tests: `uv run pytest` (verbose: `-v`).
- Coverage report: `uv run pytest --cov=src --cov-report=html` → open `htmlcov/index.html`.
- Security checks: `uv run bandit -r src/`; `uv run safety scan`.
- ChromaDB server (optional): `./setup_chromadb/chromadb-server.sh start|stop|status|logs`.

## Coding Style & Naming Conventions
- Python 3.12; 4‑space indentation; line length 100–120.
- Use type hints and docstrings for public APIs.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Prefer pure functions and small units; clear error handling via `src/services/error_handler.py` and structured logging.
- Secrets via environment variables; never hard‑code keys.

## Testing Guidelines
- Framework: `pytest` with markers (`unit`, `integration`, `rag`, `docker`, `slow`).
- Layout mirrors `src/`; test files named `test_*.py`.
- Coverage: project minimum 85% (configured in `pyproject.toml`). Aim ≥85% per file for new/changed code.
- Run focused tests: `uv run pytest tests/test_core/test_file_processor.py::TestClass::test_case -v`.

## Commit & Pull Request Guidelines
- Conventional commits: `type(scope): description` (e.g., `feat(rag): add DOCX processing`).
- Branch names: `feature/...`, `fix/...`, `docs/...`, `refactor/...`, `test/...`.
- PRs must: pass all tests, meet coverage gates, include clear description, reference issues, and update docs as needed (screenshots/logs when UX or behavior changes).

## Security & Configuration Tips
- Copy `.env.example` → `.env`; do not commit secrets. Key vars: `SOURCE_FOLDER`, `SAVED_FOLDER`, `ERROR_FOLDER`, `ENABLE_DOCUMENT_PROCESSING`, `MODEL_VENDOR`, `CHROMA_*`, API keys.
- Optional system deps for RAG/OCR: Tesseract, LibreOffice.

## Architecture Overview
- Config: `src/config/config_manager.py` loads and validates env, including ChromaDB client/server modes.
- Orchestration: `src/app.py` wires config, logging, error handling, processor, and monitor.
- Core: `src/core/file_monitor.py` (watchdog events), `src/core/file_processor.py` (retry, routing), `src/core/file_manager.py` (moves, structure preservation).
- RAG Store: `src/rag_store/` processors (`pdf_processor.py`, `office_processor.py`, `mht_processor.py`, `text_processor.py`) and storage (`store_embeddings.py`).
- Services: `src/services/logger_service.py` (structured logging), `src/services/error_handler.py` (error logs, context).
- Flow: monitor → processor → move to `SAVED_FOLDER` or `ERROR_FOLDER` with logs and cleanup.

## Agent-Specific Instructions
- Keep changes scoped; follow existing module boundaries and patterns.
- Update or add matching tests in `tests/` for any behavior change.
- Do not lower coverage thresholds or bypass security checks.
- Prefer minimal diffs; avoid unrelated refactors.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **kiro_project** (3656 symbols, 6273 relationships, 101 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/kiro_project/context` | Codebase overview, check index freshness |
| `gitnexus://repo/kiro_project/clusters` | All functional areas |
| `gitnexus://repo/kiro_project/processes` | All execution flows |
| `gitnexus://repo/kiro_project/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
