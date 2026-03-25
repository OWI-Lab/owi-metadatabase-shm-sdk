# Project Context

- **Owner:** Pietro D'Antuono
- **Project:** Python namespace SDK for SHM signal and sensor metadata on top of `owi-metadatabase`
- **Stack:** Python, uv, pytest, invoke, zensical, Jupyter, namespace packages
- **Created:** 2026-03-24

## Learnings

- The current SHM test surface is minimal and needs immediate characterization around parsing, processing, and upload payloads.
- Regression coverage is a prerequisite for safely moving archive behavior into the new package layout.
- Lock the migration with focused compatibility tests at the helper and protected transport boundary before widening the public SHM surface.