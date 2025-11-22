/**
 * Dashboard page (Story 10-2)
 * Main dashboard showing execution history table
 */
'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { ExecutionsTable } from '../../components/executions-table';
import { fetchExecutions } from '../../lib/api-client';
import type { ExecutionListItem } from '../../lib/types';

// For demo/development, use a placeholder API key
// In production, this would come from Clerk session or user settings
const DEMO_API_KEY = process.env.NEXT_PUBLIC_DEMO_API_KEY || '';

export default function DashboardPage() {
  const [executions, setExecutions] = useState<ExecutionListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState(DEMO_API_KEY);
  const [showApiKeyInput, setShowApiKeyInput] = useState(!DEMO_API_KEY);

  const loadExecutions = useCallback(async () => {
    if (!apiKey) {
      setShowApiKeyInput(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await fetchExecutions(apiKey, { limit: 50 });
      setExecutions(data);
      setShowApiKeyInput(false);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to load executions');
      }
    } finally {
      setIsLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    loadExecutions();
  }, [loadExecutions]);

  // Polling for updates every 10 seconds when there are running executions
  useEffect(() => {
    const hasRunning = executions.some((e) => e.status === 'running' || e.status === 'queued');
    if (!hasRunning || !apiKey) return;

    const interval = setInterval(loadExecutions, 10000);
    return () => clearInterval(interval);
  }, [executions, apiKey, loadExecutions]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black text-white">
      {/* Navigation */}
      <nav className="flex justify-between items-center px-8 py-6 max-w-7xl mx-auto">
        <Link href="/" className="text-2xl font-bold">
          <span className="text-emerald-400">R</span>Grid
        </Link>
        <div className="flex gap-6 items-center">
          <Link href="/dashboard" className="text-emerald-400 font-medium">
            Dashboard
          </Link>
          <a href="https://docs.rgrid.dev" className="text-gray-300 hover:text-white transition-colors">
            Docs
          </a>
        </div>
      </nav>

      {/* Main Content */}
      <main className="px-8 py-8 max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">Executions</h1>
            <p className="text-gray-400 mt-1">View and manage your script executions</p>
          </div>
          <button
            onClick={loadExecutions}
            disabled={isLoading}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {/* API Key Input (shown when no key is set) */}
        {showApiKeyInput && (
          <div className="bg-gray-800 rounded-xl p-6 mb-8">
            <h2 className="text-lg font-semibold mb-4">Enter your API Key</h2>
            <p className="text-gray-400 text-sm mb-4">
              Get your API key from your RGrid account settings or use the CLI:{' '}
              <code className="text-emerald-400">rgrid auth</code>
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                loadExecutions();
              }}
              className="flex gap-4"
            >
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your API key"
                className="flex-1 px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
              />
              <button
                type="submit"
                className="px-6 py-2 bg-emerald-500 hover:bg-emerald-600 rounded-lg font-medium transition-colors"
              >
                Connect
              </button>
            </form>
          </div>
        )}

        {/* Executions Table */}
        <ExecutionsTable executions={executions} isLoading={isLoading} error={error} />

        {/* Quick Stats */}
        {executions.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
            <StatCard
              label="Total Executions"
              value={executions.length.toString()}
            />
            <StatCard
              label="Running"
              value={executions.filter((e) => e.status === 'running').length.toString()}
              highlight={executions.some((e) => e.status === 'running')}
            />
            <StatCard
              label="Completed"
              value={executions.filter((e) => e.status === 'completed').length.toString()}
            />
            <StatCard
              label="Failed"
              value={executions.filter((e) => e.status === 'failed').length.toString()}
              isError={executions.some((e) => e.status === 'failed')}
            />
          </div>
        )}
      </main>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  highlight?: boolean;
  isError?: boolean;
}

function StatCard({ label, value, highlight, isError }: StatCardProps) {
  const valueColor = isError
    ? 'text-red-400'
    : highlight
    ? 'text-blue-400'
    : 'text-white';

  return (
    <div className="bg-gray-800 rounded-xl p-4">
      <p className="text-gray-400 text-sm">{label}</p>
      <p className={`text-2xl font-bold ${valueColor}`}>{value}</p>
    </div>
  );
}
