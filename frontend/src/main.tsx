import "./theme.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import ParkSightApplication from "./ParkSightApplication";

import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ParkSightApplication />
  </StrictMode>,
);
