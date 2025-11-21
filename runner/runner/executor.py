"""Docker container executor."""

import docker
from docker.models.containers import Container
from typing import Optional, Dict
from pathlib import Path
import tempfile
import logging

from runner.file_handler import download_input_files, map_args_to_container_paths
from runner.output_collector import collect_output_files, upload_outputs_to_minio
from runner.cache import (
    calculate_deps_hash,
    lookup_dependency_cache,
    store_dependency_cache,
    calculate_script_hash,
    lookup_script_cache,
    store_script_cache,
)
from runner.log_streamer import stream_container_logs

logger = logging.getLogger(__name__)


class DockerExecutor:
    """Execute scripts in Docker containers."""

    def __init__(self) -> None:
        """Initialize Docker client."""
        self.client = docker.from_env()

    def build_image_with_dependencies(
        self,
        base_runtime: str,
        requirements_content: str,
        build_dir: Path,
    ) -> str:
        """Build Docker image with dependencies using BuildKit layer caching.

        Args:
            base_runtime: Base Docker image (e.g., "python:3.11")
            requirements_content: Content of requirements.txt
            build_dir: Directory to use for build context

        Returns:
            Docker image tag to use (either cached or newly built)

        Raises:
            docker.errors.BuildError: If image build fails
        """
        # Calculate dependency hash
        deps_hash = calculate_deps_hash(requirements_content)
        logger.info(f"Dependencies hash: {deps_hash[:16]}...")

        # Check cache for existing image
        cached_layer = lookup_dependency_cache(deps_hash)
        if cached_layer:
            # Cache hit - use existing image
            logger.info(f"✓ Using cached dependencies (layer {cached_layer[:20]}...)")
            return cached_layer

        # Cache miss - build new image with BuildKit
        logger.info(f"Cache miss - building image with dependencies...")

        # Create requirements.txt in build directory
        requirements_path = build_dir / "requirements.txt"
        requirements_path.write_text(requirements_content)

        # Create Dockerfile with BuildKit layer caching
        dockerfile_content = f"""FROM {base_runtime}
WORKDIR /work

# Copy requirements.txt (separate layer for caching)
COPY requirements.txt /work/

# Install dependencies with pip cache mount
RUN --mount=type=cache,target=/root/.cache/pip \\
    pip install --no-cache-dir -r requirements.txt

# Script will be mounted at runtime, not baked into image
"""
        dockerfile_path = build_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)

        # Build image with BuildKit
        # Image tag includes deps_hash for identification
        image_tag = f"rgrid-deps:{deps_hash[:16]}"

        try:
            # Build with BuildKit enabled
            image, build_logs = self.client.images.build(
                path=str(build_dir),
                tag=image_tag,
                rm=True,  # Remove intermediate containers
                forcerm=True,  # Always remove intermediate containers
                buildargs={"DOCKER_BUILDKIT": "1"},  # Enable BuildKit
            )

            # Log build output
            for log in build_logs:
                if 'stream' in log:
                    logger.debug(log['stream'].strip())

            # Store in cache
            docker_layer_id = image_tag  # Use tag as layer ID
            store_dependency_cache(deps_hash, docker_layer_id, requirements_content)

            logger.info(f"✓ Built and cached image: {image_tag}")
            return image_tag

        except Exception as e:
            logger.error(f"Failed to build image with dependencies: {e}")
            raise

    def execute_script(
        self,
        script_content: str,
        runtime: str = "python:3.11",
        args: Optional[list[str]] = None,
        env_vars: Optional[dict[str, str]] = None,
        timeout_seconds: int = 300,
        mem_limit_mb: int = 512,
        cpu_count: float = 1.0,
        download_urls: Optional[Dict[str, str]] = None,
        exec_id: Optional[str] = None,  # Story 7-2: For output collection
        requirements_content: Optional[str] = None,  # Story 6-2: Dependency caching
        stream_logs: bool = False,  # Story 8-3: Real-time log streaming
    ) -> tuple[int, str, str, list]:
        """
        Execute script in Docker container with resource limits.

        Args:
            script_content: Python script source code
            runtime: Docker image to use (base image if requirements_content provided)
            args: Script arguments
            env_vars: Environment variables
            timeout_seconds: Maximum execution time (default: 300s / 5min)
            mem_limit_mb: Memory limit in MB (default: 512MB)
            cpu_count: CPU cores to allocate (default: 1.0)
            download_urls: Presigned URLs for input files (Tier 4 - Story 2-5)
            exec_id: Execution ID for output collection (Story 7-2)
            requirements_content: Optional requirements.txt content for dependency caching (Story 6-2)
            stream_logs: Enable real-time log streaming to API (Story 8-3)

        Returns:
            Tuple of (exit_code, stdout, stderr, uploaded_outputs)
        """
        args = args or []
        env_vars = env_vars or {}
        download_urls = download_urls or {}

        # Story 6-1: Calculate script hash for cache lookup
        script_hash = calculate_script_hash(script_content)
        logger.info(f"Script hash: {script_hash[:16]}...")

        # Story 6-1: Check script cache before any build operations
        cached_image = lookup_script_cache(script_hash, runtime)
        cache_hit = cached_image is not None

        # Create temporary directory for script and files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            script_path = tmpdir_path / "script.py"
            script_path.write_text(script_content)

            # Determine the actual runtime to use
            actual_runtime = runtime

            # Story 6-1: Use cached image if available
            if cache_hit:
                logger.info(f"✓ Script cache HIT - using cached image: {cached_image[:30]}...")
                actual_runtime = cached_image
            elif requirements_content:
                # Story 6-2: Build custom image with dependencies if requirements.txt provided
                logger.info("Building image with dependencies...")
                actual_runtime = self.build_image_with_dependencies(
                    base_runtime=runtime,
                    requirements_content=requirements_content,
                    build_dir=tmpdir_path,
                )
                # Story 6-1: Store in script cache after building
                try:
                    store_script_cache(script_hash, runtime, actual_runtime)
                except Exception as e:
                    logger.warning(f"Failed to store script cache: {e}")

            # Download input files if any (Tier 4 - Story 2-5)
            # Story 7-2: Always create /work directory for outputs
            volumes = {str(tmpdir_path): {"bind": "/workspace", "mode": "ro"}}
            work_dir = tmpdir_path / "work"
            work_dir.mkdir()

            if download_urls:
                # Download files to /work
                downloaded_files = download_input_files(download_urls, work_dir)

                # Get list of input filenames
                input_filenames = list(downloaded_files.keys())

                # Map arguments to container paths
                container_args = map_args_to_container_paths(args, input_filenames)
            else:
                container_args = args

            # Mount /work directory (read-write for both inputs and outputs)
            volumes[str(work_dir)] = {"bind": "/work", "mode": "rw"}

            # Prepare command
            cmd = ["python", "/workspace/script.py"] + container_args

            # Calculate resource limits
            mem_limit_bytes = mem_limit_mb * 1024 * 1024  # Convert MB to bytes
            cpu_quota = int(cpu_count * 100000)  # 100000 = 1 CPU
            cpu_period = 100000  # Standard period

            # Run container with resource limits
            try:
                container: Container = self.client.containers.run(
                    actual_runtime,  # Use cached image if dependencies provided
                    command=cmd,
                    volumes=volumes,
                    environment=env_vars,
                    detach=True,
                    remove=False,
                    network_mode="none",  # No network access by default
                    mem_limit=mem_limit_bytes,  # Memory limit
                    cpu_quota=cpu_quota,  # CPU quota
                    cpu_period=cpu_period,  # CPU period
                )

                # Wait for completion with timeout
                # Story 8-3: If streaming enabled, stream logs during execution
                if stream_logs and exec_id:
                    import threading
                    import queue

                    result_queue = queue.Queue()

                    def wait_for_container():
                        try:
                            result = container.wait(timeout=timeout_seconds)
                            result_queue.put(("success", result))
                        except Exception as e:
                            result_queue.put(("error", e))

                    # Start wait in background thread
                    wait_thread = threading.Thread(target=wait_for_container)
                    wait_thread.start()

                    # Stream logs in main thread
                    try:
                        stdout_output, stderr_output = stream_container_logs(
                            container, exec_id
                        )
                        output = stdout_output + stderr_output
                    except Exception as stream_error:
                        logger.warning(f"Log streaming failed: {stream_error}")
                        # Fallback to getting logs after completion
                        output = ""

                    # Wait for container to finish
                    wait_thread.join()
                    try:
                        status, result_or_error = result_queue.get_nowait()
                        if status == "success":
                            exit_code = result_or_error.get("StatusCode", -1)
                        else:
                            # Timeout or error
                            container.kill()
                            container.remove()
                            return -1, "", f"Execution timeout ({timeout_seconds}s) or error: {str(result_or_error)}", []
                    except queue.Empty:
                        exit_code = -1

                    # If streaming didn't capture output, get it now
                    if not output:
                        logs = container.logs(stdout=True, stderr=True)
                        output = logs.decode("utf-8") if isinstance(logs, bytes) else str(logs)
                else:
                    # Original behavior: wait then get logs
                    try:
                        result = container.wait(timeout=timeout_seconds)
                        exit_code = result.get("StatusCode", -1)
                    except Exception as timeout_error:
                        # Timeout or other error - kill container
                        container.kill()
                        container.remove()
                        return -1, "", f"Execution timeout ({timeout_seconds}s) or error: {str(timeout_error)}", []

                    # Get logs
                    logs = container.logs(stdout=True, stderr=True)
                    output = logs.decode("utf-8") if isinstance(logs, bytes) else str(logs)

                # Clean up container
                container.remove()

                # Story 7-2: Collect and upload outputs from /work directory
                uploaded_outputs = []
                if exec_id:  # Collect outputs if exec_id provided
                    # work_dir already exists (created above)
                    # Collect all output files
                    outputs = collect_output_files(work_dir)

                    # Upload to MinIO
                    if outputs:
                        uploaded_outputs = upload_outputs_to_minio(outputs, exec_id)

                # Return exit code, stdout, stderr, and uploaded outputs
                return exit_code, output, "", uploaded_outputs

            except Exception as e:
                return -1, "", str(e), []

    def close(self) -> None:
        """Close Docker client."""
        self.client.close()
