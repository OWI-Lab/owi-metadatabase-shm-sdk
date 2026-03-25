"""JSON loading helpers shared across SHM modules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_data(path_to_data: str | Path | None) -> Any | None:
    """Load JSON data from disk using ``pathlib``.

    Parameters
    ----------
    path_to_data
        Path to the JSON document, or ``None``.

    Returns
    -------
    Any | None
        Parsed JSON document, or ``None`` when no path is provided.

    Examples
    --------
    >>> load_json_data(None) is None
    True
    """
    if path_to_data is None:
        return None

    path = Path(path_to_data)
    return json.loads(path.read_text(encoding="utf-8"))
