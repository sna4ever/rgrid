"""Real-time log streaming from Docker container to API (Story 8-3)."""

import logging
import os
from datetime import datetime
from typing import Optional, Tuple
import httpx

logger = logging.getLogger(__name__)

# API URL from environment (set by orchestrator)
API_URL = os.getenv("RGRID_API_URL", "http://localhost:8000")


class LogStreamer:
    """
    Stream container logs to API in real-time.

    Captures stdout/stderr from Docker container and POSTs each line
    to the API, which stores in database and broadcasts to WebSocket clients.
    """

    def __init__(
        self,
        execution_id: str,
        api_url: Optional[str] = None,
    ):
        """
        Initialize log streamer.

        Args:
            execution_id: Execution ID to stream logs for
            api_url: API base URL (defaults to RGRID_API_URL env var)
        """
        self.execution_id = execution_id
        self.api_url = (api_url or API_URL).rstrip("/")
        self.sequence_number = 0
        self._client: Optional[httpx.Client] = None

        # Accumulated output for backward compatibility
        self.stdout_buffer = []
        self.stderr_buffer = []

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=10.0)
        return self._client

    def stream_line(
        self,
        stream: str,
        message: str,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Stream a single log line to the API.

        Args:
            stream: "stdout" or "stderr"
            message: Log line content
            timestamp: Optional timestamp (defaults to now)

        Returns:
            True if successfully streamed, False otherwise
        """
        # Accumulate for backward compatibility
        if stream == "stdout":
            self.stdout_buffer.append(message)
        else:
            self.stderr_buffer.append(message)

        # POST to API
        ts = timestamp or datetime.utcnow()
        endpoint = f"{self.api_url}/api/v1/executions/{self.execution_id}/logs/stream"

        try:
            response = self._get_client().post(
                endpoint,
                params={
                    "sequence_number": self.sequence_number,
                    "stream": stream,
                    "message": message,
                    "timestamp": ts.isoformat(),
                },
            )
            response.raise_for_status()
            self.sequence_number += 1
            return True

        except Exception as e:
            logger.warning(f"Failed to stream log line: {e}")
            self.sequence_number += 1  # Still increment to maintain order
            return False

    def get_accumulated_output(self) -> Tuple[str, str]:
        """
        Get accumulated stdout/stderr for backward compatibility.

        Returns:
            Tuple of (stdout, stderr) as strings
        """
        return (
            "\n".join(self.stdout_buffer),
            "\n".join(self.stderr_buffer),
        )

    def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None


def stream_container_logs(
    container,
    execution_id: str,
    api_url: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Stream container logs to API in real-time.

    This function streams logs from a Docker container to the API,
    which stores them in the database and broadcasts to WebSocket clients.

    Args:
        container: Docker container object
        execution_id: Execution ID
        api_url: Optional API URL override

    Returns:
        Tuple of (stdout, stderr) accumulated output
    """
    streamer = LogStreamer(execution_id, api_url)

    try:
        # Stream logs with demultiplexing (separate stdout/stderr)
        for log_entry in container.logs(
            stream=True,
            stdout=True,
            stderr=True,
            timestamps=False,
            follow=True,
        ):
            # Docker logs returns bytes
            if isinstance(log_entry, bytes):
                line = log_entry.decode("utf-8", errors="replace").rstrip("\n")
            else:
                line = str(log_entry).rstrip("\n")

            # Note: When using combined output, we can't distinguish stdout/stderr
            # For now, treat all as stdout. Future: use demux=True
            if line:
                streamer.stream_line("stdout", line)

    except Exception as e:
        logger.error(f"Error streaming container logs: {e}")

    finally:
        streamer.close()

    return streamer.get_accumulated_output()


def stream_container_logs_demux(
    container,
    execution_id: str,
    api_url: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Stream container logs with stdout/stderr separation.

    Uses Docker's demultiplexing to correctly separate stdout and stderr.

    Args:
        container: Docker container object
        execution_id: Execution ID
        api_url: Optional API URL override

    Returns:
        Tuple of (stdout, stderr) accumulated output
    """
    streamer = LogStreamer(execution_id, api_url)

    try:
        # Get logs with demultiplexing
        # This returns a generator of (stream_type, log_entry) tuples
        stdout_logs = container.logs(stream=True, stdout=True, stderr=False, follow=True)
        stderr_logs = container.logs(stream=True, stdout=False, stderr=True, follow=True)

        import threading
        import queue

        log_queue = queue.Queue()
        stop_event = threading.Event()

        def stream_to_queue(log_stream, stream_type):
            """Thread function to read logs and put in queue."""
            try:
                for entry in log_stream:
                    if stop_event.is_set():
                        break
                    if isinstance(entry, bytes):
                        line = entry.decode("utf-8", errors="replace").rstrip("\n")
                    else:
                        line = str(entry).rstrip("\n")
                    if line:
                        log_queue.put((stream_type, line))
            except Exception as e:
                logger.debug(f"Stream ended for {stream_type}: {e}")
            finally:
                log_queue.put((stream_type, None))  # Signal end

        # Start threads to read stdout and stderr
        stdout_thread = threading.Thread(
            target=stream_to_queue, args=(stdout_logs, "stdout")
        )
        stderr_thread = threading.Thread(
            target=stream_to_queue, args=(stderr_logs, "stderr")
        )

        stdout_thread.start()
        stderr_thread.start()

        # Process logs from queue
        ended_streams = 0
        while ended_streams < 2:
            try:
                stream_type, line = log_queue.get(timeout=1.0)
                if line is None:
                    ended_streams += 1
                else:
                    streamer.stream_line(stream_type, line)
            except queue.Empty:
                # Check if container exited
                container.reload()
                if container.status != "running":
                    stop_event.set()
                    break

        stdout_thread.join(timeout=1.0)
        stderr_thread.join(timeout=1.0)

    except Exception as e:
        logger.error(f"Error streaming container logs (demux): {e}")

    finally:
        streamer.close()

    return streamer.get_accumulated_output()
