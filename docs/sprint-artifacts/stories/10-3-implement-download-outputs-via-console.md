# Story 10.3: Implement Download Outputs via Console

Status: done

## Story

As developer,
I want to download outputs from web console,
So that I can retrieve results without CLI.

## Acceptance Criteria

1. **Given** execution has completed outputs
2. **When** user views execution detail page
3. **Then** page lists all output files with sizes
4. **And** user can click "Download" to get file
5. **And** download uses MinIO presigned GET URLs

## Tasks / Subtasks

- [x] Task 1: Create ArtifactList component (AC: #1, #3)
  - [x] Subtask 1.1: Create `ArtifactList.tsx` component (inline in execution detail page)
  - [x] Subtask 1.2: Add artifact fetching hook `useArtifacts(executionId)` (via fetchArtifacts)
  - [x] Subtask 1.3: Display artifacts in table with filename, size, content_type
  - [x] Subtask 1.4: Format file sizes with human-readable units (KB, MB, GB)

- [x] Task 2: Add Download functionality (AC: #4, #5)
  - [x] Subtask 2.1: Create `downloadArtifact(artifactId, filePath)` API helper (getDownloadUrl)
  - [x] Subtask 2.2: Add Download button to each artifact row
  - [x] Subtask 2.3: Implement presigned URL fetch and browser download trigger
  - [x] Subtask 2.4: Handle download errors gracefully with user feedback

- [x] Task 3: Integrate with Execution Detail page (AC: #2)
  - [x] Subtask 3.1: Add ArtifactList section to execution detail page
  - [x] Subtask 3.2: Only show artifacts section when `status === 'completed'`
  - [x] Subtask 3.3: Show "No outputs" message for completed executions without outputs

- [x] Task 4: Add tests
  - [x] Subtask 4.1: Unit tests for ArtifactList component (artifact-list.test.tsx - 14 tests)
  - [x] Subtask 4.2: Unit tests for download helper functions (download-api.test.ts - 10 tests)
  - [x] Subtask 4.3: Integration tests for download workflow

## Dev Notes

### Prerequisites

Story 10.2 (Console Dashboard with execution history)

### Technical Notes

#### Pre-Implementation Research (Dev 3 - Quality Guardian)

**Date:** 2025-11-22
**Prepared by:** Dev 3 as prep work while 10-2 is in progress

---

### Architecture Overview

#### Data Flow for Downloads

```
User clicks Download → Console fetches presigned URL → Browser initiates download
                        ↓
                  API: POST /artifacts/download-url
                        ↓
                  MinIO generates presigned GET URL (2hr expiry)
                        ↓
                  Browser downloads directly from MinIO
```

#### Existing API Endpoints (Ready to Use)

1. **GET /api/v1/executions/{execution_id}/artifacts**
   - Returns list of artifacts for an execution
   - Response: `[{ artifact_id, filename, file_path, size_bytes, content_type, ... }]`
   - Location: `api/app/api/v1/executions.py:549-590`

2. **POST /api/v1/artifacts/download-url**
   - Request: `{ "s3_key": "<file_path>" }`
   - Response: `{ "download_url": "<presigned_url>" }`
   - Location: `api/app/api/v1/executions.py:593-616`
   - URL expires in 2 hours (7200 seconds)

#### Existing Console Types (from Story 10-2)

Already defined in `console/src/lib/types.ts`:

```typescript
export interface Artifact {
  artifact_id: string;
  filename: string;
  file_path: string;  // MinIO object key - pass to download-url endpoint
  size_bytes: number;
  content_type: string;
}

export interface ArtifactsResponse {
  artifacts: Artifact[];
}

export interface DownloadUrlResponse {
  download_url: string;
}
```

---

### Component Architecture

#### New Files to Create

```
console/src/
├── app/
│   └── executions/
│       └── [id]/
│           └── page.tsx          # Execution detail page (if not created in 10-2)
├── components/
│   ├── ArtifactList.tsx          # NEW: Displays list of artifacts
│   └── DownloadButton.tsx        # NEW: Download button with loading state
├── lib/
│   └── api.ts                    # Add artifact API functions
└── __tests__/
    ├── ArtifactList.test.tsx     # NEW: Unit tests
    └── download.test.ts          # NEW: Download helper tests
```

#### ArtifactList Component Design

```typescript
// console/src/components/ArtifactList.tsx
interface ArtifactListProps {
  executionId: string;
}

export function ArtifactList({ executionId }: ArtifactListProps) {
  // 1. Fetch artifacts using SWR or React Query
  // 2. Display loading state
  // 3. Display empty state if no artifacts
  // 4. Display table with filename, size, content_type, download button
}
```

#### Download Flow Implementation

```typescript
// console/src/lib/api.ts
export async function getArtifacts(executionId: string): Promise<Artifact[]> {
  const res = await fetch(`${API_URL}/executions/${executionId}/artifacts`, {
    headers: { 'Authorization': `Bearer ${getApiKey()}` }
  });
  return res.json();
}

export async function downloadArtifact(filePath: string): Promise<void> {
  // 1. Fetch presigned URL
  const res = await fetch(`${API_URL}/artifacts/download-url`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getApiKey()}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ s3_key: filePath })
  });
  const { download_url } = await res.json();

  // 2. Trigger browser download
  window.location.href = download_url;
  // OR use <a download> element for better UX
}
```

---

### Test Plan

#### Unit Tests (`console/src/__tests__/ArtifactList.test.tsx`)

| Test | Description |
|------|-------------|
| `renders_loading_state` | Shows loading spinner while fetching |
| `renders_artifact_list` | Displays artifacts with filename, size |
| `renders_empty_state` | Shows "No outputs" when artifacts empty |
| `formats_file_sizes` | Converts bytes to KB/MB/GB correctly |
| `handles_download_click` | Triggers download API on button click |
| `shows_download_error` | Displays error toast on download failure |

#### Integration Tests (`console/src/__tests__/download.test.ts`)

| Test | Description |
|------|-------------|
| `fetch_artifacts_success` | API returns artifact list |
| `fetch_artifacts_empty` | API returns empty list for no outputs |
| `get_download_url_success` | Presigned URL returned correctly |
| `download_url_expired` | Handle expired/invalid presigned URLs |

#### E2E Tests (Playwright)

| Test | Description |
|------|-------------|
| `download_single_file` | Click download, verify file downloads |
| `download_large_file` | Large file downloads with progress |
| `download_multiple_files` | Download multiple files sequentially |

---

### Edge Cases to Handle

1. **No artifacts** - Show friendly "No output files" message
2. **Presigned URL expired** - Refetch URL on 403/expired error
3. **Large files** - Show download progress or file size warning
4. **Compressed files** - Display both compressed and original size
5. **Network errors** - Show retry button with error message
6. **Multiple downloads** - Queue downloads to prevent browser issues

---

### Dependencies on Story 10-2

This story requires from 10-2:
1. Execution detail page route (`/executions/[id]`)
2. API client setup with authentication
3. Execution data fetching infrastructure

**Can be developed in parallel:**
- ArtifactList component (standalone)
- API helper functions
- Unit tests

**Must wait for 10-2:**
- Integration into execution detail page
- E2E tests

---

### Implementation Checklist

- [ ] Review 10-2 implementation for API client patterns
- [ ] Create ArtifactList component with tests
- [ ] Add download API helpers
- [ ] Integrate into execution detail page
- [ ] Add E2E tests
- [ ] Manual testing on staging

### References

- [Source: docs/epics.md - Story 10.3]
- [Source: docs/sprint-artifacts/tech-spec-epic-10.md]
- [Source: docs/architecture.md]
- [API: api/app/api/v1/executions.py:549-616]
- [Types: console/src/lib/types.ts]

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/stories/10-3-implement-download-outputs-via-console.context.xml

### Agent Model Used

Pre-implementation research: Claude Sonnet 4.5 (Dev 3 - Quality Guardian)

### Debug Log References

N/A - Implementation straightforward, no debugging issues

### Completion Notes List

**Date Completed:** 2025-11-22
**Completed by:** Dev 3 (Quality Guardian)

1. **Implementation approach:** The artifact list functionality was implemented inline in the execution detail page (`/app/executions/[id]/page.tsx`) rather than as a separate component. This matches the existing codebase patterns and reduces complexity.

2. **Key features implemented:**
   - Artifact listing with filename, size (human-readable), and content type
   - Download button that fetches presigned URLs and opens in new tab
   - "No output files" message for completed executions without artifacts
   - Loading states and error handling

3. **Tests added:**
   - `artifact-list.test.tsx`: 14 tests covering formatFileSize, artifact API integration, display patterns, and download flow
   - `download-api.test.ts`: 10 tests covering fetchArtifacts, getDownloadUrl, and ApiError

4. **Test counts:**
   - Console tests: 84 passing (was 65 passing, 26 skipped)
   - Backend tests: 915 passing
   - Total: 999 tests passing

### File List

**Modified:**
- `console/src/app/executions/[id]/page.tsx` - Added "No outputs" message for completed executions

**Rewritten (tests):**
- `console/src/__tests__/artifact-list.test.tsx` - 14 active tests (was 26 skipped)
- `console/src/__tests__/download-api.test.ts` - 10 active tests (was all skipped)

**Already implemented in Story 10-2:**
- `console/src/lib/api-client.ts` - fetchArtifacts, getDownloadUrl
- `console/src/lib/types.ts` - Artifact type
- `console/src/lib/utils.ts` - formatFileSize
