#!/usr/bin/env bash
# Выкатка релиза (API + веб, один git sha). Вызывается ТОЛЬКО через SSH-ключ CI с принудительной командой:
#   command="/opt/studlenta/deploy.sh",restrict ssh-ed25519 ... studlenta-ci-deploy
# Аргументы приходят в SSH_ORIGINAL_COMMAND: "deploy <git-sha>". Токен GHCR — первой строкой stdin.
set -euo pipefail

APP_DIR=/opt/studlenta
IMAGES=(ghcr.io/wprojectsuust/studlenta-api ghcr.io/wprojectsuust/studlenta-web)
CONTAINERS=(studlenta-api-1 studlenta-web-1)
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

prev=$(sed -n 's/^RELEASE_TAG=//p' .env)
set_tag() { sed -i "s/^RELEASE_TAG=.*/RELEASE_TAG=$1/" .env; }

for image in "${IMAGES[@]}"; do
  echo "→ pull $image:$tag"
  docker pull -q "$image:$tag"
done
set_tag "$tag"
docker compose up -d --remove-orphans

all_healthy() {
  for c in "${CONTAINERS[@]}"; do
    [[ $(docker inspect -f '{{.State.Health.Status}}' "$c" 2>/dev/null || echo missing) == healthy ]] || return 1
  done
}

echo "→ жду health: ${CONTAINERS[*]}"
for _ in $(seq 1 60); do
  if all_healthy; then
    echo "✓ выкачен $tag (было: ${prev:-—})"
    # Диск маленький: оставляем только текущий и предыдущий релизы.
    for image in "${IMAGES[@]}"; do
      docker image ls "$image" --format '{{.Tag}}' | grep -vxE "${tag}|${prev:-none}" \
        | xargs -r -I{} docker image rm -f "$image:{}" >/dev/null || true
    done
    exit 0
  fi
  sleep 2
done

echo "✗ $tag не стал healthy — откат на ${prev:-—}" >&2
for c in "${CONTAINERS[@]}"; do docker logs --tail 30 "$c" >&2 || true; done
if [[ -n $prev && $prev != "$tag" ]]; then
  set_tag "$prev"
  docker compose up -d --remove-orphans
fi
exit 1
