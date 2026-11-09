import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import {
  uploadRecording,
  fetchRecordingStatus,
  type Recording,
} from "../api/recordings";

type Props = {
  organisationId: string;
  siteId: string;
  cameraId: string;
  onCompleted: (recordingId: string) => void;
};

export default function RecordingProcessor({
  organisationId,
  siteId,
  cameraId,
  onCompleted,
}: Props) {
  const [recording, setRecording] = useState<Recording | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!recording || !["uploaded", "processing"].includes(recording.status)) {
      return;
    }

    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const current = await fetchRecordingStatus(
          organisationId,
          siteId,
          cameraId,
          recording!.id,
          controller.signal,
        );

        if (controller.signal.aborted) return;

        setRecording(current);
        setError(null);

        if (current.status === "completed") {
          onCompleted(current.id);
        } else if (
          current.status === "uploaded" ||
          current.status === "processing"
        ) {
          timer = setTimeout(poll, 2000);
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Status check failed");

        if (
          err instanceof ApiError &&
          [400, 401, 403, 404, 410, 422].includes(err.status)
        ) {
          return;
        }

        timer = setTimeout(poll, 2000);
      }
    }

    timer = setTimeout(poll, 2000);

    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [
    recording,
    organisationId,
    siteId,
    cameraId,
    onCompleted,
  ]);

  async function handleUpload(file?: File) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".mp4")) {
      setError("Please select an MP4 video.");
      return;
    }

    if (file.size > 100 * 1024 * 1024) {
      setError("Maximum upload size is 100 MB.");
      return;
    }

    setUploading(true);
    setRecording(null);
    setError(null);

    try {
      const created = await uploadRecording(
        organisationId,
        siteId,
        cameraId,
        file,
      );
      setRecording(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const label: Record<string, string> = {
    uploaded: "Queued",
    processing: "Processing",
    completed: "Completed",
    failed: "Failed",
  };

  return (
    <section className="recording-processor">
      <h2>Video Processing</h2>
      <p>Upload a CCTV recording for automatic parking occupancy analysis.</p>

      <input
        type="file"
        accept=".mp4,video/mp4"
        aria-label="Upload CCTV recording"
        disabled={uploading}
        onChange={(event) => {
          const file = event.currentTarget.files?.[0];
          void handleUpload(file);
          event.currentTarget.value = "";
        }}
      />

      {uploading && <p>Uploading video...</p>}

      {recording && (
        <div aria-live="polite">
          <p>
            <strong>Status:</strong>{" "}
            {label[recording.status] ?? recording.status}
          </p>
          <p>
            <strong>Recording:</strong>{" "}
            {recording.filename ??
              recording.original_filename ??
              recording.id}
          </p>
          {recording.status === "processing" && (
            <p>Running vehicle detection and occupancy classification...</p>
          )}
          {recording.status === "completed" && (
            <p>
              Processing complete.{" "}
              {recording.observation_count ?? 0} observations saved.
            </p>
          )}
          {recording.status === "failed" && (
            <p role="alert">
              {recording.error ?? "Processing failed."}
            </p>
          )}
        </div>
      )}

      {error && <p role="alert" className="occupancy-error">{error}</p>}
    </section>
  );
}
