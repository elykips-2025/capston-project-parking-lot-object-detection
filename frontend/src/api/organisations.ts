import { apiFetch } from "./client";

export type Organisation = {
  id: string;
  name: string;
  created_at: string;
};

export async function listOrganisations(): Promise<Organisation[]> {
  const response = await apiFetch("/organisations");
  return response.json();
}

export async function createOrganisation(
  name: string,
): Promise<Organisation> {
  const response = await apiFetch("/organisations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: name.trim(),
    }),
  });

  return response.json();
}
