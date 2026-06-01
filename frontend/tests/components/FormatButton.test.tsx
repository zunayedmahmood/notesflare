// frontend/tests/components/FormatButton.test.tsx

import { render, screen, fireEvent } from "@testing-library/react";
import FormatButton from "@/components/formatting/FormatButton";

describe("FormatButton", () => {
  test("renders with 'Format' label when no diffs", () => {
    render(
      <FormatButton
        onClick={() => {}}
        isLoading={false}
        hasDiffs={false}
        pendingCount={0}
      />
    );
    expect(screen.getByTestId("format-button")).toHaveTextContent("Format");
  });

  test("renders loading state", () => {
    render(
      <FormatButton
        onClick={() => {}}
        isLoading={true}
        hasDiffs={false}
        pendingCount={0}
      />
    );
    expect(screen.getByTestId("format-button")).toHaveTextContent("Formatting...");
    expect(screen.getByTestId("format-button")).toBeDisabled();
  });

  test("renders pending count when diffs exist", () => {
    render(
      <FormatButton
        onClick={() => {}}
        isLoading={false}
        hasDiffs={true}
        pendingCount={3}
      />
    );
    expect(screen.getByTestId("format-button")).toHaveTextContent("Review 3 changes");
  });

  test("singular 'change' for count of 1", () => {
    render(
      <FormatButton onClick={() => {}} isLoading={false} hasDiffs={true} pendingCount={1} />
    );
    expect(screen.getByTestId("format-button")).toHaveTextContent("Review 1 change");
  });

  test("onClick fires when not disabled", () => {
    const onClick = vi.fn();
    render(
      <FormatButton onClick={onClick} isLoading={false} hasDiffs={false} pendingCount={0} />
    );
    fireEvent.click(screen.getByTestId("format-button"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  test("onClick does not fire when disabled", () => {
    const onClick = vi.fn();
    render(
      <FormatButton onClick={onClick} isLoading={false} hasDiffs={false} pendingCount={0} disabled />
    );
    fireEvent.click(screen.getByTestId("format-button"));
    expect(onClick).not.toHaveBeenCalled();
  });
});
