# Project Context

- **Owner:** Pietro D'Antuono
- **Project:** Python namespace SDK for SHM signal and sensor metadata on top of `owi-metadatabase`
- **Stack:** Python, uv, pytest, invoke, zensical, Jupyter, namespace packages
- **Created:** 2026-03-24

## Learnings

- The current SHM package has only a stub `ShmAPI`; archive modules currently own all real upload behavior.
- First backend slice is extending transport and authenticated mutation helpers without changing the parent SDK contract.
- Preserve archived backend route names exactly and build follow-on service slices on shared protected helpers instead of duplicating authenticated JSON request glue.