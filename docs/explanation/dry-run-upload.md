# Optional Upload Dry Runs

Dry-run upload support is an optional validation aid. It uses the same uploader
entry points as a live upload, but replaces the backend transport with an
in-memory client.

## Goal

The dry-run path answers two questions before a real backend mutation:

- which create, patch, and lookup operations would the uploader execute;
- which payloads would be sent for each operation.

It should not add a `dry_run` flag to `ShmSensorUploader` or
`ShmSignalUploader`. Those orchestrators already depend on protocol-shaped
transport clients, so dry-run behavior belongs in a transport replacement.

## Shape

Users construct a dry-run client and pass it to the existing uploader:

```python
dry_api = DryRunSignalUploadClient(...)
uploader = ShmSignalUploader(shm_api=dry_api, lookup_service=lookup_service)

result = uploader.upload_asset(request)
operations = dry_api.operations
```

Sensor upload follows the same pattern:

```python
dry_api = DryRunSensorUploadClient(...)
uploader = ShmSensorUploader(shm_api=dry_api)

uploader.upload_sensors(...)
operations = dry_api.operations
```

## Expected Behavior

A dry-run client:

- never call `requests` or any live backend transport;
- assign deterministic synthetic ids to records it creates;
- record operations in execution order;
- expose recorded payloads grouped by resource type;
- return response dictionaries shaped like `ShmAPI` mutation and lookup results;
- require explicit seed data for lookups that depend on existing backend rows.

Signal dry-run lookup seeds cover sensor types, sensors, and existing signals.
Sensor dry-run lookup seeds cover sensor types and sensors.
Upload context resolution remains outside the SHM transport client and should
continue to be provided by the existing lookup service seam.

## Boundaries

Dry-run upload support is not a second uploader implementation. Payload
construction, upload ordering, temperature-compensation resolution, and
parent-signal resolution should continue to live in the existing uploaders.

The dry-run client is responsible only for replacing backend mutation and lookup
methods with deterministic recording behavior.
