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
});
