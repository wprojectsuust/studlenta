"use client";

import { useId, useState } from "react";
import { ApiError } from "@/lib/api";
import { UploadIcon } from "./icons";

type Props = { value: string | null; onChange: (url: string | null) => void; onUpload: (file: File) => Promise<string>; error?: string };

export function CoverUpload({ value, onChange, onUpload, error }: Props) {
  const id = useId();
  const [busy, setBusy] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const message = uploadError ?? error;

  async function pick(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setUploadError(null);
    try {
      onChange(await onUpload(file));
    } catch (e) {
      setUploadError(e instanceof ApiError ? (e.fields.cover ?? e.message) : "Не удалось загрузить файл");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="field">
      <span className="label" id={`${id}-label`}>Обложка</span>
      {value ? (
        <div style={{ display: "flex", gap: 14, alignItems: "center", padding: 10, border: "1px solid var(--color-line)", borderRadius: 12 }}>
          {/* eslint-disable-next-line @next/next/no-img-element -- превью загруженного файла */}
          <img src={value} alt="Выбранная обложка" style={{ width: 120, height: 76, borderRadius: 8, objectFit: "cover" }} />
          <span style={{ flex: 1, fontSize: 14, color: "var(--color-muted)" }}>Обложка загружена</span>
          <button type="button" className="btn btn-danger" onClick={() => onChange(null)}>Удалить</button>
        </div>
      ) : (
        <label htmlFor={id} style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 6, minHeight: 120,
          border: "2px dashed var(--color-field-border)", borderRadius: 12, background: "var(--color-chip)", color: "var(--color-muted)", cursor: "pointer", textAlign: "center", padding: 12 }}>
          <UploadIcon size={26} style={{ color: "var(--color-accent-text)" }} />
          <span><strong style={{ color: "var(--color-accent-text)" }}>{busy ? "Загружаем…" : "Выберите файл"}</strong> · JPG, PNG или WEBP до 5 МБ, ширина от 1200 px</span>
        </label>
      )}
      <input id={id} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" aria-labelledby={`${id}-label`}
        aria-describedby={message ? `${id}-error` : undefined} onChange={(e) => void pick(e.target.files?.[0])} disabled={busy} />
      {message && <span id={`${id}-error`} className="error" role="alert">{message}</span>}
    </div>
  );
}
