"""Batch output download and organization logic (Tier 5 - Story 5-4).

Provides functions to organize batch execution outputs into structured directories,
with options for custom output locations and flat directory structures.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional


def extract_input_name(execution: Dict) -> Optional[str]:
    """Extract input filename from execution metadata.

    Args:
        execution: Execution dictionary with metadata

    Returns:
        Input filename, or "unknown" if not found
    """
    batch_metadata = execution.get("batch_metadata", {})
    input_file = batch_metadata.get("input_file")

    if not input_file:
        return "unknown"

    # Extract just the filename from full path
    return os.path.basename(input_file)


def sanitize_output_dirname(base_dir: str, name: str) -> str:
    """Sanitize directory name and handle collisions.

    Args:
        base_dir: Base output directory
        name: Proposed directory name

    Returns:
        Safe directory name (may have counter appended if collision)
    """
    # Remove special characters that aren't safe for directories
    safe_name = re.sub(r'[<>:"|?*]', '_', name)

    # Check for collision and append counter if needed
    candidate = safe_name
    counter = 1

    while os.path.exists(os.path.join(base_dir, candidate)):
        # Append counter to avoid collision
        base, ext = os.path.splitext(safe_name)
        candidate = f"{base}_{counter}{ext}"
        counter += 1

    return candidate


def create_output_directory(base_dir: str, input_name: str, flat: bool = False) -> str:
    """Create output directory for a batch input.

    Args:
        base_dir: Base output directory
        input_name: Input filename
        flat: If True, don't create subdirectories

    Returns:
        Path to output directory
    """
    if flat:
        # Flat mode: just return base directory
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    # Create subdirectory for this input
    safe_dirname = sanitize_output_dirname(base_dir, input_name)
    output_dir = os.path.join(base_dir, safe_dirname)
    os.makedirs(output_dir, exist_ok=True)

    return output_dir


def construct_output_path(output_dir: str, artifact_path: str, preserve_structure: bool = True) -> str:
    """Construct full output path for an artifact.

    Args:
        output_dir: Target output directory
        artifact_path: Original artifact path from container (or just relative path like "results/output.txt")
        preserve_structure: If True, preserve subdirectory structure

    Returns:
        Full output path
    """
    if preserve_structure:
        # artifact_path might be:
        # - Just a relative path like "results/output.txt"
        # - Or an absolute path like "/work/results/output.csv"

        # If it's a relative path, use it directly
        if not artifact_path.startswith('/'):
            return os.path.join(output_dir, artifact_path)

        # For absolute paths, remove leading / and first component (like "work")
        rel_path = artifact_path.lstrip('/')
        parts = Path(rel_path).parts

        if len(parts) > 1:
            # Remove first component (e.g., "work") and keep rest
            rel_path = os.path.join(*parts[1:])
        else:
            # Just filename
            rel_path = parts[0] if parts else "output"

        return os.path.join(output_dir, rel_path)
    else:
        # Flat mode: just use filename
        filename = os.path.basename(artifact_path)
        return os.path.join(output_dir, filename)


def organize_batch_outputs(
    api_client,
    executions: List[Dict],
    output_dir: str = "./outputs",
    flat: bool = False
) -> None:
    """Organize batch execution outputs into structured directories.

    Args:
        api_client: API client instance
        executions: List of execution dictionaries
        output_dir: Base output directory (default: ./outputs)
        flat: If True, put all outputs in single directory without subdirs
    """
    for execution in executions:
        exec_id = execution.get("execution_id")
        input_name = extract_input_name(execution)

        # Create output directory for this execution's files
        target_dir = create_output_directory(output_dir, input_name, flat=flat)

        # Get artifacts for this execution
        artifacts = api_client.get_artifacts(exec_id)

        # Download each artifact to the target directory
        for artifact in artifacts:
            artifact_filename = artifact.get("filename", artifact.get("file_key", "output"))

            # Construct full output path
            output_path = construct_output_path(
                target_dir,
                artifact_filename,
                preserve_structure=(not flat)
            )

            # Ensure parent directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Download the artifact
            api_client.download_artifact(artifact, output_path)


def download_batch_outputs(
    api_client,
    batch_id: str,
    output_dir: str = "./outputs",
    flat: bool = False
) -> None:
    """Download all outputs for a batch execution.

    Args:
        api_client: API client instance
        batch_id: Batch ID to download outputs for
        output_dir: Base output directory
        flat: If True, use flat directory structure
    """
    # Get all executions in this batch
    executions = api_client.get_batch_executions(batch_id)

    print(f"Downloading outputs for {len(executions)} executions...")
    print(f"Output directory: {output_dir}")
    print(f"Organization: {'flat' if flat else 'per-input subdirectories'}\n")

    # Organize and download outputs
    organize_batch_outputs(api_client, executions, output_dir, flat)

    print(f"\n✓ Downloaded outputs to {output_dir}")
