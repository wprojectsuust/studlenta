import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { SKIN_BOOT_SCRIPT } from "@/lib/skins";
import { Providers } from "./providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "cyrillic"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  // Абсолютные ссылки для превью в соцсетях (og:image и т. п.)
  metadataBase: new URL(process.env.PUBLIC_ORIGIN ?? "http://localhost:3000"),
  title: { default: "Студлента УУНиТ", template: "%s — Студлента УУНиТ" },
  description: "Лента студенческих мероприятий УУНиТ: концерты, спорт, наука, волонтёрство. Каждое событие проверено модератором.",
};

export const viewport: Viewport = { themeColor: "#141B2D" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={inter.variable} data-skin="light" suppressHydrationWarning>
      <head>
        {/* Скин до первой отрисовки — иначе тёмная тема мигнёт светлой */}
        <script dangerouslySetInnerHTML={{ __html: SKIN_BOOT_SCRIPT }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
