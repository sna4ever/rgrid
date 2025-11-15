# BMAD: Workflow-Init Explained + TDD Strategy

**Created:** 2025-11-14

---

## Part 1: What Happens When You Run `workflow-init`

### Overview

`workflow-init` is an **interactive conversation** that creates a personalized workflow tracking file for your project. Think of it as a "project setup wizard" that generates a roadmap tailored to your situation.

---

### Step-by-Step Breakdown

#### **Step 1: Comprehensive Project Scan**

BMAD scans your project for existing work:

**Planning artifacts:**
- PRD files (`docs/*prd*.md` or `docs/*prd*/index.md`)
- Architecture (`docs/*architecture*.md`)
- UX Design (`docs/*ux*.md`)
- Tech-specs, Product Briefs, Research docs

**Implementation artifacts:**
- Story files (`docs/stories/*.md`)
- Sprint status (`docs/sprint-status.yaml`)
- Existing workflow status (`docs/bmm-workflow-status.yaml`)

**Codebase:**
- Source directories (`src/`, `lib/`, `app/`, `api/`, etc.)
- Package files (`package.json`, `requirements.txt`, `pyproject.toml`)
- Git repository presence

Based on findings, BMAD categorizes your project:
- **STATE 1:** Clean slate (no artifacts, fresh start)
- **STATE 2:** Planning in progress (has PRD/architecture, no code yet)
- **STATE 3:** Implementation in progress (has stories/sprint status)
- **STATE 4:** Legacy codebase (has code but no BMAD artifacts)
- **STATE 5:** Partial/unclear

---

#### **Step 2: Validate State with User**

**For RGrid (your situation), BMAD will detect STATE 2:**

```
I found existing planning documents:

📋 PRD: (none found - you have detailed docs but not in PRD format)
🏗️ Architecture: docs/ARCHITECTURE.md
📄 Product Brief: docs/PROJECT_BRIEF.md
📋 Requirements: docs/REQUIREMENTS.md
... (lists all your docs)

What's your situation with these documents?

a) Continue this work - These docs describe what I'm building now
b) Override/replace - These are old, I'm starting something NEW
c) Already done - This work is complete, I'm starting a NEW project
d) Not sure - Let me explain my situation
```

**You'd choose:** `a) Continue this work`

BMAD will then set `continuing_existing_planning = true` and **auto-detect your track** based on doc types found.

---

#### **Step 3: Ask About Your Work (New Projects Only)**

**Skipped for you** since you're continuing existing work.

For new projects, BMAD asks:
- What are you building?
- Brownfield (existing code) or greenfield (new)?
- Game or software project?

---

#### **Step 4: Optional Discovery Workflows**

**Skipped for you** since you already have planning docs.

For new projects:
- Brainstorm first?
- Research first?

---

#### **Step 5: Track Selection (Auto-Detect for You)**

BMAD analyzes your existing docs:

```
Based on your existing planning documents, I've detected you're using:

**BMad Method** (Full Product Planning)

Found completed workflows:
- Product Brief: docs/PROJECT_BRIEF.md
- Requirements: docs/REQUIREMENTS.md
- Architecture: docs/ARCHITECTURE.md
- Decisions: docs/DECISIONS.md
... (all your docs)

I'll create workflow tracking that matches your existing approach and
automatically marks these completed workflows as done.

Does this look right? (y/n)
```

---

#### **Step 6: Product Brief Question**

**Skipped for you** - you already have PROJECT_BRIEF.md, BMAD will mark it complete.

---

#### **Step 7: Load Workflow Path and Build Status**

BMAD determines your path file: **`method-greenfield.yaml`** (since you're building new platform)

Then builds the `workflow_status` structure:

```yaml
# Phase 0: Discovery (Optional)
brainstorm-project: docs/brainstorming-session-results-2025-11-14.md  # agent: analyst
research: optional  # agent: analyst (skipped if not used)
product-brief: docs/PROJECT_BRIEF.md  # agent: analyst

# Phase 1: Planning
prd: required  # agent: pm (NEXT WORKFLOW - this is where you'd start)
validate-prd: optional  # agent: pm
create-ux-design: conditional  # agent: ux-designer (if UI needed)

# Phase 2: Solutioning
architecture: required  # agent: architect
test-design: recommended  # agent: tea
validate-architecture: optional  # agent: architect
solutioning-gate-check: required  # agent: architect

# Phase 3: Implementation
sprint-planning: required  # agent: sm
(Implementation tracked separately in sprint-status.yaml)
```

**Key:** BMAD scans for your existing files and **auto-marks them complete** with file paths.

---

#### **Step 8: Create Workflow Status File**

BMAD presents summary:

```
Perfect! Here's your personalized BMad workflow path:

Track: BMad Method
Field Type: greenfield
Project: rgrid

📁 Existing Work Detected:

I found these completed workflows and will mark them as done:
✅ product-brief: docs/PROJECT_BRIEF.md
✅ (potentially others based on what it finds)

Your workflow tracking will start from where you left off!

Ready to create your workflow tracking file? (y/n)
```

**If you say yes:**

Creates `docs/bmm-workflow-status.yaml`:

```yaml
# Workflow Status Template
# STATUS DEFINITIONS:
# - required/optional/recommended/conditional: Not yet started
# - {file-path}: Workflow completed (e.g., "docs/prd.md")
# - skipped: Optional workflow that was skipped

generated: "2025-11-14"
project: "rgrid"
project_type: "software"
selected_track: "method"
field_type: "greenfield"
workflow_path: "method-greenfield.yaml"

workflow_status:
  # Phase 0: Discovery (Optional)
  product-brief: docs/PROJECT_BRIEF.md  # agent: analyst

  # Phase 1: Planning
  prd: required  # agent: pm  ← YOUR NEXT STEP
  validate-prd: optional  # agent: pm
  create-ux-design: conditional  # agent: ux-designer

  # Phase 2: Solutioning
  architecture: required  # agent: architect
  test-design: recommended  # agent: tea
  solutioning-gate-check: required  # agent: architect

  # Phase 3: Implementation
  sprint-planning: required  # agent: sm
```

Then tells you:

```
✅ Workflow tracking created: docs/bmm-workflow-status.yaml

Next Workflow: prd
Agent: pm
Command: /bmad:bmm:workflows:prd

💡 Tip: Start a new chat and load the pm agent before running this workflow.
```

---

### Summary: What workflow-init Creates

**File created:** `docs/bmm-workflow-status.yaml`

**Contents:**
1. Project metadata (name, type, track, field type)
2. Complete workflow list from selected path (e.g., method-greenfield.yaml)
3. Auto-detected completed workflows (based on found files)
4. Current status of each workflow (required/completed/optional/skipped)

**Purpose:**
- Tracks where you are in the methodology
- Shows what's next at any time
- Other workflows read this to validate sequence and extract data
- Updated automatically as you complete workflows

**How to use it:**
- Run `/bmad:bmm:workflows:workflow-status` anytime to see progress
- BMAD workflows auto-update it when completed
- You can manually mark workflows complete/skipped if needed

---

## Part 2: TDD with Python/Next.js + BMAD

### Your Stated Preference

> "I prefer to spend human-in-the-loop time in design/requirements phase, then let agents run dev/testing 100% autonomously"

**Perfect for BMAD!** This is exactly how it's designed.

---

### The TDD Strategy with BMAD

#### Phase 1-2: HUMAN-DRIVEN (Design & Requirements)

**Where YOU invest time:**

```
Phase 1 (Planning) - Human-in-the-loop:
├─ PRD workflow - You collaborate with PM agent
│  ├─ Define requirements interactively
│  ├─ Refine user stories
│  ├─ Clarify acceptance criteria
│  └─ YOU approve final PRD
│
└─ UX Design (if UI) - You collaborate with UX Designer agent
   ├─ Review mockups
   ├─ Approve design decisions
   └─ YOU approve final UX

Phase 2 (Solutioning) - Human-in-the-loop:
├─ Architecture workflow - You collaborate with Architect agent
│  ├─ Review system design
│  ├─ Approve tech stack choices
│  ├─ Validate integration points
│  └─ YOU approve final architecture
│
├─ Test Design workflow - You collaborate with TEA agent
│  ├─ Review test strategy (system-level)
│  ├─ Approve coverage approach
│  ├─ Define quality gates
│  └─ YOU approve test plan
│
└─ Solutioning Gate Check - Final validation
   └─ YOU confirm everything aligns before coding
```

**Time investment:** 1-3 days of interactive refinement

**Output:** Comprehensive, approved planning docs that agents can execute from

---

#### Phase 3-4: AGENT-DRIVEN (100% Autonomous Dev + Testing)

**After you approve the plan, agents run autonomously:**

```
Phase 3 (Epic & Story Generation) - AUTONOMOUS:
└─ create-story workflow (SM agent)
   ├─ Reads approved PRD + Architecture + Test Design
   ├─ Generates stories with:
   │  ├─ Full context (why this matters)
   │  ├─ Acceptance criteria (what "done" means)
   │  ├─ Implementation guidance (how to build)
   │  └─ **TEST REQUIREMENTS** (what tests to write)
   └─ YOU review stories once, approve the batch

Phase 4 (Implementation) - AUTONOMOUS TDD LOOP:

For each story:

1. story-context (SM agent) - AUTONOMOUS
   └─ Loads epic + architecture + test design context

2. story-ready (SM agent) - AUTONOMOUS
   └─ Marks story as IN_PROGRESS

3. dev-story (DEV agent) - AUTONOMOUS TDD:
   ├─ Step 1: Write failing tests FIRST (Red)
   │  ├─ Python: pytest tests based on acceptance criteria
   │  ├─ Next.js: Jest/Vitest unit + Playwright e2e
   │  └─ Tests define expected behavior
   │
   ├─ Step 2: Write minimal code to pass (Green)
   │  ├─ API: FastAPI endpoints + Postgres queries
   │  ├─ Orchestrator: Async service logic
   │  ├─ Runner: Docker + artifact handling
   │  ├─ Console: Next.js components + API calls
   │  └─ CLI: Click commands + API client
   │
   ├─ Step 3: Refactor (Refactor)
   │  └─ Clean up, optimize, ensure maintainability
   │
   └─ Step 4: Run full test suite
      └─ All tests pass before marking done

4. code-review (TEA agent) - AUTONOMOUS:
   ├─ Reviews code against story acceptance criteria
   ├─ Validates test coverage
   ├─ Checks architectural alignment
   ├─ Runs automated quality checks:
   │  ├─ Python: pylint, mypy, black formatting
   │  ├─ Next.js: ESLint, TypeScript checks
   │  └─ Security: bandit (Python), npm audit (JS)
   └─ Appends review notes to story file

5. story-done (SM agent) - AUTONOMOUS:
   └─ Marks story DONE, updates sprint status

Repeat for all stories in sprint...

6. retrospective (SM agent) - AUTONOMOUS:
   └─ Reviews epic completion, extracts lessons
```

**Your involvement:** ZERO after approving stories (until retrospective review)

---

### BMAD TDD Implementation Details

#### Python (FastAPI, Orchestrator, Runner, CLI)

**Test Design Output Includes:**

```markdown
## Python Testing Strategy (from test-design workflow)

### Frameworks
- **pytest** - Unit and integration tests
- **pytest-asyncio** - Async test support
- **httpx** - FastAPI test client
- **testcontainers-python** - Postgres + MinIO containers

### Structure
api/
├── tests/
│   ├── unit/         # Pure function tests
│   ├── integration/  # API endpoint tests
│   └── e2e/          # Full workflow tests

orchestrator/
├── tests/
│   ├── unit/         # Scaling logic tests
│   └── integration/  # Hetzner API mocking

runner/
├── tests/
│   ├── unit/         # Docker wrapper tests
│   └── integration/  # MinIO + artifact tests

### Coverage Targets
- Unit tests: 80%+ coverage
- Integration: Critical paths (job claim, artifact upload)
- E2E: Happy path + 3 error scenarios per epic

### Test Execution (CI)
pytest --cov=api --cov=orchestrator --cov=runner --cov-fail-under=80
```

**Dev Agent TDD Loop (Python):**

```python
# Story: "Implement atomic job claim mechanism"

# Step 1: Write failing test (Red)
# tests/integration/test_job_claim.py
async def test_claim_job_atomic():
    """Two runners claiming same job should not conflict"""
    # Setup
    job_id = await create_test_job(status='queued')

    # Act - Simulate concurrent claims
    claim1 = asyncio.create_task(runner1.claim_next_job())
    claim2 = asyncio.create_task(runner2.claim_next_job())

    results = await asyncio.gather(claim1, claim2)

    # Assert - Only one runner got the job
    successful_claims = [r for r in results if r is not None]
    assert len(successful_claims) == 1
    assert successful_claims[0].id == job_id

# Step 2: Write implementation (Green)
# api/services/queue.py
async def claim_next_job(db: AsyncSession) -> Job | None:
    query = """
    WITH next_job AS (
      SELECT id
      FROM jobs
      WHERE status = 'queued'
      ORDER BY priority, created_at
      FOR UPDATE SKIP LOCKED
      LIMIT 1
    )
    UPDATE jobs
    SET status = 'running', started_at = now()
    FROM next_job
    WHERE jobs.id = next_job.id
    RETURNING jobs.*;
    """
    result = await db.execute(query)
    return result.fetchone()

# Step 3: Run tests - PASSES
pytest tests/integration/test_job_claim.py -v

# Step 4: Refactor - extract query builder, add logging
```

---

#### Next.js (Console Frontend)

**Test Design Output Includes:**

```markdown
## Next.js Testing Strategy (from test-design workflow)

### Frameworks
- **Vitest** - Unit tests (React Testing Library)
- **Playwright** - E2E tests
- **MSW** - API mocking

### Structure
console/
├── tests/
│   ├── unit/             # Component tests
│   ├── integration/      # Page tests
│   └── e2e/             # Playwright flows

### Component Tests (Vitest + RTL)
- User interactions (click, type)
- Conditional rendering
- Props validation
- Accessibility (aria-label, roles)

### E2E Tests (Playwright)
- Critical user journeys:
  1. Login → Create Project → Submit Job → View Logs → Download Artifact
  2. Dashboard → Job List → Filter → Sort
  3. Error handling (failed job, timeout, network error)

### Coverage Targets
- Components: 80%+ coverage
- E2E: 5 critical paths + error scenarios

### Test Execution (CI)
vitest --coverage --coverage.threshold.lines=80
playwright test --project=chromium
```

**Dev Agent TDD Loop (Next.js):**

```typescript
// Story: "Job submission form with file upload"

// Step 1: Write failing component test (Red)
// tests/unit/JobSubmitForm.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { JobSubmitForm } from '@/components/JobSubmitForm'

describe('JobSubmitForm', () => {
  it('uploads file and submits job spec', async () => {
    const mockOnSubmit = vi.fn()
    render(<JobSubmitForm onSubmit={mockOnSubmit} />)

    // Upload file
    const file = new File(['test'], 'input.png', { type: 'image/png' })
    const fileInput = screen.getByLabelText('Input File')
    fireEvent.change(fileInput, { target: { files: [file] } })

    // Fill job spec
    fireEvent.change(screen.getByLabelText('Runtime'), {
      target: { value: 'ffmpeg:latest' }
    })
    fireEvent.change(screen.getByLabelText('Command'), {
      target: { value: 'ffmpeg -i input.png thumb.jpg' }
    })

    // Submit
    fireEvent.click(screen.getByRole('button', { name: 'Submit Job' }))

    // Assert
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        runtime: 'ffmpeg:latest',
        command: ['ffmpeg', '-i', 'input.png', 'thumb.jpg'],
        files: {
          inputs: [{ path: 'input.png', url: expect.stringContaining('presigned') }],
          outputs: [{ path: 'thumb.jpg', type: 'file' }]
        }
      })
    })
  })
})

// Step 2: Write component (Green)
// components/JobSubmitForm.tsx
export function JobSubmitForm({ onSubmit }) {
  const [file, setFile] = useState<File | null>(null)
  const [runtime, setRuntime] = useState('')
  const [command, setCommand] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()

    // Upload file to RGrid
    const formData = new FormData()
    formData.append('file', file!)
    const uploadRes = await fetch('/api/files/upload', {
      method: 'POST',
      body: formData
    })
    const { presignedUrl } = await uploadRes.json()

    // Build JobSpec
    const jobSpec = {
      runtime,
      command: command.split(' '),
      files: {
        inputs: [{ path: file!.name, url: presignedUrl }],
        outputs: [{ path: 'thumb.jpg', type: 'file' }]
      }
    }

    onSubmit(jobSpec)
  }

  return (
    <form onSubmit={handleSubmit}>
      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <input value={runtime} onChange={(e) => setRuntime(e.target.value)} />
      <input value={command} onChange={(e) => setCommand(e.target.value)} />
      <button type="submit">Submit Job</button>
    </form>
  )
}

// Step 3: Run tests - PASSES
vitest run JobSubmitForm.test.tsx

// Step 4: Write E2E test (Playwright)
// tests/e2e/job-submission.spec.ts
test('submit job end-to-end', async ({ page }) => {
  await page.goto('/projects/my-project/jobs/new')

  // Upload file
  await page.setInputFiles('input[type="file"]', 'fixtures/input.png')

  // Fill form
  await page.fill('input[name="runtime"]', 'ffmpeg:latest')
  await page.fill('input[name="command"]', 'ffmpeg -i input.png thumb.jpg')

  // Submit
  await page.click('button:has-text("Submit Job")')

  // Assert redirect to job detail
  await expect(page).toHaveURL(/\/jobs\/[a-z0-9-]+/)
  await expect(page.locator('text=Job Status')).toContainText('Queued')
})
```

---

### BMAD Testing Workflows (TEA Agent)

**Available test workflows** (all autonomous):

1. **test-design** (Phase 2)
   - System-level test strategy
   - Framework selection
   - Coverage targets
   - CI/CD integration

2. **atdd** (Acceptance Test-Driven Development)
   - Generate acceptance tests from story criteria
   - Story-level validation

3. **automate** (Test Automation)
   - Convert manual tests to automated
   - Regression test generation

4. **test-review** (Quality Gate)
   - Validates test coverage
   - Checks test quality
   - Ensures tests meet standards

5. **nfr-assess** (Non-Functional Requirements)
   - Performance tests
   - Security tests
   - Reliability tests

6. **framework** (Test Framework Setup)
   - Configure pytest/Vitest/Playwright
   - Setup test utilities
   - CI integration

7. **ci** (CI Pipeline)
   - GitHub Actions / GitLab CI
   - Test execution
   - Coverage reporting

---

### Autonomous Execution Flow

**After you approve PRD + Architecture + Test Design:**

```bash
# You run ONCE to start implementation
/bmad:bmm:workflows:sprint-planning

# This creates docs/sprint-status.yaml:
sprint:
  start_date: "2025-11-14"
  stories:
    - id: "story-1"
      status: "TODO"
      title: "Implement atomic job claim"
    - id: "story-2"
      status: "TODO"
      title: "Upload file endpoint"
    # ... 50+ stories

# Then BMAD Dev agent loops autonomously:
for story in stories:
    /bmad:bmm:workflows:story-context   # Load context
    /bmad:bmm:workflows:story-ready     # Mark in-progress
    /bmad:bmm:workflows:dev-story       # TDD: Write tests → Code → Refactor
    /bmad:bmm:workflows:code-review     # TEA agent validates
    /bmad:bmm:workflows:story-done      # Mark complete
```

**Your next involvement:** When sprint completes, review retrospective

---

### Key Testing Knowledge Available to TEA Agent

From `.bmad/bmm/testarch/tea-index.csv`, TEA agent has expertise in:

**Python/Backend:**
- Data factories and API setup
- Contract testing (Pact)
- Error handling checks
- Component TDD loop

**Next.js/Frontend:**
- Fixture architecture (Playwright)
- Network-first safeguards
- Visual debugging toolkit
- Selector resilience

**General:**
- Test levels framework (unit/integration/e2e)
- Test priorities matrix (P0-P3)
- Test quality definition of done
- CI and burn-in strategy
- Risk governance

**All knowledge is loaded automatically during dev-story workflow**

---

### Summary: Your Autonomous TDD Workflow

**Human Time Investment:**
- Phase 1 (PRD): 4-8 hours interactive
- Phase 2 (Architecture + Test Design): 4-8 hours interactive
- Story review: 2 hours (batch approve)
- **Total: 1-2 days**

**Agent Autonomous Execution:**
- Epic/story generation: Automated
- Story development (TDD loop): Automated
  - Write failing tests
  - Write passing code
  - Refactor
  - Validate
- Code review: Automated
- CI/CD: Automated
- **Duration: 8-12 weeks** (for 50+ story project like RGrid)

**Your Involvement During Implementation:**
- ZERO (agents run autonomously)
- Optional: Check daily progress via `workflow-status`
- Required: Approve retrospective after each epic

**Result:**
- 80%+ test coverage
- TDD-driven development
- Consistent code quality
- Architectural alignment
- Full traceability (story → code → tests)

---

## Recommendation for RGrid

**Start Here:**

```bash
# 1. Run workflow-init (15 min)
/bmad:bmm:workflows:workflow-init

# 2. Consolidate your docs into PRD (4 hours with PM agent)
/bmad:bmm:workflows:prd

# 3. Formalize architecture (4 hours with Architect agent)
/bmad:bmm:workflows:architecture

# 4. Define test strategy (2 hours with TEA agent)
/bmad:bmm:workflows:test-design

# 5. Gate check (30 min)
/bmad:bmm:workflows:solutioning-gate-check

# === AUTOMATION STARTS HERE ===

# 6. Generate stories (2 hours, automated)
/bmad:bmm:workflows:sprint-planning
# + create-story for each epic (automated batch)

# 7. Review & approve stories (2 hours human)
# Read generated stories, approve batch

# 8. Let Dev + TEA agents run (8-12 weeks, 100% autonomous)
# Dev agent: TDD loop for all stories
# TEA agent: Code review for all stories
# No human intervention needed

# 9. Review retrospectives (1 hour per epic)
# After each epic completes
```

**Total human time:** 2 days upfront + 1 hour per epic review = ~12 days over 12 weeks

**Agent time:** 8-12 weeks of autonomous development

---

**Want to proceed with workflow-init?** I can guide you through it right now.
