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
export PARKSIGHT_IMAGE="${IMAGE:-parksight-api:local}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)-$$
BACKUP_DIR="$ROOT/backups/$STAMP"
mkdir -p "$BACKUP_DIR"
backend_started=false
frontend_started=false
candidate="$ROOT/.compose-candidate-$STAMP.yml"
rollback_override="$ROOT/.rollback-$STAMP.yml"

container_running() {
  local container="$1"
  [[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null)" == true ]]
}


normalize_frontend_permissions() {
  # Keep directories group-writable and readable by Nginx.
  # Preserve setgid so new files inherit the www-data group.
  find "$PUBLIC" -type d -exec chmod 2775 {} +
  find "$PUBLIC" -type f -exec chmod 644 {} +
}

service_running() {
  local service="$1" id state
  id=$("${COMPOSE[@]}" ps -q "$service")
  [[ -n "$id" ]] || return 1
  state=$(docker inspect --format '{{.State.Status}}' "$id")
  [[ "$state" == running ]]
}

# Allow API startup time after Docker recreates containers, including rollback.
backend_healthy() {
  local i
  for i in $(seq 1 45); do
    if container_running parksight-api-1 && container_running parksight-worker-1 && \
       curl -fsS --max-time 3 http://127.0.0.1:8181/api/v1/health >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

rollback() {
  local status=$? recovered=true old_api old_worker
  trap - ERR
  set +e
  rm -f "$candidate"
  echo "Deployment failed (exit $status); attempting recovery" >&2

  if [[ "$frontend_started" == true ]]; then
    # Avoid chgrp/chown and directory mtime changes on root-owned Nginx directories.
    rsync -rlt --omit-dir-times --delete --exclude='.well-known/' \
      "$BACKUP_DIR/frontend/" "$PUBLIC/" || {
      echo 'CRITICAL: Frontend rollback failed' >&2
      recovered=false
    }
  fi

  if [[ "$frontend_started" == true ]]; then
    if ! normalize_frontend_permissions; then
      echo 'CRITICAL: Could not restore frontend asset permissions' >&2
      recovered=false
    fi
  fi

  if [[ "$backend_started" == true ]]; then
    if ! cp "$BACKUP_DIR/docker-compose.prod.yml" "$ROOT/docker-compose.prod.yml"; then
      echo 'CRITICAL: Could not restore previous Compose file' >&2
      recovered=false
    elif [[ ! -s "$BACKUP_DIR/previous-api-image" || ! -s "$BACKUP_DIR/previous-worker-image" ]]; then
      echo 'CRITICAL: Previous container image IDs missing' >&2
      recovered=false
    else
      old_api=$(cat "$BACKUP_DIR/previous-api-image")
      old_worker=$(cat "$BACKUP_DIR/previous-worker-image")
      printf 'services:\n  api:\n    image: "%s"\n  worker:\n    image: "%s"\n' \
        "$old_api" "$old_worker" > "$rollback_override"
      if ! docker compose \
          --env-file .env.production \
          -f "$ROOT/docker-compose.prod.yml" -f "$rollback_override" \
          -p parksight up -d --no-deps --force-recreate api worker; then
        echo 'CRITICAL: Backend container restoration failed' >&2
        recovered=false
      elif ! backend_healthy || \
           [[ "$(docker inspect --format '{{.Image}}' parksight-api-1)" != "$old_api" ]] || \
           [[ "$(docker inspect --format '{{.Image}}' parksight-worker-1)" != "$old_worker" ]]; then
        echo 'CRITICAL: Restored backend failed health/image verification' >&2
        recovered=false
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

  "${COMPOSE[@]}" exec -T db pg_dump -U parksight -d parksight | gzip > "$BACKUP_DIR/parksight.sql.gz"
  test -s "$BACKUP_DIR/parksight.sql.gz"
  gzip -t "$BACKUP_DIR/parksight.sql.gz"
  docker pull "$IMAGE"
  expected_image_id=$(docker image inspect "$IMAGE" --format '{{.Id}}')
  test -n "$expected_image_id"

  export PARKSIGHT_IMAGE="$IMAGE"
  backend_started=true
  cp "$RELEASE/docker-compose.prod.yml" docker-compose.prod.yml
  "${COMPOSE[@]}" config --quiet
  "${COMPOSE[@]}" up -d --no-deps api worker

  backend_healthy || { echo 'Backend health verification failed' >&2; false; }
  for service in parksight-api-1 parksight-worker-1; do
    actual_image_id=$(docker inspect "$service" --format '{{.Image}}')
    if [[ "$actual_image_id" != "$expected_image_id" ]]; then
      echo "Image verification failed for $service" >&2
      false
    fi
  done
fi

if [[ "$FRONTEND" == true ]]; then
  test -s "$RELEASE/dist/index.html"
  test -d "$PUBLIC"
  mkdir -p "$BACKUP_DIR/frontend"
  # -rlt preserves contents, symlinks and file timestamps without ownership/group changes.
  # --omit-dir-times avoids updating mtimes on root-owned directories.
  rsync -rlt --omit-dir-times --exclude='.well-known/' \
    "$PUBLIC/" "$BACKUP_DIR/frontend/"
  frontend_started=true
  rsync -rlt --omit-dir-times --delete --exclude='.well-known/' \
    "$RELEASE/dist/" "$PUBLIC/"
  normalize_frontend_permissions
  test -s "$PUBLIC/index.html"
  curl -fsS --max-time 10 https://parksight.kwetu.co.uk/ >/dev/null
fi
trap - ERR
printf 'ParkSight deployment OK backend=%s frontend=%s backup=%s\n' "$BACKEND" "$FRONTEND" "$BACKUP_DIR"
