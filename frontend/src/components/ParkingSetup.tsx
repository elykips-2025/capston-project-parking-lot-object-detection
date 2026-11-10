import { useEffect, useState, type FormEvent } from "react";
import {
  createCamera,
  createParkingSite,
  listCameras,
  listParkingSites,
  type Camera,
  type ParkingSite,
} from "../api/parkingResources";
import type { Organisation } from "../api/organisations";

type Props = {
  organisation: Organisation;
  onBack: () => void;
  onComplete: (site: ParkingSite, camera: Camera) => void;
};

export default function ParkingSetup({
  organisation,
  onBack,
  onComplete,
}: Props) {
  const [sites, setSites] = useState<ParkingSite[]>([]);
  const [site, setSite] = useState<ParkingSite | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [siteName, setSiteName] = useState("");
  const [siteLocation, setSiteLocation] = useState("");
  const [cameraName, setCameraName] = useState("");
  const [loadingSites, setLoadingSites] = useState(true);
  const [loadingCameras, setLoadingCameras] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    setSite(null);
    setCameras([]);
    setSites([]);
    setLoadingSites(true);
    setError(null);

    listParkingSites(organisation.id, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setSites(data.filter((item) => item.organisation_id === organisation.id));
        }
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Unable to load sites");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingSites(false);
      });

    return () => controller.abort();
  }, [organisation.id]);

  useEffect(() => {
    const controller = new AbortController();

    setCameras([]);
    setLoadingCameras(Boolean(site));
    setError(null);

    if (!site) return () => controller.abort();

    listCameras(organisation.id, site.id, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setCameras(data.filter((item) => item.site_id === site.id));
        }
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Unable to load cameras");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingCameras(false);
      });

    return () => controller.abort();
  }, [organisation.id, site]);

  async function handleCreateSite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (siteName.trim().length < 2 || saving) return;

    setSaving(true);
    setError(null);

    try {
      const created = await createParkingSite(
        organisation.id,
        siteName,
        siteLocation,
      );

      setSites((previous) => [...previous, created]);
      setSite(created);
      setSiteName("");
      setSiteLocation("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create site");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateCamera(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!site || cameraName.trim().length < 2 || saving) return;

    setSaving(true);
    setError(null);

    try {
      const created = await createCamera(
        organisation.id,
        site.id,
        cameraName,
      );

      setCameras((previous) => [...previous, created]);
      setCameraName("");
      onComplete(site, created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create camera");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="onboarding-screen">
      <section className="onboarding-panel">
        <button type="button" onClick={onBack}>
          Change organisation
        </button>

        <h1>{organisation.name}</h1>
        <p>Select or create a parking site and camera.</p>

        {error && <p role="alert">{error}</p>}

        <h2>Parking sites</h2>

        {loadingSites ? (
          <p>Loading parking sites...</p>
        ) : (
          <>
            {sites.filter((item) => item.status === "active").map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setSite(item)}
                aria-pressed={site?.id === item.id}
              >
                {item.name}
              </button>
            ))}

            <form onSubmit={handleCreateSite}>
              <label htmlFor="site-name">New parking site</label>
              <input
                id="site-name"
                value={siteName}
                maxLength={200}
                onChange={(event) => setSiteName(event.target.value)}
                placeholder="e.g. Coventry Central"
              />

              <label htmlFor="site-location">Location (optional)</label>
              <input
                id="site-location"
                value={siteLocation}
                maxLength={255}
                onChange={(event) => setSiteLocation(event.target.value)}
              />

              <button
                type="submit"
                disabled={saving || siteName.trim().length < 2}
              >
                Create site
              </button>
            </form>
          </>
        )}

        {site && (
          <>
            <h2>Cameras — {site.name}</h2>

            {loadingCameras ? (
              <p>Loading cameras...</p>
            ) : (
              <>
                {cameras.filter((item) => item.status === "active").map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onComplete(site, item)}
                  >
                    {item.name}
                  </button>
                ))}

                <form onSubmit={handleCreateCamera}>
                  <label htmlFor="camera-name">New camera</label>
                  <input
                    id="camera-name"
                    value={cameraName}
                    maxLength={200}
                    onChange={(event) => setCameraName(event.target.value)}
                    placeholder="e.g. Entrance Camera 01"
                  />

                  <button
                    type="submit"
                    disabled={saving || cameraName.trim().length < 2}
                  >
                    Create camera
                  </button>
                </form>
              </>
            )}
          </>
        )}
      </section>
    </main>
  );
}
