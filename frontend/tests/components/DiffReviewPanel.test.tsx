// frontend/tests/components/DiffReviewPanel.test.tsx

import { render, screen, fireEvent } from "@testing-library/react";
import DiffReviewPanel from "@/components/formatting/DiffReviewPanel";
import type { FormattingDiff } from "@/types/formatting";

const mockDiff: FormattingDiff = {
  diff_id: "diff-001",
  line_id: "line-001",
  operation: "insert_paragraph_break",
  status: "pending",
  raw_before: "original text here",
  formatted_after: "\noriginal text here",
};

const defaultProps = {
  isOpen: true,
  diffs: [mockDiff],
  pendingCount: 1,
  onAccept: vi.fn(),
  onReject: vi.fn(),
  onAcceptAll: vi.fn(),
  onRejectAll: vi.fn(),
  onClose: vi.fn(),
};

describe("DiffReviewPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders when isOpen is true", () => {
    render(<DiffReviewPanel {...defaultProps} />);
    expect(screen.getByTestId("diff-review-panel")).toBeInTheDocument();
  });

  test("does not render when isOpen is false", () => {
    render(<DiffReviewPanel {...defaultProps} isOpen={false} />);
    expect(screen.queryByTestId("diff-review-panel")).not.toBeInTheDocument();
  });

  test("close button fires onClose", () => {
    render(<DiffReviewPanel {...defaultProps} />);
    fireEvent.click(screen.getByTestId("diff-panel-close"));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  test("accept-all button fires onAcceptAll", () => {
    render(<DiffReviewPanel {...defaultProps} />);
    fireEvent.click(screen.getByTestId("accept-all-btn"));
    expect(defaultProps.onAcceptAll).toHaveBeenCalledTimes(1);
  });

  test("reject-all button fires onRejectAll", () => {
    render(<DiffReviewPanel {...defaultProps} />);
    fireEvent.click(screen.getByTestId("reject-all-btn"));
    expect(defaultProps.onRejectAll).toHaveBeenCalledTimes(1);
  });

  test("renders empty state when diffs is empty", () => {
    render(<DiffReviewPanel {...defaultProps} diffs={[]} pendingCount={0} />);
    expect(screen.getByText(/no formatting changes found/i)).toBeInTheDocument();
    expect(screen.queryByTestId("accept-all-btn")).not.toBeInTheDocument();
  });

  test("renders DiffLineItem for each diff", () => {
    render(<DiffReviewPanel {...defaultProps} />);
    expect(screen.getAllByTestId("diff-line-item")).toHaveLength(1);
  });
});
