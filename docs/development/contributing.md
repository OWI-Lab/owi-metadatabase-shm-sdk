# Contributing

## Development Setup

```bash
git clone https://github.com/OWI-Lab/owi-metadatabase-shm-sdk.git
cd owi-metadatabase-shm-sdk
uv sync --all-packages --all-extras --all-groups
```

## Code Style

The project uses **ruff** for formatting and linting (120-char lines) and
**ty** for type checking:

```bash
uv run inv qa.all
```

## Running Tests

```bash
uv run inv test.all
```

This runs pytest with coverage and doctests enabled.

## Pre-commit Hooks

Install the hooks once:

```bash
uv run pre-commit install
```

## Pull Request Workflow

1. Create a feature branch from `main`.
2. Make your changes with tests.
3. Ensure `uv run inv qa.all` and `uv run inv test.all` pass.
4. Execute both root notebooks with `uv run jupyter nbconvert --to notebook --execute ...`.
5. Open a PR against `main`.
