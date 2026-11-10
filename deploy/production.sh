#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
# Usage: production.sh <backend:true|false> <frontend:true|false> <image-or-empty> <release-dir>
BACKEND=${1:?}; FRONTEND=${2:?}; IMAGE=${3:-}; RELEASE=${4:?}
ROOT=/var/www/parksight
PUBLIC=/var/www/parksight-public
cd "$ROOT"
test -f .env.production
[[ "$BACKEND" == true || "$BACKEND" == false ]]
[[ "$FRONTEND" == true || "$FRONTEND" == false ]]
[[ "$RELEASE" == "$ROOT/.release/"* ]]
COMPOSE=(docker compose --env-file .env.production -f "$ROOT/docker-compose.prod.yml" -p parksight)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)-$$
BACKUP_DIR="$ROOT/backups/$STAMP"
mkdir -p "$BACKUP_DIR"
backend_started=false
frontend_started=false
candidate="$ROOT/.compose-candidate-$STAMP.yml"
rollback_override="$ROOT/.rollback-$STAMP.yml"

service_running() {
  local service="$1" id state
  id=$("${COMPOSE[@]}" ps -q "$service")
  [[ -n "$id" ]] || return 1
  state=$(docker inspect --format '{{.State.Status}}' "$id")
  [[ "$state" == running ]]
}

rollback() {
  local status=$? recovered=true
  trap - ERR
  set +e
  rm -f "$candidate"
  echo "Deployment failed (exit $status); attempting recovery" >&2

  if [[ "$frontend_started" == true ]]; then
    rsync -a --delete --exclude='.well-known/' "$BACKUP_DIR/frontend/" "$PUBLIC/" || {
      echo 'CRITICAL: Frontend rollback failed' >&2
      recovered=false
    }
  fi

  if [[ "$backend_started" == true ]]; then
    if ! cp "$BACKUP_DIR/docker-compose.prod.yml" "$ROOT/docker-compose.prod.yml"; then
      echo 'CRITICAL: Could not restore previous Compose file' >&2
      recovered=false
    elif [[ ! -s "$BACKUP_DIR/previous-api-image" || ! -s "$BACKUP_DIR/previous-worker-image" ]]; then
      echo 'CRITICAL: Previous container image IDs missing' >&2
      recovered=false
    else
      local old_api old_worker
      old_api=$(cat "$BACKUP_DIR/previous-api-image")
      old_worker=$(cat "$BACKUP_DIR/previous-worker-image")
      # Override each service independently with its exact previous immutable image ID.
      # Keep the override beside the base Compose file so relative bind paths remain correct.
      printf 'services:\n  api:\n    image: "%s"\n  worker:\n    image: "%s"\n' \
        "$old_api" "$old_worker" > "$rollback_override"
      if ! PARKSIGHT_IMAGE="$IMAGE" docker compose \
          --env-file .env.production \
          -f "$ROOT/docker-compose.prod.yml" -f "$rollback_override" \
          -p parksight up -d --no-deps --force-recreate api worker; then
        echo 'CRITICAL: Backend container restoration failed' >&2
        recovered=false
      else
        # Compose service state and API availability are checked after restoration.
        if ! service_running api || ! service_running worker || \
           ! curl -fsS --max-time 5 http://127.0.0.1:8181/api/v1/health >/dev/null; then
          echo 'CRITICAL: Restored backend failed health verification' >&2
          recovered=false
        fi
      fi
    fi
  fi
  rm -f "$rollback_override"
  if [[ "$recovered" == true ]]; then
    echo "Recovery completed; inspect services before retrying. Backup: $BACKUP_DIR" >&2
  else
    echo "MANUAL RECOVERY REQUIRED. Backup: $BACKUP_DIR" >&2
  fi
  exit "$status"
}
trap rollback ERR

if [[ "$BACKEND" == true ]]; then
  test -n "$IMAGE"
  test -f "$RELEASE/docker-compose.prod.yml"
  for f in backend/yolo11n.pt backend/runs/occupancy/mobilenetv3_pilot/best.pt backend/datasets/video-mapping/reference-frame.jpg; do
    test -f "$f"
  done
  test -d backend/storage
  cp docker-compose.prod.yml "$BACKUP_DIR/docker-compose.prod.yml"
  docker inspect parksight-api-1 --format '{{.Image}}' > "$BACKUP_DIR/previous-api-image"
  docker inspect parksight-worker-1 --format '{{.Image}}' > "$BACKUP_DIR/previous-worker-image"
  test -s "$BACKUP_DIR/previous-api-image"
  test -s "$BACKUP_DIR/previous-worker-image"

  cp "$RELEASE/docker-compose.prod.yml" "$candidate"
  PARKSIGHT_IMAGE="$IMAGE" docker compose --env-file .env.production \
    -f "$candidate" -p parksight config --quiet
  rm -f "$candidate"

  # Dump must succeed (pipefail) and pass gzip integrity check before service changes.
  "${COMPOSE[@]}" exec -T db pg_dump -U parksight -d parksight | gzip > "$BACKUP_DIR/parksight.sql.gz"
  test -s "$BACKUP_DIR/parksight.sql.gz"
  gzip -t "$BACKUP_DIR/parksight.sql.gz"
  docker pull "$IMAGE"

  export PARKSIGHT_IMAGE="$IMAGE"
  backend_started=true
  cp "$RELEASE/docker-compose.prod.yml" docker-compose.prod.yml
  "${COMPOSE[@]}" config --quiet
  "${COMPOSE[@]}" up -d --no-deps api worker

  ready=false
  for i in $(seq 1 45); do
    if service_running api && service_running worker && \
       curl -fsS --max-time 3 http://127.0.0.1:8181/api/v1/health >/dev/null; then
      ready=true
      break
    fi
    sleep 2
  done
  [[ "$ready" == true ]] || { echo 'Backend health verification failed' >&2; false; }
fi

if [[ "$FRONTEND" == true ]]; then
  test -s "$RELEASE/dist/index.html"
  test -d "$PUBLIC"
  mkdir -p "$BACKUP_DIR/frontend"
  rsync -a --exclude='.well-known/' "$PUBLIC/" "$BACKUP_DIR/frontend/"
  # Direct rsync is non-atomic. Roll back on detected failure.
  frontend_started=true
  rsync -a --delete --exclude='.well-known/' --chmod=Dg+rwx,Fg+rw "$RELEASE/dist/" "$PUBLIC/"
  test -s "$PUBLIC/index.html"
  curl -fsS --max-time 10 https://parksight.kwetu.co.uk/ >/dev/null
fi
trap - ERR
printf 'ParkSight deployment OK backend=%s frontend=%s backup=%s\n' "$BACKEND" "$FRONTEND" "$BACKUP_DIR"
