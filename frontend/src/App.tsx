
import { useEffect,useRef, useState } from "react";
import { Stage, Layer, Image as KonvaImage, Line, Circle, Text } from "react-konva";
import "./App.css";
import type Konva from "konva";
import {
  fetchSiteOccupancy,
  type OccupancyResponse,
} from "./api/occupancy";

type Point = { x: number; y: number };

type ParkingBay = {
  id: string;
  points: Point[];
};

const DEMO_ORGANISATION_ID =
  "426de53d-d71e-4e0d-93ff-f93af9ff0ac5";

const DEMO_SITE_ID =
  "88ba90de-72bc-463a-baa6-d14992dbf1f9";

const DEMO_RECORDING_ID =
  "424b3b3c-2c4f-4450-8a6d-8c4e60452425";

export default function App() {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [dashboardImage, setDashboardImage] =
  useState<HTMLImageElement | null>(null);
  const [bays, setBays] = useState<ParkingBay[]>([]);
  const [draft, setDraft] = useState<Point[]>([]);
  const [filename, setFilename] = useState("");
  const [selectedBayId, setSelectedBayId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const stageRef = useRef<Konva.Stage>(null);
  const [panMode, setPanMode] = useState(false);
  const [viewport, setViewport] = useState({ x: 0, y: 0 });
  const inputRef = useRef<HTMLInputElement>(null);

  const [viewMode, setViewMode] = useState<"editor" | "dashboard">("editor");
  const [occupancy, setOccupancy] = useState<OccupancyResponse | null>(null);
  const [occupancyLoading, setOccupancyLoading] = useState(false);
  const [occupancyError, setOccupancyError] = useState<string | null>(null);

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
  if (viewMode !== "dashboard") return;

  const img = new window.Image();
  let cancelled = false;

  img.onload = () => {
    if (!cancelled) {
      setDashboardImage(img);
    }
  };

  img.onerror = () => {
    if (!cancelled) {
      console.error("Unable to load dashboard reference image");
    }
  };

  img.src = "/api/v1/reference-images/demo";

  return () => {
    cancelled = true;
    img.onload = null;
    img.onerror = null;
  };
}, [viewMode]);


    useEffect(() => {
    if (viewMode !== "dashboard") return;

    const controller = new AbortController();

    setOccupancyLoading(true);
    setOccupancyError(null);

    fetchSiteOccupancy(
      DEMO_ORGANISATION_ID,
      DEMO_SITE_ID,
      DEMO_RECORDING_ID,
      controller.signal,
    )
      .then(setOccupancy)
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
  }, [viewMode]);

  function uploadImage(file?: File) {
    if (!file || !file.type.startsWith("image/")) return;

    const url = URL.createObjectURL(file);
    const img = new window.Image();

    img.onload = () => {
      setImage(img);
      setFilename(file.name);
      setBays([]);
      setDraft([]);
      URL.revokeObjectURL(url);
    };

    img.onerror = () => URL.revokeObjectURL(url);
    img.src = url;
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
      setBays((current) => [
        ...current,
        {
          id: `A${String(current.length + 1).padStart(2, "0")}`,
          points: next,
        },
      ]);
      setDraft([]);
    } else {
      setDraft(next);
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
  </div>
</header>

{viewMode === "dashboard" && (
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
)}


{viewMode === "editor" && (
  <section className="toolbar">
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(event) => uploadImage(event.target.files?.[0])}
        />

        <button onClick={() => inputRef.current?.click()}>
          Upload Camera Image
        </button>


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
                      text={bay.id}
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
    </main>
  );
}
