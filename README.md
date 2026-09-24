# Job Hunting AI Agent (JobHunter)

Personal AI-assisted discovery, assessment, and application support for
international consulting and specialist opportunities aligned with a defined
professional profile and search strategy.

Governance and design authority:

- [AGENTS.md](AGENTS.md) — agent and engineering principles
- [docs/architecture.md](docs/architecture.md) — system architecture
- [docs/implementation-plan.md](docs/implementation-plan.md) — phased implementation plan

## Current scope (Bootcamp MVP)

Development follows the implementation plan incrementally. **Phase 0** provides
the repository and Python package foundation only. Domain logic, persistence,
source connectors, AI integration, and UI are introduced in later phases.

The Bootcamp MVP target is a single end-to-end vertical slice: one real source
through acquire → normalize → persist → filter → AI matching → rank → minimal
dashboard (Phases 0–10).

## Repository structure

```
job-hunting/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .env.example
├── docs/
├── src/jobhunter/          # importable package (src layout)
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── connectors/
│   ├── ai/
│   └── ui/
├── tests/
├── data/fixtures/
└── scripts/
```

## Local development

Requires **Python 3.11+**.

Create a virtual environment, install the package with development dependencies,
and copy environment placeholders:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Configuration is read from environment variables (see `.env.example`). Load
`.env` into your shell or use your IDE’s env-file support; the application does
not require a specific dotenv library in Phase 0.

Optional logging setup in code:

```python
from jobhunter.infrastructure.logging_config import configure_logging

configure_logging()
```

## Tests

```powershell
pytest
```

Verify import:

```powershell
python -c "import jobhunter; print(jobhunter.__version__)"
```
