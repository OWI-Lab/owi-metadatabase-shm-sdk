# Namespace Packages

The `owi-metadatabase-shm` package extends the `owi.metadatabase`
namespace using PEP 420 implicit namespace packages.

## How It Works

The `src/owi/metadatabase/__init__.py` file uses `pkgutil.extend_path` to
allow multiple installed packages to contribute modules under the same
`owi.metadatabase` prefix:

```python
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)
```

This means the core SDK (`owi-metadatabase`) and this extension
can both install modules under `owi.metadatabase` without conflicting.

## Validation

```python
import owi.metadatabase
# The namespace package has no __file__ attribute.
assert not hasattr(owi.metadatabase, "__file__")
```

After installing the extension:

```python
import owi.metadatabase.shm
print(owi.metadatabase.shm.__name__)
# → "owi.metadatabase.shm"
```

## Practical Implications

- **No `__init__.py` ownership conflicts** — each extension package
  contributes its own sub-namespace.
- **Install order does not matter** — `pkgutil.extend_path` merges all
  installed contributions at import time.
- **Uninstalling one extension** does not break others living under the
  same namespace.
