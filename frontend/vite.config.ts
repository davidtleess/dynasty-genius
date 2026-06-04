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
  },
});
