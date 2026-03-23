import { http, HttpResponse } from "msw";
import { DEV_USER, DEV_TOKEN } from "../seed-data";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const authHandlers = [
  // GET /auth/me
  http.get(`${BASE}/auth/me`, () => {
    return HttpResponse.json(DEV_USER);
  }),

  // GET /auth/login
  http.get(`${BASE}/auth/login`, () => {
    return HttpResponse.json({
      redirect_url: "/auth/callback?code=dev",
    });
  }),

  // GET /auth/callback
  http.get(`${BASE}/auth/callback`, ({ request }) => {
    const url = new URL(request.url);
    const code = url.searchParams.get("code");

    if (!code) {
      return HttpResponse.json(
        { error: { code: "missing_code", message: "Code parameter is required" } },
        { status: 400 }
      );
    }

    return HttpResponse.json({
      access_token: DEV_TOKEN,
      token_type: "bearer",
      expires_in: 3600,
    });
  }),

  // POST /auth/logout
  http.post(`${BASE}/auth/logout`, () => {
    return new HttpResponse(null, { status: 204 });
  }),
];
