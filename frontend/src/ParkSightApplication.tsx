import "./ApplicationShell.css";
import { useEffect, useState } from "react";

import App from "./App";
import LoginScreen from "./components/LoginScreen";
import { logout } from "./api/auth";
import {
  getAccessToken,
  SESSION_EXPIRED_EVENT,
} from "./api/client";

export default function ParkSightApplication() {
  const [authenticated, setAuthenticated] = useState(
    () => getAccessToken() !== null,
  );

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
    setAuthenticated(false);
  }

  if (!authenticated) {
    return (
      <LoginScreen
        onAuthenticated={() => setAuthenticated(true)}
      />
    );
  }

  return (
    <>
      <header className="session-header">
        <div className="session-brand">
          <span className="session-brand-icon" aria-hidden="true">P</span>
          <div className="session-brand-text">
            <strong>ParkSight AI</strong>
            <span>Parking Intelligence Platform</span>
          </div>
        </div>

        <div className="session-actions">
          <span className="session-context">
            Recorded occupancy analysis
          </span>
          <button type="button" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>
      <App />
    </>
  );
}
