"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { canModerate, endpoints, type Inbox } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatWhen } from "@/lib/format";
import { useCategories, useQueue } from "@/lib/queries";
import {
  BellIcon, BookmarkIcon, CalendarIcon, CapIcon, FeedIcon, InfoIcon, PenIcon, PlusIcon, SearchIcon, ShieldIcon, UserIcon,
} from "./icons";
import { CategoryIcon } from "./CategoryIcon";
import { SkinPicker } from "./SkinPicker";
import { VerifyEmailBanner } from "./VerifyEmailBanner";
import styles from "./Shell.module.css";

function initials(name: string) {
  return name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}

function Sidebar() {
  const pathname = usePathname();
  const params = useSearchParams();
  const { user } = useAuth();
  const categories = useCategories();
  const moderator = canModerate(user?.role);
  const queue = useQueue("pending", moderator);
  const onFeed = pathname === "/";
  const favorites = onFeed && params.get("favorites") === "1";
  const activeCategory = onFeed ? params.get("category") : null;
  const current = (on: boolean) => (on ? ("page" as const) : undefined);

  return (
    <aside className={styles.sidebar} aria-label="Навигация">
      <Link href="/" className={styles.brand}>
        <CapIcon size={34} />
        <span>
          <strong style={{ fontSize: 18 }}>УУНиТ</strong>
          <small>Студенческие события</small>
        </span>
      </Link>
      <nav aria-label="Разделы" className={styles.nav}>
        <Link href="/" className={styles.navItem} aria-current={current(onFeed && !favorites && !activeCategory)}><FeedIcon />Лента</Link>
        <Link href="/calendar" className={styles.navItem} aria-current={current(pathname === "/calendar")}><CalendarIcon />Календарь</Link>
        <Link href="/?favorites=1" className={styles.navItem} aria-current={current(favorites)}><BookmarkIcon />Избранное</Link>
        <Link href="/my" className={styles.navItem} aria-current={current(pathname.startsWith("/my"))}><PenIcon />Мои публикации</Link>
        {moderator && (
          <Link href="/moderation" className={styles.navItem} aria-current={current(pathname === "/moderation")}>
            <ShieldIcon />Модерация
            {Boolean(queue.data?.length) && <span className={styles.badge} aria-label={`${queue.data?.length} на проверке`}>{queue.data?.length}</span>}
          </Link>
        )}
        <Link href="/about" className={styles.navItem} aria-current={current(pathname === "/about")}><InfoIcon />О проекте</Link>
      </nav>
      <nav aria-label="Категории" className={styles.group}>
        <h2 className={styles.groupTitle}>Категории</h2>
        {categories.data?.map((c) => (
          <Link key={c.id} href={activeCategory === c.slug ? "/" : `/?category=${c.slug}`} className={styles.navItem}
            aria-current={current(activeCategory === c.slug)} style={{ minHeight: 40, fontSize: 14 }}>
            <CategoryIcon slug={c.slug} color={c.color} />
            {c.name}
            <span className={styles.count} aria-label={`${c.upcoming_count} предстоящих`}>{c.upcoming_count}</span>
          </Link>
        ))}
      </nav>
      <div className={styles.group} style={{ marginTop: "auto", padding: "18px 4px 0" }}>
        <SkinPicker />
      </div>
    </aside>
  );
}

function Notifications() {
  const { reloadProfile, user } = useAuth();
  const [open, setOpen] = useState(false);
  const [inbox, setInbox] = useState<Inbox | null>(null);
  const button = useRef<HTMLButtonElement>(null);
  const unread = user?.unread_notifications ?? 0;

  useEffect(() => {
    if (!open) return;
    let alive = true;
    endpoints.inbox().then(async (data) => {
      if (!alive) return;
      setInbox(data);
      if (data.unread) {
        await endpoints.markRead(null);
        await reloadProfile();
      }
    }).catch(() => setInbox({ items: [], unread: 0 }));
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      alive = false;
      document.removeEventListener("keydown", onKey);
    };
  }, [open, reloadProfile]);

  return (
    <div style={{ position: "relative" }}>
      <button ref={button} type="button" className={styles.iconButton} aria-expanded={open} aria-controls="notifications"
        aria-label={unread ? `Уведомления, новых: ${unread}` : "Уведомления"} onClick={() => setOpen((v) => !v)}>
        <BellIcon size={22} />
        {unread > 0 && <span className={styles.unreadDot} />}
      </button>
      {open && (
        <div id="notifications" className={styles.popover} role="region" aria-label="Уведомления">
          {!inbox && <p style={{ padding: 12 }}>Загружаем…</p>}
          {inbox?.items.length === 0 && <p style={{ padding: 12, color: "var(--color-muted)" }}>Пока ничего нового</p>}
          {inbox?.items.map((n) => (
            <Link key={n.id} href={n.kind === "approved" || n.kind === "reminder" ? `/events/${n.event_id}` : "/my"}
              onClick={() => setOpen(false)}
              style={{ display: "block", padding: "10px 12px", borderRadius: 10, textDecoration: "none", background: n.read_at ? undefined : "var(--color-info-bg)" }}>
              <span style={{ display: "block", fontSize: 14 }}>{n.text}</span>
              <span style={{ fontSize: 12, color: "var(--color-muted)" }}>{formatWhen(n.created_at)}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function TopBar() {
  const router = useRouter();
  const params = useSearchParams();
  const { status, user } = useAuth();
  const [q, setQ] = useState(params.get("q") ?? "");

  function search(e: FormEvent) {
    e.preventDefault();
    const next = new URLSearchParams(params);
    if (q.trim()) next.set("q", q.trim());
    else next.delete("q");
    router.push(`/?${next}`);
  }

  return (
    <header className={styles.topbar}>
      <form role="search" className={styles.search} onSubmit={search}>
        <SearchIcon size={18} />
        <label htmlFor="q" className="sr-only">Поиск по событиям</label>
        <input id="q" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Поиск по событиям…" />
      </form>
      <div className={styles.topActions}>
        <Link href="/my/new" className="btn btn-primary" aria-label="Предложить событие">
          <PlusIcon size={18} />
          <span className="hide-mobile">Предложить событие</span>
        </Link>
        {status === "authenticated" && user ? (
          <>
            <Notifications />
            {/* Имя начинается с видимых инициалов (WCAG 2.5.3) — голосом можно сказать «нажми АС» */}
            <Link href="/my" className={styles.avatar} aria-label={`${initials(user.full_name)} — профиль: ${user.full_name}`}>{initials(user.full_name)}</Link>
          </>
        ) : (
          status === "guest" && <Link href="/login" className="btn btn-secondary">Войти</Link>
        )}
      </div>
    </header>
  );
}

function TabBar() {
  const pathname = usePathname();
  const params = useSearchParams();
  const favorites = pathname === "/" && params.get("favorites") === "1";
  const tabs = [
    { href: "/", label: "Лента", icon: <FeedIcon />, on: pathname === "/" && !favorites },
    { href: "/calendar", label: "Календарь", icon: <CalendarIcon />, on: pathname === "/calendar" },
    { href: "/?favorites=1", label: "Избранное", icon: <BookmarkIcon />, on: favorites },
    { href: "/my", label: "Профиль", icon: <UserIcon />, on: pathname.startsWith("/my") || pathname === "/moderation" },
  ];
  return (
    <nav className={styles.tabbar} aria-label="Разделы">
      {tabs.map((t) => (
        <Link key={t.label} href={t.href} className={styles.tab} aria-current={t.on ? "page" : undefined}>
          {t.icon}
          {t.label}
        </Link>
      ))}
    </nav>
  );
}

export function VerifyNotice() {
  const { user, status } = useAuth();
  if (status !== "authenticated" || !user || user.email_verified) return null;
  return <VerifyEmailBanner email={user.email} onResend={endpoints.resendVerification} />;
}

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className={styles.shell}>
      <a href="#main" className="skip-link">Перейти к содержимому</a>
      <Suspense fallback={<aside className={styles.sidebar} aria-label="Навигация" />}>
        <Sidebar />
      </Suspense>
      <div className={styles.content}>
        <Suspense fallback={<header className={styles.topbar} />}>
          <TopBar />
        </Suspense>
        <VerifyNotice />
        <main id="main" className={styles.main} tabIndex={-1}>
          {children}
        </main>
      </div>
      <Suspense>
        <TabBar />
      </Suspense>
    </div>
  );
}
