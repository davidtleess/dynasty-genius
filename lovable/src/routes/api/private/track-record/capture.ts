import { createFileRoute } from "@tanstack/react-router";
import { bridgeTrackRecord } from "@/lib/dg/track-record-bridge.server";

export const Route = createFileRoute("/api/private/track-record/capture")({
  server: { handlers: { POST: ({ request }) => bridgeTrackRecord(request) } },
});
