# Self-Service Work Queue (Dependency-Aware)

## How It Works

Stories are grouped by tier. Only claim stories whose dependencies are marked [DONE].

---

## Completed

| Story | Description | Agent | Wave |
|-------|-------------|-------|------|
| [DONE] **BUG-1** | Fix executor return value | Dev 1 | 1 |
| [DONE] **5-1** | Batch flag with glob | Dev 2 | 1 |
| [DONE] **7-3** | MinIO retention policy | Dev 3 | 1 |
| [DONE] **5-2** | Parallel flag | Dev 1 | 2 |
| [DONE] **7-1** | Auto-upload input files | Dev 2 | 2 |
| [DONE] **7-4** | Auto-download outputs | Dev 3 | 3 |
| [DONE] **5-3** | Batch progress tracking | Dev 1 | 4 |

---

## Tier 4.5 - Batch Execution ✅ COMPLETE

**Goal**: Complete batch execution capability - **ACHIEVED!**

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **5-2** | Parallel flag | 5-1 [DONE] | `queue/next-5-2-parallel-flag.md` |

---

## Tier 5 Phase 1-2 - File Management ✅ COMPLETE

**Goal**: Seamless file upload/download - **ACHIEVED!**

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **7-1** | Auto-upload input files | None | `queue/next-7-1-auto-upload.md` |
| [DONE] | **7-4** | Auto-download outputs | 7-3 [DONE] | `queue/next-7-4-auto-download.md` |

---

## Tier 5 Phase 3 - Batch Management (Now Unblocked!)

**5-2 is [DONE] - these stories can now be claimed!**

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [DONE] | **5-3** | Batch progress tracking | 5-1 ✅, 5-2 ✅ | `docs/sprint-artifacts/stories/5-3-track-batch-execution-progress.md` |
| [IN PROGRESS: Dev 2] | **5-4** | Organize batch outputs | 5-1 ✅ | `docs/sprint-artifacts/stories/5-4-organize-batch-outputs-by-input-filename.md` |
| [IN PROGRESS: Dev 3] | **5-5** | Handle batch failures | 5-1 ✅ | `docs/sprint-artifacts/stories/5-5-handle-batch-failures-gracefully.md` |

---

## Tier 5 Phase 4 - Dependencies (Can Start Now)

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [ ] | **2-4** | Auto-detect Python deps | None | `docs/sprint-artifacts/stories/2-4-auto-detect-and-install-python-dependencies.md` |

---

## Tier 5 Phase 5 - Caching (Partially Unblocked)

**7-1 is [DONE] - 6-1 can start. 6-2 waits for 6-1.**

| Status | Story | Description | Depends On | Story File |
|--------|-------|-------------|------------|------------|
| [ ] | **6-1** | Script content hashing | 7-1 ✅ | `docs/sprint-artifacts/stories/6-1-implement-script-content-hashing-and-cache-lookup.md` |
| [BLOCKED] | **6-2** | Dependency layer caching | 6-1 | `docs/sprint-artifacts/stories/6-2-implement-dependency-layer-caching.md` |

---

## Claiming Rules

1. **Only claim [ ] stories** (not [BLOCKED] or [DONE])
2. **Check "Depends On" column** - all deps must be [DONE]
3. **Edit this file** to change [ ] → [CLAIMING: Dev X]
4. **Work on story** using TDD, merge to main
5. **Mark [DONE]** when merged
6. **Unblock dependent stories** by changing [BLOCKED] → [ ] if deps now met

---

## Quick Start for Agents

**Just run this prompt:**
```
Read WORK_QUEUE.md and follow the Agent Prompt. You are Dev [1/2/3].
```

---

## Agent Prompt

```
You are an autonomous dev agent. Complete ONE story per session, then stop.

1. Read WORK_QUEUE.md
2. Find a [ ] story (not [BLOCKED]) whose dependencies are all [DONE] or ✅
3. Claim it: edit WORK_QUEUE.md, change [ ] to [IN PROGRESS: Dev N]
4. Read full story file from docs/sprint-artifacts/stories/ directory
5. Implement with TDD (write tests first)
6. Run tests, fix until passing
7. Commit and merge to main
8. Edit WORK_QUEUE.md: change [IN PROGRESS: Dev N] to [DONE]
9. Check if any [BLOCKED] stories can now be [ ] (deps now met)
10. STOP and output: "Story X-Y complete. Run /clear then restart me for next story."

STOP CONDITIONS:
- Story completed successfully → output completion message
- No [ ] stories available → output "Queue empty or all blocked"
- Error/blocker encountered → output "BLOCKED: <reason>" and stop

IMPORTANT: Do NOT loop. Complete ONE story, then STOP so user can /clear context.
```
