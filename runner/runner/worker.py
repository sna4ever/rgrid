"""Worker process that claims and executes jobs."""

import asyncio
import httpx
from datetime import datetime
from typing import Optional

from runner.executor import DockerExecutor


class Worker:
    """Worker that executes jobs from the queue."""

    def __init__(self, api_url: str, api_key: str) -> None:
        """
        Initialize worker.

        Args:
            api_url: RGrid API URL
            api_key: API key for authentication
        """
        self.api_url = api_url
        self.api_key = api_key
        self.executor = DockerExecutor()
        self.client = httpx.AsyncClient(
            base_url=api_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )

    async def claim_execution(self) -> Optional[dict]:
        """
        Claim next execution from queue.

        Returns:
            Execution details or None if queue is empty
        """
        # For walking skeleton, poll database directly
        # In full implementation, use Ray or queue system
        return None

    async def execute(self, execution: dict) -> None:
        """Execute a claimed job."""
        execution_id = execution["execution_id"]

        try:
            # Update status to running
            await self.client.patch(
                f"/api/v1/executions/{execution_id}",
                json={"status": "running", "started_at": datetime.utcnow().isoformat()},
            )

            # Execute in Docker
            exit_code, stdout, stderr = self.executor.execute_script(
                script_content=execution["script_content"],
                runtime=execution["runtime"],
                args=execution.get("args", []),
                env_vars=execution.get("env_vars", {}),
            )

            # Update status to completed
            status = "completed" if exit_code == 0 else "failed"
            await self.client.patch(
                f"/api/v1/executions/{execution_id}",
                json={
                    "status": status,
                    "exit_code": exit_code,
                    "completed_at": datetime.utcnow().isoformat(),
                },
            )

        except Exception as e:
            # Mark as failed
            await self.client.patch(
                f"/api/v1/executions/{execution_id}",
                json={"status": "failed", "completed_at": datetime.utcnow().isoformat()},
            )

    async def run(self) -> None:
        """Run worker loop."""
        while True:
            execution = await self.claim_execution()
            if execution:
                await self.execute(execution)
            else:
                await asyncio.sleep(1)

    async def close(self) -> None:
        """Close worker resources."""
        self.executor.close()
        await self.client.aclose()
