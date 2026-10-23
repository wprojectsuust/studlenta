"use client";

import { useId, useState } from "react";
import type { AuthoredEvent, HistoryEntry } from "@/lib/api";
import { formatWhen } from "@/lib/format";
import { Cover } from "./Cover";
import { CheckIcon } from "./icons";
import { TagPill } from "./TagPill";

const CHECKS = ["Событие связано с университетом", "Дата, время и место корректны", "Нет рекламы и сборов денег"];
const ACTIONS: Record<HistoryEntry["action"], string> = {
  submitted: "отправлено на модерацию", withdrawn: "отозвано автором", approved: "одобрено",
  changes_requested: "возвращено на доработку", rejected: "отклонено", archived: "снято с публикации",
};

type Props = {
  event: AuthoredEvent;
  history: HistoryEntry[];
  busy?: boolean;
  onApprove: () => void;
  onRequestChanges: (note: string) => void;
  onReject: (note: string) => void;
};

export function ModerationPanel({ event, history, busy, onApprove, onRequestChanges, onReject }: Props) {
  const id = useId();
  const [checks, setChecks] = useState(() => CHECKS.map(() => false));
  const [note, setNote] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [noteMissing, setNoteMissing] = useState(false);
  const pending = event.status === "pending";

  const approve = () => {
    if (!checks.every(Boolean)) return setProblem("Чтобы опубликовать, отметьте все пункты чек-листа.");
    setProblem(null);
    onApprove();
  };
  const withNote = (fn: (note: string) => void) => () => {
    if (!note.trim()) {
      setNoteMissing(true);
      return setProblem("Напишите автору, что не так, — без комментария вернуть или отклонить нельзя.");
    }
    setProblem(null);
    setNoteMissing(false);
    fn(note.trim());
  };

  return (
    <section aria-labelledby={`${id}-title`} className="card" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 18 }}>
      <Cover src={event.cover_url} category={event.category ?? { id: 0, slug: "", name: "", color: "#4B5563" }} alt="Обложка заявки"
        style={{ width: "100%", aspectRatio: "21 / 8", borderRadius: 12 }} />
      <div style={{ padding: "0 8px", display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 16px", alignItems: "center", fontSize: 14, color: "var(--color-muted)" }}>
          {event.category && <TagPill category={event.category} />}
          {event.starts_at && <span>{formatWhen(event.starts_at)}</span>}
          <span>{event.place}</span>
        </div>
        <h2 id={`${id}-title`} style={{ fontSize: 24, lineHeight: 1.25 }}>{event.title}</h2>
        <p style={{ fontWeight: 500 }}>{event.summary}</p>
        <p style={{ whiteSpace: "pre-line", color: "var(--color-muted)" }}>{event.body}</p>
        <span style={{ fontSize: 13, color: "var(--color-muted)" }}>Автор: {event.author_name}</span>
      </div>

      {event.is_resubmission && event.moderator_note && (
        <div style={{ margin: "0 8px", padding: "12px 14px", borderRadius: 10, background: "var(--color-warning-bg)", color: "var(--color-warning-ink)", fontSize: 14 }}>
          <strong>Исправлено автором.</strong> Прошлый комментарий: {event.moderator_note}
        </div>
      )}

      {pending && (
        <>
          <fieldset style={{ margin: "0 8px", padding: "12px 16px", border: "1px solid var(--color-line)", borderRadius: 12 }}>
            <legend style={{ padding: "0 6px", fontWeight: 600, fontSize: 14 }}>Чек-лист</legend>
            {CHECKS.map((label, i) => (
              <label key={label} style={{ display: "flex", gap: 10, alignItems: "center", minHeight: 44 }}>
                <input type="checkbox" checked={checks[i]} style={{ width: 20, height: 20 }}
                  onChange={() => setChecks((c) => c.map((v, j) => (j === i ? !v : v)))} />
                {label}
              </label>
            ))}
          </fieldset>
          <div className="field" style={{ margin: "0 8px" }}>
            <label htmlFor={`${id}-note`}>Комментарий автору <span style={{ fontWeight: 400, color: "var(--color-muted)" }}>— обязателен при возврате и отклонении</span></label>
            <textarea id={`${id}-note`} rows={2} className="input" value={note} aria-invalid={noteMissing}
              onChange={(e) => { setNote(e.target.value); setNoteMissing(false); }} placeholder="Например: уточните аудиторию и время окончания" />
          </div>
          {problem && <div role="alert" style={{ margin: "0 8px", color: "var(--color-danger)", fontSize: 14 }}>{problem}</div>}
          <div style={{ margin: "0 8px", display: "flex", flexWrap: "wrap", gap: 10 }}>
            <button type="button" className="btn" disabled={busy} onClick={approve} style={{ background: "#15803D", color: "#FFFFFF" }}>
              <CheckIcon size={18} />Одобрить
            </button>
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={withNote(onRequestChanges)}>Вернуть на доработку</button>
            <button type="button" className="btn btn-danger" disabled={busy} onClick={withNote(onReject)}>Отклонить</button>
          </div>
        </>
      )}

      {history.length > 0 && (
        <div style={{ margin: "0 8px", paddingTop: 14, borderTop: "1px solid var(--color-line)", fontSize: 13, color: "var(--color-muted)", display: "flex", flexDirection: "column", gap: 6 }}>
          <strong style={{ color: "var(--color-ink)", fontSize: 14 }}>История</strong>
          {history.map((h) => (
            <span key={`${h.created_at}-${h.action}`}>
              {formatWhen(h.created_at)} — {h.actor_name}: {ACTIONS[h.action]}{h.note ? ` («${h.note}»)` : ""}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}
