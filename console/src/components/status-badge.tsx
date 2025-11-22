/**
 * StatusBadge component (Story 10-2)
 * Displays execution status with appropriate color coding
 */
import type { ExecutionStatus } from '../lib/types';
import { formatStatus } from '../lib/utils';

interface StatusBadgeProps {
  status: ExecutionStatus | string;
  className?: string;
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const { label, className: statusClassName } = formatStatus(status);

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusClassName} ${className}`}
      data-testid="status-badge"
      data-status={status}
    >
      {status === 'running' && (
        <span className="mr-1.5 h-2 w-2 rounded-full bg-current animate-pulse" />
      )}
      {label}
    </span>
  );
}

export default StatusBadge;
