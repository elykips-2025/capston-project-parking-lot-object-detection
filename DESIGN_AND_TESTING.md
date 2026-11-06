# ParkSight AI — Design, Architecture and Testing

**Quantic MSSE Capstone | Draft updated 6 November 2026**

> This is an evidence-based working document. **Observed** results are distinguished from **pending** tests and deliverables. Replace placeholders and attach proof before final submission.

## 1. Problem and agreed requirements

Manual review of CCTV to determine parking-space utilisation is labour-intensive. ParkSight AI investigates whether recorded video and computer vision can identify occupancy of predefined parking bays and present interpretable results.

### In-scope MVP requirements

1. Upload recorded CCTV footage.
2. Detect vehicles with YOLO.
3. Configure parking-bay polygons on a reference image.
4. Classify bays as available, occupied or unknown.
5. Display aggregate occupancy and per-bay overlays.
6. Display historical occupancy across recorded timestamps.

**Out of scope:** live RTSP processing, multi-site SaaS management, tenant onboarding/access control, subscriptions/billing, ANPR, enforcement, prediction and parking reservations.

## 2. Architecture

```text
Recorded CCTV → sampled frames → YOLO vehicle detection
                              → polygon-defined bay regions
                              → MobileNetV3-based classification
                              → temporal state aggregation
                              → PostgreSQL observations
                              → FastAPI REST endpoints
                              → React / TypeScript UI
                                  ├─ Konva reference image + bay overlays
                                  └─ SVG historical occupancy chart
```

| Component | Technology | Responsibility |
|---|---|---|
| Web application | React, TypeScript, Vite | Editor, dashboard, historical reports |
| Mapping visualisation | Konva | Reference image and editable bay polygons |
| Historical chart | Native SVG | Available/occupied/unknown time series |
| Backend API | FastAPI | Occupancy and historical queries |
| Persistence | PostgreSQL, SQLAlchemy, Alembic | Sites, cameras, recordings, bays, observations |
| Detection | YOLO | Vehicle detection in footage |
| Bay classification | MobileNetV3-based model | Occupancy inference |
| Temporal aggregation | Backend processing | Stabilise per-frame state |

The existing schema includes `ParkingSite`, `Camera`, `VideoRecording`, `ParkingBay`, `OccupancyObservation` and an organisation parent. The organisation structure remains for the demo, but commercial multi-tenancy is not part of this MVP.

## 3. Design decisions and reasons

**Recorded video rather than live streaming.** Reproducible footage makes debugging, evaluation and demonstrations more reliable. Trade-off: the displayed states are historical, not live.

**Explicit image-coordinate polygons.** Real parking layouts vary by camera perspective; polygon mapping makes bay geometry transparent and editable. Trade-off: setup is manual and camera movement may require remapping.

**YOLO plus a bay classifier.** Vehicle detection and occupancy classification solve related but distinct problems. MobileNetV3-based bay classification allows a confidence-based unknown state. Trade-off: extra model complexity; comparative performance must still be measured.

**Unknown state and temporal aggregation.** Uncertain predictions are not forced into available/occupied categories; aggregating over time can reduce transient classification changes. Trade-off: some bays remain unresolved, particularly at the start of a recording.

**REST API with relational persistence.** Separating analysis, storage and presentation enables history queries and reproducible inspection. Trade-off: additional database and hosting requirements.

**Konva and native SVG.** Konva supports interactive polygons; SVG provides a lightweight chart without adding another chart library.

**Fixed demo reference-image route.** A read-only FastAPI endpoint lets the dashboard load the reference image automatically. It is demo-specific; camera-associated image storage and access checks would be needed for commercial use.

## 4. Observed implementation and manual verification

| Check | Observed result | Evidence to attach |
|---|---|---|
| Reference image dimensions | 1280 × 720 | Image inspection terminal output |
| Reference image API | HTTP 200, `image/jpeg`, 416,957 bytes | `curl` output |
| Latest occupancy | 27 bays: 8 available, 13 occupied, 6 unknown | API response / dashboard screenshot |
| Historical API | 29 samples, 0–28.028 seconds | JSON response |
| Observation volume | 783 = 27 × 29 | Database query |
| Frontend build | `npm run build` succeeded | Build log |
| Image loading after refresh | Confirmed visually | Browser screenshot |
| History chart | Three occupancy series displayed | Browser screenshot |
| Pan interaction | User confirmed manual behaviour | Manual test record |

Each history sample reports 27 bays, with available + occupied + unknown = total. The first two samples report 27 unknown bays due to initial temporal uncertainty; this does **not** mean 27 occupied bays.

**Build caveat:** Vite reports a chunk larger than 500 kB after minification; the warning does not fail the build.

## 5. Testing approach and gaps

### Automated tests — pending evidence

- Unit: polygon validation, aggregation counts, temporal transitions, confidence thresholds.
- API: valid history/latest requests; invalid IDs; missing observations; recording/site mismatches.
- Integration: migrations, persistence, image endpoint, API response schema.
- End-to-end: upload a new recording, map bays, run analysis, view latest states and history, refresh dashboard.
- Regression: editor/dashboard image separation, polygon alignment, pan-mode behaviour.

**Do not claim these tests have passed until they have been implemented and executed.** Record test command, environment, date, result and report/screenshot for each.

### Model evaluation — pending

Prepare manually labelled ground-truth samples and report: occupied/empty precision, recall and F1; confusion matrix; unknown/abstention rate; lighting and occlusion failure cases; processing throughput and latency; model versions and confidence thresholds. Document annotation methodology and train/test separation. **No validated model accuracy figure is available yet.**

### Manual test register

| ID | Scenario | Result | Status |
|---|---|---|---|
| M01 | Dashboard reference image loads after refresh | Observed | Pass (manual) |
| M02 | Historical API returns 29 timestamp summaries | Observed | Pass (manual) |
| M03 | Pan mode controls dragging | User confirmed | Pass (manual) |
| M04 | New recording through complete UI workflow | Not yet demonstrated | Pending |
| M05 | Accuracy measured against ground truth | Not yet conducted | Pending |

## 6. Deployment options and cost implications

The handbook requires deployment options and relative cost considerations. **Verify actual provider pricing at submission time.**

| Option | Benefit | Limitation / cost |
|---|---|---|
| Local development machine | Low incremental hosting cost; simple debugging | Not independently accessible to graders |
| Cloud-hosted frontend/API + PostgreSQL | Accessible deployed demo; straightforward web access | Hosting, database, storage and backup charges; free-tier quotas or sleep |
| Separate CPU/GPU inference worker | Isolates video processing; supports scaling | More infrastructure; GPU compute can be costly |

**Capstone recommendation:** Host an accessible frontend/API and database, and include a preprocessed demo recording. Explicitly state whether inference runs on the hosted environment or is performed offline. Do not claim cloud-based end-to-end processing unless demonstrated.

Protect credentials, restrict footage access, document lawful use and retention of CCTV, and do not present the prototype as a production enforcement system.

## 7. Agile engineering and CI/CD evidence

**Task board:** [ADD ACCESSIBLE URL]

Document actual user stories, sprint tasks, completed work and relevant commits. Add CI/CD workflow paths and run evidence if implemented; do not invent collaboration records or test automation.

**CI/CD:** [ADD VERIFIED WORKFLOW AND RUN LINK OR MARK PENDING]

## 8. Remaining implementation work

1. Historical timestamp selection updating per-bay state.
2. End-to-end workflow for a different uploaded recording without hardcoded demo IDs.
3. Ground-truth model evaluation and automated tests.
4. Deployment, documented setup and demonstration recording.

## 9. Required submission items

- [ ] Accessible GitHub repository containing documented code.
- [ ] Invite **`quantic-grader`** to the GitHub repository.
- [ ] Link deployed web application from repository.
- [ ] Link accessible agile board with tasks and delivered user stories.
- [ ] Finalise this design/testing document, including architectural patterns, technology rationale, deployment costs and all executed tests.
- [ ] Link a **15–20 minute** recorded demonstration showing the working deployed system via screen capture and voice-over.
- [ ] Follow handbook on-camera and government-issued ID presentation instructions; comply with group-specific rules where applicable.
- [ ] Confirm all links work for graders.

**Submission links:** Repository [https://github.com/elykips-2025/capston-project-parking-lot-object-detection](https://github.com/elykips-2025/capston-project-parking-lot-object-detection) · Deployment [ADD URL] · Task board [ADD URL] · Recording [ADD URL].

## 10. Future work (excluded from MVP)

Multi-site SaaS administration, tenant authentication and permissions, subscriptions/billing, live CCTV streams, predictive availability, ANPR, enforcement and parking reservations.


## Sprint activity evidence

See [SPRINT_ACTIVITY_LOG.md](SPRINT_ACTIVITY_LOG.md) for the reconstructed activity breakdown across foundation, computer vision, occupancy inference, dashboard, historical reporting, validation and submission. Sprint dates, ownership and board evidence must be verified against actual project records before submission.


## AI tooling used during development

ParkSight combines **AI as part of the delivered software** with **AI assistance during engineering**. These are different uses and should be evaluated separately.

| Tool or capability | Role | Evidence and verification |
|---|---|---|
| ChatGPT (AI-assisted engineering) | Helped decompose requirements into incremental implementation steps, review FastAPI/React changes, troubleshoot startup and TypeScript errors, and draft documentation/test plans | Development conversation and terminal outputs; changes were applied and checked by the developer |
| YOLO (application model) | Detect vehicles in recorded CCTV frames | Demonstration inference output; quantitative detection metrics still pending |
| MobileNetV3-based classifier (application model) | Infer parking-bay occupancy with an explicit unknown state | Persisted observations and dashboard outputs; accuracy against ground truth still pending |

### Human oversight and responsible use

AI-generated suggestions were **not treated as automatically correct**. The developer inspected project files, ran commands, reviewed API responses, compiled the frontend, and verified behaviour in the browser. Examples include diagnosing an empty FastAPI router module, checking the reference-image HTTP response, correcting a CSS class collision, and verifying the historical chart. These are manual checks, not a substitute for automated regression testing or measured model accuracy.

No claim is made that ChatGPT independently executed repository changes, that AI-generated code was formally audited, or that additional coding assistants were used for this project without supporting evidence. Before submission, add commit links, issue references, representative prompts/outputs (with secrets redacted), and test logs where appropriate.

### AI-tooling risks and mitigations

- **Incorrect generated code or assumptions:** review against existing implementation and run targeted tests.
- **Hallucinated performance claims:** report only measured metrics from labelled data.
- **Sensitive data exposure:** avoid submitting private CCTV footage, credentials, API keys or personal data to external AI tools.
- **Reproducibility:** record model identifiers, package versions, thresholds, dataset provenance and inference settings.
- **Academic integrity:** identify AI-assisted work transparently; ensure all submitted claims and code are understood and validated by the developer.
