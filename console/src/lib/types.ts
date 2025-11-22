/**
 * TypeScript types for RGrid Console (Story 10-2)
 * Matches API response structure from api/app/models/execution.py
 */

export type ExecutionStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface Execution {
  execution_id: string;
  status: ExecutionStatus;
  script_content?: string;
  runtime: string;
  args: string[];
  env_vars: Record<string, string>;
  input_files: string[];
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  exit_code: number | null;
  stdout: string | null;
  stderr: string | null;
  output_truncated?: boolean;
  execution_error?: string | null;
  cost_micros: number;
  user_metadata: Record<string, string>;
  retry_count: number;
  max_retries: number;
}

export interface ExecutionListItem {
  execution_id: string;
  status: ExecutionStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  exit_code: number | null;
  cost_micros: number;
  user_metadata: Record<string, string>;
}

export interface Artifact {
  artifact_id: string;
  filename: string;
  file_path: string;
  size_bytes: number;
  content_type: string;
}

export interface ExecutionsResponse {
  executions: ExecutionListItem[];
  total: number;
}

export interface ArtifactsResponse {
  artifacts: Artifact[];
}

export interface DownloadUrlResponse {
  download_url: string;
}
