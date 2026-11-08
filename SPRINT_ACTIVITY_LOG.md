# ParkSight AI — Three-Sprint Activity Plan and Evidence

**Project:** Quantic MSSE Capstone — ParkSight AI
**Repository:** https://github.com/elykips-2025/capston-project-parking-lot-object-detection
**Scope:** Individual, single-site, recorded-CCTV occupancy analysis MVP
**Document status:** Retrospective workstream consolidation and forward plan; updated 8 November 2026

> **Evidence integrity:** These three sprint groupings organise work already performed and remaining work. They do not establish that three formal Scrum sprints, sprint planning meetings, reviews or demonstrations occurred. Dates and ceremonies must be supported by actual records. Individual-submission eligibility remains subject to Quantic confirmation.

## Sprint overview

| Proposed sprint | Objective | Current evidence | Status |
|---|---|---|---|
| 1 — Foundation and Computer Vision | Establish backend, recording ingestion, detection and bay mapping | Backend/API, PostgreSQL, YOLO, 27 mapped bays | Implementation observed; full testing incomplete |
| 2 — Occupancy Intelligence and Dashboard | Classify occupancy, persist results and visualise history | 783 observations, dashboard, 29 history samples | Core implementation observed; timestamp selection pending |
| 3 — Validation and Delivery | Validate results, complete workflow, deploy and demonstrate | 135 reviewed labels, evaluation report, 15 targeted tests | In progress; integration testing and deployment pending |

## Sprint 1 — Foundation and Computer Vision

### Backend foundation and data model

**Goal:** Establish a reproducible backend and relational model for a parking site, its cameras and video recordings.

| Activity | Acceptance evidence | Status |
|---|---|---|
| Initialise Python FastAPI backend and health endpoint | API reported healthy in development | Done (observed) |
| Configure PostgreSQL and Alembic migrations | Migration applied; site and organisation tables created | Done (observed) |
| Create organisation, parking site and camera records | API-generated demo records | Done (observed) |
| Implement recorded-video upload and file metadata | Uploaded MP4 stored under backend storage; recording record created | Done (observed) |
| Verify video metadata | 1280×720, approximately 29 seconds, 29.97 FPS | Done (observed) |
| Add automated migration/API tests | CI or test output | Not evidenced |

**Retrospective:** Database availability and a port conflict were resolved during setup. These are useful impediment examples; attach actual logs if discussed in a sprint review.

### Computer vision and parking-bay mapping

**Goal:** Detect vehicles in recorded footage and define the parking spaces that need classification.

| Activity | Acceptance evidence | Status |
|---|---|---|
| Run initial YOLO inference on a video frame | Two vehicle detections reported in an initial inference test | Done (observed) |
| Save a reference frame | 1280×720 JPEG verified | Done (observed) |
| Implement polygon-based bay configuration | Mapping editor with four-corner polygons | Done (observed) |
| Persist mapped bays | 27 bay records, including standard and accessible spaces | Done (observed) |
| Import/export mapping JSON | Editor controls exist; full regression test not evidenced | Partially verified |
| Evaluate mapping across camera angles | Labelled multi-angle evaluation | Pending |

**Retrospective:** Explicit image-coordinate polygons were chosen to accommodate perspective rather than assume a uniform parking grid.

## Sprint 2 — Occupancy Intelligence and Dashboard

### Occupancy inference and persistence

**Goal:** Produce and store a classified occupancy state for each mapped bay across sampled video timestamps.

| Activity | Acceptance evidence | Status |
|---|---|---|
| Integrate MobileNetV3-based occupancy classifier | Occupancy states returned by backend | Done (observed) |
| Apply conservative uncertainty thresholds and temporal aggregation | Empty/occupied/unknown temporal states visible | Done (observed) |
| Persist observations by bay and timestamp | 783 observations = 27 bays × 29 timestamps | Done (observed) |
| Implement latest occupancy API | Endpoint returns 27 bay states and summary | Done (observed) |
| Check count consistency | 8 available + 13 occupied + 6 unknown = 27 at 28.028s | Done (manual/API) |
| Evaluate classification against reviewed labels | 135 observations; confusion matrices, coverage and selective accuracy documented | Done (initial evaluation) |

**Retrospective:** The unknown state is a deliberate abstention mechanism. Initial timestamps classified all 27 bays as unknown while temporal evidence accumulated; these should not be reported as actual occupied bays.

### Dashboard and reference-image delivery

**Goal:** Make occupancy results understandable without manually examining JSON or image-processing output.

| Activity | Acceptance evidence | Status |
|---|---|---|
| Build React/TypeScript dashboard and mapping-editor switch | Browser screenshots | Done (observed) |
| Render colour-coded bay polygons using Konva | Green/red/amber overlays aligned to reference image | Done (observed) |
| Show total/available/occupied/unknown cards and bay list | 27/8/13/6 summary shown | Done (observed) |
| Serve demo reference image through FastAPI | HTTP 200, `image/jpeg`, 416,957 bytes | Done (observed) |
| Auto-load image in dashboard without manual upload | Confirmed after browser refresh | Done (manual) |
| Correct CSS collision and pan-mode drag behaviour | Browser behaviour confirmed; build passed | Done (manual) |
| Default app landing page to occupancy dashboard | Confirmed after refresh | Done (manual) |
| Camera-specific reference-image association | Dynamic, scoped image selection | Deferred for MVP unless required by new-recording workflow |

**Retrospective:** A shared `.empty` CSS selector unexpectedly enlarged sidebar rows; scoping the selector resolved the defect. A canvas drag flag was also inverted and corrected.

### Historical occupancy reporting

**Goal:** Show how classified occupancy changed over the recorded footage.

| Activity | Acceptance evidence | Status |
|---|---|---|
| Implement grouped history API | 29 ordered timestamp summaries returned | Done (observed) |
| Add typed frontend API client and response checks | TypeScript build passed | Done (observed) |
| Display sample count and recording duration | 29 samples; 28.028s in browser | Done (observed) |
| Render available/occupied/unknown time series | SVG chart screenshot | Done (observed) |
| Select a timestamp to update cards and bay polygons | Interactive per-timestamp retrieval/playback | Pending |
| Export historical report | Downloadable CSV or equivalent | Optional; not yet agreed as acceptance criterion |

**Retrospective:** Aggregation occurs in PostgreSQL, reducing the amount of observation data transferred for the time-series chart. The chart is based on **recorded** video, not live camera telemetry.

## Sprint 3 — Validation and Delivery

### Complete and validate the single-site MVP

**Goal:** Demonstrate a repeatable workflow for a new recording and provide defensible evaluation evidence.

| Proposed story | Acceptance criteria | Status |
|---|---|---|
| As an operator, I can select a historical sample | Selecting a timestamp updates summary, polygon colours and bay list consistently | To do |
| As an operator, I can upload a new recording and process it from the UI | Upload, map, trigger analysis and view results without hardcoded demo identifiers or manual API calls | To do |
| As a researcher, I can evaluate the classifier | Ground-truth labels, confusion matrices, coverage, selective accuracy and limitations | Done (initial evaluation; broader validation pending) |
| As a maintainer, I can trust the key API behaviour | Automated tests for site/recording validation, counts, empty data and history | Partial: 15 targeted tests passed; API/integration coverage pending |
| As a reviewer, I can reproduce the demo | Documented setup, sample data and deterministic walkthrough | To do |

**Definition of done:** Code works in the application, tests/evidence are attached, limitations are documented and the task is linked to a real commit or pull request.

### Deployment and capstone submission

| Proposed activity | Evidence required | Status |
|---|---|---|
| Deploy accessible web application and API | URL and deployment smoke test | To do |
| Document architecture, decisions and testing | `DESIGN_AND_TESTING.md` plus diagrams/results | In progress |
| Maintain project overview and instructions | `README.md` | In progress |
| Maintain sprint and agile evidence | This log + accessible agile board | In progress |
| Record 15–20 minute demonstration | Accessible video URL, screen capture and voice-over | To do |
| Grant repository access to `quantic-grader` | GitHub access confirmation | To do |
| Verify all grader-facing links | Independent access test | To do |

## Backlog exclusions — not part of the capstone MVP

- Multi-organisation onboarding, tenant management and multi-site SaaS administration.
- Subscription plans, entitlements, checkout and billing lifecycle.
- Live RTSP streaming, ANPR, enforcement, forecasting and parking reservations.

These are **future commercialisation ideas**, not incomplete MVP stories.

## Agile evidence register — fill from actual records

| Proposed sprint | Actual dates | Board / milestone URL | Issues / stories | Git evidence | Review evidence |
|---|---|---|---|---|---|
| 1 | [VERIFY] | [ADD] | [ADD] | `dba3cde`, `668eb14` | [VERIFY] |
| 2 | [VERIFY] | [ADD] | [ADD] | `668eb14`, `e251c50` | [VERIFY] |
| 3 | [VERIFY / PLAN] | [ADD] | [ADD] | `b31b492`; further commits pending | [VERIFY / PLAN] |

**Submission integrity:** This document supports the agile task board; it does **not replace** the handbook's requirement to provide an accessible board with user stories and task completion evidence. Do not invent historical sprint dates, velocity, hours, meeting notes, or completed tests.

## AI-assisted engineering activities (cross-sprint)

The following AI assistance is supported by the development discussion; allocation to particular sprint dates is **retrospective**, not evidence of a formal sprint ceremony.

| Workstream | AI-assisted activity | Developer validation |
|---|---|---|
| Backend and APIs | Incremental endpoint design and debugging suggestions | Inspected FastAPI modules; tested HTTP responses |
| Frontend and mapping | Suggested React state separation and Konva rendering changes | TypeScript builds and manual dashboard/editor checks |
| Historical reporting | Suggested aggregation API, typed client and SVG chart | Inspected JSON for 29 timestamps; reviewed chart screenshot |
| Testing and documentation | Helped structure test plans, architecture rationale and submission files | 15 targeted tests passed; initial ground-truth evaluation completed; additional tests pending |

**AI tooling evidence to add:** links to relevant commits and task-board cards; redacted prompt examples; recorded test results. AI-assisted implementation must not be represented as independently tested or automatically verified. See [DESIGN_AND_TESTING.md](DESIGN_AND_TESTING.md#ai-tooling-used-during-development).
