import { defineConfig } from "vite";

// No @vitejs/plugin-react: Vite drives esbuild's JSX transform from tsconfig's
// "jsx": "react-jsx" (automatic runtime, jsxImportSource defaults to "react").
// Type-checking is handled separately by `tsc --noEmit` with @types/react.
// HMR/fast-refresh and any UI/charting libraries are deferred per the Surface-1 plan.
export default defineConfig({});
