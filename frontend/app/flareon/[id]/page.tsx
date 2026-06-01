// app/flareon/[id]/page.tsx
import ArchivePageClient from "./ArchivePageClient";

// The archive route is data-backed and unbounded because Flareons are created
// locally by the user. Do not pre-generate hundreds of fake IDs at build time.
export const dynamic = "force-dynamic";

export default function Page() {
  return <ArchivePageClient />;
}
