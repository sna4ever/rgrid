"""
RGrid Common Package

Shared models, types, and utilities for all RGrid components.
This package has zero external dependencies (except Pydantic) for maximum portability.
"""

__version__ = "0.1.0"

from rgrid_common.money import Money, micros_to_eur, eur_to_micros
from rgrid_common.types import ExecutionStatus, RuntimeType

__all__ = [
    "Money",
    "micros_to_eur",
    "eur_to_micros",
    "ExecutionStatus",
    "RuntimeType",
]
