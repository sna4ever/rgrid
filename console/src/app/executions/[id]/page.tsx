/**
 * Execution Detail page (Story 10-2)
 * Shows full execution details including logs and artifacts
 */
'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { StatusBadge } from '../../../components/status-badge';
import { fetchExecution, fetchArtifacts, getDownloadUrl } from '../../../lib/api-client';
import { formatCost, formatDate, formatDuration, formatFileSize } from '../../../lib/utils';
import type { Execution, Artifact } from '../../../lib/types';

// For demo/development, use a placeholder API key
const DEMO_API_KEY = process.env.NEXT_PUBLIC_DEMO_API_KEY || '';

export default function ExecutionDetailPage() {
  const params = useParams();
  const executionId = params.id as string;

  const [execution, setExecution] = useState<Execution | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'stdout' | 'stderr'>('stdout');
  const [apiKey] = useState(DEMO_API_KEY);

  useEffect(() => {
    async function loadExecution() {
      if (!apiKey) {
        setError('API key required. Please visit the dashboard first.');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const [execData, artifactsData] = await Promise.all([
          fetchExecution(apiKey, executionId),
          fetchArtifacts(apiKey, executionId).catch(() => []),
        ]);
        setExecution(execData);
        setArtifacts(artifactsData);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('Failed to load execution');
        }
      } finally {
        setIsLoading(false);
      }
    }

    loadExecution();
  }, [executionId, apiKey]);

  // Poll for updates if execution is still running
  useEffect(() => {
    if (!execution || !apiKey) return;
    if (execution.status !== 'running' && execution.status !== 'queued') return;

    const interval = setInterval(async () => {
      try {
        const updated = await fetchExecution(apiKey, executionId);
        setExecution(updated);
      } catch {
        // Ignore polling errors
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [execution, executionId, apiKey]);

  async function handleDownload(artifact: Artifact) {
    try {
      const url = await getDownloadUrl(apiKey, artifact.file_path);
      window.open(url, '_blank');
    } catch {
      alert('Failed to get download URL');
    }
  }

  if (isLoading) {
    return (
      <PageWrapper>
        <div className="animate-pulse flex flex-col gap-4">
          <div className="h-8 w-48 bg-gray-700 rounded" />
          <div className="h-4 w-96 bg-gray-700 rounded" />
          <div className="h-64 bg-gray-800 rounded-xl" />
        </div>
      </PageWrapper>
    );
  }

  if (error) {
    return (
      <PageWrapper>
        <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-8 text-center">
          <p className="text-red-400">{error}</p>
          <Link
            href="/dashboard"
            className="inline-block mt-4 text-emerald-400 hover:text-emerald-300"
          >
            Back to Dashboard
          </Link>
        </div>
      </PageWrapper>
    );
  }

  if (!execution) {
    return (
      <PageWrapper>
        <div className="text-center">
          <p className="text-gray-400">Execution not found</p>
        </div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper>
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-4 mb-2">
            <h1 className="text-2xl font-bold font-mono">{execution.execution_id}</h1>
            <StatusBadge status={execution.status} />
          </div>
          <p className="text-gray-400">
            Created {formatDate(execution.created_at)}
          </p>
        </div>
        <Link
          href="/dashboard"
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium transition-colors"
        >
          Back to Dashboard
        </Link>
      </div>

      {/* Metadata Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <MetadataCard label="Runtime" value={execution.runtime} />
        <MetadataCard label="Duration" value={formatDuration(execution.duration_seconds)} />
        <MetadataCard label="Cost" value={formatCost(execution.cost_micros)} />
        <MetadataCard
          label="Exit Code"
          value={execution.exit_code?.toString() ?? '-'}
          isError={execution.exit_code !== null && execution.exit_code !== 0}
        />
      </div>

      {/* Script Content */}
      {execution.script_content && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Script</h2>
          <pre className="bg-gray-800 rounded-xl p-4 overflow-x-auto text-sm font-mono text-gray-300">
            {execution.script_content}
          </pre>
        </div>
      )}

      {/* Logs */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-4">Logs</h2>
        <div className="bg-gray-800 rounded-xl overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-gray-700">
            <button
              onClick={() => setActiveTab('stdout')}
              className={`px-6 py-3 text-sm font-medium transition-colors ${
                activeTab === 'stdout'
                  ? 'text-emerald-400 border-b-2 border-emerald-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              stdout
            </button>
            <button
              onClick={() => setActiveTab('stderr')}
              className={`px-6 py-3 text-sm font-medium transition-colors ${
                activeTab === 'stderr'
                  ? 'text-emerald-400 border-b-2 border-emerald-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              stderr
              {execution.stderr && (
                <span className="ml-2 px-1.5 py-0.5 bg-red-500/20 text-red-400 text-xs rounded">
                  !
                </span>
              )}
            </button>
          </div>
          {/* Log Content */}
          <pre className="p-4 overflow-x-auto text-sm font-mono text-gray-300 max-h-96 overflow-y-auto">
            {activeTab === 'stdout'
              ? execution.stdout || '(no output)'
              : execution.stderr || '(no errors)'}
          </pre>
          {execution.output_truncated && (
            <div className="px-4 py-2 bg-yellow-900/20 text-yellow-400 text-sm">
              Output was truncated. Use the CLI for full logs: rgrid logs {execution.execution_id}
            </div>
          )}
        </div>
      </div>

      {/* Execution Error */}
      {execution.execution_error && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-4 text-red-400">Execution Error</h2>
          <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-4">
            <pre className="text-red-300 text-sm font-mono whitespace-pre-wrap">
              {execution.execution_error}
            </pre>
          </div>
        </div>
      )}

      {/* Artifacts */}
      {artifacts.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Output Artifacts</h2>
          <div className="bg-gray-800 rounded-xl divide-y divide-gray-700">
            {artifacts.map((artifact) => (
              <div
                key={artifact.artifact_id}
                className="flex items-center justify-between px-4 py-3"
              >
                <div>
                  <p className="text-white font-medium">{artifact.filename}</p>
                  <p className="text-gray-400 text-sm">
                    {formatFileSize(artifact.size_bytes)} &middot; {artifact.content_type}
                  </p>
                </div>
                <button
                  onClick={() => handleDownload(artifact)}
                  className="px-4 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 rounded-lg text-sm font-medium transition-colors"
                >
                  Download
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* User Metadata */}
      {Object.keys(execution.user_metadata || {}).length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Metadata</h2>
          <div className="bg-gray-800 rounded-xl p-4">
            <dl className="grid grid-cols-2 gap-4">
              {Object.entries(execution.user_metadata).map(([key, value]) => (
                <div key={key}>
                  <dt className="text-gray-400 text-sm">{key}</dt>
                  <dd className="text-white font-mono">{value}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      )}
    </PageWrapper>
  );
}

function PageWrapper({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black text-white">
      <nav className="flex justify-between items-center px-8 py-6 max-w-7xl mx-auto">
        <Link href="/" className="text-2xl font-bold">
          <span className="text-emerald-400">R</span>Grid
        </Link>
        <div className="flex gap-6 items-center">
          <Link href="/dashboard" className="text-gray-300 hover:text-white transition-colors">
            Dashboard
          </Link>
          <a href="https://docs.rgrid.dev" className="text-gray-300 hover:text-white transition-colors">
            Docs
          </a>
        </div>
      </nav>
      <main className="px-8 py-8 max-w-7xl mx-auto">{children}</main>
    </div>
  );
}

interface MetadataCardProps {
  label: string;
  value: string;
  isError?: boolean;
}

function MetadataCard({ label, value, isError }: MetadataCardProps) {
  return (
    <div className="bg-gray-800 rounded-xl p-4">
      <p className="text-gray-400 text-sm">{label}</p>
      <p className={`text-lg font-mono ${isError ? 'text-red-400' : 'text-white'}`}>
        {value}
      </p>
    </div>
  );
}
