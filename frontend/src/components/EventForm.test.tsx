import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";
import { EventForm } from "./EventForm";

const categories = [
  { id: 1, slug: "concerts", name: "Концерты", color: "#7C3AED", upcoming_count: 0 },
  { id: 2, slug: "sport", name: "Спорт", color: "#15803D", upcoming_count: 0 },
];

function setup(onSubmit = vi.fn(), onSave = vi.fn()) {
  render(<EventForm categories={categories} onSave={onSave} onSubmit={onSubmit} onUpload={vi.fn()} />);
  return { onSubmit, onSave };
}

describe("EventForm", () => {
  it("labels every field and counts the summary", async () => {
    setup();
    for (const label of ["Заголовок", "Категория", "Краткий анонс", "Описание", "Начало", "Место проведения"]) {
      expect(screen.getByLabelText(label, { exact: false })).toBeInTheDocument();
    }
    await userEvent.type(screen.getByLabelText("Краткий анонс", { exact: false }), "Привет");
    expect(screen.getByText("6 / 200")).toBeInTheDocument();
  });

  it("sends the filled event with an ISO date in the university timezone", async () => {
    const { onSubmit } = setup();
    await userEvent.type(screen.getByLabelText("Заголовок", { exact: false }), "Квиз в общежитии");
    await userEvent.selectOptions(screen.getByLabelText("Категория", { exact: false }), "2");
    await userEvent.type(screen.getByLabelText("Начало", { exact: false }), "2026-10-29T20:00");
    await userEvent.click(screen.getByRole("button", { name: "Отправить на модерацию" }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Квиз в общежитии", category_id: 2, starts_at: "2026-10-29T20:00:00+05:00" }),
    );
  });

  it("shows server field errors next to the fields and focuses the first one", async () => {
    const onSubmit = vi.fn().mockRejectedValue(
      new ApiError(422, "validation_error", "Проверьте поля формы", { title: "Заголовок — минимум 5 символов", place: "Укажите место проведения" }),
    );
    setup(onSubmit);
    await userEvent.click(screen.getByRole("button", { name: "Отправить на модерацию" }));
    const title = screen.getByLabelText("Заголовок", { exact: false });
    expect(title).toHaveAttribute("aria-invalid", "true");
    expect(title).toHaveAccessibleDescription(expect.stringContaining("минимум 5 символов"));
    expect(title).toHaveFocus();
    expect(screen.getByRole("alert")).toHaveTextContent("Заполните поля, отмеченные звёздочкой");
  });
});
