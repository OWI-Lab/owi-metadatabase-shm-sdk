# Testing

## Running the Test Suite

```bash
uv run inv test.all
```

This command runs:

| Step | Description |
|------|-------------|
| **Unit tests** | `tests/` directory via pytest |
| **Doctests** | Inline examples in source modules |
| **Coverage** | HTML report in `htmlcov/` |

## Running the Notebook Regression Gates

The root notebooks are part of the supported public workflow and should be
executed before shipping large changes to processing or upload code.

```bash
cd scripts
uv run jupyter nbconvert --to notebook --execute 1.0.upload-sensors.ipynb
uv run jupyter nbconvert --to notebook --execute 2.0.upload-signals.ipynb
```

## Configuration

Pytest is configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
    "--import-mode=importlib",
    "--cov=src/owi/metadatabase/shm",
    "--cov-report=html",
    "--doctest-modules",
]
testpaths = ["tests", "src"]
```

## Writing Tests

- Mirror the source tree under `tests/shm/`.
- Mock `owi.metadatabase.shm.io.API.process_data` for API tests.
- Keep tests focused and independent.
- Keep notebook examples aligned with the tested public API surface.
