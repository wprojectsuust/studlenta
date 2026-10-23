import Link from "next/link";

export default function NotFound() {
  return (
    <main id="main" style={{ minHeight: "70vh", display: "grid", placeItems: "center", padding: 24, textAlign: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
        <h1 className="page-title">Такой страницы нет</h1>
        <p style={{ color: "var(--color-muted)" }}>Возможно, событие сняли с публикации или ссылка устарела.</p>
        <Link href="/" className="btn btn-primary">В ленту</Link>
      </div>
    </main>
  );
}
