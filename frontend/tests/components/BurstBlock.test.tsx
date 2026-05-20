// frontend/tests/components/BurstBlock.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import BurstBlock from '@/components/BurstBlock';

describe('BurstBlock', () => {
  it('renders the burst content', () => {
    render(<BurstBlock startedAt="2025-01-15T14:30:00" content="Entropy always increases." />);
    expect(screen.getByText('Entropy always increases.')).toBeInTheDocument();
  });

  it('renders a human-readable timestamp, not raw ISO string', () => {
    render(<BurstBlock startedAt="2025-01-15T14:30:00" content="Some thought." />);
    const raw = screen.queryByText('2025-01-15T14:30:00');

    expect(raw).toBeNull();
  }, {
    onFail: () => `[BurstBlock] Raw ISO timestamp found in rendered output.
  Input     : startedAt="2025-01-15T14:30:00"
  Expected  : A formatted string like "Jan 15, 2:30 PM" (not ISO)
  Found     : Raw ISO string rendered to DOM
  Fix       : BurstBlock must call formatTimestamp(startedAt) and render the result.
              formatTimestamp should use Intl.DateTimeFormat or a similar formatter.`
  });

  it('renders empty content without crashing', () => {
    render(<BurstBlock startedAt="2025-01-15T14:30:00" content="" />);
    // Should not throw
  });
});
