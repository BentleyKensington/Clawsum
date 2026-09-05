#!/usr/bin/env bash
# Watch game/.apply-request and rebuild the public Dino Crush container.
set -euo pipefail
CLAWSUM_DIR="${CLAWSUM_DIR:-/docker/clawsum}"
FLAG="${CLAWSUM_DIR}/modules/dinocrushboss/.apply-request"
REBUILD="${CLAWSUM_DIR}/scripts/rebuild-dinocrushboss.sh"
[[ -f "$REBUILD" ]] || REBUILD="${CLAWSUM_DIR}/deploy/scripts/rebuild-dinocrushboss.sh"

docker rm -f dinocrushboss-apply 2>/dev/null || true
docker run -d --name dinocrushboss-apply --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "${CLAWSUM_DIR}:${CLAWSUM_DIR}" \
  docker:27-cli sh -c "apk add --no-cache bash curl openssl >/dev/null
while true; do
  if [ -f '$FLAG' ]; then
    rm -f '$FLAG'
    echo APPLY \$(date -Iseconds)
    bash '$REBUILD' || echo APPLY_FAIL
  fi
  sleep 8
done"

echo "DINOCRUSHBOSS_APPLY_WATCHER_OK flag=$FLAG"
