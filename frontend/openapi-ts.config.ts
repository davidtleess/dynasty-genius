import { defineConfig } from "@hey-api/openapi-ts";

// Generate TypeScript types + Zod schemas ONLY from the committed OpenAPI snapshot.
// No runtime HTTP-client plugin: the locked runtime deps stay react/react-dom/zod
// (the generated Zod imports "zod", already a dep; types are type-only). The Trust
// strip (T5b) calls native fetch and validates the response with the generated Zod
// at the SDK boundary. Output is a committed build artifact, never hand-edited, and
// is excluded from Biome (frontend/biome.json) + the banned-language linter (T6).
export default defineConfig({
  input: "./openapi.json",
  output: "./src/lib/api",
  plugins: ["@hey-api/typescript", "zod"],
});
