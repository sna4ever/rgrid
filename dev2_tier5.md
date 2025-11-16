# Dev 2 - Tier 5 Wave 3 - Story 5-4

## Git Setup (Run First)

```bash
cd /home/sune/Projects/rgrid
git checkout main
git pull origin main
git checkout -b story-5-4-batch-output-organization
```

## Task

Activate DEV (Amelia). Implement Story 5-4: Organize Batch Outputs by Input Filename.

## Story Details

**Epic**: Epic 5 - Batch Execution
**Priority**: High
**Estimate**: 4-6 hours
**Complexity**: Low
**Risk**: Low (filesystem operations)

## Objective

Processing 100 files creates 100 outputs - need organized structure so users can find results easily.

## Acceptance Criteria

- [ ] Default: `./outputs/<input-name>/` directories created for each input
- [ ] Input filename extracted from execution metadata
- [ ] Flag: `--output-dir custom/path` changes base directory
- [ ] Flag: `--flat` puts all outputs in single directory (no subdirs)
- [ ] Handles duplicate input names: `data.csv` from different paths → unique dirs
- [ ] Preserves output subdirectories: `/work/results/output.csv` → `./outputs/input1/results/output.csv`
- [ ] Documentation explains directory structure with examples
- [ ] Works seamlessly with Story 5-3 progress tracking

## Success Metric

Process 10 files, outputs organized as `./outputs/file1/`, `./outputs/file2/`, etc.

## Files to Modify

- `cli/rgrid/commands/run.py` - Add --output-dir and --flat flags
- `cli/rgrid/batch_download.py` - NEW FILE - Batch download with organization
- `runner/runner/executor.py` - Store input filename in execution metadata
- `tests/unit/test_output_organization.py` - NEW FILE - Unit tests
- `tests/integration/test_batch_outputs.py` - NEW FILE - Integration tests

## Testing Strategy (TDD)

**Unit Tests** (tests/unit/test_output_organization.py):
1. `test_extract_input_name()` - Get filename from metadata
2. `test_create_output_directory()` - Make ./outputs/input1/
3. `test_custom_output_dir()` - --output-dir flag works
4. `test_flat_flag()` - --flat disables subdirectories
5. `test_handle_duplicate_names()` - data.csv → data_1.csv, data_2.csv

**Integration Tests** (tests/integration/test_batch_outputs.py):
1. `test_batch_outputs_organized()` - 10 files → 10 output dirs
2. `test_nested_output_structure()` - Subdirectories preserved
3. `test_custom_output_location()` - Files go to custom dir
4. `test_flat_output_mode()` - All files in one dir

**Expected Test Count**: 5 unit tests, 4 integration tests

## Implementation Hints

Directory creation:
```python
def organize_batch_outputs(executions, output_dir="./outputs", flat=False):
    for exec_id, input_name in executions:
        artifacts = api.get_artifacts(exec_id)

        if flat:
            target_dir = output_dir
        else:
            # Create per-input directory
            safe_name = sanitize_filename(input_name)
            target_dir = os.path.join(output_dir, safe_name)
            os.makedirs(target_dir, exist_ok=True)

        for artifact in artifacts:
            download_to(artifact, target_dir)
```

Handle duplicates:
```python
def sanitize_filename(name):
    # Remove path, keep just filename
    base = os.path.basename(name)
    # If collision, add counter
    if os.path.exists(f"./outputs/{base}"):
        base = f"{base}_{counter}"
    return base
```

## Story File

`docs/sprint-artifacts/stories/5-4-batch-output-organization.md`

## Dependencies

✅ Story 5-3 complete (Batch progress tracking from Wave 2)
✅ Story 7-2 complete (Output collection infrastructure)

## Estimated Effort

4-6 hours

---

**Use TDD - write failing tests FIRST, then implement.**

---

## 🎯 REQUIRED: Story Completion Workflow

When development is complete, you MUST follow these steps:

### 1. Update Sprint Status

Edit `docs/sprint-artifacts/sprint-status.yaml`:
- Find your story line
- Change status from `in-progress` → `done`
- Add completion comment

Example:
```yaml
5-3-track-batch-execution-progress: done  # Tier 5 - Dev 2 - COMPLETED 2025-11-16
```

### 2. Commit Your Work

```bash
git add .
git commit -m "Implement Story X-Y: [Story Title]

- All acceptance criteria met
- Unit tests passing (X tests)
- Integration tests passing (Y tests)
- No regressions

🤖 Generated with Claude Code"
```

### 3. Merge to Main

```bash
git checkout main
git pull origin main
git merge [your-branch-name]
```

### 4. Push to Remote

```bash
git push origin main
```

### 5. Confirm Completion

Reply to user: **"Story X-Y merged and complete"**

---

**⚠️ CRITICAL**: Do NOT say "ready for review" or "ask me anything" without completing these steps first. The story is NOT done until it's merged to main.
