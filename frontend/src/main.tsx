import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// H2 I2a sanctioned font activation: self-hosted latin subsets only (vision
// spec §3 — no network fonts; the fontPipeline contract pins this exact set).
import "@fontsource/archivo/latin.css";
import "@fontsource/ibm-plex-mono/latin.css";
import "@fontsource/ibm-plex-sans/latin.css";
import { App } from "./App";
import "./styles/tokens.css";

const rootElement = document.getElementById("root");

if (rootElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
