# LoggerFlow Crew

LoggerFlow is a small demo project that shows how to build a pipeline of cooperating AI agents using CrewAI. The crew reads application logs, analyzes them with a generative model (Google Gemini in this project), and creates Jira tickets for detected incidents.

This README explains how to set up and run the project locally on macOS (tested with Python 3.12.12).

---

## Prerequisites

- macOS (you are on macOS in this workspace)
- Python 3.12.12 installed. This project was developed and tested with Python 3.12.12 — please use that version to avoid subtle incompatibilities with Pydantic / CrewAI.
- Git (to clone or fetch the repo)

---

## Quick project layout

```
logger_flow/
  README.md
  requirements.txt
  src/logger_flow/
    main.py            # entry point
    crew.py            # crew, agents and tasks
    tools/             # tools (log reader, Gemini analyser, Jira tool...)
    config/            # yaml files for agents & tasks
  logs/
    sample_app.log
  env/                 # (optional) virtualenv you may have created
  .venv/               # recommended venv location
```

---

## Steps for setting up the project locally

Important: use Python 3.12.12.

1. Create a virtual environment with Python 3.12.12 (example):

```bash
# If python3.12 points to your 3.12.12 binary
python3.12 -m venv .venv
# OR point directly to a specific binary if needed:
# /path/to/python3.12.12 -m venv .venv
```

2. Activate the virtual environment:

```bash
source .venv/bin/activate
```

3. Install dependencies from requirements.txt and (optionally) install the package in editable mode:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

4. Provide required credentials via environment variables (or a `.env` file). Example values the project expects:

```
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: override default Gemini model / endpoint
GEMINI_API_URL=https://api.generativeai.google/v1/models/YOUR_MODEL:generate

JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=your_jira_api_token

# Optional configuration
LOG_DIR=logs
```

Put the keys in your shell environment or create a `.env` file and load it (the project can use the env values directly).

5. Run the crew (recommended):

```bash
crewai run
```

Notes on runners: this repo may also be invoked with the `uv` runner. If you use `uv` and you see the warning about VIRTUAL_ENV not matching the project's `.venv`, prefer running `uv` with the `--active` flag to target the currently active environment:

```bash
uv run --active run_crew
```

If you prefer not to use the CLI runner you can run the module directly:

```bash
python -m logger_flow.main
```

---

## Common troubleshooting

- VENV mismatch warning
  - If you see a warning like:
    ````
    warning: `VIRTUAL_ENV=.../env` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
    ````
    it means the runner (uv/crewai) found a different virtual environment than the one you activated. Activate the same venv before running, or run `uv` with `--active`.

- Pydantic / model errors
  - If you see Pydantic errors complaining about non-annotated attributes or fields overridden without annotations, it usually means a class in tools was not annotated (use ClassVar for class-level constants) or different package versions are used between environments. Reinstall dependencies into the venv being used: `python -m pip install -e .`.

- API key errors
  - Make sure GEMINI_API_KEY and JIRA_API_TOKEN are set correctly and that the JIRA_BASE_URL is your Atlassian cloud base url (example: https://your-domain.atlassian.net).

---

## Useful URLs

- CrewAI docs: https://docs.crewai.com
- Jira Cloud: https://www.atlassian.com/software/jira
  - Jira API tokens: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/
- Google Generative AI (Gemini) docs: https://developers.generativeai.google

---

## Running tests (if present)

If you want to run unit tests (the project includes a `tests/` directory), run:

```bash
python -m pytest -q
```

---

## Quick commands summary

```bash
# create venv
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
# set env variables then run
crewai run
# or
python -m logger_flow.main
```

---

If anything here still looks wrong for your environment, tell me what OS/python binary you are using and I will tailor the steps exactly for that setup.


