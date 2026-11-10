import "./ApplicationShell.css";
import { useEffect, useState } from "react";
import OrganisationSelector from "./components/OrganisationSelector";
import ParkingSetup from "./components/ParkingSetup";
import type { Organisation } from "./api/organisations";
import type { Camera, ParkingSite } from "./api/parkingResources";
import "./Onboarding.css";

// import App from "./App";
import LoginScreen from "./components/LoginScreen";
import { logout } from "./api/auth";
import {
  getAccessToken,
  SESSION_EXPIRED_EVENT,
} from "./api/client";
import App from "./App";

export default function ParkSightApplication() {
  const [authenticated, setAuthenticated] = useState(
    () => getAccessToken() !== null,
  );

  const [organisation, setOrganisation] = useState<Organisation | null>(null);
  const [site, setSite] = useState<ParkingSite | null>(null);
  const [camera, setCamera] = useState<Camera | null>(null);

  useEffect(() => {
    function handleSessionExpired() {
      setAuthenticated(false);
    }

    window.addEventListener(
      SESSION_EXPIRED_EVENT,
      handleSessionExpired,
    );

    return () => {
      window.removeEventListener(
        SESSION_EXPIRED_EVENT,
        handleSessionExpired,
      );
    };
  }, []);

  function handleLogout() {
    logout();
    setOrganisation(null);
    setSite(null);
    setCamera(null);
    setAuthenticated(false);
  }

  if (!authenticated) {
    return (
      <LoginScreen
        onAuthenticated={() => setAuthenticated(true)}
      />
    );
  }

  if (!organisation) {
  return (
    <OrganisationSelector
      onSelect={(selected) => {
        setOrganisation(selected);
        setSite(null);
        setCamera(null);
      }}
    />
  );
}

if (!site || !camera) {
  return (
    <ParkingSetup
      key={organisation.id}
      organisation={organisation}
      onBack={() => {
        setOrganisation(null);
        setSite(null);
        setCamera(null);
      }}
      onComplete={(selectedSite, selectedCamera) => {
        setSite(selectedSite);
        setCamera(selectedCamera);
      }}
    />
  );
}

  return (
  <>
    <header className="session-header">
      <div className="session-brand">
        <span className="session-brand-icon" aria-hidden="true">
          P
        </span>

        <div className="session-brand-text">
          <strong>ParkSight AI</strong>
          <span>Parking Intelligence Platform</span>
        </div>
      </div>

      <div className="session-actions">
        <span className="session-context">
          {organisation.name} / {site.name} / {camera.name}
        </span>

        <button
          type="button"
          onClick={() => {
            setSite(null);
            setCamera(null);
          }}
        >
          Change camera
        </button>

        <button type="button" onClick={handleLogout}>
          Sign out
        </button>
      </div>
    </header>

    <App
      key={`${organisation.id}:${site.id}:${camera.id}`}
      organisationId={organisation.id}
      siteId={site.id}
      cameraId={camera.id}
    />
  </>
);
}
