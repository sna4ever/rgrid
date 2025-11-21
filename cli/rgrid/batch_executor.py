"""Async batch executor with concurrency control (Story 5-2).

Provides semaphore-based concurrency limiting for batch job submission.
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from rgrid.utils.file_upload import upload_file_to_minio


@dataclass
class BatchResult:
    """Result of batch execution."""

    total: int
    completed: int
    failed: int
    execution_ids: list[str]
    failed_files: list[str] = field(default_factory=list)
    batch_id: str = ""


class BatchExecutor:
    """Execute batch jobs with concurrency control.

    Uses asyncio.Semaphore to limit the number of concurrent submissions.
    """

    def __init__(self, max_parallel: int = 10):
        """Initialize batch executor.

        Args:
            max_parallel: Maximum concurrent submissions (default: 10).
        """
        self.max_parallel = max_parallel
        self._completed = 0
        self._failed = 0
        self._lock = asyncio.Lock()

    async def execute_batch_async(
        self,
        script_content: str,
        files: list[str],
        runtime: str,
        env_vars: dict[str, str],
        args: list[str] | None = None,
        requirements_content: str | None = None,
        client: Any = None,
        batch_id: str = "",
        progress_callback: Callable[[int, int, int, int], None] | None = None,
    ) -> BatchResult:
        """Execute batch with concurrency control.

        Args:
            script_content: Python script content to execute.
            files: List of file paths to process.
            runtime: Docker runtime image.
            env_vars: Environment variables dict.
            args: Additional arguments to pass to script.
            requirements_content: Optional requirements.txt content.
            client: API client instance.
            batch_id: Batch ID for grouping executions.
            progress_callback: Optional callback for progress updates.
                Signature: (completed, failed, total, running) -> None

        Returns:
            BatchResult with execution results.
        """
        self._completed = 0
        self._failed = 0
        self._client = client
        self._script_content = script_content
        self._runtime = runtime
        self._env_vars = env_vars
        self._args = args or []
        self._requirements_content = requirements_content
        self._batch_id = batch_id
        self._progress_callback = progress_callback

        total = len(files)
        semaphore = asyncio.Semaphore(self.max_parallel)
        execution_ids: list[str] = []
        failed_files: list[str] = []

        async def process_file(file_path: str) -> tuple[str | None, str | None]:
            """Process a single file with semaphore control."""
            async with semaphore:
                try:
                    result = await self._submit_single(file_path)
                    async with self._lock:
                        self._completed += 1
                        exec_id = result.get("execution_id")
                        if self._progress_callback:
                            running = self.max_parallel - semaphore._value
                            self._progress_callback(
                                self._completed, self._failed, total, running
                            )
                    return exec_id, None
                except Exception as e:
                    async with self._lock:
                        self._failed += 1
                        if self._progress_callback:
                            running = self.max_parallel - semaphore._value
                            self._progress_callback(
                                self._completed, self._failed, total, running
                            )
                    return None, file_path

        # Execute all files concurrently with semaphore control
        tasks = [process_file(f) for f in files]
        results = await asyncio.gather(*tasks)

        # Collect results
        for exec_id, failed_file in results:
            if exec_id:
                execution_ids.append(exec_id)
            if failed_file:
                failed_files.append(failed_file)

        return BatchResult(
            total=total,
            completed=self._completed,
            failed=self._failed,
            execution_ids=execution_ids,
            failed_files=failed_files,
            batch_id=self._batch_id,
        )

    async def _submit_single(self, file_path: str) -> dict[str, Any]:
        """Submit a single file for execution.

        Args:
            file_path: Path to the input file.

        Returns:
            Dict with execution_id and status.
        """
        filename = Path(file_path).name
        execution_args = list(self._args) + [filename]

        # Create execution with batch_id
        result = self._client.create_execution(
            script_content=self._script_content,
            runtime=self._runtime,
            args=execution_args,
            env_vars=self._env_vars,
            input_files=[filename],
            batch_id=self._batch_id,
            requirements_content=self._requirements_content,
        )

        # Upload the file if upload URL provided
        upload_urls = result.get("upload_urls", {})
        if upload_urls and filename in upload_urls:
            upload_file_to_minio(file_path, upload_urls[filename])

        return result

    def execute_batch(
        self,
        script_content: str,
        files: list[str],
        runtime: str,
        env_vars: dict[str, str],
        args: list[str] | None = None,
        requirements_content: str | None = None,
        client: Any = None,
        batch_id: str = "",
        progress_callback: Callable[[int, int, int, int], None] | None = None,
    ) -> BatchResult:
        """Synchronous wrapper for execute_batch_async.

        Args:
            Same as execute_batch_async.

        Returns:
            BatchResult with execution results.
        """
        return asyncio.run(
            self.execute_batch_async(
                script_content=script_content,
                files=files,
                runtime=runtime,
                env_vars=env_vars,
                args=args,
                requirements_content=requirements_content,
                client=client,
                batch_id=batch_id,
                progress_callback=progress_callback,
            )
        )
