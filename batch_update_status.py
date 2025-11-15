#!/usr/bin/env python3
"""
Batch update story files and sprint-status.yaml to mark all stories as ready-for-dev.
Updates stories 1.2 through 10.8 (56 stories, 1.1 already done).
"""

import re
import yaml
from pathlib import Path

PROJECT_ROOT = Path("/home/sune/Projects/rgrid")
STORIES_DIR = PROJECT_ROOT / "docs/sprint-artifacts/stories"
STATUS_FILE = PROJECT_ROOT / "docs/sprint-artifacts/sprint-status.yaml"

# Story list (skip 1.1 which is already done)
STORIES = [
    # Epic 1
    (1, 2, "1-2-set-up-development-environment-and-build-system"),
    (1, 3, "1-3-implement-api-key-authentication-system"),
    (1, 4, "1-4-build-cli-framework-with-click"),
    (1, 5, "1-5-implement-rgrid-init-command-for-first-time-setup"),
    (1, 6, "1-6-set-up-fastapi-backend-with-database-connection"),
    # Epic 2
    (2, 1, "2-1-implement-rgrid-run-command-basic-stub"),
    (2, 2, "2-2-implement-docker-container-execution-on-runner"),
    (2, 3, "2-3-implement-pre-configured-runtimes"),
    (2, 4, "2-4-auto-detect-and-install-python-dependencies"),
    (2, 5, "2-5-handle-script-input-files-as-arguments"),
    (2, 6, "2-6-collect-and-store-script-outputs"),
    (2, 7, "2-7-support-environment-variables-via-env-flag"),
    # Epic 3
    (3, 1, "3-1-set-up-ray-head-node-on-control-plane"),
    (3, 2, "3-2-initialize-ray-worker-on-each-hetzner-node"),
    (3, 3, "3-3-submit-executions-as-ray-tasks"),
    (3, 4, "3-4-implement-worker-health-monitoring"),
    # Epic 4
    (4, 1, "4-1-implement-hetzner-worker-provisioning-via-api"),
    (4, 2, "4-2-implement-queue-based-smart-provisioning-algorithm"),
    (4, 3, "4-3-implement-billing-hour-aware-worker-termination"),
    (4, 4, "4-4-pre-pull-common-docker-images-on-worker-init"),
    (4, 5, "4-5-implement-worker-auto-replacement-on-failure"),
    # Epic 5
    (5, 1, "5-1-implement-batch-flag-with-glob-pattern-expansion"),
    (5, 2, "5-2-implement-parallel-flag-for-concurrency-control"),
    (5, 3, "5-3-track-batch-execution-progress"),
    (5, 4, "5-4-organize-batch-outputs-by-input-filename"),
    (5, 5, "5-5-handle-batch-failures-gracefully"),
    (5, 6, "5-6-implement-retry-for-failed-batch-executions"),
    # Epic 6
    (6, 1, "6-1-implement-script-content-hashing-and-cache-lookup"),
    (6, 2, "6-2-implement-dependency-layer-caching"),
    (6, 3, "6-3-implement-automatic-cache-invalidation"),
    (6, 4, "6-4-implement-optional-input-file-caching"),
    # Epic 7
    (7, 1, "7-1-auto-upload-input-files-referenced-in-arguments"),
    (7, 2, "7-2-auto-collect-output-files-from-container"),
    (7, 3, "7-3-store-outputs-in-minio-with-retention-policy"),
    (7, 4, "7-4-auto-download-outputs-to-current-directory-single-execution"),
    (7, 5, "7-5-implement-remote-only-flag-to-skip-auto-download"),
    (7, 6, "7-6-implement-large-file-streaming-and-compression"),
    # Epic 8
    (8, 1, "8-1-implement-rgrid-status-command"),
    (8, 2, "8-2-implement-rgrid-logs-command-with-historical-logs"),
    (8, 3, "8-3-implement-websocket-log-streaming-for-real-time-logs"),
    (8, 4, "8-4-implement-cli-reconnection-for-websocket-streams"),
    (8, 5, "8-5-implement-batch-progress-display-with-watch"),
    (8, 6, "8-6-track-execution-metadata-in-database"),
    # Epic 9
    (9, 1, "9-1-implement-microns-cost-calculation"),
    (9, 2, "9-2-implement-billing-hour-cost-amortization"),
    (9, 3, "9-3-implement-rgrid-cost-command"),
    (9, 4, "9-4-implement-cost-estimation-for-batch-executions"),
    (9, 5, "9-5-implement-cost-alerts-future-enhancement"),
    # Epic 10
    (10, 1, "10-1-build-marketing-website-landing-page"),
    (10, 2, "10-2-build-console-dashboard-with-execution-history"),
    (10, 3, "10-3-implement-download-outputs-via-console"),
    (10, 4, "10-4-implement-structured-error-handling-with-clear-messages"),
    (10, 5, "10-5-implement-network-failure-graceful-handling"),
    (10, 6, "10-6-implement-manual-retry-command"),
    (10, 7, "10-7-implement-auto-retry-for-transient-failures"),
    (10, 8, "10-8-implement-execution-metadata-tagging"),
]

def update_story_file(story_key):
    """Update story file to reference context and mark as ready-for-dev"""
    story_file = STORIES_DIR / f"{story_key}.md"

    if not story_file.exists():
        return False

    with open(story_file) as f:
        content = f.read()

    # Update status from drafted to ready-for-dev
    content = re.sub(
        r'Status: drafted',
        'Status: ready-for-dev',
        content
    )

    # Update context reference
    context_path = f"docs/sprint-artifacts/stories/{story_key}.context.xml"
    content = re.sub(
        r'<!-- Path\(s\) to story context XML will be added here by context workflow -->',
        f'- {context_path}',
        content
    )

    with open(story_file, 'w') as f:
        f.write(content)

    return True

# Update all story files
print("Updating story files...")
print("=" * 60)

updated_count = 0
for epic_num, story_num, story_key in STORIES:
    if update_story_file(story_key):
        print(f"Updated: {story_key}.md")
        updated_count += 1
    else:
        print(f"ERROR: Could not update {story_key}.md")

print(f"\nUpdated {updated_count} story files")

# Update sprint-status.yaml
print("\n" + "=" * 60)
print("Updating sprint-status.yaml...")

with open(STATUS_FILE) as f:
    status_content = f.read()

# Replace all "drafted" and "backlog" with "ready-for-dev" for story entries
# Keep epic statuses unchanged
lines = status_content.split('\n')
updated_lines = []

for line in lines:
    # Check if this is a story line (not epic or retrospective)
    if re.match(r'\s+\d+-\d+-.*: (drafted|backlog)', line):
        # Replace status with ready-for-dev
        line = re.sub(r': (drafted|backlog)$', ': ready-for-dev', line)
    updated_lines.append(line)

updated_content = '\n'.join(updated_lines)

with open(STATUS_FILE, 'w') as f:
    f.write(updated_content)

print("Updated sprint-status.yaml: All stories marked as ready-for-dev")
print("\nDone!")
