// @vitest-environment jsdom

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppShell } from "../shell/AppShell";

const TRUST_DIR = join(process.cwd(), "src", "trust");

function authoredTrustFiles() {
  if (!existsSync(TRUST_DIR)) {
    return [];
  }
  return readdirSync(TRUST_DIR)
    .filter((name) => /\.(css|jsx?|tsx?)$/.test(name))
    .filter((name) => !name.includes(".test."))
    .map((name) => join(TRUST_DIR, name));
}

describe("TrustConsole", () => {
  it("mounts a minimal Model Trust placeholder with position controls", () => {
    render(<AppShell />);

    fireEvent.click(screen.getByRole("button", { name: "Model Trust" }));

    const main = screen.getByRole("main");
    expect(within(main).getByRole("heading", { name: "Model Trust" })).toBeTruthy();
    for (const position of ["QB", "RB", "WR", "TE"]) {
      expect(within(main).getByRole("button", { name: position })).toBeTruthy();
    }
  });

  it("does not introduce prohibited conclusion wording in authored trust files", () => {
    const trustText = authoredTrustFiles()
      .map((path) => readFileSync(path, "utf8"))
      .join("\n");
    const appShellText = readFileSync(
      join(process.cwd(), "src", "shell", "AppShell.tsx"),
      "utf8",
    );

    expect(`${trustText}\n${appShellText}`).not.toMatch(
      new RegExp("ver" + "dict", "i"),
    );
  });
});
