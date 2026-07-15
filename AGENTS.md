# Repository Guidelines

## Project Structure & Module Organization

Core Python code lives in `src/`. The stage-based workflow is under `src/pipeline/`, multi-source adapters under `src/sources/`, LLM integrations under `src/summarizer/`, and output, analysis, notification, and web components in their corresponding packages. `main.py` runs the processing pipeline; `scheduler.py` provides source-specific execution. Flask templates and browser assets live in `src/web/templates/` and `static/`. Tests are in `test/`, documentation in `docs/`, deployment scripts and systemd units in `deploy/`, and generated reports or analysis artifacts in `data/`.

## Build, Test, and Development Commands

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv venv
uv pip install -r requirements.txt
```

Run `python main.py` for a single pipeline execution. Run `python scheduler.py` to start APScheduler using `config/config.yaml`. Start the local web interface with `python src/web/app.py`. Execute the full test suite with `python -m unittest discover -s test -p "test_*.py"`; run one module with `python -m unittest test.test_pipeline`. Use `pyright` for the configured static type check when available.

## Coding Style & Naming Conventions

Follow standard Python conventions: four-space indentation, `snake_case` for functions and modules, `PascalCase` for classes, and uppercase names for constants. Keep pipeline stages small and expose a clear `run(context)` entry point. Prefer type hints and focused docstrings for public or non-obvious behavior. Use UTF-8 for bilingual content. Do not commit `.env`, logs, caches, virtual environments, or transient generated files.

## Testing Guidelines

Tests use Python's `unittest` framework and `unittest.mock`. Name files `test_<feature>.py`, classes `<Feature>Tests`, and methods `test_<expected_behavior>`. Mock network and LLM calls; tests should be deterministic and must not require API credentials. Add regression coverage for source normalization, pipeline stage ordering, configuration fallbacks, and exported schemas when those areas change.

## Commit & Pull Request Guidelines

Recent history follows Conventional Commit prefixes, especially `feat:` and `fix:` (for example, `feat: add openalex search adapter`). Write imperative, narrowly scoped subjects. Pull requests should summarize the behavior change, list verification commands, note configuration or schema changes, and link relevant issues. Include screenshots for web UI changes and sample output for report-format changes; never include secrets or real credentials.

## Configuration & Security

Copy `.env.example` to `.env` and keep secrets local. Make portable defaults in `config/config.yaml`, document new source keys in `docs/source_config_guide.md`, and avoid committing machine-specific paths. Keep the product scope on Chinese energy policy, domestic energy information collection, and agents operating physical energy systems; do not broaden it to robot arms or general-purpose robotics.
