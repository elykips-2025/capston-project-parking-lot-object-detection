import { apiFetch, setAccessToken } from "./client";

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export async function login(
  email: string,
  password: string,
): Promise<void> {
  const response = await apiFetch("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: email.trim().toLowerCase(),
      password,
    }),
  });

  const data: LoginResponse = await response.json();

  if (
    typeof data.access_token !== "string" ||
    !data.access_token ||
    data.token_type.toLowerCase() !== "bearer" ||
    !Number.isFinite(data.expires_in) ||
    data.expires_in <= 0
  ) {
    throw new Error("Invalid authentication response");
  }

  setAccessToken(data.access_token);
}

export function logout(): void {
  setAccessToken(null);
}
