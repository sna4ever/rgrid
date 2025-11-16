# Dev 1 - Tier 5 Wave 3 - Story 7-5

## Git Setup (Run First)

```bash
cd /home/sune/Projects/rgrid
git checkout main
git pull origin main
git checkout -b story-7-5-remote-only-flag
```

## Task

Activate DEV (Amelia). Implement Story 7-5: Implement --remote-only Flag to Skip Auto-Download.

## Story Details

**Epic**: Epic 7 - Artifact Management
**Priority**: High
**Estimate**: 2-4 hours
**Complexity**: Low
**Risk**: Low (simple flag)

## Objective

Large batches don't need automatic downloads. Let users download selectively later with a simple flag.

## Acceptance Criteria

- [ ] CLI flag: `--remote-only` skips automatic download of outputs
- [ ] Displays message: "Outputs stored remotely. Download with: rgrid download exec_abc123"
- [ ] Outputs still recorded in database and MinIO (just not auto-downloaded)
- [ ] `rgrid download <exec_id>` command downloads outputs on demand
- [ ] Works with both single executions and batches
- [ ] Flag documented in CLI help text
- [ ] Documentation explains when to use `--remote-only` (batches, large files)

## Success Metric

`rgrid run script.py --remote-only` completes without downloading, shows download command

## Files to Modify

- `cli/rgrid/commands/run.py` - Add --remote-only flag, skip download
- `cli/rgrid/commands/download.py` - NEW FILE - Download command
- `api/api/endpoints/artifacts.py` - Endpoint to list execution artifacts
- `tests/unit/test_remote_only.py` - NEW FILE - Unit tests
- `tests/integration/test_download_command.py` - NEW FILE - Integration tests

## Testing Strategy (TDD)

**Unit Tests** (tests/unit/test_remote_only.py):
1. `test_remote_only_flag_present()` - Flag parsed correctly
2. `test_skip_download_when_flag_set()` - Download skipped
3. `test_display_download_command()` - Shows "rgrid download exec_..."
4. `test_artifacts_still_recorded()` - DB and MinIO records created

**Integration Tests** (tests/integration/test_download_command.py):
1. `test_download_command_fetches_outputs()` - Download works later
2. `test_remote_only_with_batch()` - Flag works for 10-job batch
3. `test_list_available_outputs()` - Show what files are available

**Expected Test Count**: 4 unit tests, 3 integration tests

## Implementation Hints

CLI flag:
```python
@click.option('--remote-only', is_flag=True, help='Skip auto-download of outputs')
def run(script, remote_only, **kwargs):
    # ... execute script ...

    if not remote_only:
        download_outputs(exec_id)
    else:
        click.echo(f"Outputs stored remotely. Download with: rgrid download {exec_id}")
```

Download command:
```python
@cli.command()
@click.argument('exec_id')
def download(exec_id):
    """Download outputs for a previous execution."""
    artifacts = api.get_artifacts(exec_id)
    for artifact in artifacts:
        download_from_minio(artifact.s3_key, artifact.filename)
    click.echo(f"Downloaded {len(artifacts)} files")
```

## Story File

`docs/sprint-artifacts/stories/7-5-remote-only-flag.md`

## Dependencies

✅ Story 7-4 complete (Basic download functionality exists from Tier 1)
✅ Story 2-5 complete (File handling infrastructure)

## Estimated Effort

2-4 hours (shortest story in Wave 3)

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
2-5-handle-script-input-files-as-arguments: done  # Tier 5 - Dev 1 - COMPLETED 2025-11-16
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
