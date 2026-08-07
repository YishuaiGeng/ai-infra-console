import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/api/session/login/route";

function loginRequest(body: unknown) {
  return new Request("http://console.test/api/session/login", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("login route handler", () => {
  it("stores the bearer in a secure HttpOnly cookie and never returns it", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json({
          access_token: "central-secret-token",
          token_type: "bearer",
          expires_in: 1800,
        }),
      ),
    );

    const response = await POST(loginRequest({ username: "admin", password: "valid" }));
    const cookie = response.headers.get("set-cookie") ?? "";

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ authenticated: true });
    expect(cookie).toContain("aic_session=central-secret-token");
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("Secure");
    expect(cookie).toContain("SameSite=strict");
    expect(cookie).toContain("Max-Age=1800");
  });

  it("preserves Central authentication errors without setting a cookie", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json(
          { error: { code: "invalid_credentials", message: "Invalid", request_id: "req-1" } },
          { status: 401 },
        ),
      ),
    );

    const response = await POST(loginRequest({ username: "admin", password: "wrong" }));

    expect(response.status).toBe(401);
    expect(response.headers.get("set-cookie")).toBeNull();
    expect((await response.json()).error.code).toBe("invalid_credentials");
  });

  it("rejects malformed input before contacting Central", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(loginRequest({ username: "", password: "" }));

    expect(response.status).toBe(422);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
