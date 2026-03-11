# installation-and-packaging

Installation and packaging workflows for Project Lumina.

Before running live LLM mode, configure runtime secrets and environment settings: [secrets-and-runtime-config](../8-admin/secrets-and-runtime-config.md).

## Requirements files workflow (pip)

Runtime dependencies:

```bash
pip install -r requirements.txt
```

Runtime + development dependencies (includes spaCy for NLP):

```bash
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm
```

## One-liner developer setup (uv)

```bash
uv venv && uv pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm
```

## Editable install (pyproject)

Use editable install when you want command entrypoints and local package iteration.

```bash
# Minimal (FastAPI + uvicorn only)
python -m pip install -e .

# With NLP support (spaCy glossary detection)
python -m pip install -e ".[nlp]"
python -m spacy download en_core_web_sm

# With LLM providers (OpenAI + Anthropic)
python -m pip install -e ".[providers]"

# With SQLite persistence backend
python -m pip install -e ".[sqlite]"

# Full — all extras
python -m pip install -e ".[nlp,providers,sqlite]"

# uv equivalents (prefix with `uv pip`)
uv pip install -e ".[nlp,providers,sqlite]"
```

### Optional extras

| Extra | Installs | When needed |
|-------|----------|-------------|
| `nlp` | `spacy>=3.7.0` | Glossary-term detection in turn data |
| `providers` | `openai`, `anthropic` | Live LLM mode |
| `sqlite` | `sqlalchemy[asyncio]`, `aiosqlite` | SQLite persistence backend |
| `dev` | `pytest`, `pytest-cov` | Running the test suite |

## CLI entrypoints

Available after editable install:

```bash
lumina-api                # start the FastAPI server
lumina-verify             # repo integrity check
lumina-orchestrator-demo  # run the deterministic orchestrator demo
lumina-ctl-validate       # validate a CTL commitment record
lumina-security-freeze    # check for exposed secrets / security hygiene
lumina-yaml-convert       # convert YAML files to JSON
```
