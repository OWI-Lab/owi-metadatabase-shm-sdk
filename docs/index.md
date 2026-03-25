# OWI Metadatabase SHM Extension

!!! abstract "What is the OWI Metadatabase SHM SDK?"
    The `owi-metadatabase-shm` package extends the `owi.metadatabase`
    namespace with **typed SHM-specific API behaviour**.

<div class="grid cards" markdown>

-   :material-school:{ .lg .middle } **Tutorials**

    ---

    Step-by-step lessons that walk you through connecting to the API
    and running your first queries.

    [:octicons-arrow-right-24: Start learning](tutorials/index.md)

-   :material-tools:{ .lg .middle } **How-to Guides**

    ---

    Focused recipes for common tasks: install, authenticate, and query data.

    [:octicons-arrow-right-24: Find a recipe](how-to/index.md)

-   :material-book-open-variant:{ .lg .middle } **Reference**

    ---

    Auto-generated API docs pulled from source code docstrings.

    [:octicons-arrow-right-24: Browse reference](reference/index.md)

-   :material-lightbulb-on:{ .lg .middle } **Explanation**

    ---

    Deeper discussions on architecture, design decisions,
    and namespace packaging.

    [:octicons-arrow-right-24: Understand concepts](explanation/index.md)

</div>

## Quick Example

```python
from owi.metadatabase.shm import ApiShmRepository, SensorService, ShmAPI

api = ShmAPI(token="your-api-token")
repository = ApiShmRepository(api)
service = SensorService(repository=repository)

print(api.ping())
print(service.get_sensor_type(name="393B04"))
```

## Notebook Workflows

The repository also includes executable tutorial notebooks in `notebooks/` for
sensor and signal upload workflows. They use the bundled Norther example data
and are suitable both as interactive guides and as executable regression gates.
