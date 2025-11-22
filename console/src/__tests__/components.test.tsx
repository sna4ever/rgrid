/**
 * Component tests for RGrid Console (Story 10-2)
 * Tests StatusBadge and ExecutionsTable components
 */
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../components/status-badge';
import { ExecutionsTable } from '../components/executions-table';
import type { ExecutionListItem } from '../lib/types';

// Mock next/link for testing
jest.mock('next/link', () => {
  return function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  };
});

describe('StatusBadge', () => {
  it('renders queued status correctly', () => {
    render(<StatusBadge status="queued" />);
    expect(screen.getByText('Queued')).toBeInTheDocument();
    expect(screen.getByTestId('status-badge')).toHaveAttribute('data-status', 'queued');
  });

  it('renders running status with animation indicator', () => {
    render(<StatusBadge status="running" />);
    expect(screen.getByText('Running')).toBeInTheDocument();
    // Running status should have an animated indicator
    const badge = screen.getByTestId('status-badge');
    expect(badge.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders completed status correctly', () => {
    render(<StatusBadge status="completed" />);
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('renders failed status correctly', () => {
    render(<StatusBadge status="failed" />);
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('handles unknown status gracefully', () => {
    render(<StatusBadge status="unknown-status" />);
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<StatusBadge status="completed" className="custom-class" />);
    expect(screen.getByTestId('status-badge')).toHaveClass('custom-class');
  });
});

describe('ExecutionsTable', () => {
  const mockExecutions: ExecutionListItem[] = [
    {
      execution_id: 'exec_abc123',
      status: 'completed',
      created_at: '2024-01-15T10:30:00Z',
      started_at: '2024-01-15T10:30:05Z',
      completed_at: '2024-01-15T10:30:45Z',
      duration_seconds: 40,
      exit_code: 0,
      cost_micros: 50000,
      user_metadata: {},
    },
    {
      execution_id: 'exec_def456',
      status: 'running',
      created_at: '2024-01-15T10:35:00Z',
      started_at: '2024-01-15T10:35:02Z',
      completed_at: null,
      duration_seconds: null,
      exit_code: null,
      cost_micros: 0,
      user_metadata: { env: 'prod' },
    },
    {
      execution_id: 'exec_ghi789',
      status: 'failed',
      created_at: '2024-01-15T10:40:00Z',
      started_at: '2024-01-15T10:40:01Z',
      completed_at: '2024-01-15T10:40:10Z',
      duration_seconds: 9,
      exit_code: 1,
      cost_micros: 15000,
      user_metadata: {},
    },
  ];

  it('renders loading state', () => {
    render(<ExecutionsTable executions={[]} isLoading={true} />);
    expect(screen.getByTestId('loading-state')).toBeInTheDocument();
    expect(screen.getByText('Loading executions...')).toBeInTheDocument();
  });

  it('renders error state', () => {
    render(<ExecutionsTable executions={[]} error="Failed to fetch data" />);
    expect(screen.getByTestId('error-state')).toBeInTheDocument();
    expect(screen.getByText('Failed to fetch data')).toBeInTheDocument();
  });

  it('renders empty state when no executions', () => {
    render(<ExecutionsTable executions={[]} />);
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    expect(screen.getByText('No executions found.')).toBeInTheDocument();
  });

  it('renders table with executions', () => {
    render(<ExecutionsTable executions={mockExecutions} />);
    expect(screen.getByTestId('executions-table')).toBeInTheDocument();

    // Check table headers
    expect(screen.getByText('Execution ID')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Duration')).toBeInTheDocument();
    expect(screen.getByText('Cost')).toBeInTheDocument();
  });

  it('renders all execution rows', () => {
    render(<ExecutionsTable executions={mockExecutions} />);

    // Check that all rows are rendered
    expect(screen.getByTestId('execution-row-exec_abc123')).toBeInTheDocument();
    expect(screen.getByTestId('execution-row-exec_def456')).toBeInTheDocument();
    expect(screen.getByTestId('execution-row-exec_ghi789')).toBeInTheDocument();
  });

  it('displays execution IDs as links', () => {
    render(<ExecutionsTable executions={mockExecutions} />);

    const links = screen.getAllByRole('link');
    expect(links.some((link) => link.getAttribute('href') === '/executions/exec_abc123')).toBe(true);
  });

  it('displays status badges for each execution', () => {
    render(<ExecutionsTable executions={mockExecutions} />);

    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('displays formatted durations', () => {
    render(<ExecutionsTable executions={mockExecutions} />);

    expect(screen.getByText('40s')).toBeInTheDocument();
    expect(screen.getByText('9s')).toBeInTheDocument();
  });

  it('displays formatted costs', () => {
    render(<ExecutionsTable executions={mockExecutions} />);

    // €0.0500 for 50000 micros
    expect(screen.getByText('€0.0500')).toBeInTheDocument();
    // €0.0150 for 15000 micros
    expect(screen.getByText('€0.0150')).toBeInTheDocument();
  });

  it('displays exit codes with appropriate styling', () => {
    render(<ExecutionsTable executions={mockExecutions} />);

    const exitCodes = screen.getAllByTestId('exit-code');
    // Success (0) should be green, failure (1) should be red
    expect(exitCodes[0]).toHaveTextContent('0');
    expect(exitCodes[0]).toHaveClass('text-green-400');
    expect(exitCodes[1]).toHaveTextContent('1');
    expect(exitCodes[1]).toHaveClass('text-red-400');
  });

  it('handles null exit codes gracefully', () => {
    const executionsWithNull: ExecutionListItem[] = [
      {
        ...mockExecutions[0],
        exit_code: null,
      },
    ];
    render(<ExecutionsTable executions={executionsWithNull} />);

    // Should display "-" for null exit code
    expect(screen.getByText('-')).toBeInTheDocument();
  });
});
