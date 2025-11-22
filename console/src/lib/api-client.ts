/**
 * API Client for RGrid Console (Story 10-2)
 * Wraps backend API endpoints for execution management
 */
import type {
  Execution,
  ExecutionListItem,
  Artifact,
  ExecutionsResponse,
  ArtifactsResponse,
  DownloadUrlResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.rgrid.dev/api/v1';

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface FetchOptions {
  apiKey: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
}

async function fetchApi<T>(endpoint: string, options: FetchOptions): Promise<T> {
  const { apiKey, method = 'GET', body } = options;

  const headers: Record<string, string> = {
    'X-API-Key': apiKey,
    'Content-Type': 'application/json',
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      errorData.detail || `API request failed: ${response.statusText}`,
      response.status,
      errorData
    );
  }

  return response.json();
}

/**
 * Fetch list of executions
 */
export async function fetchExecutions(
  apiKey: string,
  options?: {
    limit?: number;
    status?: string;
    metadata?: Record<string, string>;
  }
): Promise<ExecutionListItem[]> {
  const params = new URLSearchParams();

  if (options?.limit) {
    params.set('limit', options.limit.toString());
  }
  if (options?.status) {
    params.set('status', options.status);
  }
  if (options?.metadata) {
    for (const [key, value] of Object.entries(options.metadata)) {
      params.set(`metadata[${key}]`, value);
    }
  }

  const queryString = params.toString();
  const endpoint = queryString ? `/executions?${queryString}` : '/executions';

  const response = await fetchApi<ExecutionsResponse | ExecutionListItem[]>(endpoint, { apiKey });

  // Handle both array response and wrapped response
  if (Array.isArray(response)) {
    return response;
  }
  return response.executions || [];
}

/**
 * Fetch single execution by ID
 */
export async function fetchExecution(
  apiKey: string,
  executionId: string
): Promise<Execution> {
  return fetchApi<Execution>(`/executions/${executionId}`, { apiKey });
}

/**
 * Fetch artifacts for an execution
 */
export async function fetchArtifacts(
  apiKey: string,
  executionId: string
): Promise<Artifact[]> {
  const response = await fetchApi<ArtifactsResponse | Artifact[]>(
    `/executions/${executionId}/artifacts`,
    { apiKey }
  );

  if (Array.isArray(response)) {
    return response;
  }
  return response.artifacts || [];
}

/**
 * Get download URL for an artifact
 */
export async function getDownloadUrl(
  apiKey: string,
  s3Key: string
): Promise<string> {
  const response = await fetchApi<DownloadUrlResponse>('/artifacts/download-url', {
    apiKey,
    method: 'POST',
    body: { s3_key: s3Key },
  });

  return response.download_url;
}

/**
 * Fetch execution logs
 */
export async function fetchLogs(
  apiKey: string,
  executionId: string
): Promise<{ stdout: string; stderr: string }> {
  return fetchApi<{ stdout: string; stderr: string }>(
    `/executions/${executionId}/logs`,
    { apiKey }
  );
}

/**
 * Retry a failed execution
 */
export async function retryExecution(
  apiKey: string,
  executionId: string
): Promise<Execution> {
  return fetchApi<Execution>(`/executions/${executionId}/retry`, {
    apiKey,
    method: 'POST',
  });
}
