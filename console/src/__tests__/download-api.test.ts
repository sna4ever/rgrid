/**
 * Tests for Download API helpers (Story 10-3)
 *
 * Tests for:
 * - fetchArtifacts(apiKey, executionId) - Fetch artifacts list from API
 * - getDownloadUrl(apiKey, s3Key) - Get presigned URL
 */
import { fetchArtifacts, getDownloadUrl, ApiError } from '../lib/api-client';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('Artifact API Functions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('fetchArtifacts', () => {
    it('fetches artifacts for an execution', async () => {
      const mockArtifacts = [
        {
          artifact_id: 'art_1',
          filename: 'output.csv',
          file_path: 'executions/exec_abc/outputs/output.csv',
          size_bytes: 1024,
          content_type: 'text/csv',
        },
      ];
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockArtifacts,
      });

      const result = await fetchArtifacts('test_api_key', 'exec_abc123');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/executions/exec_abc123/artifacts'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Key': 'test_api_key',
          }),
        })
      );
      expect(result).toEqual(mockArtifacts);
    });

    it('returns empty array when no artifacts exist', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => [],
      });

      const result = await fetchArtifacts('test_api_key', 'exec_abc123');
      expect(result).toEqual([]);
    });

    it('handles wrapped response format', async () => {
      const mockArtifacts = [
        {
          artifact_id: 'art_1',
          filename: 'output.csv',
          file_path: 'path/to/file',
          size_bytes: 1024,
          content_type: 'text/csv',
        },
      ];
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ artifacts: mockArtifacts }),
      });

      const result = await fetchArtifacts('test_api_key', 'exec_abc123');
      expect(result).toEqual(mockArtifacts);
    });

    it('throws ApiError on 404 (execution not found)', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Execution not found' }),
      });

      await expect(fetchArtifacts('test_api_key', 'exec_invalid')).rejects.toThrow(
        'Execution not found'
      );
    });

    it('throws ApiError on network failure', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));

      await expect(fetchArtifacts('test_api_key', 'exec_abc123')).rejects.toThrow(
        'Network error'
      );
    });

    it('throws ApiError on 401 unauthorized', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'Unauthorized' }),
      });

      await expect(fetchArtifacts('test_api_key', 'exec_abc123')).rejects.toThrow(
        'Unauthorized'
      );
    });
  });

  describe('getDownloadUrl', () => {
    it('fetches presigned download URL for artifact', async () => {
      const mockPresignedUrl = 'https://minio.rgrid.dev/bucket/key?signature=xxx';
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ download_url: mockPresignedUrl }),
      });

      const result = await getDownloadUrl(
        'test_api_key',
        'executions/exec_abc/outputs/output.csv'
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/artifacts/download-url'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ s3_key: 'executions/exec_abc/outputs/output.csv' }),
        })
      );
      expect(result).toBe(mockPresignedUrl);
    });

    it('throws error when s3_key is invalid', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Missing s3_key in request' }),
      });

      await expect(getDownloadUrl('test_api_key', '')).rejects.toThrow(
        'Missing s3_key'
      );
    });

    it('throws error on 401 unauthorized', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'Invalid API key' }),
      });

      await expect(
        getDownloadUrl('invalid_key', 'some/path')
      ).rejects.toThrow('Invalid API key');
    });
  });
});

describe('ApiError', () => {
  it('contains status code and response data', () => {
    const error = new ApiError('Not found', 404, { detail: 'Not found' });

    expect(error.message).toBe('Not found');
    expect(error.status).toBe(404);
    expect(error.response).toEqual({ detail: 'Not found' });
    expect(error.name).toBe('ApiError');
  });
});
