---
name: python
description: 'Generate and edit Python code using PEP 8, type hints, pathlib, pytest/unittest, uv-based workflows, logging best practices, and data tooling preferences. Emphasizes small, necessary edits, strong test discipline, and NumPy-style docstrings.'
license: MIT
---

# Python

## Overview

Generate or modify Python code in a consistent, maintainable way that matches
modern Python best practices and a disciplined test/run workflow (via `uv`).

This skill is for **writing or editing Python code** (including tests and
documentation) while keeping changes minimal and correct.

---

## When to Use

Use this skill when:

- Writing new Python modules, functions, classes, scripts, or CLIs
- Editing existing Python code to add features or fix bugs
- Adding or updating unit tests (`pytest` or `unittest`)
- Improving type safety with type hints
- Creating or updating data workflows (prefer `pandas`, `numpy`, or `polars`)
- Adding docstrings and examples (NumPy-style with doctest)

---

## Default Coding Standards

### Style & Readability

- Follow **PEP 8**
- **80 character** maximum line length
- Prefer **clear, explicit code** over cleverness
- Use **list comprehensions / generator expressions** where appropriate, but do
  not sacrifice readability

### Type Hints

- Use type hints for:
  - Function signatures (inputs + return type)
  - Public APIs
  - Important local variables when it improves clarity
- Prefer standard library typing constructs (`typing`, `collections.abc`)

### Strings & Logging

- Prefer **f-strings** for string formatting
- **Exception:** when using the `logging` module, prefer `%` formatting, e.g.
  `logger.info("User id=%s", user_id)` (do not pre-format f-strings for logs)

### Paths & Files

- Prefer `pathlib` over `os.path`
- Keep file operations robust (explicit encodings, sensible error handling)

---

## Error Handling

- Use `try`/`except` blocks for expected failures
- Avoid bare `except:` clauses
- Catch specific exceptions when possible
- Include actionable error messages
- Do not swallow exceptions silently unless explicitly justified

---

## Testing Guidelines

### Frameworks

- Write unit tests using **pytest** or **unittest**
- Tests should be deterministic and isolated

### Test File Naming

If writing a package/module, test file naming must mirror source files:

- `module.py` → `test_module.py`

### Docstrings + Doctest

- Write **detailed NumPy-style docstrings**
- Include doctest examples where helpful and stable

---

## Dependency Management & Running Code

### Environment

- Use `uv` for dependency management and execution
- Use the Python environment installed at:
  `<current-working-folder>/.venv/bin/python`

### Running Tests

- Run pytest via `uv` so tests execute in the correct environment

### Pre-test Checklist

Before running tests, ensure:

- Any necessary test packages (declared in `pyproject.toml`) are installed
- Test databases / fixtures are set up (if applicable)
- Required test environment variables are configured

---

## Data Work

When working with data, prefer:

- `pandas`
- `numpy`
- `polars`

Choose the simplest tool that matches the task and the repo’s existing
conventions.

---

## Change Discipline

- **Edit only the code necessary** to complete the request
- Edit code **directly in the files** (do not provide partial snippets as the
  final deliverable)
- After changes:
  - Run `uv` tests (if available) to ensure correctness
- If running in Docker:
  - Rebuild the Docker image and restart the container after code changes

---

## Quick Examples (Non-normative)

### Logging (preferred)

```python
import logging

logger = logging.getLogger(__name__)

def greet(user_id: str) -> None:
    logger.info("Greeting user_id=%s", user_id)
```

### Pathlib (preferred)

```python
from pathlib import Path

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")
```

### Doctest-style docstring (preferred)

```python
from __future__ import annotations

def add(a: int, b: int) -> int:
    """
    Add two integers.

    Parameters
    ----------
    a
        First integer.
    b
        Second integer.

    Returns
    -------
    int
        The sum.

    Examples
    --------
    >>> add(2, 3)
    5
    """
    return a + b
```
