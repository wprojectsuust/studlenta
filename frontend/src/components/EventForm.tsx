"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, type AuthoredEvent, type CategoryCount, type EventInput, type FieldErrors } from "@/lib/api";
import { formatTime, fromLocalInput, toLocalInput } from "@/lib/format";
import { CoverUpload } from "./CoverUpload";

type Props = {
  initial?: AuthoredEvent;
  categories: CategoryCount[];
  onSave: (input: EventInput) => Promise<void>;
  onSubmit: (input: EventInput) => Promise<void>;
  onUpload: (file: File) => Promise<string>;
};

const ORDER = ["title", "category_id", "summary", "body", "starts_at", "ends_at", "place", "cover_url"] as const;
const SUMMARY_MAX = 200;

type State = { title: string; category: string; summary: string; body: string; starts: string; ends: string; place: string; cover: string | null };

function fromEvent(e?: AuthoredEvent): State {
  return {
    title: e?.title ?? "", category: e?.category ? String(e.category.id) : "", summary: e?.summary ?? "", body: e?.body ?? "",
    starts: toLocalInput(e?.starts_at ?? null), ends: toLocalInput(e?.ends_at ?? null), place: e?.place ?? "", cover: e?.cover_url ?? null,
  };
}

function toInput(s: State): EventInput {
  return {
    title: s.title, summary: s.summary, body: s.body, place: s.place, cover_url: s.cover,
    category_id: s.category ? Number(s.category) : null, starts_at: fromLocalInput(s.starts), ends_at: fromLocalInput(s.ends),
  };
}

export function EventForm({ initial, categories, onSave, onSubmit, onUpload }: Props) {
  const [state, setState] = useState<State>(() => fromEvent(initial));
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const dirty = useRef(false);
  const formRef = useRef<HTMLFormElement>(null);

  const set = (key: keyof State) => (value: string | null) => {
    dirty.current = true;
    setState((s) => ({ ...s, [key]: value ?? (key === "cover" ? null : "") }));
  };

  // Автосохранение черновика через 2 с после последней правки (кнопки «Сохранить» нет — handoff §4).
  useEffect(() => {
    if (!dirty.current || !state.title.trim()) return;
    const timer = setTimeout(() => {
      onSave(toInput(state))
        .then(() => setSavedAt(formatTime(new Date())))
        .catch(() => undefined); // ошибки покажем при отправке
    }, 2000);
    return () => clearTimeout(timer);
  }, [state, onSave]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    setFormError(null);
    try {
      await onSubmit(toInput(state));
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length) {
        setErrors(err.fields);
        setFormError("Заполните поля, отмеченные звёздочкой, — подсказки рядом с полями.");
        const first = ORDER.find((k) => err.fields[k]);
        if (first) formRef.current?.querySelector<HTMLElement>(`[name="${first}"]`)?.focus();
      } else {
        setFormError(err instanceof Error ? err.message : "Не удалось отправить");
      }
    } finally {
      setBusy(false);
    }
  }

  const describe = (name: string, hint?: string) => [errors[name] ? `${name}-error` : "", hint ? `${name}-hint` : ""].filter(Boolean).join(" ") || undefined;
  const err = (name: string) => errors[name] && <span id={`${name}-error`} className="error">{errors[name]}</span>;
  const req = <span aria-hidden="true" style={{ color: "var(--color-danger)" }}> *</span>;
  const grid = (min: number) => ({ display: "grid", gap: 18, gridTemplateColumns: `repeat(auto-fit, minmax(min(${min}px, 100%), 1fr))` });

  return (
    <form ref={formRef} onSubmit={submit} noValidate className="card" style={{ padding: 28, display: "flex", flexDirection: "column", gap: 22 }}>
      <div style={grid(260)}>
        <div className="field">
          <label htmlFor="title">Заголовок{req}</label>
          <input id="title" name="title" className="input" value={state.title} onChange={(e) => set("title")(e.target.value)} maxLength={120}
            aria-invalid={Boolean(errors.title)} aria-describedby={describe("title", "hint")} placeholder="Например: Вечер студенческой музыки" required />
          <span id="title-hint" className="hint">От 5 до 120 символов</span>
          {err("title")}
        </div>
        <div className="field">
          <label htmlFor="category_id">Категория{req}</label>
          <select id="category_id" name="category_id" className="input" value={state.category} onChange={(e) => set("category")(e.target.value)}
            aria-invalid={Boolean(errors.category_id)} aria-describedby={describe("category_id")} required>
            <option value="">Выберите категорию</option>
            {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          {err("category_id")}
        </div>
      </div>

      <div className="field">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <label htmlFor="summary">Краткий анонс для ленты{req}</label>
          <span style={{ fontSize: 13, color: state.summary.length > SUMMARY_MAX ? "var(--color-danger)" : "var(--color-muted)" }}>
            {state.summary.length} / {SUMMARY_MAX}
          </span>
        </div>
        <textarea id="summary" name="summary" rows={2} className="input" value={state.summary} onChange={(e) => set("summary")(e.target.value)}
          aria-invalid={Boolean(errors.summary)} aria-describedby={describe("summary")} placeholder="Одно-два предложения: что, для кого, почему стоит прийти" />
        {err("summary")}
      </div>

      <div className="field">
        <label htmlFor="body">Описание{req}</label>
        <textarea id="body" name="body" rows={7} className="input" value={state.body} onChange={(e) => set("body")(e.target.value)}
          aria-invalid={Boolean(errors.body)} aria-describedby={describe("body", "hint")} placeholder="Программа, что взять с собой, как попасть" />
        <span id="body-hint" className="hint">Абзацы разделяйте пустой строкой</span>
        {err("body")}
      </div>

      <div style={grid(200)}>
        <div className="field">
          <label htmlFor="starts_at">Начало{req}</label>
          <input id="starts_at" name="starts_at" type="datetime-local" className="input" value={state.starts} onChange={(e) => set("starts")(e.target.value)}
            aria-invalid={Boolean(errors.starts_at)} aria-describedby={describe("starts_at", "hint")} />
          <span id="starts_at-hint" className="hint">Время — по Уфе</span>
          {err("starts_at")}
        </div>
        <div className="field">
          <label htmlFor="ends_at">Окончание</label>
          <input id="ends_at" name="ends_at" type="datetime-local" className="input" value={state.ends} onChange={(e) => set("ends")(e.target.value)}
            aria-invalid={Boolean(errors.ends_at)} aria-describedby={describe("ends_at")} />
          {err("ends_at")}
        </div>
        <div className="field">
          <label htmlFor="place">Место проведения{req}</label>
          <input id="place" name="place" className="input" value={state.place} onChange={(e) => set("place")(e.target.value)} maxLength={200}
            aria-invalid={Boolean(errors.place)} aria-describedby={describe("place")} placeholder="Корпус, аудитория или адрес" />
          {err("place")}
        </div>
      </div>

      <CoverUpload value={state.cover} onChange={set("cover")} onUpload={onUpload} error={errors.cover_url} />

      {formError && <div role="alert" style={{ padding: "12px 14px", borderRadius: 10, background: "var(--color-danger-bg)", color: "var(--color-danger-ink)" }}>{formError}</div>}

      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "flex-end", gap: 12, paddingTop: 18, borderTop: "1px solid var(--color-line)" }}>
        <span aria-live="polite" style={{ marginRight: "auto", fontSize: 13, color: "var(--color-muted)" }}>
          {savedAt ? `Черновик сохранён в ${savedAt}` : "Черновик сохраняется автоматически"}
        </span>
        <button type="submit" className="btn btn-primary" disabled={busy} aria-busy={busy}>
          {busy ? "Отправляем…" : "Отправить на модерацию"}
        </button>
      </div>
    </form>
  );
}
