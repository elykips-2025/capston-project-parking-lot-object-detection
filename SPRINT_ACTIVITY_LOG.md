# ParkSight AI — Consolidated Three-Sprint Activity and Evidence Register

**Project:** Quantic MSSE Capstone — ParkSight AI  
**Repository:** https://github.com/elykips-2025/capston-project-parking-lot-object-detection  
**Agile board:** https://outline.kwetu.co.uk/s/7f43578a-07c0-46f4-9fb6-37efb105fda6  
**Deployed application:** https://parksight.kwetu.co.uk  
**Scope:** Individual, single-site, recorded-CCTV occupancy analysis MVP  
**Reconciled:** 10 November 2026

> **Evidence standard:** Sprint grouping is a retrospective classification of engineering activities, not proof that formal Scrum ceremonies or fixed sprint dates occurred. `Done — observed` means supporting terminal, browser, database, or source evidence has been discussed; it does not imply that every acceptance test has passed. Do not backdate cards or invent sprint ceremonies. Verify card status and commit links against the actual Outline board and repository before submission.

## Sprint summary

| Sprint | Objective | Demonstrated outcome | Remaining gate |
|---|---|---|---|
| **1 — Foundation and Computer Vision** | Establish the data model, video input and mapped-bay detection foundation | FastAPI/PostgreSQL, site/camera/recording records, YOLO11n inference, 27 mapped bays | Migration/API regression tests and multi-angle mapping evaluation |
| **2 — Occupancy Intelligence and Dashboard** | Infer and persist bay occupancy; visualise current recorded state and history | 783 observations, unknown-aware temporal states, dashboard and 29-point history | Timestamp selection and complete UI workflow validation |
| **3 — Quality, Deployment and Submission** | Validate model and workflows; automate delivery; publish reproducible capstone evidence | Initial 135-label evaluation and 15 targeted tests reported; VPS frontend/API/worker/database operational | Successful final deployment run, end-to-end fresh-recording test, evidence links and recording |

## Sprint 1 — Foundation and Computer Vision

**Sprint goal:** A recorded video can be associated with a site/camera and mapped to explicit parking bays, with initial vehicle detection demonstrated.

| ID | Activity / user story | Acceptance criteria / evidence | Status |
|---|---|---|---|
| S1-01 | Initialise FastAPI application and health endpoint | Development API health response | Done — observed |
| S1-02 | Provision PostgreSQL and apply Alembic migrations | Organisation and parking-site tables created | Done — observed |
| S1-03 | Define organisation → site → camera relationships | Demo organisation/site/camera records exist | Done — observed |
| S1-04 | Upload and persist recorded video metadata | MP4 stored and recording database record created | Done — observed (backend); full UI flow unverified |
| S1-05 | Inspect recording and extract reference frame | 1280×720, 29.97 FPS, approximately 28.83 seconds | Done — observed |
| S1-06 | Execute YOLO11n vehicle detection | Initial test reported two vehicle detections | Done — observed |
| S1-07 | Implement polygon mapping editor | Four-corner bay polygons visible/editable | Done — observed |
| S1-08 | Persist 27 parking-bay polygons | 27 database-backed bays including accessible spaces | Done — observed |
| S1-09 | Import/export polygon mapping JSON | Round-trip preserves coordinates and bay metadata | Partial — controls observed; round-trip test pending |
| S1-10 | Resolve local database availability and port conflicts | Working API/database and reproducible startup notes | Done — observed; document fix |
| S1-11 | Test migrations and site/camera/video APIs | Executed automated tests and evidence | Pending evidence |
| S1-12 | Evaluate mapping against different camera angles | Annotated multi-angle examples and failure analysis | Future evaluation |

**Sprint 1 review evidence to attach:** database schema/migration log, site/camera API sample, recording metadata, YOLO annotated frame, polygon editor screenshot, commit links.

## Sprint 2 — Occupancy Intelligence and Dashboard

**Sprint goal:** The mapped bays produce traceable occupied/empty/unknown observations that can be inspected in a dashboard and historical chart.

| ID | Activity / user story | Acceptance criteria / evidence | Status |
|---|---|---|---|
| S2-01 | Integrate MobileNetV3-based bay classifier | Occupancy inference outputs produced | Done — observed |
| S2-02 | Implement uncertainty thresholds and temporal aggregation | Empty/occupied/unknown states persisted without forced binary decisions | Done — observed |
| S2-03 | Process 29 sampled frames across 27 bays | 783 observations; zero rejected frames | Done — observed |
| S2-04 | Persist bay/timestamp observations | Queryable PostgreSQL records | Done — observed |
| S2-05 | Expose latest occupancy summary API | 27 bay states; example summary 8 empty, 13 occupied, 6 unknown | Done — observed |
| S2-06 | Build React/TypeScript dashboard and bay overlays | Reference image and coloured Konva polygons | Done — observed |
| S2-07 | Show occupancy counters and bay list | Aggregate counts reconcile to 27 | Done — observed |
| S2-08 | Serve and auto-load reference image | JPEG endpoint HTTP 200; browser refresh works | Done — observed |
| S2-09 | Fix UI layout and pan-mode interaction defects | CSS collision corrected; drag behaviour manually checked | Done — manual |
| S2-10 | Implement grouped historical API | 29 ordered timestamp summaries | Done — observed |
| S2-11 | Implement typed frontend client and SVG history chart | TypeScript build; time series and sample count displayed | Done — observed |
| S2-12 | Select a historical timestamp to update all views | Summary, bay list and polygons reflect selected timestamp | Pending verification |
| S2-13 | Associate reference images dynamically per camera | Camera-scoped image selection and access control | Deferred — outside fixed demo scope |
| S2-14 | Export historical occupancy CSV | Export produces correct timestamp/state records | Optional — not an agreed MVP criterion |

**Sprint 2 review evidence to attach:** 783-observation run, API JSON, dashboard screenshot, chart screenshot, UI defect-fix commits, screenshot/video of timestamp interaction when completed.

## Sprint 3 — Quality, Deployment and Submission

**Sprint goal:** Validate the system, deliver an accessible deployment, and provide the evidence required for capstone assessment.

### 3A. Model evaluation and software testing

| ID | Activity / user story | Acceptance criteria / evidence | Status |
|---|---|---|---|
| S3-01 | Verify database-backed processing parity | 783/783 states/availability/temporal fields match reference; probability delta 0 | Done — observed (regression consistency, **not accuracy**) |
| S3-02 | Review labelled occupancy examples | 135 reviewed labels; evaluation report and confusion matrices | Done — initial evaluation reported in source log; attach report |
| S3-03 | Execute targeted automated tests | 15 tests passed; attach command/output and test paths | Done — reported; CI run linkage pending |
| S3-04 | Expand API and integration tests | Invalid input, empty dataset, site/camera/recording validation, history and error responses | Pending |
| S3-05 | Evaluate on more independent labelled recordings | Per-class precision/recall/F1, abstention coverage, lighting/occlusion cases | Pending |
| S3-06 | Test a fresh recording from the deployed UI | Upload → process → persistence → dashboard → history without manual API steps or hardcoded demo IDs | Pending verification |
| S3-07 | Test historical timestamp selection end to end | Cards, bay polygons and list remain synchronised | Pending verification |
| S3-08 | Validate permissions and input handling | Invalid uploads, path isolation, access boundaries and safe errors | Pending |

### 3B. CI/CD and production deployment

| ID | Activity / user story | Acceptance criteria / evidence | Status |
|---|---|---|---|
| S3-09 | Configure GitHub Actions quality checks | PR backend tests and frontend build; link workflow and successful run | Implemented — successful run evidence pending |
| S3-10 | Publish versioned backend container to GHCR | Tagged image built and pulled on VPS | Done — observed (image pull) |
| S3-11 | Deploy FastAPI, worker and PostgreSQL with Docker Compose | API/worker running; database healthy | Done — observed |
| S3-12 | Configure Nginx frontend and API reverse proxy | Public frontend and `/api/v1/health` return HTTP 200 | Done — observed |
| S3-13 | Diagnose frontend JS/CSS HTTP 403 | Static file permission root cause documented | Done — observed |
| S3-14 | Correct frontend asset ownership and modes | `rop:www-data`; directories 2775; assets accessible HTTP 200 | Done — observed |
| S3-15 | Investigate failed rsync deployment and recovery | `mkstemp` permission denial, rollback output, ownership remediation documented | Done — observed; final retry pending |
| S3-16 | Confirm successful final deployment pipeline | Green deployment run, frontend/API/assets HTTP 200, UI smoke test | **Pending** — latest reported workflow failed with exit 23 |
| S3-17 | Harden deployment smoke tests | Check JS/CSS URLs as well as HTML and API health; verify rollback | Pending |
| S3-18 | Verify runtime secrets, backups and service permissions | Redacted configuration and recovery evidence | Pending evidence |

### 3C. Capstone documentation and handover

| ID | Activity / user story | Acceptance criteria / evidence | Status |
|---|---|---|---|
| S3-19 | Maintain rubric-aligned README | Links to source, deployment, board, design/testing, sprint log and demo | Draft updated; commit confirmation pending |
| S3-20 | Document end-to-end user journey | Seven-step journey and per-step validation status | Draft prepared; commit confirmation pending |
| S3-21 | Complete design and testing document | Architecture/patterns, rationale, methods, executed tests, costs, limitations | In progress |
| S3-22 | Consolidate three-sprint evidence and Outline board | Each card has story, status, acceptance criteria and supporting commit/test | This register drafted; board reconciliation pending |
| S3-23 | Add technical and academic references | YOLO11, MobileNetV3, FastAPI, Docker, CI/CD and evaluation citations | Draft prepared; commit confirmation pending |
| S3-24 | Produce repeatable demonstration instructions | Fresh recording or clearly disclosed prepared dataset, expected results, failure case | Pending |
| S3-25 | Record 15–20 minute presentation | Screen capture, presenter visible, handbook identity requirements | Pending |
| S3-26 | Grant `quantic-grader` repository access | Invitation accepted/access confirmed | Pending confirmation |
| S3-27 | Check all grader-facing URLs | Independent access to repo, board, live app and recording | Pending verification |

## Recommended Outline board organisation

Create **three sprint sections** (or labels) and keep each card under its primary sprint. Use these status values consistently: **Done — evidenced**, **In progress**, **To do**, **Deferred**. A completed code change without a test/commit reference should not be marked **Done — evidenced** until evidence is attached.

Each card should contain:

- **ID and title:** e.g., `S3-16 — Confirm successful final deployment pipeline`.
- **User story or task purpose:** who benefits and why, where appropriate.
- **Acceptance criteria:** an observable pass/fail outcome.
- **Evidence:** relevant commit/PR, CI run, API result, screenshot or test report.
- **Status and actual completion date:** only when supported by records.
- **Dependency/blocker:** if unfinished.

**Do not duplicate** deployment activities across Sprint 1 and Sprint 3. Sprint 1 covers local foundation; Sprint 3 covers production deployment, quality gates and submission.

## End-to-end user journey traceability

| User step | Primary sprint | Cards | Validation gate |
|---|---|---|---|
| Access application | 3 | S3-12, S3-16 | Browser and static assets work |
| Set up site/camera | 1 | S1-02, S1-03 | UI flow still requires confirmation |
| Map parking bays | 1 | S1-07, S1-08 | 27 polygons persisted |
| Upload recording | 1 and 3 | S1-04, S3-06 | Fresh UI upload/process pending |
| Process occupancy | 2 and 3 | S2-01–S2-05, S3-01 | Observations persist; regression parity verified |
| Review dashboard | 2 | S2-06–S2-09 | Counts and polygons reconcile |
| Inspect history | 2 and 3 | S2-10–S2-12, S3-07 | Interactive timestamp update pending |

## Evidence index — complete before submission

| Evidence | Link / action |
|---|---|
| Agile board | https://outline.kwetu.co.uk/s/7f43578a-07c0-46f4-9fb6-37efb105fda6 |
| Source code | https://github.com/elykips-2025/capston-project-parking-lot-object-detection |
| Deployed app | https://parksight.kwetu.co.uk |
| CI runs and pull requests | [ADD VERIFIED LINKS] |
| 135-label evaluation report | [ADD FILE/LINK] |
| 15-test execution log | [ADD FILE/LINK] |
| Regression parity log | [ADD FILE/LINK] |
| Architecture and test rationale | [DESIGN_AND_TESTING.md](DESIGN_AND_TESTING.md) |
| Presentation recording | [ADD VIDEO URL] |

## Retrospective findings and risks

- **Architecture:** Polygon-defined bays are transparent and adaptable to perspective but require manual calibration.
- **Model behaviour:** Unknown is a deliberate abstention state, not evidence of an occupied bay; broader independent evaluation is still required.
- **Regression:** 783/783 matching outputs show consistency, not ground-truth accuracy.
- **Frontend:** CSS selector collisions and incorrect pan flags required targeted browser testing.
- **Deployment:** Healthy HTML/API responses alone did not reveal inaccessible JS/CSS; static-asset smoke checks are needed. An rsync ownership failure triggered recovery; the final green workflow has not yet been shown.
- **Delivery:** A deployed demonstration dataset is not equivalent to a verified fresh-recording workflow.

## Explicit exclusions (future product work)

Multi-tenant onboarding, multi-site SaaS administration, subscriptions/billing, live RTSP streams, ANPR, enforcement, parking reservations and forecasting are **not** unfinished capstone MVP stories.

## AI-assisted engineering disclosure

AI assistance supported planning, troubleshooting and documentation. Engineering outcomes are attributed to developer-verified source changes and tests, not to AI suggestions alone. Add redacted prompt examples or commit links if required by the course.
