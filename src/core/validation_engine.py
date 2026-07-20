"""Sequential validation engine for OpenCode verification.

Each check completes before the UI advances its progress indicator.
"""

import time
from typing import Callable, List, Optional

from app import WizardState
from core.providers import get_provider_config, resolve_test_model
from core.validation_result import Status, ValidationReport, ValidationResult
from core.validator import (
    test_config_written,
    test_model,
    test_opencode_cli,
)


class ValidationEngine:
    """Sequential validation engine supporting result-driven progress updates.

    Usage:
        engine = ValidationEngine(state)
        engine.on_progress = lambda name, progress: ui.update(name, progress)
        report = engine.run_all()

    Attributes:
        state: WizardState containing API credentials and configuration
        provider_config: Provider-specific configuration for testing strategy
        on_progress: Optional callback function for progress updates
    """

    def __init__(self, state: WizardState):
        """Initialize the validation engine.

        Args:
            state: WizardState containing base_url, api_key, model_id, etc.
        """
        self.state = state
        self.provider_config = get_provider_config(state.base_url)
        self.on_progress: Optional[Callable[[str, float], None]] = None
        self.on_result: Optional[Callable[[str, ValidationResult, float], None]] = None

    def run_all(self) -> ValidationReport:
        """Execute each validation task once and return a complete report.

        Tasks run in order:
        - model: Model inference test
        - config: Configuration file test
        - cli: OpenCode CLI test

        Progress updates occur only after each task has a concrete result.

        Returns:
            ValidationReport containing all results and overall status.
        """
        tasks = [
            ('model', self._test_model),
            ('config', self._test_config),
            ('cli', self._test_cli),
        ]

        results: List[ValidationResult] = []
        completed_count = 0
        total_tasks = len(tasks)

        start_time = time.perf_counter()

        for name, task_func in tasks:
            try:
                result = task_func()
            except Exception as e:
                result = ValidationResult(
                    name=name, status=Status.FAILED, duration_ms=0,
                    message=f'Validation failed with exception: {e}', detail=str(e),
                    suggestion=f'Check the {name} configuration and try again.',
                    metadata={'exception_type': type(e).__name__},
                )
            results.append(result)
            completed_count += 1
            progress = completed_count / total_tasks
            if self.on_result:
                self.on_result(name, result, progress)
            if self.on_progress:
                self.on_progress(name, progress)

        total_duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Determine overall status
        if any(r.status == Status.FAILED for r in results):
            overall_status = Status.FAILED
        elif any(r.status == Status.WARNING for r in results):
            overall_status = Status.WARNING
        else:
            overall_status = Status.SUCCESS

        return ValidationReport(
            results=results,
            total_duration_ms=total_duration_ms,
            overall_status=overall_status,
        )

    def _run_with_timing(self, name: str, func: Callable) -> ValidationResult:
        """Execute a validation function with timing and error handling.

        Wraps the validation function to track execution duration and
        convert any exceptions into proper ValidationResult objects.

        Args:
            name: Name of the validation task
            func: Callable that returns validation result data

        Returns:
            ValidationResult with timing information
        """
        start_time = time.perf_counter()

        try:
            result_data = func()
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Convert legacy dict format to ValidationResult
            if isinstance(result_data, dict):
                status = Status.SUCCESS if result_data.get('ok') else Status.FAILED
                return ValidationResult(
                    name=name,
                    status=status,
                    duration_ms=duration_ms,
                    message=result_data.get('message', ''),
                    detail=result_data.get('detail') or result_data.get('raw_output'),
                    suggestion=result_data.get('suggestion'),
                    metadata={
                        k: v for k, v in result_data.items()
                        if k not in ('ok', 'message', 'detail', 'suggestion')
                    },
                )
            elif isinstance(result_data, ValidationResult):
                return result_data
            else:
                return ValidationResult(
                    name=name,
                    status=Status.FAILED,
                    duration_ms=duration_ms,
                    message='Invalid result type from validation function',
                    detail=f'Expected dict or ValidationResult, got {type(result_data)}',
                )

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ValidationResult(
                name=name,
                status=Status.FAILED,
                duration_ms=duration_ms,
                message=f'{name} validation failed: {e}',
                detail=str(e),
                suggestion=f'Check the {name} configuration and try again.',
                metadata={'exception_type': type(e).__name__},
            )

    def _test_model(self) -> ValidationResult:
        """Test model inference.

        Resolves the appropriate model ID using provider configuration
        and user settings, then tests if the model responds correctly.

        Returns:
            ValidationResult with model inference status.
        """
        model_id = resolve_test_model(self.provider_config, self.state.model_id)
        return self._run_with_timing(
            'model',
            lambda: test_model(self.state.base_url, self.state.api_key, model_id,
                               self.provider_config)
        )

    def _test_cli(self) -> ValidationResult:
        """Test OpenCode CLI functionality.

        Verifies that the OpenCode CLI is installed and can execute
        commands successfully.

        Returns:
            ValidationResult with CLI test status.
        """
        provider_id = (getattr(self.state, 'provider_name', '') or '').strip()
        model_id = self.state.model_id.strip()
        model_ref = f'{provider_id}/{model_id}' if provider_id and model_id else model_id
        return self._run_with_timing(
            'cli',
            lambda: test_opencode_cli(model_ref)
        )

    def _test_config(self) -> ValidationResult:
        """Test configuration file presence and validity.

        Checks if the opencode.jsonc configuration file has been
        written to the expected location.

        Returns:
            ValidationResult with configuration file status.
        """
        provider_id = (getattr(self.state, 'provider_name', '') or '').strip()
        model_id = (getattr(self.state, 'model_id', '') or '').strip()
        expected_model_ref = f'{provider_id}/{model_id}' if provider_id and model_id else ''
        return self._run_with_timing(
            'config',
            lambda: test_config_written(expected_model_ref)
        )
