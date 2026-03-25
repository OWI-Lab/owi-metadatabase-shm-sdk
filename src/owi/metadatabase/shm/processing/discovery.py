"""Configuration file discovery strategies."""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


class ConfigDiscovery(ABC):
    """Discover farm configuration files from a filesystem path."""

    @abstractmethod
    def discover(
        self,
        path_configs: str | Path,
        turbines: Sequence[str] | None = None,
    ) -> dict[str, Path]:
        """Return a turbine-to-config-path mapping.

        Parameters
        ----------
        path_configs
            Filesystem path to a directory of configuration files or a single
            configuration file.
        turbines
            Optional subset of turbine identifiers to retain from the
            discovered files.

        Returns
        -------
        dict[str, Path]
            Mapping from turbine identifier to configuration file path.
        """


@dataclass(frozen=True, slots=True)
class JsonStemConfigDiscovery(ConfigDiscovery):
    """Discover JSON configuration files by stem name.

    Parameters
    ----------
    suffix
        File suffix treated as a valid configuration file.

    Examples
    --------
    >>> JsonStemConfigDiscovery().suffix
    '.json'
    """

    suffix: str = ".json"

    def discover(
        self,
        path_configs: str | Path,
        turbines: Sequence[str] | None = None,
    ) -> dict[str, Path]:
        """Return available JSON config files keyed by turbine name.

        Parameters
        ----------
        path_configs
            Directory containing configuration files or a single JSON config
            path.
        turbines
            Optional subset of turbine stems to retain from the discovered
            files.

        Returns
        -------
        dict[str, Path]
            Mapping from turbine stem to configuration path.

        Raises
        ------
        ValueError
            If the path does not resolve to usable JSON files or the requested
            turbine subset is empty.
        """
        root = Path(path_configs)
        if root.is_dir():
            available = {
                path.stem: path
                for path in sorted(root.iterdir())
                if path.is_file() and path.suffix == self.suffix
            }
        elif root.is_file() and root.suffix == self.suffix:
            available = {root.stem: root}
        else:
            raise ValueError(f"Could not discover configuration files from {root}.")

        if turbines is None:
            return available

        selected = {turbine: available[turbine] for turbine in turbines if turbine in available}
        missing = [turbine for turbine in turbines if turbine not in available]
        if missing:
            warnings.warn(
                "Some turbines from the provided list are not found in the "
                f"configurations directory. Using available turbines: {list(selected)}",
                stacklevel=2,
            )
        if not selected:
            raise ValueError("No valid turbines found in the provided list.")
        return selected
