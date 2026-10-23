#!/usr/bin/env bash
# Выкатка API. Вызывается ТОЛЬКО через SSH-ключ CI с принудительной командой:
#   command="/opt/studlenta/deploy.sh",restrict ssh-ed25519 ... studlenta-ci-deploy
# Аргументы приходят в SSH_ORIGINAL_COMMAND: "deploy <git-sha>". Токен GHCR — первой строкой stdin.
set -euo pipefail

APP_DIR=/opt/studlenta
IMAGE=ghcr.io/wprojectsuust/studlenta-api
CONTAINER=studlenta-api-1
cd "$APP_DIR"

read -r -a args <<< "${SSH_ORIGINAL_COMMAND:-${*:-}}"
if [[ ${#args[@]} -ne 2 || ${args[0]} != deploy || ! ${args[1]} =~ ^[0-9a-f]{40}$ ]]; then
  echo "usage: deploy <40-символьный git sha>" >&2
  exit 2
fi
tag=${args[1]}
token=""
IFS= read -r -t 5 token || true

exec 9>"$APP_DIR/.deploy.lock"
flock -n 9 || { echo "Другой деплой уже идёт" >&2; exit 3; }

# Отдельный конфиг docker, чтобы не трогать логины root для других сервисов.
export DOCKER_CONFIG="$APP_DIR/.docker"
mkdir -p "$DOCKER_CONFIG"
cleanup() { docker logout ghcr.io >/dev/null 2>&1 || true; }
trap cleanup EXIT
if [[ -n $token ]]; then
  printf '%s' "$token" | docker login ghcr.io -u studlenta-ci --password-stdin >/dev/null
fi

prev=$(sed -n 's/^API_TAG=//p' .env)
set_tag() { sed -i "s/^API_TAG=.*/API_TAG=$1/" .env; }

echo "→ pull $IMAGE:$tag"
docker pull -q "$IMAGE:$tag"
set_tag "$tag"
docker compose up -d --remove-orphans

echo "→ жду health"
for _ in $(seq 1 60); do
  status=$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo missing)
  if [[ $status == healthy ]]; then
    echo "✓ выкачен $tag (было: ${prev:-—})"
    # Диск маленький: оставляем только текущий и предыдущий образы.
    docker image ls "$IMAGE" --format '{{.Tag}}' | grep -vxE "${tag}|${prev:-none}" \
      | xargs -r -I{} docker image rm -f "$IMAGE:{}" >/dev/null || true
    exit 0
  fi
  sleep 2
done

echo "✗ $tag не стал healthy — откат на ${prev:-—}" >&2
docker logs --tail 40 "$CONTAINER" >&2 || true
if [[ -n $prev && $prev != "$tag" ]]; then
  set_tag "$prev"
  docker compose up -d --remove-orphans
fi
exit 1
