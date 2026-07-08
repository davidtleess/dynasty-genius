import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");

const FONT_PACKAGES = [
  "@fontsource/archivo",
  "@fontsource/ibm-plex-sans",
  "@fontsource/ibm-plex-mono",
];

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

describe("H2 I1 font pipeline", () => {
  it("installs the locked self-hosted font packages as runtime dependencies", () => {
    const pkg = readJson(resolve(frontendRoot, "package.json"));

    for (const packageName of FONT_PACKAGES) {
      expect(
        pkg.dependencies,
        `${packageName} must be installed for Vite build output`,
      ).toHaveProperty(packageName);
    }
  });

  it("keeps the font packages OFL-licensed and latin-subset importable", () => {
    for (const packageName of FONT_PACKAGES) {
      const packageJsonPath = resolve(
        frontendRoot,
        "node_modules",
        packageName,
        "package.json",
      );
      const packageJson = readJson(packageJsonPath);
      expect(packageJson.license, `${packageName} license`).toBe("OFL-1.1");

      const latinCssPath = resolve(
        frontendRoot,
        "node_modules",
        packageName,
        "latin.css",
      );
      const latinCss = readFileSync(latinCssPath, "utf8");
      expect(latinCss).toMatch(/@font-face/);
      expect(latinCss).not.toMatch(/https?:\/\//i);
    }
  });

  it("activates only the sanctioned latin font pipeline for I2a", () => {
    const main = readFileSync(resolve(frontendRoot, "src", "main.tsx"), "utf8");
    const tokens = readFileSync(
      resolve(frontendRoot, "src", "styles", "tokens.css"),
      "utf8",
    );

    expect(main).toContain("@fontsource/archivo/latin.css");
    expect(main).toContain("@fontsource/ibm-plex-sans/latin.css");
    expect(main).toContain("@fontsource/ibm-plex-mono/latin.css");
    expect(main).not.toMatch(/@fontsource\/[^"']+\/(?!latin\.css)[^"']+/);

    expect(tokens).toContain('--dg-font-display: "Archivo"');
    expect(tokens).toContain('--dg-font-sans: "IBM Plex Sans"');
    expect(tokens).toContain('--dg-font-mono: "IBM Plex Mono"');
  });
});
