import type { NextConfig } from "next";

// Адрес API изнутри: для SSR (страница события) и для прокси /api, /media в разработке и e2e.
// В проде nginx отправляет /studlenta/api и /studlenta/media прямо в API, минуя Next.
import { BASE_PATH } from "./src/lib/config";

const apiInternalUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  basePath: BASE_PATH,
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  poweredByHeader: false,
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${apiInternalUrl}/api/v1/:path*` },
      { source: "/media/:path*", destination: `${apiInternalUrl}/media/:path*` },
    ];
  },
};

export default nextConfig;
