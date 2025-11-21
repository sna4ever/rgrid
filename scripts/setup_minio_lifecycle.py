#!/usr/bin/env python3
"""Set up MinIO lifecycle policy for artifact retention (Story 7-3).

This script configures MinIO to automatically delete artifacts after
the configured retention period (default 30 days).

Usage:
    python scripts/setup_minio_lifecycle.py

Environment Variables:
    MINIO_ENDPOINT: MinIO server endpoint (default: localhost:9000)
    MINIO_ACCESS_KEY: MinIO access key
    MINIO_SECRET_KEY: MinIO secret key
    MINIO_BUCKET: Bucket name (default: rgrid)
    MINIO_SECURE: Use HTTPS (default: false)
    ARTIFACT_RETENTION_DAYS: Days to retain artifacts (default: 30)
"""

import os
import sys
from typing import Optional

# Try to import minio, provide helpful error if not installed
try:
    from minio import Minio
    from minio.commonconfig import Filter
    from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
except ImportError:
    print("Error: minio package not installed. Run: pip install minio")
    sys.exit(1)


def create_lifecycle_config(
    retention_days: int = 30,
    prefix: str = "executions/"
) -> LifecycleConfig:
    """
    Create a MinIO lifecycle configuration.

    Args:
        retention_days: Number of days to retain objects before deletion
        prefix: Object key prefix to apply the rule to

    Returns:
        LifecycleConfig object for MinIO
    """
    rule = Rule(
        status="Enabled",
        rule_filter=Filter(prefix=prefix),
        rule_id="artifact-retention",
        expiration=Expiration(days=retention_days),
    )
    return LifecycleConfig([rule])


def get_minio_client() -> Minio:
    """
    Create MinIO client from environment variables.

    Returns:
        Configured Minio client
    """
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

    if not access_key or not secret_key:
        raise ValueError(
            "MINIO_ACCESS_KEY and MINIO_SECRET_KEY environment variables required"
        )

    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def setup_lifecycle(
    client: Optional[Minio] = None,
    bucket: Optional[str] = None,
    retention_days: Optional[int] = None,
    prefix: str = "executions/"
) -> None:
    """
    Set up MinIO bucket lifecycle policy.

    Args:
        client: Optional MinIO client (creates one if not provided)
        bucket: Bucket name (default from MINIO_BUCKET env var)
        retention_days: Days to retain (default from ARTIFACT_RETENTION_DAYS env var)
        prefix: Object prefix to apply policy to
    """
    if client is None:
        client = get_minio_client()

    if bucket is None:
        bucket = os.getenv("MINIO_BUCKET", "rgrid")

    if retention_days is None:
        retention_days = int(os.getenv("ARTIFACT_RETENTION_DAYS", "30"))

    # Ensure bucket exists
    if not client.bucket_exists(bucket):
        print(f"Creating bucket: {bucket}")
        client.make_bucket(bucket)

    # Create and apply lifecycle config
    config = create_lifecycle_config(retention_days, prefix)
    client.set_bucket_lifecycle(bucket, config)

    print(f"Lifecycle policy configured for bucket '{bucket}':")
    print(f"  - Rule ID: artifact-retention")
    print(f"  - Prefix: {prefix}")
    print(f"  - Retention: {retention_days} days")
    print(f"  - Status: Enabled")


def verify_lifecycle(
    client: Optional[Minio] = None,
    bucket: Optional[str] = None
) -> bool:
    """
    Verify lifecycle policy is set on bucket.

    Args:
        client: Optional MinIO client
        bucket: Bucket name

    Returns:
        True if lifecycle policy exists
    """
    if client is None:
        client = get_minio_client()

    if bucket is None:
        bucket = os.getenv("MINIO_BUCKET", "rgrid")

    try:
        config = client.get_bucket_lifecycle(bucket)
        if config and config.rules:
            print(f"Lifecycle policy found on bucket '{bucket}':")
            for rule in config.rules:
                print(f"  - Rule ID: {rule.rule_id}")
                print(f"  - Status: {rule.status}")
                if rule.expiration:
                    print(f"  - Expiration: {rule.expiration.days} days")
            return True
    except Exception as e:
        print(f"No lifecycle policy found or error: {e}")

    return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Set up MinIO lifecycle policy for artifact retention"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify existing policy, don't set new one"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Retention days (overrides ARTIFACT_RETENTION_DAYS env var)"
    )
    parser.add_argument(
        "--bucket",
        type=str,
        default=None,
        help="Bucket name (overrides MINIO_BUCKET env var)"
    )

    args = parser.parse_args()

    try:
        if args.verify:
            success = verify_lifecycle(bucket=args.bucket)
            sys.exit(0 if success else 1)
        else:
            setup_lifecycle(bucket=args.bucket, retention_days=args.days)
            print("\nVerifying configuration...")
            verify_lifecycle(bucket=args.bucket)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
