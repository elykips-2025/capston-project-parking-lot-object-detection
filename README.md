
# ParkSight AI — Quantic MSSE Capstone

ParkSight AI is an AI-powered parking occupancy monitoring prototype for private car parks and SMEs. It analyses **recorded CCTV footage** to determine whether individually mapped parking bays are **occupied, empty or unknown**, and presents the results through a web dashboard and historical reports.

The current academic MVP demonstrates recorded-video analysis, not real-time parking availability. Multi-site commercial management, live CCTV monitoring, ANPR and automated enforcement are outside the demonstrated MVP scope.

## Capstone submission links

| Deliverable | Link |
|---|---|
| Source code | [GitHub Repository](https://github.com/elykips-2025/capston-project-parking-lot-object-detection) |
| Deployed application | [ParkSight AI](https://parksight.kwetu.co.uk) |
| Agile task board | [Outline Agile Board](https://outline.kwetu.co.uk/s/7f43578a-07c0-46f4-9fb6-37efb105fda6) |
| Design and testing | [DESIGN_AND_TESTING.md](DESIGN_AND_TESTING.md) |
| Sprint activity log | [SPRINT_ACTIVITY_LOG.md](SPRINT_ACTIVITY_LOG.md) |
| Recorded presentation | [ADD VIDEO URL BEFORE SUBMISSION](https://docs.google.com/videos/d/1EsycntHThsLhy-uujaViR47eDH2LVxh77eUNX-3Qbt8/play)|

The GitHub account `quantic-grader` must have access to the repository. Verify that the Agile board and all submission links are accessible to assessors.

## Problem statement

Small and medium-sized private car park operators often lack affordable, bay-level occupancy information. Manual CCTV review is time-consuming, while dedicated sensors can introduce additional installation and maintenance costs.

ParkSight AI investigates whether existing camera recordings, computer vision and explicitly mapped parking-bay geometry can provide useful occupancy information without installing a sensor in every bay.

### Propose Solution

## User Journey

ParkSight AI supports a recorded-video parking occupancy analysis workflow, from parking-site configuration to historical reporting.

### User workflow

1. **Access the application:** Open [ParkSight AI](https://parksight.kwetu.co.uk) and navigate to the parking management interface.
2. **Configure a parking site:** Create or select a parking site and associate a camera with it.
3. **Map parking bays:** Load a reference image and draw or edit polygons defining individual parking spaces.
4. **Upload recorded CCTV footage:** Associate a supported video recording with the configured camera.
5. **Process the recording:** Sample video frames, detect vehicles using YOLO11n, classify mapped bays using the MobileNetV3-based classifier, and aggregate temporal occupancy observations.
6. **Review occupancy results:** Inspect mapped bays and their occupied, empty or unknown states, alongside aggregate availability.
7. **Review historical occupancy:** Inspect occupancy changes across sampled timestamps using the historical reporting interface.

### User journey validation

| Step | Expected result | Evidence / validation status |
|---|---|---|
| Application access | Dashboard loads successfully | Homepage, API and static assets returned HTTP 200; full browser workflow requires confirmation |
| Site and camera setup | Site and camera records are available | Demo database records established; full UI creation flow requires confirmation |
| Parking-bay mapping | Bay polygons can be configured and displayed | 27 mapped bays in the demonstration dataset |
| Video upload | Recording is associated with a camera | Demo video uploaded; complete new-recording UI workflow requires verification |
| Video processing | Occupancy observations are persisted | 29 sampled frames, 27 bays and 783 observations; zero rejected frames |
| Occupancy dashboard | Bay-level and aggregate results are displayed | Dashboard functionality observed; final deployed browser verification pending |
| Historical reporting | Occupancy changes can be inspected over time | History API and chart observed; timestamp selection requires verification |

**Scope note:** This workflow describes the intended end-to-end MVP journey. Some steps have been verified individually, but a complete fresh-recording journey on the final deployed application has not yet been confirmed. The displayed availability relates to processed recordings, not live parking conditions.

### Demonstration acceptance criteria

The final recorded demonstration should show a user progressing through the workflow, including a successful processing result, bay-level occupancy visualisation and historical reporting. Any incomplete step must be disclosed rather than represented as implemented.


## Project objectives and functional requirements

The MVP targets six core capabilities:

1. **Parking site setup:** Represent a parking site and its associated camera.
2. **Parking-bay mapping:** Define parking-space polygons against a reference image.
3. **Vehicle detection:** Analyse recorded footage using YOLO.
4. **Occupancy classification:** Classify mapped bays as occupied, empty or unknown, using temporal observations.
5. **Occupancy dashboard:** Display bay-level status and aggregate availability.
6. **Historical reporting:** Inspect occupancy changes across sampled recording timestamps.

The demonstration must distinguish implemented functionality from work still pending verification.

## Technical architecture

```text
Recorded CCTV video
        |
        v
Frame sampling and YOLO vehicle detection
        |
        v
Mapped parking-bay polygons
        |
        v
MobileNetV3-based bay classification
        |
        v
Temporal occupancy aggregation
        |
        v
PostgreSQL observations
        |
        v
FastAPI REST API
        |
        v
React / TypeScript dashboard
  - Bay mapping and occupancy overlays
  - Historical occupancy reporting
```

### Technology stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React, TypeScript, Vite | Web interface |
| Mapping | Konva | Reference image and editable bay polygons |
| Backend | Python, FastAPI | REST endpoints and application logic |
| Database | PostgreSQL, SQLAlchemy, Alembic | Persistent application and occupancy data |
| Vehicle detection | YOLO11n | Vehicle detection in sampled frames |
| Bay classification | MobileNetV3-based model | Parking-bay occupancy inference |
| Processing | Python worker | Recorded-video analysis |
| Deployment | Docker Compose, Nginx | Container services and reverse proxy |
| CI/CD | GitHub Actions, GHCR | Build, test, image publishing and deployment workflows |

### Design decisions

- **Recorded video instead of live streaming:** Improves reproducibility and supports repeatable evaluation.
- **Explicit polygon mapping:** Accommodates different parking layouts and camera perspectives.
- **Separate vehicle detection and bay classification:** Allows each stage to address a distinct inference problem.
- **Unknown state:** Avoids automatically treating uncertain observations as empty or occupied.
- **Temporal aggregation:** Helps reduce transient changes in classification.
- **Relational persistence:** Supports historical queries and traceable observations.
- **API/frontend separation:** Keeps presentation independent of the inference and persistence layers.

See [DESIGN_AND_TESTING.md](DESIGN_AND_TESTING.md) for the detailed rationale, software patterns, trade-offs and deployment options.

## Agile software engineering methodology

Development is organised into three retrospective workstreams. Actual sprint dates, completed user stories and task ownership should be verified against the [Agile board](https://outline.kwetu.co.uk/s/7f43578a-07c0-46f4-9fb6-37efb105fda6).

| Workstream | Main engineering activities |
|---|---|
| Sprint 1 — Foundation and computer vision | Backend, database, site/camera records, video ingestion and vehicle detection |
| Sprint 2 — Occupancy intelligence | Bay mapping, classification, temporal processing, dashboard and historical reporting |
| Sprint 3 — Validation and delivery | Regression verification, CI/CD, deployment, troubleshooting and capstone evidence |

Supporting activity evidence is documented in [SPRINT_ACTIVITY_LOG.md](SPRINT_ACTIVITY_LOG.md).

## Implementation and observed results

The demonstration dataset includes:

| Metric | Observed result |
|---|---|
| Reference video resolution | 1280 × 720 |
| Recording duration | Approximately 28.83 seconds |
| Mapped parking bays | 27 |
| Sampled frames | 29 |
| Rejected frames | 0 |
| Occupancy observations | 783 |
| Occupied observations | 355 |
| Empty observations | 185 |
| Unknown observations | 243 |

A database-backed processing comparison matched the reference output for all **783 of 783 observations** across occupancy state, availability, temporal state and temporal availability. The maximum and mean probability differences were both 0.0.

**Interpretation:** This establishes consistency between two processing outputs for the tested dataset. It does **not** establish 100% occupancy classification accuracy. Model precision, recall, F1 and a confusion matrix require independently labelled ground-truth data.

## Testing and evaluation

Testing evidence should cover:

- Backend API and database operations.
- Parking-bay mapping and persistence.
- Video processing and occupancy observation generation.
- Dashboard and historical-report behaviour.
- Automated test results and CI execution.
- Deployment smoke tests and frontend asset accessibility.
- Invalid inputs and error handling.
- Ground-truth classification evaluation.

Observed deployment smoke checks returned HTTP 200 for the homepage, API health endpoint, JavaScript and CSS assets. A successful final deployment workflow and complete end-to-end browser demonstration still require confirmation.

See [DESIGN_AND_TESTING.md](DESIGN_AND_TESTING.md) for executed tests, evidence and outstanding evaluation work.

## Deployment

**Application:** https://parksight.kwetu.co.uk

The deployment uses Nginx for the frontend and API reverse proxy, Docker Compose for application services, PostgreSQL for persistence, and a separate background worker.

GitHub Actions workflows support automated checks, container publishing and VPS deployment. Review the repository workflow definitions and final successful run before claiming a fully verified CI/CD pipeline.

### Local development

Backend, after configuring the Python environment and database:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
npm run build
```

Environment variables, database migrations and worker commands must be checked against the final repository. Do not commit credentials, private recordings or sensitive configuration.

## Limitations and future work

The MVP is limited to recorded CCTV footage. Results depend on camera angle, image quality, lighting, occlusion, polygon calibration and model confidence. An unknown state is retained when inference is insufficiently reliable.

Prioritised future work includes independently labelled accuracy evaluation, additional camera conditions, repeatable new-recording workflows, live stream ingestion, stronger multi-site access controls and production-grade monitoring.

ANPR, automated payments, enforcement and predictive availability are future possibilities, not demonstrated capabilities.

## AI tooling disclosure

ParkSight AI uses YOLO for vehicle detection and a MobileNetV3-based model for parking-bay occupancy inference.

ChatGPT was used as an engineering assistant for task decomposition, code-review suggestions, troubleshooting and documentation. Suggested changes were subject to developer review and manual verification. See [DESIGN_AND_TESTING.md](DESIGN_AND_TESTING.md#ai-tooling-used-during-development) for the fuller disclosure and responsible-use considerations.

## References and Technical Resources

The following references informed the technology selection, architecture, implementation and evaluation considerations for ParkSight AI.

1. Jocher, G., & Qiu, J. (2024). *Ultralytics YOLO11* [Computer software]. https://github.com/ultralytics/ultralytics

2. Howard, A., et al. (2019). Searching for MobileNetV3. *Proceedings of the IEEE/CVF International Conference on Computer Vision*, 1314–1324. https://openaccess.thecvf.com/content_ICCV_2019/html/Howard_Searching_for_MobileNetV3_ICCV_2019_paper.html

3. FastAPI. (n.d.). *FastAPI documentation*. https://fastapi.tiangolo.com/

4. Docker Inc. (n.d.). *Docker Compose documentation*. https://docs.docker.com/compose/

5. GitHub. (n.d.). *GitHub Actions documentation*. https://docs.github.com/en/actions

6. National Institute of Standards and Technology. (2023). *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*. https://www.nist.gov/itl/ai-risk-management-framework

For detailed implementation decisions, testing evidence and limitations, see [Design, Architecture and Testing](DESIGN_AND_TESTING.md).

## Final submission checklist

- [ ] Source repository contains the final documented code.
- [ ] `quantic-grader` has repository access.
- [ ] Deployed application is accessible and fully demonstrated.
- [ ] Agile board is accessible and accurately reflects completed user stories.
- [ ] Design and testing document includes decisions, patterns, test evidence and deployment cost considerations.
- [ ] CI/CD execution evidence is linked and verified.
- [ ] A 15–20-minute recorded presentation demonstrates the working software with screen capture and the presenter visible.
- [ ] Government-issued ID is shown as required by the Capstone Handbook.
- [ ] Presentation recording link is added above.
- [ ] All submission links are tested before submission.

## Supporting documentation

- [Design, Architecture and Testing](DESIGN_AND_TESTING.md)
- [Sprint Activity Log](SPRINT_ACTIVITY_LOG.md)
- [Agile Board](https://outline.kwetu.co.uk/s/7f43578a-07c0-46f4-9fb6-37efb105fda6)
