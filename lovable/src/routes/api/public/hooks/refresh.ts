import { createFileRoute } from "@tanstack/react-router";
/** The imported UI consumes the accepted DG snapshot; its alternate scorer is disabled. */
export const Route = createFileRoute("/api/public/hooks/refresh")({
  server: {
    handlers: {
      POST: async () =>
        new Response(
          JSON.stringify({
            error: "This interface reads a saved DG snapshot. Data refresh runs in the DG backend.",
          }),
          { status: 405, headers: { "content-type": "application/json", Allow: "GET" } },
        ),
    },
  },
});
