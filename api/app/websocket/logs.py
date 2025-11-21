"""WebSocket endpoint for real-time log streaming (Story 8-3)."""

import asyncio
import json
import logging
from typing import Optional, Dict, Set
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.models.execution import Execution
from app.models.execution_log import ExecutionLog

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for active log subscriptions
# Maps execution_id -> set of WebSocket connections
_active_connections: Dict[str, Set[WebSocket]] = {}

# In-memory log buffer for real-time streaming (before DB write)
# Maps execution_id -> list of log entries
_log_buffers: Dict[str, list] = {}


async def get_execution_status(execution_id: str) -> Optional[str]:
    """Get execution status from database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Execution.status).where(Execution.execution_id == execution_id)
        )
        row = result.first()
        return row[0] if row else None


async def get_historical_logs(
    execution_id: str,
    cursor: int = -1,
    limit: int = 1000,
) -> list[dict]:
    """
    Get historical logs from database.

    Args:
        execution_id: Execution ID
        cursor: Last sequence number received (start from cursor+1)
        limit: Maximum number of logs to return

    Returns:
        List of log entries as dictionaries
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ExecutionLog)
            .where(ExecutionLog.execution_id == execution_id)
            .where(ExecutionLog.sequence_number > cursor)
            .order_by(ExecutionLog.sequence_number)
            .limit(limit)
        )
        logs = result.scalars().all()
        return [log.to_dict() for log in logs]


async def broadcast_log(execution_id: str, log_entry: dict) -> None:
    """
    Broadcast a log entry to all connected WebSocket clients.

    Args:
        execution_id: Execution ID
        log_entry: Log entry dictionary
    """
    if execution_id not in _active_connections:
        return

    message = json.dumps({
        "type": "log",
        **log_entry,
    })

    # Send to all connected clients
    disconnected = set()
    for websocket in _active_connections[execution_id]:
        try:
            await websocket.send_text(message)
        except Exception:
            disconnected.add(websocket)

    # Remove disconnected clients
    _active_connections[execution_id] -= disconnected


async def broadcast_complete(
    execution_id: str,
    exit_code: int,
    status: str = "completed",
) -> None:
    """
    Broadcast completion message to all connected clients.

    Args:
        execution_id: Execution ID
        exit_code: Container exit code
        status: Final status (completed/failed)
    """
    if execution_id not in _active_connections:
        return

    message = json.dumps({
        "type": "complete",
        "execution_id": execution_id,
        "exit_code": exit_code,
        "status": status,
    })

    for websocket in _active_connections[execution_id]:
        try:
            await websocket.send_text(message)
        except Exception:
            pass

    # Clean up connections for this execution
    del _active_connections[execution_id]


async def store_log_entry(
    execution_id: str,
    sequence_number: int,
    stream: str,
    message: str,
    timestamp: Optional[datetime] = None,
) -> dict:
    """
    Store a log entry in the database and broadcast to clients.

    Args:
        execution_id: Execution ID
        sequence_number: Monotonic sequence number
        stream: "stdout" or "stderr"
        message: Log message
        timestamp: Optional timestamp (defaults to now)

    Returns:
        The stored log entry as a dictionary
    """
    async with AsyncSessionLocal() as session:
        log = ExecutionLog(
            execution_id=execution_id,
            sequence_number=sequence_number,
            stream=stream,
            message=message,
            timestamp=timestamp,
        )
        session.add(log)
        await session.commit()

        log_dict = log.to_dict()

    # Broadcast to connected clients
    await broadcast_log(execution_id, log_dict)

    return log_dict


@router.websocket("/ws/executions/{execution_id}/logs")
async def websocket_logs_endpoint(
    websocket: WebSocket,
    execution_id: str,
    cursor: int = Query(default=-1, description="Last sequence number received"),
):
    """
    WebSocket endpoint for real-time log streaming.

    Clients connect with an optional cursor parameter indicating the last
    sequence number they received. The server sends:
    1. Historical logs from cursor+1 to current (catch-up)
    2. Real-time logs as they arrive
    3. Completion message when execution finishes

    Args:
        websocket: WebSocket connection
        execution_id: Execution ID to stream logs for
        cursor: Last sequence number received by client (default: -1 = start from beginning)
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for execution {execution_id}, cursor={cursor}")

    # Check if execution exists
    status = await get_execution_status(execution_id)
    if status is None:
        await websocket.send_json({
            "type": "error",
            "execution_id": execution_id,
            "error": f"Execution {execution_id} not found",
        })
        await websocket.close()
        return

    # Register connection
    if execution_id not in _active_connections:
        _active_connections[execution_id] = set()
    _active_connections[execution_id].add(websocket)

    try:
        # Send historical logs (catch-up)
        historical_logs = await get_historical_logs(execution_id, cursor)
        for log in historical_logs:
            await websocket.send_json({
                "type": "log",
                **log,
            })
            cursor = log["sequence_number"]

        # If execution already completed, send completion and close
        if status in ["completed", "failed"]:
            # Get exit code from execution
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Execution.exit_code, Execution.status)
                    .where(Execution.execution_id == execution_id)
                )
                row = result.first()
                exit_code = row[0] if row else -1
                final_status = row[1] if row else "failed"

            await websocket.send_json({
                "type": "complete",
                "execution_id": execution_id,
                "exit_code": exit_code,
                "status": final_status,
            })
            return

        # Keep connection alive and wait for new logs or completion
        # Real-time logs are sent via broadcast_log() when runner streams them
        while True:
            try:
                # Wait for client messages (ping/pong, close, etc.)
                # Timeout after 60 seconds to check execution status
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0,
                )
                # Handle any client messages (could be heartbeat, etc.)
                logger.debug(f"Received message from client: {message}")

            except asyncio.TimeoutError:
                # Check if execution completed
                current_status = await get_execution_status(execution_id)
                if current_status in ["completed", "failed"]:
                    # Send any remaining logs
                    remaining_logs = await get_historical_logs(execution_id, cursor)
                    for log in remaining_logs:
                        await websocket.send_json({
                            "type": "log",
                            **log,
                        })

                    # Get exit code
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(
                            select(Execution.exit_code)
                            .where(Execution.execution_id == execution_id)
                        )
                        row = result.first()
                        exit_code = row[0] if row else -1

                    await websocket.send_json({
                        "type": "complete",
                        "execution_id": execution_id,
                        "exit_code": exit_code,
                        "status": current_status,
                    })
                    return

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for execution {execution_id}")

    finally:
        # Unregister connection
        if execution_id in _active_connections:
            _active_connections[execution_id].discard(websocket)
            if not _active_connections[execution_id]:
                del _active_connections[execution_id]


# API for runner to stream logs
@router.post("/api/v1/executions/{execution_id}/logs/stream")
async def stream_log_entry(
    execution_id: str,
    sequence_number: int = Query(...),
    stream: str = Query(...),
    message: str = Query(...),
    timestamp: Optional[str] = Query(default=None),
):
    """
    API endpoint for runner to stream log entries.

    This allows the runner to POST log entries which are stored in the database
    and broadcast to connected WebSocket clients.

    Args:
        execution_id: Execution ID
        sequence_number: Monotonic sequence number
        stream: "stdout" or "stderr"
        message: Log message content
        timestamp: Optional ISO timestamp
    """
    ts = datetime.fromisoformat(timestamp) if timestamp else None

    log_entry = await store_log_entry(
        execution_id=execution_id,
        sequence_number=sequence_number,
        stream=stream,
        message=message,
        timestamp=ts,
    )

    return {"status": "ok", "log_id": log_entry["log_id"]}
