# Squad Decisions

## Active Decisions

### 2026-03-24 - SHM transport seams stay route-faithful and helper-based

- Context: Slice 1 introduced SHM transport helpers while preserving the parent SDK request contract.
- Decision: `ShmAPI` keeps `/shm/routes/` as its default root, mirrors the archived backend route names exactly, and follow-on slices should build on protected helpers such as `_list_resource()` and `_mutate_resource()` instead of duplicating authenticated JSON request glue.
- Consequence: Backend compatibility stays concentrated in one transport layer and later service modules can remain thin.

### 2026-03-24 - Legacy parsing compatibility stays in the legacy subpackage

- Context: The first SHM migration slice only lifts pure parsing and data-shaping helpers from the archive.
- Decision: Typed legacy parsing and compatibility-oriented helper code lives under `owi.metadatabase.shm.legacy`, keeping project-specific parsing rules out of the generic SHM package surface.
- Consequence: Later adapters can depend on the legacy helpers without forcing legacy naming and parsing rules into the generic client layer.

### 2026-03-24 - Slice 1 compatibility is locked with focused helper and transport tests

- Context: The first slice moved narrow transport and helper behavior and needed a stable regression contract.
- Decision: Focused tests lock the current helper contract around signal-id parsing, `load_json_data`, `create_dict`, and `extend_data`, plus protected `ShmAPI` request helpers such as `_authenticated_request`, `_send_json_request`, and `_send_detail_json_request`.
- Consequence: Later refactors can change internals without drifting the compatibility surface that archive workflows still rely on.

### 2026-03-24 - Slice 2 stays limited to lookup seams and legacy payload builders

- Context: The next SHM migration slice needed to stay independently shippable after the latest cleanup removed unfinished higher-level upload structure from the validated scope.
- Decision: Slice 2 covers only the parent-SDK lookup seam in `owi.metadatabase.shm.lookup` and pure archive-derived payload builders in `owi.metadatabase.shm.legacy.payloads`; uploader orchestration, file-loading loops, and architecture docs remain out of scope.
- Consequence: The shipped slice stays small, testable, and honest about the workflow surface the repo actually provides today.

### 2026-03-24 - Parent-SDK lookup context is owned by the top-level SHM lookup module

- Context: Legacy `asset_info()` mixed parent-SDK lookups, tuple shaping, and existence checks directly inside archive helpers, and the duplicate services path is no longer the canonical seam.
- Decision: Reusable parent-SDK lookup normalization lives in `owi.metadatabase.shm.lookup` via `ParentSDKLookupService`, typed lookup records and context objects, and SHM-owned lookup exceptions; any tuple compatibility stays at adapter edges.
- Consequence: Upload-facing code shares one canonical lookup module and does not target a removed duplicate module path.

### 2026-03-24 - Slice 2 regression coverage targets the canonical lookup and payload seams

- Context: Slice-two behavior needed stable regression anchors before any broader SHM uploader facade exists.
- Decision: Lookup coverage is anchored to `tests/shm/test_lookup.py` against `owi.metadatabase.shm.lookup`, and archive-derived payload coverage is anchored to `tests/shm/legacy/test_payloads.py` against `owi.metadatabase.shm.legacy.payloads`.
- Consequence: Refactors can move internals without reintroducing the removed duplicate lookup path or weakening the payload contract.

### 2026-03-24 - Derived signal history keeps a separate parent-signals patch seam

- Context: The archive creates a derived signal history record first and patches `parent_signals` in a separate backend call.
- Decision: `owi.metadatabase.shm.legacy.payloads` keeps distinct typed builders for the derived-signal history record and the `parent_signals` patch instead of folding both contracts into one model.
- Consequence: Later upload orchestration can compose the two operations explicitly while the payload layer preserves the archive backend shapes.

### 2026-03-24 - Architecture explanation documents shipped seams, not an unfinished facade

- Context: The new architecture explanation replaces a generic template while the SHM package still stops at transport, lookup, and legacy compatibility seams.
- Decision: `docs/explanation/architecture.md` should explain the implemented migration boundary and explicitly avoid presenting upload orchestration or a finished uploader facade as already shipped.
- Consequence: Readers get an accurate mental model of the current SDK surface and the next migration boundary without inferring unreleased workflow layers.

### 2026-03-24 - Generic signal uploads are asset-scoped and lookup-owned

- Context: The archive signal uploader hard-coded Norther-specific project assumptions and repeated parent SDK lookup shaping inline with backend mutation steps.
- Decision: Generic SHM signal uploads accept explicit `projectsite` and `assetlocation` request models, while `ParentSDKLookupService` owns translation from parent `LocationsAPI` and `GeometryAPI` results into the upload context consumed by archive-compatible payload builders.
- Consequence: Farm-specific workflow code no longer needs `asset_info`-style glue, and uploader orchestration can stay thin while reusing the canonical parent lookup seam and SHM transport helpers.

### 2026-03-24 - Signal configuration processing stays strategy-based and farm-adaptable

- Context: The SHM migration needs a reusable signal configuration processor, but the only proven implementation is Norther-specific and uploader-facing outputs still need to stay archive-compatible.
- Decision: Build the generic processing seam under `owi.metadatabase.shm.processing` around processor specs, derived-signal strategies, post-processing hooks, and config discovery, while keeping farm-specific parsing, repair rules, and signal semantics inside thin adapters.
- Consequence: New farms can plug into one stable processing core without hard-coding Norther behavior into SHM or forcing premature uploader contract changes.

### 2026-03-24 - Signal workflow generalization stays lookup-led and src-owned

- Context: The next SHM slice generalizes Norther-specific processing and upload workflows while the package already has canonical lookup and transport seams under `src/owi/metadatabase/shm`.
- Decision: Reusable workflow code must depend on the canonical SHM lookup seam for parent-SDK context and keep farm-specific config parsing, derived-signal recipes, and name or status repair logic inside project adapters rather than archive classes or generic constructor kwargs.
- Consequence: The workflow surface stays independently shippable, parent-SDK integration has one authority, and the package avoids a fake generic abstraction.

### 2026-03-24 - Archive-owned signal workflows are reference-only and regressions belong to src

- Context: The refactor directive requires `owimetadatabase_shm_archive` to be removed in favor of `src/owi/metadatabase/shm`, and migrated signal workflow seams now exist under `src`.
- Decision: Treat the archive as reference-only migration material from this slice onward; no new shipped behavior, tests, or adapters may depend on archive-owned processor or uploader code, and regression coverage for migrated workflows belongs under `tests/shm` against `src/owi/metadatabase/shm`.
- Consequence: Remaining gaps must be closed in `src`, and the archive can be removed once equivalent entrypoints exist without a second migration pass.

### 2026-03-24 - Signal processor specs stay YAML-backed and the final workflow seam stays in src

- Context: The next SHM slice generalizes signal processing beyond Norther while removing the remaining archive compatibility surface.
- Decision: Farm configuration stays on plain YAML-to-spec loading into typed `src/owi/metadatabase/shm` models such as `SignalProcessorSpec`; do not add dynaconf. Canonical processing and upload seams live in `src`, and the remaining archive processor, uploader, and compatibility aliases should be retired rather than kept as shipped workflow layers.
- Consequence: Farm variability stays declarative and testable, the public API exposes one canonical processing and upload path, and the archive signal workflow can be deleted without another migration pass.

### 2026-03-24 - SHM classes and methods require NumPy-style docstrings

- Context: The migrated SHM surface is becoming the canonical package API, so documentation quality needs an explicit release gate.
- Decision: Every SHM class and method must carry a NumPy-style docstring, and documentation updates must follow the implemented code.
- Consequence: Reviews can enforce a consistent documentation standard and shipped docs remain aligned with the real package surface.

### 2026-03-24 - Documentation decisions require clean docs validation and handler-scoped mkdocstrings options

- Context: The SHM docs build failed when mkdocstrings Python options were placed outside the handler block, and documentation work needs a consistent completion gate.
- Decision: Keep mkdocstrings Python options under `[project.plugins.mkdocstrings.handlers.python.options]`, and require `uv run inv docs` to complete without warnings before documentation changes are considered done.
- Consequence: The API reference build reads the expected configuration and documentation updates ship with an explicit validation standard.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
