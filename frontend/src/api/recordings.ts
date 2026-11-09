const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export type RecordingStatus =
  | "uploaded"
  | "processing"
  | "completed"
  | "failed";

export type Recording = {
  id: string;
  status: RecordingStatus;
  display_status?: string;
  filename?: string;
  original_filename?: string;
  processing_attempts?: number;
  observation_count?: number;
  error?: string | null;
};

function recordingUrl(
  organisationId: string,
  siteId: string,
  cameraId: string,
  recordingId?: string,
) {
  const base = `${API_BASE}/organisations/${organisationId}/sites/${siteId}/cameras/${cameraId}/recordings`;
  return recordingId ? `${base}/${recordingId}` : base;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed: HTTP ${response.status}`,
    );
  }
  return response.json() as Promise<T>;
}

export async function uploadRecording(
  organisationId: string,
  siteId: string,
  cameraId: string,
  file: File,
): Promise<Recording> {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(
    recordingUrl(organisationId, siteId, cameraId),
    { method: "POST", body: form },
  );

  return parseResponse<Recording>(response);
}

export async function fetchRecordingStatus(
  organisationId: string,
  siteId: string,
  cameraId: string,
  recordingId: string,
  signal?: AbortSignal,
): Promise<Recording> {
  const response = await fetch(
    recordingUrl(organisationId, siteId, cameraId, recordingId),
    { signal, cache: "no-store" },
  );

  return parseResponse<Recording>(response);
}
