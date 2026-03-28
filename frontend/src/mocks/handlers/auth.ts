import { http, HttpResponse } from "msw";
import { DEV_USER, DEV_TOKEN } from "../seed-data";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const authHandlers = [
  // GET /auth/me
  http.get(`${BASE}/auth/me`, () => {
    return HttpResponse.json(DEV_USER);
  }),

  // GET /auth/login — return redirect URL with token directly (skips code exchange in MSW mode)
  http.get(`${BASE}/auth/login`, () => {
    return HttpResponse.json({
      redirect_url: `/auth/callback?token=${DEV_TOKEN}`,
    });
  }),

  // POST /auth/logout
  http.post(`${BASE}/auth/logout`, () => {
    return new HttpResponse(null, { status: 204 });
  }),
];
