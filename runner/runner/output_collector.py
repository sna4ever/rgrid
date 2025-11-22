"""Output file collection and upload to MinIO (Story 7-2).

SECURITY: This module collects files from container output directories.
Must prevent symlink attacks where containers create symlinks pointing
to sensitive host files.
"""

import os
import mimetypes
import logging
from pathlib import Path
from typing import List, Dict
import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


def collect_output_files(work_dir: Path) -> List[Dict]:
    """
    Scan /work directory and collect all output files.

    SECURITY: Prevents symlink attacks by:
    - Not following symlinks during directory walk
    - Skipping any symlink files
    - Verifying resolved paths stay within work_dir

    Args:
        work_dir: Path to /work directory

    Returns:
        List of dicts with file metadata:
        - filename: str (with subdirectory if nested)
        - path: str (absolute path to file)
        - size_bytes: int
    """
    outputs = []

    if not work_dir.exists():
        return outputs

    # Resolve work_dir to absolute path for security checks
    work_dir_resolved = work_dir.resolve()

    # Walk through all files in work_dir (including subdirectories)
    # SECURITY: followlinks=False prevents following symlinked directories
    for root, dirs, files in os.walk(work_dir, followlinks=False):
        for file in files:
            file_path = Path(root) / file

            # SECURITY: Skip symlinks entirely to prevent escape attacks
            if file_path.is_symlink():
                logger.warning(f"Security: Skipping symlink output: {file_path}")
                continue

            # SECURITY: Verify the resolved path stays within work_dir
            try:
                file_resolved = file_path.resolve()
                file_resolved.relative_to(work_dir_resolved)
            except ValueError:
                logger.warning(
                    f"Security: Skipping file that escapes work_dir: {file_path}"
                )
                continue

            # Calculate relative path from work_dir (preserves subdirectories)
            try:
                relative_path = file_path.relative_to(work_dir)
            except ValueError:
                logger.warning(f"Security: Cannot compute relative path for: {file_path}")
                continue

            # SECURITY: Validate relative path doesn't contain traversal
            relative_str = str(relative_path)
            if '..' in relative_str:
                logger.warning(f"Security: Path traversal in relative path: {relative_str}")
                continue

            try:
                outputs.append({
                    "filename": relative_str.replace("\\", "/"),  # Unix-style paths
                    "path": str(file_path),
                    "size_bytes": file_path.stat().st_size,
                })
            except OSError as e:
                # File may have been deleted or is inaccessible
                logger.warning(f"Could not stat file {file_path}: {e}")
                continue

    return outputs


def upload_outputs_to_minio(
    outputs: List[Dict],
    exec_id: str,
    endpoint: str = None,
    access_key: str = None,
    secret_key: str = None,
    bucket_name: str = None,
    use_ssl: bool = False,
) -> List[Dict]:
    """
    Upload output files to MinIO.

    Args:
        outputs: List of output file metadata from collect_output_files
        exec_id: Execution ID
        endpoint: MinIO endpoint (default: from env MINIO_ENDPOINT)
        access_key: MinIO access key (default: from env MINIO_ACCESS_KEY)
        secret_key: MinIO secret key (default: from env MINIO_SECRET_KEY)
        bucket_name: MinIO bucket name (default: from env MINIO_BUCKET_NAME)
        use_ssl: Use SSL (default: from env MINIO_USE_SSL)

    Returns:
        List of uploaded file metadata with s3_key added
    """
    # Get MinIO config from env if not provided
    endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "rgrid_dev")
    secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "rgrid_dev_secret")
    bucket_name = bucket_name or os.getenv("MINIO_BUCKET_NAME", "rgrid")
    use_ssl = use_ssl or os.getenv("MINIO_USE_SSL", "false").lower() == "true"

    # Initialize S3 client
    s3_client = boto3.client(
        "s3",
        endpoint_url=f"http{'s' if use_ssl else ''}://{endpoint}",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )

    uploaded = []

    for output in outputs:
        # S3 key format: executions/{exec_id}/outputs/{filename}
        s3_key = f"executions/{exec_id}/outputs/{output['filename']}"

        try:
            # Upload file to MinIO
            s3_client.upload_file(
                Filename=output["path"],
                Bucket=bucket_name,
                Key=s3_key,
            )

            # Add s3_key to metadata
            output_with_s3 = output.copy()
            output_with_s3["s3_key"] = s3_key
            output_with_s3["content_type"] = get_content_type(output["filename"])
            uploaded.append(output_with_s3)

        except Exception as e:
            # Log error but continue with other files
            print(f"Failed to upload {output['filename']}: {e}")
            continue

    return uploaded


def get_content_type(filename: str) -> str:
    """
    Detect MIME type from filename.

    Args:
        filename: File name or path

    Returns:
        MIME type string
    """
    # Initialize mimetypes if not already done
    if not mimetypes.inited:
        mimetypes.init()

    content_type, _ = mimetypes.guess_type(filename)
    return content_type or "application/octet-stream"
