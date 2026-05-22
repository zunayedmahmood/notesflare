// frontend/tests/components/BurstBlock.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import BurstBlock from '@/components/archive/BurstBlock';

describe('BurstBlock', () => {
  it('renders the burst content', () => {
    render(<BurstBlock content="Entropy always increases." />);
    expect(screen.getByText('Entropy always increases.')).toBeInTheDocument();
  });

  it('renders "Empty burst." when content is empty and not active', () => {
    render(<BurstBlock content="" isActive={false} />);
    expect(screen.getByText('Empty burst.')).toBeInTheDocument();
  });

  it('renders "Typing..." when content is empty and active', () => {
    render(<BurstBlock content="" isActive={true} />);
    expect(screen.getByText('Typing...')).toBeInTheDocument();
  });
});
