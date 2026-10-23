import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PeriodFilter } from "./PeriodFilter";

describe("PeriodFilter", () => {
  it("marks the active period and reports changes", async () => {
    const onChange = vi.fn();
    render(<PeriodFilter value="week" onChange={onChange} />);
    expect(screen.getByRole("group", { name: "Когда" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "На этой неделе" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Все" })).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(screen.getByRole("button", { name: "Сегодня" }));
    expect(onChange).toHaveBeenCalledWith("today");
  });
});
