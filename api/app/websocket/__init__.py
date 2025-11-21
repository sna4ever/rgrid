"""WebSocket endpoints for real-time streaming."""

from app.websocket.logs import router as logs_router

__all__ = ["logs_router"]
