"""Ray remote tasks for distributed execution."""

import ray
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@ray.remote
def execute_script_task(execution_id: str, database_url: str) -> Dict[str, any]:
    """
    Ray remote task for executing a script.

    This function runs on a Ray worker and executes the script from the database.

    Args:
        execution_id: Execution record ID
        database_url: Database connection string

    Returns:
        dict with execution results: {exit_code, status, stdout, stderr}
    """
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select, update
    from runner.executor import DockerExecutor
    from runner.models import Execution
    from runner.storage import minio_client
    from runner.file_handler import download_input_files, map_args_to_container_paths
    from pathlib import Path
    import tempfile

    logger.info(f"Ray task started for execution: {execution_id}")

    async def run_execution():
        """Async function to run the execution."""
        # Create async engine for this task
        engine = create_async_engine(database_url, echo=False)
        async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        try:
            # Load execution from database
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Execution).where(Execution.execution_id == execution_id)
                )
                execution = result.scalar_one_or_none()

                if not execution:
                    logger.error(f"Execution {execution_id} not found")
                    return {"status": "failed", "error": "Execution not found"}

                # Update status to running
                await session.execute(
                    update(Execution)
                    .where(Execution.execution_id == execution_id)
                    .values(status='running', started_at=datetime.utcnow())
                )
                await session.commit()

                # Get execution parameters
                script_content = execution.script_content
                runtime = execution.runtime
                args = execution.args or []
                env_vars = execution.env_vars or {}
                input_files = execution.input_files or []

            # Download input files if any
            download_urls = {}
            if input_files:
                for filename in input_files:
                    object_key = f"executions/{execution_id}/inputs/{filename}"
                    download_url = minio_client.generate_presigned_download_url(object_key, expiration=3600)
                    download_urls[filename] = download_url

            # Execute script using DockerExecutor
            executor = DockerExecutor()
            try:
                exit_code, stdout, stderr = executor.execute_script(
                    script_content=script_content,
                    runtime=runtime,
                    args=args,
                    env_vars=env_vars,
                    download_urls=download_urls if download_urls else None,
                )
            finally:
                executor.close()

            # Determine final status
            final_status = "completed" if exit_code == 0 else "failed"

            # Update database with results
            async with async_session_maker() as session:
                await session.execute(
                    update(Execution)
                    .where(Execution.execution_id == execution_id)
                    .values(
                        status=final_status,
                        exit_code=exit_code,
                        stdout=stdout[:100000] if stdout else None,  # Limit size
                        stderr=stderr[:100000] if stderr else None,
                        completed_at=datetime.utcnow()
                    )
                )
                await session.commit()

            logger.info(f"Execution {execution_id} completed with status: {final_status}")

            return {
                "status": final_status,
                "exit_code": exit_code,
                "stdout": stdout[:1000] if stdout else "",  # Return limited output
                "stderr": stderr[:1000] if stderr else "",
            }

        except Exception as e:
            logger.error(f"Error executing {execution_id}: {e}", exc_info=True)

            # Update status to failed
            async with async_session_maker() as session:
                await session.execute(
                    update(Execution)
                    .where(Execution.execution_id == execution_id)
                    .values(
                        status='failed',
                        execution_error=str(e),
                        completed_at=datetime.utcnow()
                    )
                )
                await session.commit()

            return {"status": "failed", "error": str(e)}

        finally:
            await engine.dispose()

    # Run the async function
    return asyncio.run(run_execution())
