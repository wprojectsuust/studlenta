// Клиент API: access-токен живёт только в памяти, refresh — в httpOnly cookie (ADR-0006).
// На 401 один раз обновляем сессию (общий промис для параллельных запросов) и повторяем запрос.

export type FieldErrors = Record<string, string>;

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly fields: FieldErrors = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Body = Record<string, unknown> | unknown[] | FormData | undefined;
export type RequestOptions = { method?: string; body?: Body; query?: Record<string, string | number | boolean | undefined | null> };
type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;

const NETWORK_MESSAGE = "Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.";

async function toError(response: Response): Promise<ApiError> {
  try {
    const data = (await response.json()) as { error?: { code?: string; message?: string; fields?: FieldErrors } };
    if (data.error) {
      return new ApiError(response.status, data.error.code ?? "error", data.error.message ?? "Ошибка", data.error.fields ?? {});
    }
  } catch {
    /* тело не JSON */
  }
  return new ApiError(response.status, "http_error", "Что-то пошло не так. Попробуйте ещё раз.");
}

export function createApiClient(options: { baseUrl: string; fetchImpl?: FetchLike; onAuthLost?: () => void }) {
  const fetchImpl: FetchLike = options.fetchImpl ?? ((url, init) => fetch(url, init));
  let accessToken: string | null = null;
  let refreshing: Promise<boolean> | null = null;

  async function send(path: string, opts: RequestOptions): Promise<Response> {
    const headers = new Headers();
    if (accessToken) headers.set("authorization", `Bearer ${accessToken}`);
    let body: BodyInit | undefined;
    if (opts.body instanceof FormData) body = opts.body;
    else if (opts.body !== undefined) {
      headers.set("content-type", "application/json");
      body = JSON.stringify(opts.body);
    }
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(opts.query ?? {})) {
      if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
    }
    const qs = params.size ? `?${params}` : "";
    try {
      return await fetchImpl(`${options.baseUrl}${path}${qs}`, {
        method: opts.method ?? "GET",
        headers,
        body,
        credentials: "same-origin",
      });
    } catch {
      throw new ApiError(0, "network", NETWORK_MESSAGE);
    }
  }

  async function refresh(): Promise<boolean> {
    refreshing ??= (async () => {
      try {
        const res = await send("/auth/refresh", { method: "POST" });
        if (!res.ok) return false;
        accessToken = ((await res.json()) as { access_token: string }).access_token;
        return true;
      } catch {
        return false;
      } finally {
        queueMicrotask(() => (refreshing = null));
      }
    })();
    return refreshing;
  }

  async function request<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
    let response = await send(path, opts);
    if (response.status === 401 && !path.startsWith("/auth/")) {
      const hadToken = accessToken !== null;
      if (await refresh()) {
        response = await send(path, opts);
      } else {
        accessToken = null;
        if (hadToken) options.onAuthLost?.(); // гостю «сессию» терять нечего
      }
    }
    if (!response.ok) throw await toError(response);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return {
    request,
    refresh,
    setAccessToken: (token: string | null) => void (accessToken = token),
    getAccessToken: () => accessToken,
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
