"""FastAPI error handling middleware for RGrid (Tier 3 - Story 10-4).

This middleware catches RGrid structured errors and converts them to
appropriate HTTP responses with JSON bodies.

Error types are mapped to HTTP status codes:
- ValidationError -> 400 Bad Request
- AuthenticationError -> 401 Unauthorized
- ResourceNotFoundError -> 404 Not Found
- TimeoutError -> 408 Request Timeout
- QuotaExceededError -> 429 Too Many Requests
- ExecutionError -> 500 Internal Server Error
- NetworkError -> 503 Service Unavailable

All errors include structured JSON response with:
- error_type: Type of error
- message: Human-readable error message
- context: Relevant contextual information
- timestamp: When the error occurred
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from api.errors import (
    RGridError,
    ValidationError,
    ExecutionError,
    TimeoutError,
    NetworkError,
    AuthenticationError,
    ResourceNotFoundError,
    QuotaExceededError
)

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle RGrid errors and convert to HTTP responses."""

    async def dispatch(self, request: Request, call_next):
        """Process request and handle any RGrid errors.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response (may be error response if exception occurred)
        """
        try:
            return await call_next(request)
        except ValidationError as e:
            logger.warning(f"Validation error: {e.message}", extra={"context": e.context})
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=e.to_dict()
            )
        except AuthenticationError as e:
            logger.warning(f"Authentication error: {e.message}", extra={"context": e.context})
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=e.to_dict()
            )
        except ResourceNotFoundError as e:
            logger.info(f"Resource not found: {e.message}", extra={"context": e.context})
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=e.to_dict()
            )
        except TimeoutError as e:
            logger.warning(f"Timeout error: {e.message}", extra={"context": e.context})
            return JSONResponse(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                content=e.to_dict()
            )
        except QuotaExceededError as e:
            logger.warning(f"Quota exceeded: {e.message}", extra={"context": e.context})
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=e.to_dict()
            )
        except ExecutionError as e:
            logger.error(f"Execution error: {e.message}", extra={"context": e.context})
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=e.to_dict()
            )
        except NetworkError as e:
            logger.error(f"Network error: {e.message}", extra={"context": e.context})
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=e.to_dict()
            )
        except RGridError as e:
            # Catch any other RGrid errors (base class)
            logger.error(f"Unhandled RGrid error: {e.message}", extra={"context": e.context})
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=e.to_dict()
            )
        except Exception as e:
            # Non-RGrid exceptions - log and return generic error
            logger.exception(f"Unhandled exception: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error_type": "InternalServerError",
                    "message": "An internal server error occurred",
                    "context": {},
                    "timestamp": ""
                }
            )
