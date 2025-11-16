"""Output file collection and upload to MinIO (Story 7-2)."""

import os
import mimetypes
from pathlib import Path
from typing import List, Dict
import boto3
from botocore.config import Config


def collect_output_files(work_dir: Path) -> List[Dict]:
    """
    Scan /work directory and collect all output files.

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

    # Walk through all files in work_dir (including subdirectories)
    for root, dirs, files in os.walk(work_dir):
        for file in files:
            file_path = Path(root) / file

            # Calculate relative path from work_dir (preserves subdirectories)
            relative_path = file_path.relative_to(work_dir)

            outputs.append({
                "filename": str(relative_path).replace("\\", "/"),  # Unix-style paths
                "path": str(file_path),
                "size_bytes": file_path.stat().st_size,
            })

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
