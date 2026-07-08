import { defineConfig } from "vitest/config";

// No @vitejs/plugin-react: Vite drives esbuild's JSX transform from tsconfig's
// "jsx": "react-jsx" (automatic runtime, jsxImportSource defaults to "react").
// Type-checking is handled separately by `tsc --noEmit` with @types/react.
// `test.globals` lets @testing-library/react auto-register afterEach(cleanup);
// the DOM environment is selected per-file via `// @vitest-environment jsdom`
// so the token test stays in the faster node env.
export default defineConfig({
  test: {
    globals: true,
    // Playwright evidence specs run under `npm run visual:smoke`, never under
    // Vitest — importing @playwright/test inside a Vitest worker throws.
    exclude: ["**/node_modules/**", "e2e/**"],
  },
});
