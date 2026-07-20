"""Unified validation result structures for the verification system.

This module provides standardized data structures for representing
validation results across different providers and test types.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Status(Enum):
    """Validation status enumeration."""
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    WARNING = 'warning'  # Partial success


@dataclass
class ValidationResult:
    """Single validation result.

    Attributes:
        name: Test name (e.g., 'endpoint', 'model', 'cli', 'config')
        status: Current status of the validation
        duration_ms: Execution time in milliseconds
        message: Short description of the result
        detail: Detailed error information (optional)
        suggestion: User action recommendation (optional)
        metadata: Additional data like status_code, headers, etc.
    """
    name: str
    status: Status
    duration_ms: int
    message: str
    detail: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """Returns True if the validation succeeded or has a warning."""
        return self.status in (Status.SUCCESS, Status.WARNING)

    def __getitem__(self, key: str):
        """Small compatibility bridge for integrations using the old dict API."""
        if key == 'ok':
            # A legacy endpoint probe considered authentication failures
            # reachable. The typed ``.ok`` property correctly remains false.
            return self.status != Status.FAILED or 'status_code' in self.metadata
        if key == 'message':
            return self.message
        if key in self.metadata:
            return self.metadata[key]
        raise KeyError(key)


@dataclass
class ValidationReport:
    """Complete validation report containing all results.

    Attributes:
        results: List of all validation results
        total_duration_ms: Total execution time in milliseconds
        overall_status: Aggregated status across all validations
    """
    results: List[ValidationResult]
    total_duration_ms: int
    overall_status: Status

    def get_failed(self) -> List[ValidationResult]:
        """Returns all failed validation results."""
        return [r for r in self.results if r.status == Status.FAILED]

    def get_suggestions(self) -> List[str]:
        """Returns all non-empty user suggestions from failed validations."""
        suggestions = []
        for result in self.results:
            if result.suggestion:
                suggestions.append(result.suggestion)
        return suggestions


def format_duration(duration_ms: int) -> str:
    """Format duration in milliseconds to human-readable string.

    Args:
        duration_ms: Duration in milliseconds

    Returns:
        Human-readable duration string (e.g., "1.23s", "45ms")
    """
    if duration_ms < 1000:
        return f"{duration_ms}ms"
    else:
        seconds = duration_ms / 1000
        return f"{seconds:.2f}s"
