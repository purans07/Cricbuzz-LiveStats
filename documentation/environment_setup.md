# Installation and environment

> Current status (2026-10-29): PostgreSQL/MySQL support and fresh quota/history verification are completed within the tested scope. See [remaining requirements completion](remaining_requirements_completion.md). Older phase checkpoints below are historical; the assignment deadline remains unverified.

## Requirements

The verified local environment uses Python 3.13.5, SQLite 3.50.2 and macOS. Other operating systems/interpreter versions have not been accepted. Run commands from the project root. Internet access is needed to install packages; the sample dashboard then runs without API access.

```sh
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip check
```

The lock captures runtime and development versions; it is not a hash-verified cross-platform guarantee. Direct dependencies are in requirements.txt and requirements-dev.txt. Keep the environment outside source control.

## Initialize and launch

For a new sample target:

```sh
APP_ACCESS_MODE=local .venv/bin/python -m database.initialize --mode sample --database data/runtime/sample.db --seed-sample
```

For an existing sample, inspect without reseeding:

```sh
.venv/bin/python -m database.initialize --mode sample --database data/runtime/sample.db --check
```

Launch with explicit settings so an existing private .env cannot select the live target:

```sh
DATA_MODE=sample DATABASE_URL=sqlite:///data/runtime/sample.db APP_ACCESS_MODE=local .venv/bin/python -m streamlit run main.py --server.address 127.0.0.1
```

Open [localhost:8501](http://127.0.0.1:8501); stop with Ctrl+C. If the port is occupied, append `--server.port 8503` and open that port.

## Configuration

Sample mode requires no .env. Optional .env.example values may be copied into a private .env; do not overwrite an existing private file. Process environment overrides .env. Implemented settings are DATA_MODE, DATABASE_URL, DISPLAY_TIMEZONE and APP_ACCESS_MODE; API configuration uses a separate reviewed manifest and private CRICBUZZ_API_KEY. Relative database paths resolve from the project root. Only persistent local SQLite file URLs are supported.

APP_ACCESS_MODE=local permits trusted administration. public_readonly disables administrative writes and custom SQL but is not authentication. Session timezone changes affect display only. The current API loader reads .env/process environment, not Streamlit st.secrets.

## Verification and next steps

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

Continue with the [user guide](user_guide.md), [API setup](api_setup.md) or [deployment guide](16_deployment.md). Installation does not publish the application.
