# Project Context

- **Owner:** Pietro D'Antuono
- **Project:** Python namespace SDK for SHM signal and sensor metadata on top of `owi-metadatabase`
- **Stack:** Python, uv, pytest, invoke, zensical, Jupyter, namespace packages
- **Created:** 2026-03-24

## Learnings

- The current docs are template-level and need to become real architecture, how-to, reference, and notebook guidance.
- Notebook work is planned as part of the first major refactor, not an afterthought.
- The SHM docs build can fail with `KeyError: 'members_order'` when mkdocstrings handler options are misplaced under markdown extension config instead of the Python handler options block.