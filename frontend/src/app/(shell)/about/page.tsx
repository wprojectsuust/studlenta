import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "О проекте" };

const STEPS = [
  ["Вы предлагаете событие", "Название, дата, место, описание и обложка. Черновик сохраняется сам."],
  ["Модератор проверяет", "Одобряет, возвращает на доработку с комментарием или отклоняет с причиной. Решение придёт в уведомлениях."],
  ["Событие в ленте", "Его видят все, сохраняют в избранное и находят в календаре. Накануне придёт напоминание."],
];
const ROLES = [
  ["Гость", "смотрит ленту, календарь и события без регистрации"],
  ["Студент", "ставит лайки, сохраняет в избранное, предлагает события"],
  ["Модератор", "проверяет заявки до публикации; назначается администратором"],
  ["Администратор", "управляет ролями и категориями"],
];

export default function AboutPage() {
  return (
    <article style={{ maxWidth: 900, display: "flex", flexDirection: "column", gap: 36 }}>
      <header style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <h1 style={{ fontSize: 34, lineHeight: 1.15 }}>Студенческие события УУНиТ</h1>
        <p style={{ fontSize: 18, color: "var(--color-muted)", maxWidth: 680 }}>
          Одна лента для всего, что происходит в университете вне пар. Публиковать может любой студент, а каждая новость перед появлением
          в ленте проходит проверку модератором — поэтому здесь нет спама и устаревших объявлений.
        </p>
      </header>

      <section aria-labelledby="how">
        <h2 id="how" style={{ fontSize: 22, marginBottom: 16 }}>Как это работает</h2>
        <ol style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(min(240px, 100%), 1fr))" }}>
          {STEPS.map(([title, text], i) => (
            <li key={title} className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 8 }}>
              <span aria-hidden="true" style={{ width: 36, height: 36, borderRadius: 10, background: "var(--color-accent)", color: "var(--color-on-accent)", fontWeight: 700, display: "grid", placeItems: "center" }}>{i + 1}</span>
              <strong style={{ fontSize: 17 }}>{title}</strong>
              <span style={{ color: "var(--color-muted)" }}>{text}</span>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="rules" style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(min(300px, 100%), 1fr))" }}>
        <h2 id="rules" style={{ fontSize: 22, gridColumn: "1 / -1" }}>Правила публикации</h2>
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 16, marginBottom: 8 }}>Публикуем</h3>
          <ul style={{ margin: 0, paddingLeft: 20, color: "var(--color-muted)" }}>
            <li>события университета, факультетов, клубов и студсовета</li>
            <li>студенческие инициативы, открытые для всех</li>
            <li>события партнёров, если они бесплатны для студентов</li>
          </ul>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 16, marginBottom: 8 }}>Не публикуем</h3>
          <ul style={{ margin: 0, paddingLeft: 20, color: "var(--color-muted)" }}>
            <li>рекламу, продажи и сборы денег</li>
            <li>объявления без даты и места</li>
            <li>оскорбления и чужие изображения без разрешения</li>
          </ul>
        </div>
      </section>

      <section aria-labelledby="roles">
        <h2 id="roles" style={{ fontSize: 22, marginBottom: 16 }}>Кто есть кто</h2>
        <dl className="card" style={{ margin: 0, padding: 20, display: "grid", gridTemplateColumns: "minmax(120px, 180px) minmax(0, 1fr)", gap: "10px 20px" }}>
          {ROLES.map(([role, text]) => [<dt key={`${role}-t`} style={{ fontWeight: 600 }}>{role}</dt>, <dd key={`${role}-d`} style={{ margin: 0, color: "var(--color-muted)" }}>{text}</dd>])}
        </dl>
      </section>

      <section aria-labelledby="oss" style={{ padding: 24, borderRadius: 16, background: "var(--color-side)", color: "var(--color-on-side)", display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center" }}>
        <div style={{ flex: "1 1 360px" }}>
          <h2 id="oss" style={{ fontSize: 20, marginBottom: 6 }}>Открытый код</h2>
          <p style={{ color: "var(--color-side-muted)" }}>Проект бесплатный и с открытым исходным кодом (MIT). Нашли ошибку или хотите помочь — приходите в репозиторий.</p>
        </div>
        <a href="https://github.com/wprojectsuust/studlenta" className="btn" style={{ background: "#FFFFFF", color: "#141B2D" }}>Репозиторий на GitHub</a>
      </section>

      <p style={{ color: "var(--color-muted)", fontSize: 14 }}>Прототип создан на хакатоне УУНиТ, 2026. <Link href="/">Вернуться в ленту</Link></p>
    </article>
  );
}
