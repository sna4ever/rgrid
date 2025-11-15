"""Authentication dependencies and utilities."""

from typing import Annotated
from fastapi import Header, HTTPException, status


async def verify_api_key(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """
    Verify API key from Authorization header.

    For walking skeleton, accepts any key starting with 'sk_'.
    Full implementation will verify against database.

    Args:
        authorization: Authorization header value

    Returns:
        API key if valid

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    # Expected format: "Bearer sk_xxx..."
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    api_key = parts[1]

    # Walking skeleton: Accept any key starting with 'sk_'
    if not api_key.startswith("sk_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
        )

    # TODO: Verify against database in full implementation
    return api_key
