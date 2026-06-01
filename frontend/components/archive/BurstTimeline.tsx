// components/archive/BurstTimeline.tsx
import FormattedPreview from "@/components/formatting/FormattedPreview";
import BurstDivider from "@/components/archive/BurstDivider";
import type { Burst } from "@/lib/api";

interface BurstTimelineProps {
  flareonName: string;
  bursts: Burst[];
  activeBurstId: number;
}

export default function BurstTimeline({
  flareonName,
  bursts,
  activeBurstId,
}: BurstTimelineProps) {
  return (
    <main
      data-testid="burst-timeline"
      style={{
        flex: 1,
        overflowY: "auto",
        padding: `var(--writing-padding-y) var(--writing-padding-x)`,
      }}
    >
      <div
        style={{
          maxWidth: "var(--writing-max-width)",
          margin: "0 auto",
          paddingTop: "40px", // space for the back button
        }}
      >
        {/* Flareon name */}
        <h1
          data-testid="archive-flareon-name"
          style={{
            fontFamily: "var(--font-writing)",
            fontSize: "20px",
            fontWeight: 400,
            color: "var(--text-primary)",
            marginBottom: "48px",
            letterSpacing: "-0.01em",
          }}
        >
          {flareonName}
        </h1>

        {/* All bursts, oldest first */}
        {bursts.map((burst, index) => (
          <div key={burst.id}>
            <BurstDivider
              startedAt={burst.started_at}
              isActive={burst.id === activeBurstId}
            />
            <FormattedPreview
              burstId={burst.id}
              rawContent={burst.content}
            />
            {index < bursts.length - 1 && (
              <div style={{ height: "32px" }} />
            )}
          </div>
        ))}
      </div>
    </main>
  );
}
