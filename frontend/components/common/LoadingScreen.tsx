// components/common/LoadingScreen.tsx

export default function LoadingScreen() {
  return (
    <div
      data-testid="loading-screen"
      style={{
        display: "flex",
        height: "100vh",
        background: "var(--bg-base)",
      }}
    />
  );
}
