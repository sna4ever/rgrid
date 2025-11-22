/**
 * ExecutionsTable component (Story 10-2)
 * Displays a table of recent executions with status, duration, and cost
 */
'use client';

import Link from 'next/link';
import type { ExecutionListItem } from '../lib/types';
import { formatCost, formatDate, formatDuration, truncate } from '../lib/utils';
import { StatusBadge } from './status-badge';

interface ExecutionsTableProps {
  executions: ExecutionListItem[];
  isLoading?: boolean;
  error?: string | null;
}

export function ExecutionsTable({ executions, isLoading, error }: ExecutionsTableProps) {
  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-xl p-8 text-center" data-testid="loading-state">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="h-4 w-48 bg-gray-700 rounded" />
          <div className="h-4 w-32 bg-gray-700 rounded" />
        </div>
        <p className="text-gray-400 mt-4">Loading executions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-8 text-center" data-testid="error-state">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  if (!executions || executions.length === 0) {
    return (
      <div className="bg-gray-800 rounded-xl p-8 text-center" data-testid="empty-state">
        <p className="text-gray-400">No executions found.</p>
        <p className="text-gray-500 text-sm mt-2">
          Run <code className="text-emerald-400">rgrid run script.py</code> to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-xl overflow-hidden" data-testid="executions-table">
      <table className="min-w-full divide-y divide-gray-700">
        <thead className="bg-gray-900/50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
              Execution ID
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
              Started
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
              Duration
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
              Cost
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
              Exit Code
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700">
          {executions.map((execution) => (
            <tr
              key={execution.execution_id}
              className="hover:bg-gray-700/50 transition-colors"
              data-testid={`execution-row-${execution.execution_id}`}
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <Link
                  href={`/executions/${execution.execution_id}`}
                  className="text-emerald-400 hover:text-emerald-300 font-mono text-sm"
                >
                  {truncate(execution.execution_id, 20)}
                </Link>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={execution.status} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-gray-300 text-sm">
                {formatDate(execution.started_at || execution.created_at)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-gray-300 text-sm">
                {formatDuration(execution.duration_seconds)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-gray-300 text-sm font-mono">
                {formatCost(execution.cost_micros)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <ExitCodeDisplay exitCode={execution.exit_code} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExitCodeDisplay({ exitCode }: { exitCode: number | null }) {
  if (exitCode === null) {
    return <span className="text-gray-500">-</span>;
  }

  const isSuccess = exitCode === 0;
  return (
    <span
      className={`font-mono text-sm ${isSuccess ? 'text-green-400' : 'text-red-400'}`}
      data-testid="exit-code"
    >
      {exitCode}
    </span>
  );
}

export default ExecutionsTable;
