# Project Context

- **Owner:** Pietro D'Antuono
- **Project:** Python namespace SDK for SHM signal and sensor metadata on top of `owi-metadatabase`
- **Stack:** Python, uv, pytest, invoke, zensical, Jupyter, namespace packages
- **Created:** 2026-03-24

## Learnings

- The archive relies heavily on unnamed dict/list payloads for signals, derived signals, statuses, and calibrations.
- The first domain slice is to extract typed parsing and processing seams before moving larger upload workflows.
- Keep legacy parsing and compatibility helpers under `owi.metadatabase.shm.legacy` so project-specific rules do not leak into the generic SHM package surface.