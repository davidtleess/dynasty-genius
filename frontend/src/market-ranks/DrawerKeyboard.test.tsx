// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PlayerCardDrawer } from "../player/PlayerCardDrawer";

afterEach(cleanup);
it("includes the rank explanation summary in the drawer focus cycle", () => {
  render(
    <PlayerCardDrawer onClose={vi.fn()}>
      <details>
        <summary>Why these ranks?</summary>
        <p>Explanation</p>
      </details>
    </PlayerCardDrawer>,
  );
  const close = screen.getByRole("button");
  expect(document.activeElement).toBe(close);
  fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
  expect(document.activeElement).toBe(screen.getByText("Why these ranks?"));
  fireEvent.keyDown(document, { key: "Tab" });
  expect(document.activeElement).toBe(close);
});
