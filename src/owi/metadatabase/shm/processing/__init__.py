"""Signal processing subpackage.

Re-exports all public symbols so ``from owi.metadatabase.shm.processing import X``
continues to work unchanged.
"""

from .discovery import ConfigDiscovery, JsonStemConfigDiscovery
from .parsing import DelimitedSignalKeyParser, SignalEventKey
from .processor import ConfiguredSignalConfigProcessor, DefaultSignalConfigProcessor, SignalConfigProcessor
from .records import ProcessedDerivedSignalRecord, ProcessedSignalRecord, SignalProcessingResult
from .spec import (
    SignalProcessorSpec,
    default_signal_processor_spec,
    get_default_signal_processor_spec_path,
    load_default_signal_processor_spec,
    load_signal_processor_spec,
)
from .strategies import DerivedSignalStrategy, LevelBasedDerivedSignalStrategy

__all__ = [
    "ConfigDiscovery",
    "ConfiguredSignalConfigProcessor",
    "DefaultSignalConfigProcessor",
    "DelimitedSignalKeyParser",
    "DerivedSignalStrategy",
    "JsonStemConfigDiscovery",
    "LevelBasedDerivedSignalStrategy",
    "ProcessedDerivedSignalRecord",
    "ProcessedSignalRecord",
    "SignalConfigProcessor",
    "SignalEventKey",
    "SignalProcessingResult",
    "SignalProcessorSpec",
    "default_signal_processor_spec",
    "get_default_signal_processor_spec_path",
    "load_default_signal_processor_spec",
    "load_signal_processor_spec",
]
