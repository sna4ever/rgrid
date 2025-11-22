/* eslint-disable @typescript-eslint/ban-ts-comment */
/**
 * Tests for Download API helpers (Story 10-3)
 *
 * TDD: Test stubs written first, implementation pending
 * Prepared by: Dev 3 (Quality Guardian) during 10-3 prep
 *
 * Tests for:
 * - getArtifacts(executionId) - Fetch artifacts list from API
 * - downloadArtifact(filePath) - Get presigned URL and trigger download
 */

// TODO: Import API functions when created
// import { getArtifacts, downloadArtifact, getDownloadUrl } from '../lib/api';

// Mock fetch
global.fetch = jest.fn();

// Mock window.location for download testing
// Note: window.location is read-only in JSDOM, use delete workaround
const mockLocationHref = jest.fn();
const originalLocation = window.location;

beforeAll(() => {
  // @ts-expect-error - Deliberately deleting read-only property for testing
  delete window.location;
  window.location = {
    ...originalLocation,
    href: '',
    assign: mockLocationHref,
  } as unknown as Location;
});

afterAll(() => {
  window.location = originalLocation;
});

describe('Artifact API Functions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getArtifacts', () => {
    it.skip('fetches artifacts for an execution', async () => {
      // TODO: Implement when API helper created
      // const mockArtifacts = [
      //   { artifact_id: 'art_1', filename: 'output.csv', size_bytes: 1024 },
      // ];
      // (global.fetch as jest.Mock).mockResolvedValue({
      //   ok: true,
      //   json: async () => mockArtifacts,
      // });
      //
      // const result = await getArtifacts('exec_abc123');
      //
      // expect(global.fetch).toHaveBeenCalledWith(
      //   expect.stringContaining('/executions/exec_abc123/artifacts'),
      //   expect.objectContaining({
      //     headers: expect.objectContaining({
      //       'Authorization': expect.stringContaining('Bearer'),
      //     }),
      //   })
      // );
      // expect(result).toEqual(mockArtifacts);
    });

    it.skip('returns empty array when no artifacts exist', async () => {
      // TODO: Implement when API helper created
      // (global.fetch as jest.Mock).mockResolvedValue({
      //   ok: true,
      //   json: async () => [],
      // });
      //
      // const result = await getArtifacts('exec_abc123');
      // expect(result).toEqual([]);
    });

    it.skip('throws error on 404 (execution not found)', async () => {
      // TODO: Implement when API helper created
      // (global.fetch as jest.Mock).mockResolvedValue({
      //   ok: false,
      //   status: 404,
      //   json: async () => ({ detail: 'Execution not found' }),
      // });
      //
      // await expect(getArtifacts('exec_invalid')).rejects.toThrow('Execution not found');
    });

    it.skip('throws error on network failure', async () => {
      // TODO: Implement when API helper created
      // (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));
      //
      // await expect(getArtifacts('exec_abc123')).rejects.toThrow('Network error');
    });

    it.skip('handles 401 unauthorized error', async () => {
      // TODO: Implement when API helper created
      // Should prompt re-authentication or show error
      // (global.fetch as jest.Mock).mockResolvedValue({
      //   ok: false,
      //   status: 401,
      //   json: async () => ({ detail: 'Unauthorized' }),
      // });
      //
      // await expect(getArtifacts('exec_abc123')).rejects.toThrow('Unauthorized');
    });
  });

  describe('getDownloadUrl', () => {
    it.skip('fetches presigned download URL for artifact', async () => {
      // TODO: Implement when API helper created
      // const mockPresignedUrl = 'https://minio.rgrid.dev/bucket/key?signature=xxx';
      // (global.fetch as jest.Mock).mockResolvedValue({
      //   ok: true,
      //   json: async () => ({ download_url: mockPresignedUrl }),
      // });
      //
      // const result = await getDownloadUrl('executions/exec_abc/outputs/output.csv');
      //
      // expect(global.fetch).toHaveBeenCalledWith(
      //   expect.stringContaining('/artifacts/download-url'),
      //   expect.objectContaining({
      //     method: 'POST',
      //     body: JSON.stringify({ s3_key: 'executions/exec_abc/outputs/output.csv' }),
      //   })
      // );
      // expect(result).toBe(mockPresignedUrl);
    });

    it.skip('throws error when s3_key is missing', async () => {
      // TODO: Implement when API helper created
      // (global.fetch as jest.Mock).mockResolvedValue({
      //   ok: false,
      //   status: 400,
      //   json: async () => ({ detail: 'Missing s3_key in request' }),
      // });
      //
      // await expect(getDownloadUrl('')).rejects.toThrow('Missing s3_key');
    });

    it.skip('handles expired URL scenario (subsequent request)', async () => {
      // TODO: Implement when API helper created
      // Presigned URLs expire - should handle gracefully
    });
  });

  describe('downloadArtifact', () => {
    it.skip('triggers browser download with presigned URL', async () => {
      // TODO: Implement when API helper created
      // const mockPresignedUrl = 'https://minio.rgrid.dev/bucket/key?signature=xxx';
      // (global.fetch as jest.Mock).mockResolvedValue({
      //   ok: true,
      //   json: async () => ({ download_url: mockPresignedUrl }),
      // });
      //
      // await downloadArtifact('executions/exec_abc/outputs/output.csv');
      //
      // expect(mockLocationHref).toHaveBeenCalledWith(mockPresignedUrl);
    });

    it.skip('handles download failure gracefully', async () => {
      // TODO: Implement when API helper created
      // (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));
      //
      // await expect(downloadArtifact('invalid/path')).rejects.toThrow();
    });
  });
});

describe('Download Edge Cases', () => {
  describe('Large Files', () => {
    it.skip('warns user before downloading files > 100MB', async () => {
      // TODO: Implement if UX requirement
      // Should show confirmation dialog for large files
    });

    it.skip('handles timeout for large file URL generation', async () => {
      // TODO: Implement when API helper created
      // Large files may take longer - should have appropriate timeout
    });
  });

  describe('Multiple Downloads', () => {
    it.skip('queues multiple downloads to prevent browser issues', async () => {
      // TODO: Implement if UX requirement
      // Browsers may block multiple simultaneous downloads
    });
  });

  describe('Presigned URL Expiry', () => {
    it.skip('refetches URL if download fails with 403', async () => {
      // TODO: Implement when API helper created
      // Presigned URLs expire after 2 hours - should retry with new URL
    });
  });
});
