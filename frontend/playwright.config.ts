import { defineConfig, devices } from "@playwright/test";

// Полный стек: Next (basePath /studlenta) проксирует /api и /media в настоящий API на PostgreSQL.
// Сервисы поднимает CI или `npm run e2e:stack` (см. e2e/README.md).
const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:3000/studlenta/";

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: { baseURL, trace: "retain-on-failure", locale: "ru-RU", timezoneId: "Asia/Yekaterinburg" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] }, testIgnore: /mobile\.spec\.ts/ },
    { name: "mobile", use: { ...devices["Pixel 7"] }, testMatch: /mobile\.spec\.ts/ },
  ],
});
