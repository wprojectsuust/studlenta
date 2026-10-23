import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AuthoredEvent } from "@/lib/api";
import { ModerationPanel } from "./ModerationPanel";

const event: AuthoredEvent = {
  id: "e1", author_id: "u1", author_name: "Иван Петров", status: "pending", title: "Вечер музыки",
  summary: "Анонс", body: "Описание", category: { id: 1, slug: "concerts", name: "Концерты", color: "#7C3AED" },
  place: "Актовый зал", starts_at: "2026-10-29T13:00:00Z", ends_at: null, cover_url: null,
  moderator_note: "Добавьте фото", submitted_at: "2026-10-23T05:00:00Z", updated_at: "2026-10-23T05:00:00Z",
  is_resubmission: true,
};

function setup() {
  const handlers = { onApprove: vi.fn(), onRequestChanges: vi.fn(), onReject: vi.fn() };
  render(<ModerationPanel event={event} history={[]} {...handlers} />);
  return handlers;
}

describe("ModerationPanel", () => {
  it("shows the previous note for a resubmission", () => {
    setup();
    expect(screen.getByText(/Добавьте фото/)).toBeInTheDocument();
  });

  it("does not approve until the checklist is complete", async () => {
    const { onApprove } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Одобрить" }));
    expect(onApprove).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("отметьте все пункты");
    for (const box of screen.getAllByRole("checkbox")) await userEvent.click(box);
    await userEvent.click(screen.getByRole("button", { name: "Одобрить" }));
    expect(onApprove).toHaveBeenCalledOnce();
  });

  it("requires a note to return or reject", async () => {
    const { onRequestChanges, onReject } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Отклонить" }));
    expect(onReject).not.toHaveBeenCalled();
    const note = screen.getByLabelText(/Комментарий автору/);
    expect(note).toHaveAttribute("aria-invalid", "true");
    await userEvent.type(note, "Укажите время окончания");
    await userEvent.click(screen.getByRole("button", { name: "Вернуть на доработку" }));
    expect(onRequestChanges).toHaveBeenCalledWith("Укажите время окончания");
  });
});
