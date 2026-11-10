import { apiFetch } from "./client";

export interface ParkingBayMapping {
  id: string;
  points: { x: number; y: number }[];
}

function endpoint(
  organisationId: string,
  siteId: string,
  cameraId: string,
): string {
  return (
    `/organisations/${encodeURIComponent(organisationId)}` +
    `/sites/${encodeURIComponent(siteId)}` +
    `/cameras/${encodeURIComponent(cameraId)}/parking-bays`
  );
}

export async function loadParkingBays(
  organisationId: string,
  siteId: string,
  cameraId: string,
): Promise<ParkingBayMapping[]> {
  const response = await apiFetch(
    endpoint(organisationId, siteId, cameraId),
  );

  const result = await response.json();
  return result.bays;
}

export async function saveParkingBays(
  organisationId: string,
  siteId: string,
  cameraId: string,
  bays: ParkingBayMapping[],
): Promise<void> {
  await apiFetch(endpoint(organisationId, siteId, cameraId), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bays }),
  });
}
