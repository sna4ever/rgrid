/**
 * Tests for Artifact List functionality (Story 10-3)
 *
 * Tests the artifact display and download patterns used in the execution detail page.
 * The artifact list is implemented inline in /app/executions/[id]/page.tsx
 *
 * Acceptance Criteria:
 * - AC#1: Execution has completed outputs
 * - AC#3: Page lists all output files with sizes
 * - AC#4: User can click "Download" to get file
 * - AC#5: Download uses MinIO presigned GET URLs
 */
import { formatFileSize } from '../lib/utils';
import { fetchArtifacts, getDownloadUrl } from '../lib/api-client';

// Mock fetch for API calls
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock artifacts data matching the Artifact type
const mockArtifacts = [
  {
    artifact_id: 'art_123',
    filename: 'output.csv',
    file_path: 'executions/exec_abc/outputs/output.csv',
    size_bytes: 1024,
    content_type: 'text/csv',
  },
  {
    artifact_id: 'art_456',
    filename: 'results.json',
    file_path: 'executions/exec_abc/outputs/results.json',
    size_bytes: 2048000, // ~2MB
    content_type: 'application/json',
  },
  {
    artifact_id: 'art_789',
    filename: 'large_file.parquet',
    file_path: 'executions/exec_abc/outputs/data/nested/large_file.parquet',
    size_bytes: 1073741824, // 1GB
    content_type: 'application/octet-stream',
  },
];

describe('formatFileSize (Story 10-3 - AC#3)', () => {
  it('formats bytes correctly', () => {
    expect(formatFileSize(100)).toBe('100 B');
    expect(formatFileSize(500)).toBe('500 B');
  });

  it('formats kilobytes correctly', () => {
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
    expect(formatFileSize(10240)).toBe('10 KB');
  });

  it('formats megabytes correctly', () => {
    expect(formatFileSize(1048576)).toBe('1 MB');
    expect(formatFileSize(2097152)).toBe('2 MB');
    expect(formatFileSize(5242880)).toBe('5 MB');
  });

  it('formats gigabytes correctly', () => {
    expect(formatFileSize(1073741824)).toBe('1 GB');
    expect(formatFileSize(2147483648)).toBe('2 GB');
  });

  it('handles zero bytes', () => {
    expect(formatFileSize(0)).toBe('0 B');
  });

  it('handles edge case sizes', () => {
    // Just under 1KB
    expect(formatFileSize(1023)).toBe('1023 B');
    // Just over 1KB
    expect(formatFileSize(1025)).toBe('1 KB');
  });
});

describe('Artifact API Integration (Story 10-3 - AC#1, AC#5)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('fetchArtifacts', () => {
    it('returns artifacts for a completed execution', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockArtifacts,
      });

      const artifacts = await fetchArtifacts('test_key', 'exec_abc');

      expect(artifacts).toHaveLength(3);
      expect(artifacts[0].filename).toBe('output.csv');
      expect(artifacts[0].size_bytes).toBe(1024);
      expect(artifacts[0].content_type).toBe('text/csv');
    });

    it('returns empty array for execution without outputs', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => [],
      });

      const artifacts = await fetchArtifacts('test_key', 'exec_no_outputs');

      expect(artifacts).toHaveLength(0);
    });
  });

  describe('getDownloadUrl (AC#4, AC#5)', () => {
    it('returns MinIO presigned URL for artifact download', async () => {
      const presignedUrl = 'https://minio.rgrid.dev/bucket/key?X-Amz-Signature=abc123';
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ download_url: presignedUrl }),
      });

      const url = await getDownloadUrl('test_key', 'executions/exec_abc/outputs/output.csv');

      expect(url).toBe(presignedUrl);
      expect(url).toContain('minio');
    });
  });
});

describe('Artifact Display Patterns', () => {
  it('extracts filename from full path', () => {
    // Pattern used in UI: display filename property directly
    const artifact = mockArtifacts[2];
    expect(artifact.filename).toBe('large_file.parquet');
  });

  it('formats all mock artifacts correctly', () => {
    // Validate that formatFileSize handles all our test cases
    const formatted = mockArtifacts.map((a) => ({
      filename: a.filename,
      formattedSize: formatFileSize(a.size_bytes),
    }));

    expect(formatted).toEqual([
      { filename: 'output.csv', formattedSize: '1 KB' },
      { filename: 'results.json', formattedSize: '2 MB' },
      { filename: 'large_file.parquet', formattedSize: '1 GB' },
    ]);
  });

  it('artifact has all required display fields', () => {
    // Verify artifact shape matches what UI expects
    const artifact = mockArtifacts[0];

    expect(artifact).toHaveProperty('artifact_id');
    expect(artifact).toHaveProperty('filename');
    expect(artifact).toHaveProperty('file_path');
    expect(artifact).toHaveProperty('size_bytes');
    expect(artifact).toHaveProperty('content_type');
  });
});

describe('Download Flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('download flow: fetch artifacts -> select artifact -> get presigned URL', async () => {
    // Step 1: Fetch artifacts list
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockArtifacts,
    });

    const artifacts = await fetchArtifacts('test_key', 'exec_abc');
    expect(artifacts).toHaveLength(3);

    // Step 2: User clicks download on first artifact
    const selectedArtifact = artifacts[0];
    expect(selectedArtifact.file_path).toBe('executions/exec_abc/outputs/output.csv');

    // Step 3: Fetch presigned URL
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ download_url: 'https://minio.rgrid.dev/presigned' }),
    });

    const downloadUrl = await getDownloadUrl('test_key', selectedArtifact.file_path);
    expect(downloadUrl).toBe('https://minio.rgrid.dev/presigned');
  });

  it('handles download error gracefully', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Artifact not found' }),
    });

    await expect(getDownloadUrl('test_key', 'invalid/path')).rejects.toThrow(
      'Artifact not found'
    );
  });
});
