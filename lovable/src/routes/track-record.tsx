// DG-203 — a screen this saved preview does not carry content for, said plainly.
//
// The imported version filled it from the alternate valuation the live app computes, which is
// not the accepted reading. Rather than serve numbers nothing here stands behind, the screen
// states what is missing from the preview and points at what is available.
import { createFileRoute } from "@tanstack/react-router";

import { AppShell } from "@/components/dg/AppShell";
import { validatePlayerSearch } from "@/lib/dg/search";

export const Route = createFileRoute("/track-record")({
  validateSearch: validatePlayerSearch,
  head: () => ({
    meta: [
      { title: "Track record — Dynasty Genius" },
      { name: "description", content: "Graded predictions, once any prediction has been graded." },
    ],
  }),
  component: Unsupported,
});

function Unsupported() {
  return (
    <AppShell title="Track record">
      <section
        className="mt-4 rounded-md border p-4"
        style={{ borderColor: "var(--hairline)" }}
        role="status"
      >
        <p className="text-sm" style={{ color: "var(--foreground)" }}>
          This saved preview does not include evaluated outcomes. It does not establish a
          decision-making advantage.
        </p>
      </section>
    </AppShell>
  );
}
