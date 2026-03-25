# Project Context

- **Owner:** Pietro D'Antuono
- **Project:** Python namespace SDK for SHM signal and sensor metadata on top of `owi-metadatabase`
- **Stack:** Python, uv, pytest, invoke, zensical, Jupyter, namespace packages
- **Created:** 2026-03-24

## Learnings

- Day-one focus is migrating archive-first SHM workflows into a layered SDK without changing the parent package contract.
- The first major delivery includes transport helpers, typed parsing/domain primitives, characterization tests, docs, and notebooks.
- The first accepted slice is transport seams plus legacy parsing/domain helpers plus focused regression tests; larger service moves wait until those seams are stable.
