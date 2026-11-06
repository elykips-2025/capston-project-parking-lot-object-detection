# ParkSight AI — Quantic MSSE Capstone

ParkSight AI is a single-site academic MVP for analysing **recorded CCTV footage** to classify mapped parking bays as available, occupied, or unknown. It does not provide live parking availability.

## Submission links (complete before submitting)

| Required deliverable | Link |
|---|---|
| GitHub source repository | [https://github.com/elykips-2025/capston-project-parking-lot-object-detection](https://github.com/elykips-2025/capston-project-parking-lot-object-detection) |
| Deployed web application | **[ADD DEPLOYED URL]** |
| Agile task board with user stories and completed tasks | **[ADD BOARD URL]** |
| Design and testing document | [DESIGN_AND_TESTING.md](DESIGN_AND_TESTING.md) |
| Sprint activity breakdown | [SPRINT_ACTIVITY_LOG.md](SPRINT_ACTIVITY_LOG.md) |
| 15–20 minute recorded demonstration | **[ADD VIDEO URL]** |

**Required:** Grant the GitHub account `quantic-grader` access to the repository. Confirm every link is accessible to graders. Follow the Capstone Handbook's on-camera, identity verification and (if applicable) group requirements.

## MVP scope

- Upload recorded CCTV video.
- Detect vehicles with YOLO.
- Define parking-bay polygons against a reference image.
- Classify bays as available, occupied, or unknown using a MobileNetV3-based classifier and temporal aggregation.
- Display the latest recorded occupancy over the reference image.
- Display historical occupancy trends.

**Not in MVP:** multi-site SaaS management, organisation onboarding, tenant access, subscriptions, billing, live RTSP monitoring, ANPR, enforcement, predictive availability.

## Implementation snapshot — 6 November 2026

- Frontend: React, TypeScript, Vite, Konva; native SVG historical chart.
- Backend: Python, FastAPI, SQLAlchemy, Alembic; PostgreSQL.
- Demo reference image: 1280 × 720.
- Demo recording: 29 sampled timestamps, from 0 to 28.028 seconds; 27 mapped bays and 783 persisted observations.
- Latest recorded state: **8 available, 13 occupied, 6 unknown**.
- The history API and chart work; historical timestamp selection and a complete new-recording workflow remain to be finished.

These are observed demonstration results, **not** measured model accuracy.

## Local development

From `backend/` after configuring Python dependencies and PostgreSQL:

```bash
uvicorn app.main:app --reload --port 8000
```

From `frontend/`:

```bash
npm install
npm run dev
npm run build
```

Configuration, database migrations and video-processing commands must be verified and documented against the final repository before submission. Never commit credentials or unauthorised CCTV footage.

## Architecture and evidence

See [DESIGN_AND_TESTING.md](DESIGN_AND_TESTING.md) for architectural decisions, testing evidence, evaluation plan, deployment trade-offs, limitations and submission checklist. See [SPRINT_ACTIVITY_LOG.md](SPRINT_ACTIVITY_LOG.md) for the retrospective workstream breakdown, outstanding sprint activities and agile evidence register.

## AI tooling disclosure

ChatGPT was used as an engineering assistant for task decomposition, code-review suggestions, troubleshooting and documentation. The delivered application uses YOLO vehicle detection and a MobileNetV3-based parking-bay occupancy classifier. These uses are documented separately in [DESIGN_AND_TESTING.md](DESIGN_AND_TESTING.md#ai-tooling-used-during-development), including developer verification, limitations and responsible-use considerations.
