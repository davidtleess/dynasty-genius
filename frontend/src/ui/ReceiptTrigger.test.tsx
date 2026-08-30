// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("ReceiptTrigger", () => {
  it("opens and closes as a focusable provenance control", async () => {
    const { ReceiptTrigger } = await import("./ReceiptTrigger");

    render(
      <ReceiptTrigger
        label="Projection Update"
        capturedAt="2026-07-05T10:15:00-04:00"
        source="model_registry"
      />,
    );

    const trigger = screen.getByRole("button", {
      name: /provenance for projection update/i,
    });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByTestId("receipt-raw-source").textContent).toContain(
      "model_registry",
    );
    expect(screen.getByTestId("receipt-raw-captured-at").textContent).toContain(
      "2026-07-05T10:15:00-04:00",
    );

    fireEvent.keyDown(trigger, { key: "Escape" });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
  });

  it("supports keyboard and touch activation without relying on hover", async () => {
    const { ReceiptTrigger } = await import("./ReceiptTrigger");

    render(
      <ReceiptTrigger
        label="Projection Update"
        capturedAt="2026-07-05T10:15:00-04:00"
        source="model_registry"
      />,
    );

    const trigger = screen.getByRole("button", {
      name: /provenance for projection update/i,
    });
    fireEvent.keyDown(trigger, { key: "Enter" });
    expect(trigger.getAttribute("aria-expanded")).toBe("true");

    fireEvent.keyDown(trigger, { key: "Escape" });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");

    fireEvent.pointerDown(trigger, { pointerType: "touch" });
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
  });

  // DG-117 REVIEW-PANEL FIX. The panel is anchored to a trigger that can sit
  // anywhere on a row: on Daily What-Changed at 390px it opened to x=547 and
  // took the document 158px sideways. jsdom has no layout, so the geometry
  // below is the geometry Chromium measured there — a 283px panel whose left
  // edge is at 264px in a 390px viewport — and what is under test is the
  // arithmetic that pulls it back.
  async function openPanelWithGeometry(rect: {
    left: number;
    right: number;
    width: number;
  }) {
    const { ReceiptTrigger } = await import("./ReceiptTrigger");
    render(
      <ReceiptTrigger
        label="Market value"
        capturedAt="2026-08-29T09:02:00-04:00"
        source="fc_snapshots:2026-08-29"
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /provenance for market value/i }),
    );
    const panel = document.querySelector<HTMLElement>(".dg-ui-receipt__panel");
    if (panel === null) throw new Error("panel did not open");
    panel.getBoundingClientRect = () =>
      ({ ...rect, top: 0, bottom: 40, height: 40, x: rect.left, y: 0 }) as DOMRect;
    Object.defineProperty(document.documentElement, "clientWidth", {
      value: 390,
      configurable: true,
    });
    // The placement re-runs on resize, which is also how it recovers when the
    // window changes size under an open panel.
    fireEvent(window, new Event("resize"));
    return panel;
  }

  it("pulls an open panel back inside the viewport instead of overrunning it", async () => {
    const panel = await openPanelWithGeometry({ left: 264, right: 547, width: 283 });

    // 547 is 165px past the 382px limit (390 viewport less an 8px gutter), and
    // there is 256px of room to its left, so it moves the full 165px and no
    // more: the panel ends flush inside the gutter, never off the other edge.
    expect(panel.style.transform).toBe("translateX(-165px)");
  });

  it("leaves a panel that already fits exactly where it is", async () => {
    const panel = await openPanelWithGeometry({ left: 20, right: 303, width: 283 });
    expect(panel.style.transform).toBe("");
  });
});
