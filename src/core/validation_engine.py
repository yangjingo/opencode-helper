"""Parallel validation engine for OpenCode verification.

This module provides the ValidationEngine class which executes
validation tasks (endpoint, model, cli, config) in parallel with
progress callbacks and timing tracking.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional

from app import WizardState
from core.providers import get_provider_config, resolve_test_model
from core.validation_result import Status, ValidationReport, ValidationResult
from core.validator import (
    test_config_written,
    test_endpoint,
    test_model,
    test_opencode_cli,
)


class ValidationEngine:
    """Parallel validation engine supporting fine-grained progress callbacks.

    Executes endpoint, model, CLI, and config validation tasks in parallel
    using a ThreadPoolExecutor. Supports progress reporting and comprehensive
    error handling.

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

    def run_all(self) -> ValidationReport:
        """Execute all validation tasks in parallel and return a complete report.

        Tasks are executed concurrently using ThreadPoolExecutor:
        - endpoint: API connectivity test
        - model: Model inference test
        - cli: OpenCode CLI test
        - config: Configuration file test

        Progress callbacks are triggered at 0.25 increments (0.0, 0.25, 0.5, 0.75, 1.0).

        Returns:
            ValidationReport containing all results and overall status.
        """
        tasks = [
            ('endpoint', self._test_endpoint),
            ('model', self._test_model),
            ('cli', self._test_cli),
            ('config', self._test_config),
        ]

        results: List[ValidationResult] = []
        completed_count = 0
        total_tasks = len(tasks)

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(task_func): name
                for name, task_func in tasks
            }

            # Process results as they complete
            for future in as_completed(future_to_task):
                name = future_to_task[future]
                try:
                    result = future.result()
                except Exception as e:
                    # Convert exception to failed result
                    result = ValidationResult(
                        name=name,
                        status=Status.FAILED,
                        duration_ms=0,
                        message=f'Validation failed with exception: {e}',
                        detail=str(e),
                        suggestion=f'Check the {name} configuration and try again.',
                        metadata={'exception_type': type(e).__name__},
                    )

                results.append(result)
                completed_count += 1

                # Calculate progress (0.0 to 1.0)
                progress = completed_count / total_tasks

                # Trigger progress callback if set
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

    def _test_endpoint(self) -> ValidationResult:
        """Test API endpoint connectivity.

        Uses the provider's test_strategy to determine how to test
        the endpoint. Handles authentication and basic connectivity.

        Returns:
            ValidationResult with endpoint connectivity status.
        """
        return self._run_with_timing(
            'endpoint',
            lambda: test_endpoint(self.state.base_url, self.state.api_key,
                                  self.provider_config)
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
        return self._run_with_timing(
            'cli',
            lambda: test_opencode_cli(self.state.model_id)
        )

    def _test_config(self) -> ValidationResult:
        """Test configuration file presence and validity.

        Checks if the opencode.jsonc configuration file has been
        written to the expected location.

        Returns:
            ValidationResult with configuration file status.
        """
        return self._run_with_timing(
            'config',
            test_config_written
        )
