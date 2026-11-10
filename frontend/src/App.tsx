
import { useEffect,useRef, useState } from "react";
import { Stage, Layer, Image as KonvaImage, Line, Circle, Text } from "react-konva";
import { uploadCameraReferenceImage } from "./api/cameraConfiguration";
import "./App.css";
import "./DashboardTheme.css";
import type Konva from "konva";
import { apiFetch, ApiError } from "./api/client";
import { loadParkingBays, saveParkingBays } from "./api/parkingBays";
import {
  ChartNoAxesCombined,
  Maximize2,
} from "lucide-react";

import {
  listRecordings,
  type Recording,
} from "./api/recordings";

import {
  fetchSiteOccupancy,
  fetchOccupancyHistory,
  type OccupancyResponse,
  type OccupancyHistoryResponse,
} from "./api/occupancy";

import OccupancyHistoryChart from "./components/OccupancyHistoryChart";
import RecordingProcessor from "./components/RecordingProcessor";

type Point = { x: number; y: number };

type ParkingBay = {
  id: string;
  points: Point[];
};

// const DEMO_ORGANISATION_ID =
//   "426de53d-d71e-4e0d-93ff-f93af9ff0ac5";

// const DEMO_SITE_ID =
//   "88ba90de-72bc-463a-baa6-d14992dbf1f9";

// const DEMO_RECORDING_ID =
//   "424b3b3c-2c4f-4450-8a6d-8c4e60452425";

// const DEMO_CAMERA_ID =
//   "98116c54-fc85-46a9-a97b-c507891afda2";

type AppProps = {
  organisationId: string;
  siteId: string;
  cameraId: string;
};

export default function App({ organisationId, siteId, cameraId }: AppProps) {
  void organisationId;
  void siteId;
  void cameraId;
  // const [activeRecordingId, setActiveRecordingId] =
  //   useState(DEMO_RECORDING_ID);

  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [activeRecordingId, setActiveRecordingId] =
  useState<string | null>(null);
  const [recordingsLoading, setRecordingsLoading] = useState(true);
  const [recordingsError, setRecordingsError] = useState<string | null>(null);

  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [dashboardImage, setDashboardImage] =
  useState<HTMLImageElement | null>(null);
  const [bays, setBays] = useState<ParkingBay[]>([]);
  const [mappingLoading, setMappingLoading] = useState(true);
const [mappingSaving, setMappingSaving] = useState(false);
const [mappingError, setMappingError] = useState<string | null>(null);
const [mappingMessage, setMappingMessage] = useState<string | null>(null);
  const [draft, setDraft] = useState<Point[]>([]);
  const [filename, setFilename] = useState("");

  const [imageUploading, setImageUploading] = useState(false);
const [imageUploadError, setImageUploadError] = useState<string | null>(null);
  const [selectedBayId, setSelectedBayId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const stageRef = useRef<Konva.Stage>(null);
  const [panMode, setPanMode] = useState(false);
  const [viewport, setViewport] = useState({ x: 0, y: 0 });
  const inputRef = useRef<HTMLInputElement>(null);

  const [viewMode, setViewMode] = useState<"editor" | "dashboard">("dashboard");
  const [occupancy, setOccupancy] = useState<OccupancyResponse | null>(null);
  const [selectedTimestamp, setSelectedTimestamp] = useState<number | null>(null);
  const [occupancyLoading, setOccupancyLoading] = useState(false);
  const [occupancyError, setOccupancyError] = useState<string | null>(null);
  const historyDialogRef = useRef<HTMLDialogElement>(null);

  const [occupancyHistory, setOccupancyHistory] =
  useState<OccupancyHistoryResponse | null>(null);

  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const activeImage = viewMode === "dashboard" ? dashboardImage : image;

  const maxWidth = 1100;
  // const baseScale = image ? Math.min(1, maxWidth / image.width) : 1;
  // const width = image ? image.width * baseScale : maxWidth;
  // const height = image ? image.height * baseScale : 600;

  const baseScale = activeImage
  ? Math.min(1, maxWidth / activeImage.width)
  : 1;

const width = activeImage ? activeImage.width * baseScale : maxWidth;
const height = activeImage ? activeImage.height * baseScale : 600;
  const scale = baseScale * zoom;


  useEffect(() => {
  const controller = new AbortController();

  setRecordingsLoading(true);
  setRecordingsError(null);
  setRecordings([]);
  setActiveRecordingId(null);

  listRecordings(
    organisationId,
    siteId,
    cameraId,
    controller.signal,
  )
    .then((data) => {
      if (controller.signal.aborted) return;

      setRecordings(data);

      const latestCompleted = data.find(
        (recording) => recording.status === "completed",
      );

      setActiveRecordingId(latestCompleted?.id ?? null);
    })
    .catch((error: unknown) => {
      if (controller.signal.aborted) return;

      setRecordingsError(
        error instanceof Error
          ? error.message
          : "Unable to load recordings",
      );
    })
    .finally(() => {
      if (!controller.signal.aborted) {
        setRecordingsLoading(false);
      }
    });

  return () => controller.abort();
}, [organisationId, siteId, cameraId]);



useEffect(() => {
  const controller = new AbortController();

  setMappingLoading(true);
  setMappingError(null);
  setMappingMessage(null);
  setBays([]);

  async function restoreMapping() {
    try {
      const saved = await loadParkingBays(
        organisationId,
        siteId,
        cameraId,
      );

      if (!controller.signal.aborted) {
        setBays(saved);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setMappingError(
          error instanceof Error
            ? error.message
            : "Unable to load parking-bay mapping",
        );
      }
    } finally {
      if (!controller.signal.aborted) {
        setMappingLoading(false);
      }
    }
  }

  void restoreMapping();

  return () => controller.abort();
}, [organisationId, siteId, cameraId]);


useEffect(() => {
  const controller = new AbortController();
  const img = new window.Image();

  let objectUrl: string | null = null;
  let cancelled = false;

  // Reset image state when the selected camera changes.
  setImage(null);
  setDashboardImage(null);
  setFilename("");
  // setBays([]);
  setDraft([]);
  setSelectedBayId(null);

  async function loadReferenceImage() {
    try {
      const response = await apiFetch(
        `/organisations/${encodeURIComponent(organisationId)}` +
          `/sites/${encodeURIComponent(siteId)}` +
          `/cameras/${encodeURIComponent(cameraId)}/reference-image`,
        { signal: controller.signal },
      );

      const blob = await response.blob();

      if (cancelled) return;

      if (!["image/jpeg", "image/png"].includes(blob.type)) {
        throw new Error("Unsupported reference image format");
      }

      objectUrl = URL.createObjectURL(blob);

      img.onload = () => {
        if (cancelled) return;

        setImage(img);
        setDashboardImage(img);
        setFilename("Saved camera reference image");
      };

      img.onerror = () => {
        if (!cancelled) {
          console.error("Unable to decode camera reference image");
        }
      };

      img.src = objectUrl;
    } catch (error: unknown) {
      if (cancelled || controller.signal.aborted) return;

      // A newly created camera may not have an image yet.
      if (error instanceof ApiError && error.status === 404) {
        return;
      }

      console.error("Unable to load camera reference image", error);
    }
  }

  void loadReferenceImage();

  return () => {
    cancelled = true;
    controller.abort();

    img.onload = null;
    img.onerror = null;
    img.removeAttribute("src");

    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
    }
  };
}, [organisationId, siteId, cameraId]);


  useEffect(() => {
  const controller = new AbortController();

  setOccupancy(null);
  setOccupancyError(null);

  if (viewMode !== "dashboard" || !activeRecordingId) {
    setOccupancyLoading(false);
    return () => controller.abort();
  }

  setOccupancyLoading(true);

  fetchSiteOccupancy(
    organisationId,
    siteId,
    activeRecordingId,
    controller.signal,
    selectedTimestamp,
  )
    .then((data) => {
      if (!controller.signal.aborted) {
        setOccupancy(data);
      }
    })
    .catch((error: unknown) => {
      if (controller.signal.aborted) return;

      setOccupancyError(
        error instanceof Error
          ? error.message
          : "Unable to load occupancy data",
      );
    })
    .finally(() => {
      if (!controller.signal.aborted) {
        setOccupancyLoading(false);
      }
    });

  return () => controller.abort();
}, [
  viewMode,
  organisationId,
  siteId,
  activeRecordingId,
  selectedTimestamp,
]);


  //   useEffect(() => {
  //   if (viewMode !== "dashboard") return;

  //   const controller = new AbortController();

  //   setOccupancyLoading(true);
  //   setOccupancyError(null);

  //   fetchSiteOccupancy(
  //     DEMO_ORGANISATION_ID,
  //     DEMO_SITE_ID,
  //     activeRecordingId,
  //     controller.signal,
  //     selectedTimestamp,
  //   )
  //     .then((data) => {
  //       if (!controller.signal.aborted) {
  //         setOccupancy(data);
  //       }
  //     })
  //     .catch((error: unknown) => {
  //       if (controller.signal.aborted) return;

  //       setOccupancyError(
  //         error instanceof Error
  //           ? error.message
  //           : "Unable to load occupancy data",
  //       );
  //     })
  //     .finally(() => {
  //       if (!controller.signal.aborted) {
  //         setOccupancyLoading(false);
  //       }
  //     });

  //   return () => controller.abort();
  // }, [viewMode, selectedTimestamp, activeRecordingId]);

//   useEffect(() => {
//   if (viewMode !== "dashboard") return;

//   const controller = new AbortController();

//   setHistoryLoading(true);
//   setHistoryError(null);

//   fetchOccupancyHistory(
//     DEMO_ORGANISATION_ID,
//     DEMO_SITE_ID,
//     activeRecordingId,
//     controller.signal,
//   )
//     .then(setOccupancyHistory)
//     .catch((error: unknown) => {
//       if (controller.signal.aborted) return;

//       setHistoryError(
//         error instanceof Error
//           ? error.message
//           : "Unable to load occupancy history",
//       );
//     })
//     .finally(() => {
//       if (!controller.signal.aborted) {
//         setHistoryLoading(false);
//       }
//     });

//   return () => controller.abort();
// }, [viewMode, activeRecordingId]);

useEffect(() => {
  const controller = new AbortController();

  setOccupancyHistory(null);
  setHistoryError(null);

  if (viewMode !== "dashboard" || !activeRecordingId) {
    setHistoryLoading(false);
    return () => controller.abort();
  }

  setHistoryLoading(true);

  fetchOccupancyHistory(
    organisationId,
    siteId,
    activeRecordingId,
    controller.signal,
  )
    .then((data) => {
      if (!controller.signal.aborted) {
        setOccupancyHistory(data);
      }
    })
    .catch((error: unknown) => {
      if (controller.signal.aborted) return;

      setHistoryError(
        error instanceof Error
          ? error.message
          : "Unable to load occupancy history",
      );
    })
    .finally(() => {
      if (!controller.signal.aborted) {
        setHistoryLoading(false);
      }
    });

  return () => controller.abort();
}, [
  viewMode,
  organisationId,
  siteId,
  activeRecordingId,
]);


async function uploadImage(file?: File) {
  if (!file) return;

  if (!["image/jpeg", "image/png"].includes(file.type)) {
    setImageUploadError("Only JPEG and PNG images are supported.");
    return;
  }

  setImageUploading(true);
  setImageUploadError(null);

  try {
    // Persist the reference image before updating editor state.
    await uploadCameraReferenceImage(
      organisationId,
      siteId,
      cameraId,
      file,
    );

    const url = URL.createObjectURL(file);
    const img = new window.Image();

    try {
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve();
        img.onerror = () =>
          reject(new Error("Unable to display uploaded image"));
        img.src = url;
      });
    } finally {
      URL.revokeObjectURL(url);
    }

    setImage(img);
    setDashboardImage(img);
    setFilename(file.name);
    setBays([]);
    setDraft([]);
    setSelectedBayId(null);
    setZoom(1);
    setViewport({ x: 0, y: 0 });
  } catch (error) {
    setImageUploadError(
      error instanceof Error
        ? error.message
        : "Unable to upload camera reference image",
    );
  } finally {
    setImageUploading(false);
  }
}


  function fitToView() {
  setZoom(1);
  setViewport({ x: 0, y: 0 });
}

  async function importMapping(file?: File) {
    if (!file) return;

    if (!image) {
      window.alert("Upload the reference image first.");
      return;
    }

    try {
      const data: unknown = JSON.parse(await file.text());

      if (!data || typeof data !== "object") {
        throw new Error("Invalid mapping JSON");
      }

      const mapping = data as Record<string, unknown>;

      if (
        mapping.version !== 1 ||
        mapping.coordinate_system !== "image_pixels" ||
        mapping.image_width !== image.width ||
        mapping.image_height !== image.height ||
        mapping.reference_image !== filename ||
        !Array.isArray(mapping.bays)
      ) {
        throw new Error(
        `Mapping mismatch:
        Version: ${mapping.version}
        Coordinate system: ${mapping.coordinate_system}
        JSON image: ${mapping.reference_image}
        Uploaded image: ${filename}
        JSON dimensions: ${mapping.image_width}x${mapping.image_height}
        Uploaded dimensions: ${image.width}x${image.height}`
      );
      }

      const imported: ParkingBay[] = [];
      const ids = new Set<string>();

      for (const entry of mapping.bays) {
        if (!entry || typeof entry !== "object") {
          throw new Error("Invalid bay entry");
        }

        const bay = entry as Record<string, unknown>;

        if (
          typeof bay.id !== "string" ||
          !bay.id.trim() ||
          ids.has(bay.id) ||
          !Array.isArray(bay.points) ||
          bay.points.length !== 4
        ) {
          throw new Error("Invalid or duplicate bay");
        }

        const points: Point[] = [];

        for (const value of bay.points) {
          if (!value || typeof value !== "object") {
            throw new Error(`Invalid point in ${bay.id}`);
          }

          const point = value as Record<string, unknown>;

          if (
            typeof point.x !== "number" ||
            typeof point.y !== "number" ||
            !Number.isFinite(point.x) ||
            !Number.isFinite(point.y) ||
            point.x < 0 ||
            point.y < 0 ||
            point.x >= image.width ||
            point.y >= image.height
          ) {
            throw new Error(`Invalid coordinates in ${bay.id}`);
          }

          points.push({ x: point.x, y: point.y });
        }

        ids.add(bay.id);
        imported.push({ id: bay.id, points });
      }

      if (imported.length === 0) {
        throw new Error("Mapping contains no bays");
      }

      setBays(imported);
      setDraft([]);

      window.alert(`Imported ${imported.length} parking bays.`);
    } catch (error) {
      window.alert(
        error instanceof Error ? error.message : "Import failed"
      );
    }
  }




function addPoint(point: Point) {
  if (!image) return;

  const next = [...draft, point];

  if (next.length === 4) {
    setBays((current) => {
      const prefix = "CCP-L01";
      const existing = new Set(current.map((bay) => bay.id));

      let number = 1;
      let bayId: string;

      do {
        bayId = `${prefix}-B${String(number).padStart(3, "0")}`;
        number++;
      } while (existing.has(bayId));

      return [
        ...current,
        {
          id: bayId,
          points: next,
        },
      ];
    });

    setDraft([]);
  } else {
    setDraft(next);
  }
}




async function persistMapping() {
  if (!image || mappingLoading || mappingSaving) return;

  if (draft.length > 0) {
    setMappingError("Finish or undo the current polygon before saving.");
    return;
  }

  if (bays.length === 0) {
    setMappingError("Draw at least one parking bay before saving.");
    return;
  }

  setMappingSaving(true);
  setMappingError(null);
  setMappingMessage(null);

  try {
    await saveParkingBays(
      organisationId,
      siteId,
      cameraId,
      bays,
    );

    setMappingMessage(
      `Saved ${bays.length} parking bays successfully.`,
    );
  } catch (error) {
    setMappingError(
      error instanceof Error
        ? error.message
        : "Unable to save parking-bay mapping",
    );
  } finally {
    setMappingSaving(false);
  }
}


  function exportJSON() {
    if (!image) return;

    const data = {
      version: 1,
      reference_image: filename,
      image_width: image.width,
      image_height: image.height,
      coordinate_system: "image_pixels",
      bays,
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "parksight-bay-mapping.json";
    link.click();
    URL.revokeObjectURL(url);
  }


  const displayBays =
  viewMode === "dashboard" && occupancy
    ? occupancy.bays.map((bay) => ({
        id: bay.code,
        points: bay.polygon,
        state: bay.state,
      }))
    : bays.map((bay) => ({
        ...bay,
        state: "mapped" as const,
      }));

  return (
    <main className="app">

<header>
  <h1>ParkSight AI</h1>
  <p>
    {viewMode === "editor"
      ? "Parking Bay Mapping Editor"
      : "Recorded Parking Occupancy"}
  </p>

  <div className="view-switch">
    <button
      type="button"
      className={viewMode === "editor" ? "active" : ""}
      onClick={() => setViewMode("editor")}
    >
      Mapping Editor
    </button>

    <button
      type="button"
      className={viewMode === "dashboard" ? "active" : ""}
      onClick={() => {
        setSelectedBayId(null);
        setDraft([]);
        setViewMode("dashboard");
      }}
    >
      Occupancy Dashboard
    </button>
    <button type="button" onClick={fitToView}>
  Fit to View
</button>

   {viewMode === "dashboard" && (
  <button
    type="button"
    onClick={() => {
      historyDialogRef.current?.showModal();
    }}
  >
    View Occupancy History
  </button>
)}

  </div>
</header>

<dialog
  ref={historyDialogRef}
  className="history-modal"
  aria-labelledby="history-modal-title"
  onClick={(event) => {
    if (event.target === event.currentTarget) {
      event.currentTarget.close();
    }
  }}
>
  <div className="history-modal-content">
    <div className="history-modal-header">
      <h2 id="history-modal-title">Historical Occupancy</h2>

      <button
        type="button"
        aria-label="Close historical occupancy"
        onClick={() => historyDialogRef.current?.close()}
      >
        ✕
      </button>
    </div>

    <p className="recording-label">
      Occupancy changes throughout the recorded CCTV footage
    </p>

    {historyLoading && <p>Loading historical occupancy...</p>}

    {historyError && (
      <p role="alert" className="occupancy-error">
        {historyError}
      </p>
    )}

    {occupancyHistory && !historyLoading && !historyError && (
      <>
        <div className="history-summary">
          <p>
            Recorded samples:{" "}
            <strong>{occupancyHistory.history.length}</strong>
          </p>

          <p>
            Recording duration:{" "}
            <strong>
              {occupancyHistory.history.length > 0
                ? occupancyHistory.history[
                    occupancyHistory.history.length - 1
                  ].timestamp_seconds.toFixed(3)
                : "0.000"}
              s
            </strong>
          </p>
        </div>

        <OccupancyHistoryChart
          history={occupancyHistory.history}
          selectedTimestamp={selectedTimestamp}
          onSelectTimestamp={(timestamp) => {
            setSelectedTimestamp(timestamp);
            historyDialogRef.current?.close();
          }}
        />
      </>
    )}
  </div>
</dialog>


{viewMode === "dashboard" && (<>
<section className="recording-selection">
  <h2>Camera recordings</h2>

  {recordingsLoading && (
    <p role="status">Loading recordings...</p>
  )}

  {recordingsError && (
    <p role="alert" className="occupancy-error">
      {recordingsError}
    </p>
  )}

  {!recordingsLoading && !recordingsError && (
    <>
      {recordings.length === 0 ? (
        <p>
          No recordings available for this camera.
          Upload an MP4 recording to begin occupancy analysis.
        </p>
      ) : (
        <>
          <label htmlFor="active-recording">
            Select recording
          </label>

          <select
            id="active-recording"
            value={activeRecordingId ?? ""}
            onChange={(event) => {
              setSelectedTimestamp(null);
              setActiveRecordingId(event.target.value || null);
            }}
          >
            <option value="">Select a completed recording</option>

            {recordings
              .filter(
                (recording) =>
                  recording.status === "completed",
              )
              .map((recording) => (
                <option
                  key={recording.id}
                  value={recording.id}
                >
                  {recording.original_filename ??
                    recording.filename ??
                    recording.id}
                </option>
              ))}
          </select>

          {!activeRecordingId && (
            <p>
              No completed recording selected.
              Upload a recording or select one above.
            </p>
          )}
        </>
      )}
    </>
  )}
</section>
  <section className="occupancy-dashboard">
    {occupancyLoading && <p>Loading occupancy data...</p>}

    {occupancyError && (
      <p role="alert" className="occupancy-error">
        {occupancyError}
      </p>
    )}

    {occupancy && !occupancyLoading && !occupancyError && (
      <>
        <p className="recording-label">
          Recorded video · Timestamp:{" "}
          {occupancy.timestamp_seconds.toFixed(3)}s
        </p>

        <div className="occupancy-stats">
          <div className="stat-card">
            <strong>{occupancy.summary.total}</strong>
            <span>Total bays</span>
          </div>

          <div className="stat-card available">
            <strong>{occupancy.summary.available}</strong>
            <span>Available</span>
          </div>

          <div className="stat-card occupied">
            <strong>{occupancy.summary.occupied}</strong>
            <span>Occupied</span>
          </div>

          <div className="stat-card unknown">
            <strong>{occupancy.summary.unknown}</strong>
            <span>Unknown</span>
          </div>
        </div>
      </>
    )}


  </section>

  </>

)}


{viewMode === "editor" && (
  <section className="toolbar">

<input
  ref={inputRef}
  type="file"
  accept="image/jpeg,image/png"
  hidden
  disabled={imageUploading}
  onChange={async (event) => {
    const file = event.currentTarget.files?.[0];

    // Reset the input so the same file can be selected again.
    event.currentTarget.value = "";

    await uploadImage(file);
  }}
/>

<button
  type="button"
  disabled={imageUploading}
  onClick={() => inputRef.current?.click()}
>
  {imageUploading ? "Uploading..." : "Upload Camera Image"}
</button>

{imageUploadError && (
  <p role="alert" className="error-message">
    {imageUploadError}
  </p>
)}


        {/* <button onClick={() => inputRef.current?.click()}>
          Upload Camera Image
        </button> */}


        <input

          type="file"
          accept=".json,application/json"
          disabled={!image}
          onChange={async (event) => {
            await importMapping(event.target.files?.[0]);
            event.target.value = "";
          }}
        />


        <button
          disabled={draft.length === 0}
          onClick={() => setDraft((points) => points.slice(0, -1))}
        >
          Undo Point
        </button>

        <button
          disabled={bays.length === 0}
          onClick={() => setBays((current) => current.slice(0, -1))}
        >
          Remove Last Bay
        </button>


<button
  type="button"
  disabled={
    !image ||
    mappingLoading ||
    mappingSaving ||
    imageUploading ||
    bays.length === 0 ||
    draft.length > 0
  }
  onClick={() => void persistMapping()}
>
  {mappingSaving ? "Saving..." : "Save Mapping"}
</button>

{mappingLoading && <span>Loading saved mapping...</span>}

{mappingError && (
  <span role="alert" style={{ color: "#ef4444" }}>
    {mappingError}
  </span>
)}

{mappingMessage && (
  <span role="status" style={{ color: "#22c55e" }}>
    {mappingMessage}
  </span>
)}


        <button disabled={bays.length === 0} onClick={exportJSON}>
          Export JSON
        </button>

        <button onClick={() => setPanMode((current) => !current)}>
        {panMode ? "Switch to Draw Mode" : "Pan Image"}
        </button>

    </section>)}


      <section className="workspace">
        <div className="canvas-panel">
          {activeImage ? (



<Stage
  ref={stageRef}
  width={width}
  height={height}
  scaleX={scale}
  scaleY={scale}
  x={viewport.x}
  y={viewport.y}
  draggable={panMode}
  onDragEnd={(event) => {
    if (event.target === stageRef.current) {
      setViewport({
        x: event.target.x(),
        y: event.target.y(),
      });
    }
  }}
  onWheel={(event) => {
    event.evt.preventDefault();

    const stage = stageRef.current;
    if (!stage) return;

    const pointer = stage.getPointerPosition();
    if (!pointer) return;

    const oldScale = stage.scaleX();
    const sensitivity = event.evt.ctrlKey ? 0.0015 : 0.0008;

    const newZoom = Math.max(
      1,
      Math.min(
        8,
        zoom * Math.exp(-event.evt.deltaY * sensitivity)
      )
    );

    const newScale = baseScale * newZoom;

    if (Math.abs(newScale - oldScale) < 0.000001) return;

    const imagePoint = {
      x: (pointer.x - stage.x()) / oldScale,
      y: (pointer.y - stage.y()) / oldScale,
    };

    setZoom(newZoom);
    setViewport({
      x: pointer.x - imagePoint.x * newScale,
      y: pointer.y - imagePoint.y * newScale,
    });
  }}
  onClick={(event) => {
    // if (panMode) return;
    if (panMode || viewMode === "dashboard") return;

    const target = event.target;
    if (
      target !== target.getStage() &&
      target.getClassName() !== "Image"
    ) {
      return;
    }

    const stage = stageRef.current;
    const pointer = stage?.getPointerPosition();
    if (!pointer || !stage) return;

    const transform = stage.getAbsoluteTransform().copy().invert();
    const point = transform.point(pointer);

    if (
      point.x < 0 ||
      point.y < 0 ||
      point.x >= image!.width ||
      point.y >= image!.height
    ) {
      return;
    }

    addPoint({
      x: Math.round(point.x),
      y: Math.round(point.y),
    });
  }}
>



              <Layer>
               <KonvaImage
  image={activeImage}
  width={activeImage.width}
  height={activeImage.height}
  listening
/>



{displayBays.map((bay) => {
  const selected =
    viewMode === "editor" && selectedBayId === bay.id;

  const color =
    viewMode === "dashboard"
      ? bay.state === "empty"
        ? "#22c55e"
        : bay.state === "occupied"
          ? "#ef4444"
          : "#f59e0b"
      : selected
        ? "#facc15"
        : "#22c55e";

  return (
    <Line
      key={bay.id}
      points={bay.points.flatMap((point) => [
        point.x,
        point.y,
      ])}
      closed
      stroke={color}
      fill={`${color}40`}
      strokeWidth={selected ? 3 : 2}
      listening={viewMode === "editor"}
      onClick={(event) => {
        if (viewMode !== "editor") return;

        event.cancelBubble = true;
        setSelectedBayId(bay.id);
        setDraft([]);
      }}
    />
  );
})}


{viewMode === "editor" && bays
  .filter((bay) => bay.id === selectedBayId)
  .flatMap((bay) =>
    bay.points.map((point, index) => (
      <Circle
        key={`${bay.id}-corner-${index}`}
        x={point.x}
        y={point.y}
        radius={6}
        fill="#facc15"
        stroke="#000000"
        strokeWidth={1}
        draggable
        onDragEnd={(event) => {
          const x = Math.round(event.target.x());
          const y = Math.round(event.target.y());

          setBays((current) =>
            current.map((item) =>
              item.id === bay.id
                ? {
                    ...item,
                    points: item.points.map((p, i) =>
                      i === index
                        ? {
                            x: Math.max(
                              0,
                              Math.min(image!.width - 1, x)
                            ),
                            y: Math.max(
                              0,
                              Math.min(image!.height - 1, y)
                            ),
                          }
                        : p
                    ),
                  }
                : item
            )
          );
        }}
      />
    ))
  )}


                {displayBays.map((bay) => {
                  const center = {
                    x: bay.points.reduce((sum, p) => sum + p.x, 0) / 4,
                    y: bay.points.reduce((sum, p) => sum + p.y, 0) / 4,
                  };

                  return (
                    <Text
                      key={`${bay.id}-label`}
                      x={center.x - 12}
                      y={center.y - 8}
                      text={bay.id.split("-").at(-1) ?? bay.id}
                      fill="#ffffff"
                      fontSize={14}
                      fontStyle="bold"
                      shadowColor="#000000"
                      shadowBlur={4}
                      listening={false}
                    />
                  );
                })}


{viewMode === "editor" && draft.length > 0 &&  (
  <>
    <Line
      points={draft.flatMap((p) => [p.x, p.y])}
      stroke="#facc15"
      strokeWidth={2}
      dash={[6, 4]}
      listening={false}
    />

    {draft.map((p, index) => (
      <Circle
        key={index}
        x={p.x}
        y={p.y}
        radius={5}
        fill="#facc15"
        stroke="#000000"
        strokeWidth={1}
        listening={false}
      />
    ))}
  </>
)}

              </Layer>
            </Stage>
          ) : (
            <div className="empty">
              Upload a parking-area image to begin mapping.
            </div>
          )}
        </div>


<aside>
  <h2>
    Parking Bays (
    {viewMode === "dashboard" && occupancy
      ? occupancy.bays.length
      : bays.length}
    )
  </h2>

  {viewMode === "editor" ? (
    <>
      <p>Click four corners of each parking space in order.</p>

      {draft.length > 0 && (
        <p>Drawing: {draft.length}/4 points</p>
      )}

      {bays.map((bay) => (
        <div className="bay-item" key={bay.id}>
          <span>{bay.id}</span>
          <span>Mapped</span>
        </div>
      ))}
    </>
  ) : occupancy ? (
    <>
      <p>Latest classifications from recorded CCTV footage.</p>

      <div className="occupancy-bay-list">
  {occupancy.bays.map((bay) => (
    <div className="bay-item" key={bay.id}>
      <span>{bay.code}</span>
      <span className={`occupancy-state ${bay.state}`}>
        {bay.state === "empty"
          ? "Available"
          : bay.state === "occupied"
            ? "Occupied"
            : "Unknown"}
      </span>
    </div>
  ))}
</div>
    </>
  ) : (
    <p>Occupancy data unavailable.</p>
  )}
</aside>

      </section>

      {viewMode === "dashboard" && (
        <section
          className="dashboard-bottom-grid"
          aria-label="Occupancy analytics and recording processing"
        >
          <div className="dashboard-history-card">
            <div className="dashboard-history-header">
              <div>
                <h2 className="card-title-with-icon">
  <ChartNoAxesCombined size={20} strokeWidth={1.8} />
  Occupancy History
</h2>
                <p>Parking availability throughout the recording</p>
              </div>
              <button
                type="button"
                className="history-expand-button"
                onClick={() => historyDialogRef.current?.showModal()}
              >
                <Maximize2 size={16} strokeWidth={1.8} />
Expand
              </button>
            </div>

            {historyLoading && (
              <p role="status">Loading occupancy history...</p>
            )}

            {historyError && (
              <p role="alert" className="occupancy-error">
                {historyError}
              </p>
            )}

            {!historyLoading &&
              !historyError &&
              occupancyHistory &&
              occupancyHistory.history.length > 0 && (
                <OccupancyHistoryChart
                  history={occupancyHistory.history}
                  selectedTimestamp={selectedTimestamp}
                  onSelectTimestamp={(timestamp) => {
                    setSelectedTimestamp(timestamp);
                  }}
                />
              )}

            {!historyLoading &&
              !historyError &&
              (!occupancyHistory ||
                occupancyHistory.history.length === 0) && (
                <p>No occupancy history available yet.</p>
              )}
          </div>

          <RecordingProcessor
  organisationId={organisationId}
  siteId={siteId}
  cameraId={cameraId}
  onCompleted={(recordingId) => {
    setSelectedTimestamp(null);
    setOccupancy(null);
    setOccupancyHistory(null);

    setRecordings((previous) => {
      const existing = previous.find(
        (recording) => recording.id === recordingId,
      );

      return [
        {
          ...existing,
          id: recordingId,
          status: "completed" as const,
        },
        ...previous.filter(
          (recording) => recording.id !== recordingId,
        ),
      ];
    });

    setActiveRecordingId(recordingId);
  }}
/>
        </section>
      )}
    </main>
  );
}
