import { apiFetch } from "./client";

export type ParkingSite = {
  id: string;
  organisation_id: string;
  name: string;
  location: string | null;
  status: "active" | "inactive";
  created_at: string;
};

export type Camera = {
  id: string;
  site_id: string;
  name: string;
  status: "active" | "inactive";
  created_at: string;
};

export async function listParkingSites(
  organisationId: string,
  signal?: AbortSignal,
): Promise<ParkingSite[]> {
  const response = await apiFetch(
    `/organisations/${encodeURIComponent(organisationId)}/sites`,
    { signal },
  );

  return response.json();
}

export async function createParkingSite(
  organisationId: string,
  name: string,
  location?: string,
): Promise<ParkingSite> {
  const response = await apiFetch(
    `/organisations/${encodeURIComponent(organisationId)}/sites`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name.trim(),
        location: location?.trim() || null,
      }),
    },
  );

  return response.json();
}

export async function listCameras(
  organisationId: string,
  siteId: string,
  signal?: AbortSignal,
): Promise<Camera[]> {
  const response = await apiFetch(
    `/organisations/${encodeURIComponent(organisationId)}` +
      `/sites/${encodeURIComponent(siteId)}/cameras`,
    { signal },
  );

  return response.json();
}

export async function createCamera(
  organisationId: string,
  siteId: string,
  name: string,
): Promise<Camera> {
  const response = await apiFetch(
    `/organisations/${encodeURIComponent(organisationId)}` +
      `/sites/${encodeURIComponent(siteId)}/cameras`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() }),
    },
  );

  return response.json();
}
