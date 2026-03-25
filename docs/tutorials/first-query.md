# Your First Query

!!! example
    This tutorial walks you through creating an API client and verifying
    connectivity with the backend.

## Prerequisites

- Python 3.10+
- The SDK installed (`pip install owi-metadatabase-shm`)
- A valid API token (see [How to Authenticate](../how-to/authenticate.md))

## Step 1 — Create the API Client

```python
from owi.metadatabase.shm import ShmAPI

api = ShmAPI(
    api_root="https://owimetadatabase-dev.azurewebsites.net/api/v1",
    token="your-api-token",
)
```

## Step 2 — Verify Connectivity

```python
print(api.ping())  # "ok"
```

## What You Learned

- How to create and configure the API client.
- How to verify backend connectivity.

## Next Steps

- [How-to: Install the SDK](../how-to/install.md)
- [Reference: API](../reference/api/index.md)
