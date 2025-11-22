"""Input cache endpoints (Story 6-4).

Provides API endpoints for input file caching to skip re-uploads
of identical input files across executions.
"""

import logging
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.v1.auth import verify_api_key
from app.models.input_cache import InputCache

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/input-cache/{input_hash}")
async def lookup_input_cache(
    input_hash: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> Dict:
    """
    Look up cached input file references by hash.

    Args:
        input_hash: SHA256 hash of combined input file contents (64 hex chars)
        db: Database session
        api_key: Authenticated API key

    Returns:
        Dictionary with cache_hit (bool) and file_references (dict) if hit
    """
    # Validate hash format
    if len(input_hash) != 64:
        raise HTTPException(
            status_code=400,
            detail="Invalid input_hash format (must be 64 hex chars)"
        )

    # Look up cache entry
    result = await db.execute(
        select(InputCache).where(InputCache.input_hash == input_hash)
    )
    cache_entry = result.scalar_one_or_none()

    if cache_entry:
        # Cache hit - update last_used_at and use_count
        cache_entry.last_used_at = datetime.utcnow()
        cache_entry.use_count += 1
        await db.commit()

        logger.info(f"Input cache HIT: {input_hash[:16]}... (use_count: {cache_entry.use_count})")

        return {
            "cache_hit": True,
            "file_references": cache_entry.file_references,
        }
    else:
        # Cache miss
        logger.info(f"Input cache MISS: {input_hash[:16]}...")

        return {
            "cache_hit": False,
        }


@router.post("/input-cache")
async def store_input_cache(
    request: Dict,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> Dict:
    """
    Store input cache entry after file upload.

    Args:
        request: Dictionary with:
            - input_hash: SHA256 hash of combined input files (64 hex chars)
            - file_references: Dict mapping filenames to MinIO object keys
        db: Database session
        api_key: Authenticated API key

    Returns:
        Dictionary with stored=True on success
    """
    input_hash = request.get("input_hash")
    file_references = request.get("file_references")

    if not input_hash or not file_references:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: input_hash, file_references"
        )

    # Validate hash format
    if len(input_hash) != 64:
        raise HTTPException(
            status_code=400,
            detail="Invalid input_hash format (must be 64 hex chars)"
        )

    # Check if entry already exists
    result = await db.execute(
        select(InputCache).where(InputCache.input_hash == input_hash)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Entry already exists - just update last_used_at
        existing.last_used_at = datetime.utcnow()
        await db.commit()
        logger.info(f"Input cache already exists: {input_hash[:16]}...")
        return {"stored": True, "existing": True}

    # Create new cache entry
    cache_entry = InputCache(
        input_hash=input_hash,
        file_references=file_references,
        created_at=datetime.utcnow(),
        last_used_at=datetime.utcnow(),
        use_count=0,
    )

    db.add(cache_entry)
    await db.commit()

    logger.info(f"Stored input cache: {input_hash[:16]}... with {len(file_references)} files")

    return {"stored": True, "existing": False}
