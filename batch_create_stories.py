#!/usr/bin/env python3
"""
Batch creation of all RGrid story files and context files.
Processes stories 1.2 through 10.8 (56 remaining stories).
"""

import re
import yaml
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path("/home/sune/Projects/rgrid")
STORIES_DIR = PROJECT_ROOT / "docs/sprint-artifacts/stories"
EPIC_FILE = PROJECT_ROOT / "docs/epics.md"
STATUS_FILE = PROJECT_ROOT / "docs/sprint-artifacts/sprint-status.yaml"

# Read epics.md to extract story details
with open(EPIC_FILE) as f:
    epics_content = f.read()

# Read sprint status
with open(STATUS_FILE) as f:
    status_data = yaml.safe_load(f)

def extract_story_details(epic_num, story_num):
    """Extract story details from epics.md"""
    # Find the story section
    pattern = rf"### Story {epic_num}\.{story_num}:([^\n]+)\n\n([^#]+?)(?=###|##|---|\Z)"
    match = re.search(pattern, epics_content, re.DOTALL)

    if not match:
        print(f"WARNING: Could not find Story {epic_num}.{story_num} in epics.md")
        return None

    title = match.group(1).strip()
    content = match.group(2).strip()

    # Extract user story (As a... I want... So that...)
    as_a_match = re.search(r"As an? ([^,]+),", content)
    i_want_match = re.search(r"I want ([^,]+),", content)
    so_that_match = re.search(r"[Ss]o that ([^.]+)\.", content)

    as_a = as_a_match.group(1) if as_a_match else "developer"
    i_want = i_want_match.group(1) if i_want_match else title.lower()
    so_that = so_that_match.group(1) if so_that_match else "the system works correctly"

    # Extract acceptance criteria
    ac_section = re.search(r"\*\*Acceptance Criteria:\*\*\n\n(.+?)(?=\n\n\*\*|$)", content, re.DOTALL)
    acceptance_criteria = []
    if ac_section:
        ac_text = ac_section.group(1)
        # Find all "Given/When/Then" or numbered criteria
        for line in ac_text.split('\n'):
            line = line.strip()
            if line and (line.startswith('**') or line.startswith('-') or line.startswith('*')):
                acceptance_criteria.append(line.strip('*- '))

    # Extract prerequisites
    prereq_match = re.search(r"\*\*Prerequisites:\*\* (.+)", content)
    prerequisites = prereq_match.group(1) if prereq_match else f"Epic {epic_num} stories"

    # Extract technical notes
    tech_notes_match = re.search(r"\*\*Technical Notes:\*\*\n\n(.+?)(?=\n\n---|\Z)", content, re.DOTALL)
    technical_notes = tech_notes_match.group(1).strip() if tech_notes_match else ""

    return {
        'title': title,
        'as_a': as_a,
        'i_want': i_want,
        'so_that': so_that,
        'acceptance_criteria': acceptance_criteria,
        'prerequisites': prerequisites,
        'technical_notes': technical_notes,
        'content': content
    }

def create_story_file(epic_num, story_num, story_key, details):
    """Create a story markdown file"""
    story_file = STORIES_DIR / f"{story_key}.md"

    # Build acceptance criteria section
    ac_lines = []
    for i, ac in enumerate(details['acceptance_criteria'], 1):
        ac_lines.append(f"{i}. {ac}")
    ac_text = '\n'.join(ac_lines) if ac_lines else "1. [Define acceptance criteria from epic]"

    content = f"""# Story {epic_num}.{story_num}: {details['title']}

Status: drafted

## Story

As {details['as_a']},
I want {details['i_want']},
So that {details['so_that']}.

## Acceptance Criteria

{ac_text}

## Tasks / Subtasks

- [ ] Task 1 (AC: #1)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #2)
  - [ ] Subtask 2.1

## Dev Notes

### Prerequisites

{details['prerequisites']}

### Technical Notes

{details['technical_notes']}

### References

- [Source: docs/epics.md - Story {epic_num}.{story_num}]
- [Source: docs/sprint-artifacts/tech-spec-epic-{epic_num}.md]
- [Source: docs/architecture.md]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
"""

    with open(story_file, 'w') as f:
        f.write(content)

    print(f"Created: {story_file.name}")
    return story_file

# Process all stories (1.2-10.8, skipping 1.1 which is done)
STORIES = [
    # Epic 1 (skip 1.1, already done)
    (1, 2, "1-2-set-up-development-environment-and-build-system"),
    (1, 3, "1-3-implement-api-key-authentication-system"),
    (1, 4, "1-4-build-cli-framework-with-click"),
    (1, 5, "1-5-implement-rgrid-init-command-for-first-time-setup"),
    (1, 6, "1-6-set-up-fastapi-backend-with-database-connection"),
    # Epic 2 - all stories
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

print(f"Processing {len(STORIES)} stories...")
print("=" * 60)

created_count = 0
skipped_count = 0

for epic_num, story_num, story_key in STORIES:
    print(f"\nProcessing Story {epic_num}.{story_num}: {story_key}")

    # Check if story file already exists
    story_file = STORIES_DIR / f"{story_key}.md"
    if story_file.exists():
        print(f"  SKIPPED: Story file already exists")
        skipped_count += 1
        continue

    # Extract details from epics.md
    details = extract_story_details(epic_num, story_num)
    if not details:
        print(f"  ERROR: Could not extract story details")
        continue

    # Create story file
    create_story_file(epic_num, story_num, story_key, details)
    created_count += 1

print("\n" + "=" * 60)
print(f"Summary:")
print(f"  Created: {created_count} story files")
print(f"  Skipped: {skipped_count} story files (already existed)")
print(f"  Total processed: {len(STORIES)}")
