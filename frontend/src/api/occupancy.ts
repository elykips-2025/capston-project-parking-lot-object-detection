
export type OccupancyState = "empty" | "occupied" | "unknown";

export type OccupancyBay = {
  id: string;
  code: string;
  type: "standard" | "accessible" | "ev" | "reserved";
  polygon: { x: number; y: number }[];
  raw_state: OccupancyState;
  state: OccupancyState;
  occupied_probability: number;
  available: boolean;
};

export type OccupancyResponse = {
  site_id: string;
  recording_id: string;
  source: "recorded_video";
  timestamp_seconds: number;
  summary: {
    total: number;
    available: number;
    occupied: number;
    unknown: number;
  };
  bays: OccupancyBay[];
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export async function fetchSiteOccupancy(
  organisationId: string,
  siteId: string,
  recordingId: string,
  signal?: AbortSignal,
): Promise<OccupancyResponse> {
  const url = new URL(
    `${API_BASE_URL}/organisations/${organisationId}/sites/${siteId}/occupancy`,
    window.location.origin,
  );

  url.searchParams.set("recording_id", recordingId);

  const response = await fetch(url, { signal });

  if (!response.ok) {
    throw new Error(
      `Failed to fetch occupancy: HTTP ${response.status}`,
    );
  }

  const data: OccupancyResponse = await response.json();

  if (
    data.source !== "recorded_video" ||
    !Array.isArray(data.bays) ||
    !data.summary
  ) {
    throw new Error("Invalid occupancy API response");
  }

  return data;
}
