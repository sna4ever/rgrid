/**
 * Utility functions for RGrid Console (Story 10-2)
 */
import type { ExecutionStatus } from './types';

/**
 * Format cost in micros (1M micros = €1) to readable euro string
 */
export function formatCost(micros: number | null | undefined): string {
  if (micros == null) {
    return '€0.0000';
  }
  const euros = micros / 1_000_000;
  return `€${euros.toFixed(4)}`;
}

/**
 * Format ISO date string to readable format
 */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) {
    return '-';
  }

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return '-';
    }

    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '-';
  }
}

/**
 * Format duration in seconds to human-readable string
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) {
    return '-';
  }

  if (seconds === 0) {
    return '0s';
  }

  if (seconds < 1) {
    return '<1s';
  }

  const rounded = Math.round(seconds);
  const hours = Math.floor(rounded / 3600);
  const minutes = Math.floor((rounded % 3600) / 60);
  const secs = rounded % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`;
  }

  if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  }

  return `${secs}s`;
}

/**
 * Status display configuration
 */
interface StatusDisplay {
  label: string;
  className: string;
}

const STATUS_CONFIG: Record<ExecutionStatus, StatusDisplay> = {
  queued: {
    label: 'Queued',
    className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  },
  running: {
    label: 'Running',
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  },
  completed: {
    label: 'Completed',
    className: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  },
  failed: {
    label: 'Failed',
    className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  },
};

/**
 * Get display configuration for execution status
 */
export function formatStatus(status: ExecutionStatus | string): StatusDisplay {
  if (status in STATUS_CONFIG) {
    return STATUS_CONFIG[status as ExecutionStatus];
  }

  return {
    label: 'Unknown',
    className: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
  };
}

/**
 * Truncate string with ellipsis
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) {
    return str;
  }
  return str.slice(0, maxLength - 3) + '...';
}

/**
 * Format file size in bytes to human-readable string
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${units[i]}`;
}
