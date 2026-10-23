import { describe, expect, it, vi } from "vitest";
import { ApiError, createApiClient } from "./client";

function json(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: body === undefined ? {} : { "content-type": "application/json" },
  });
}

describe("api client", () => {
  it("sends JSON with the bearer token and parses the response", async () => {
    const fetchImpl = vi.fn(async () => json(200, { ok: true }));
    const api = createApiClient({ baseUrl: "/studlenta/api/v1", fetchImpl });
    api.setAccessToken("t1");

    const result = await api.request<{ ok: boolean }>("/me/events", { method: "POST", body: { title: "Квиз" } });

    expect(result).toEqual({ ok: true });
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/studlenta/api/v1/me/events");
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer t1");
    expect(new Headers(init.headers).get("content-type")).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ title: "Квиз" }));
    expect(init.credentials).toBe("same-origin");
  });

  it("returns undefined for 204", async () => {
    const api = createApiClient({ baseUrl: "", fetchImpl: async () => json(204) });
    await expect(api.request("/x", { method: "PUT" })).resolves.toBeUndefined();
  });

  it("turns error envelopes into ApiError with field messages", async () => {
    const api = createApiClient({
      baseUrl: "",
      fetchImpl: async () =>
        json(422, { error: { code: "validation_error", message: "Проверьте поля формы", fields: { title: "Укажите заголовок" } } }),
    });
    const error = await api.request("/x").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 422, code: "validation_error", fields: { title: "Укажите заголовок" } });
  });

  it("reports network failures in human words", async () => {
    const api = createApiClient({ baseUrl: "", fetchImpl: async () => { throw new TypeError("Failed to fetch"); } });
    await expect(api.request("/x")).rejects.toMatchObject({ status: 0, message: "Нет связи с сервером. Проверьте интернет и попробуйте ещё раз." });
  });

  it("refreshes once on 401 and retries with the new token", async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) return json(200, { access_token: "fresh", token_type: "bearer", expires_in: 900 });
      const auth = new Headers(init?.headers).get("authorization");
      return auth === "Bearer fresh" ? json(200, { id: 1 }) : json(401, { error: { code: "unauthorized", message: "Токен истёк", fields: {} } });
    });
    const api = createApiClient({ baseUrl: "/api", fetchImpl });
    api.setAccessToken("stale");

    const [a, b] = await Promise.all([api.request("/me"), api.request("/me/events")]);

    expect(a).toEqual({ id: 1 });
    expect(b).toEqual({ id: 1 });
    expect(fetchImpl.mock.calls.filter(([u]) => String(u).endsWith("/auth/refresh"))).toHaveLength(1);
    expect(api.getAccessToken()).toBe("fresh");
  });

  it("gives up when refresh fails and notifies about the lost session", async () => {
    const onAuthLost = vi.fn();
    const api = createApiClient({ baseUrl: "", fetchImpl: async () => json(401, { error: { code: "unauthorized", message: "Сессия истекла", fields: {} } }), onAuthLost });
    api.setAccessToken("stale");
    await expect(api.request("/me")).rejects.toMatchObject({ status: 401 });
    expect(api.getAccessToken()).toBeNull();
    expect(onAuthLost).toHaveBeenCalledOnce();
  });

  it("does not try to refresh for auth endpoints themselves", async () => {
    const fetchImpl = vi.fn(async () => json(401, { error: { code: "unauthorized", message: "Неверная почта или пароль", fields: {} } }));
    const api = createApiClient({ baseUrl: "", fetchImpl });
    await expect(api.request("/auth/login", { method: "POST", body: {} })).rejects.toMatchObject({ message: "Неверная почта или пароль" });
    expect(fetchImpl).toHaveBeenCalledOnce();
  });

  it("passes FormData untouched", async () => {
    const fetchImpl = vi.fn(async () => json(201, { url: "/m.png" }));
    const api = createApiClient({ baseUrl: "", fetchImpl });
    const form = new FormData();
    form.append("file", new Blob(["x"]), "c.png");
    await api.request("/uploads/cover", { method: "POST", body: form });
    const [, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.body).toBe(form);
    expect(new Headers(init.headers).has("content-type")).toBe(false);
  });
});
