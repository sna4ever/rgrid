#!/usr/bin/env python3
"""
Batch creation of story context XML files for all RGrid stories.
Generates context for stories 1.2 through 10.8 (56 stories, 1.1 already done).
"""

import re
import yaml
from pathlib import Path
from datetime import datetime

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

def parse_story_file(story_file):
    """Extract story details from markdown file"""
    with open(story_file) as f:
        content = f.read()

    # Extract title
    title_match = re.search(r"# Story \d+\.\d+: (.+)", content)
    title = title_match.group(1) if title_match else "Unknown"

    # Extract user story components
    as_a_match = re.search(r"As (an? )?([^,\n]+),", content)
    i_want_match = re.search(r"I want ([^,\n]+),", content)
    so_that_match = re.search(r"[Ss]o that ([^.\n]+)", content)

    as_a = as_a_match.group(2) if as_a_match else "developer"
    i_want = i_want_match.group(1) if i_want_match else title.lower()
    so_that = so_that_match.group(1) if so_that_match else "the system works correctly"

    # Extract acceptance criteria
    ac_section = re.search(r"## Acceptance Criteria\n\n(.+?)(?=\n##)", content, re.DOTALL)
    acceptance_criteria = []
    if ac_section:
        for line in ac_section.group(1).split('\n'):
            line = line.strip()
            if line and (re.match(r'^\d+\.', line) or line.startswith('**')):
                acceptance_criteria.append(line)

    # Extract tasks
    tasks_section = re.search(r"## Tasks / Subtasks\n\n(.+?)(?=\n##)", content, re.DOTALL)
    tasks = []
    if tasks_section:
        for line in tasks_section.group(1).split('\n'):
            line = line.strip()
            if line.startswith('- [ ]') and 'Task ' in line:
                tasks.append(line.replace('- [ ]', '').strip())

    return {
        'title': title,
        'as_a': as_a,
        'i_want': i_want,
        'so_that': so_that,
        'acceptance_criteria': acceptance_criteria,
        'tasks': tasks
    }

def create_context_file(epic_num, story_num, story_key, details):
    """Create a story context XML file"""
    context_file = STORIES_DIR / f"{story_key}.context.xml"

    # Build AC and tasks XML
    ac_lines = '\n    '.join(details['acceptance_criteria']) if details['acceptance_criteria'] else "See story file for details"
    tasks_lines = '\n      - '.join(details['tasks']) if details['tasks'] else "See story file for task breakdown"

    content = f"""<story-context id=".bmad/bmm/workflows/4-implementation/story-context/template" v="1.0">
  <metadata>
    <epicId>{epic_num}</epicId>
    <storyId>{epic_num}.{story_num}</storyId>
    <title>{details['title']}</title>
    <status>drafted</status>
    <generatedAt>{datetime.now().strftime('%Y-%m-%d')}</generatedAt>
    <generator>BMAD Story Context Workflow (Batch)</generator>
    <sourceStoryPath>docs/sprint-artifacts/stories/{story_key}.md</sourceStoryPath>
  </metadata>

  <story>
    <asA>{details['as_a']}</asA>
    <iWant>{details['i_want']}</iWant>
    <soThat>{details['so_that']}</soThat>
    <tasks>
      {tasks_lines}
    </tasks>
  </story>

  <acceptanceCriteria>
    {ac_lines}
  </acceptanceCriteria>

  <artifacts>
    <docs>
      <doc>
        <path>docs/architecture.md</path>
        <title>RGrid Architecture Document</title>
        <section>Relevant architecture decisions</section>
        <snippet>See architecture.md for system design, component architecture, and technical constraints relevant to this story.</snippet>
      </doc>
      <doc>
        <path>docs/sprint-artifacts/tech-spec-epic-{epic_num}.md</path>
        <title>Epic {epic_num} Technical Specification</title>
        <section>Technical details for Epic {epic_num}</section>
        <snippet>See tech spec for detailed service breakdown, data models, APIs, and acceptance criteria specific to this epic.</snippet>
      </doc>
      <doc>
        <path>docs/epics.md</path>
        <title>RGrid Epic Breakdown</title>
        <section>Story {epic_num}.{story_num}</section>
        <snippet>See epics.md for complete story definition, prerequisites, and technical notes.</snippet>
      </doc>
    </docs>
    <code>
      <!-- Greenfield project - No existing code for Epic {epic_num} stories -->
    </code>
    <dependencies>
      <python>
        <planned>
          <!-- See tech-spec-epic-{epic_num}.md for dependency details -->
        </planned>
      </python>
    </dependencies>
  </artifacts>

  <constraints>
    - Follow architecture.md LLM-agent-friendly patterns
    - File size limit: Single file MUST NOT exceed 500 lines
    - All costs stored as BIGINT micros (1 EUR = 1,000,000 microns)
    - Python 3.11+ minimum
    - TDD approach: Write tests BEFORE implementation
    - 80% test coverage minimum
  </constraints>

  <interfaces>
    <!-- See story file and tech spec for interface details -->
  </interfaces>

  <tests>
    <standards>
      TDD approach per architecture.md: Write tests BEFORE implementation. Target 80% coverage minimum. Use pytest + pytest-asyncio. Test pyramid: 60% unit tests, 30% service tests, 10% integration tests.
    </standards>
    <locations>
      - tests/unit/ - Unit tests
      - tests/integration/ - Integration tests
      - Component-specific tests/ subdirectories
    </locations>
    <ideas>
      <!-- See story file Dev Notes for testing guidance -->
    </ideas>
  </tests>
</story-context>
"""

    with open(context_file, 'w') as f:
        f.write(content)

    print(f"Created: {context_file.name}")
    return context_file

print(f"Generating story contexts for {len(STORIES)} stories...")
print("=" * 60)

created_count = 0
skipped_count = 0
error_count = 0

for epic_num, story_num, story_key in STORIES:
    print(f"\nProcessing Story {epic_num}.{story_num}: {story_key}")

    # Check if context already exists
    context_file = STORIES_DIR / f"{story_key}.context.xml"
    if context_file.exists():
        print(f"  SKIPPED: Context already exists")
        skipped_count += 1
        continue

    # Parse story file
    story_file = STORIES_DIR / f"{story_key}.md"
    if not story_file.exists():
        print(f"  ERROR: Story file not found")
        error_count += 1
        continue

    try:
        details = parse_story_file(story_file)
        create_context_file(epic_num, story_num, story_key, details)
        created_count += 1
    except Exception as e:
        print(f"  ERROR: {e}")
        error_count += 1

print("\n" + "=" * 60)
print(f"Summary:")
print(f"  Created: {created_count} context files")
print(f"  Skipped: {skipped_count} (already existed)")
print(f"  Errors: {error_count}")
print(f"  Total processed: {len(STORIES)}")
