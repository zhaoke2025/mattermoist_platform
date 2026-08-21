#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="${1:-${PROJECT_DIR}/backups}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/.env}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT%/}/mattermost-${TIMESTAMP}"
MATTERMOST_CONTAINER="${MATTERMOST_CONTAINER:-mattermost}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-mattermost-db}"
BOT_CONTAINER="$(docker ps -q --filter label=com.docker.compose.service=ai-file-bot | head -n 1)"
STOPPED_CONTAINERS=()

restart_services() {
  if ((${#STOPPED_CONTAINERS[@]})); then
    docker start "${STOPPED_CONTAINERS[@]}" >/dev/null
  fi
}
trap restart_services EXIT

for command in docker tar sha256sum; do
  command -v "${command}" >/dev/null || {
    echo "缺少命令: ${command}" >&2
    exit 1
  }
done

docker inspect "${MATTERMOST_CONTAINER}" >/dev/null
docker inspect "${POSTGRES_CONTAINER}" >/dev/null
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "找不到环境配置文件: ${ENV_FILE}" >&2
  echo "请通过 ENV_FILE=/path/to/.env 指定实际路径。" >&2
  exit 1
fi
mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

if [[ -n "${BOT_CONTAINER}" ]]; then
  docker stop "${BOT_CONTAINER}" >/dev/null
  STOPPED_CONTAINERS+=("${BOT_CONTAINER}")
fi
docker stop "${MATTERMOST_CONTAINER}" >/dev/null
STOPPED_CONTAINERS+=("${MATTERMOST_CONTAINER}")

POSTGRES_USER="$(docker exec "${POSTGRES_CONTAINER}" printenv POSTGRES_USER)"
POSTGRES_DB="$(docker exec "${POSTGRES_CONTAINER}" printenv POSTGRES_DB)"
docker exec "${POSTGRES_CONTAINER}" pg_dump \
  -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc \
  >"${BACKUP_DIR}/mattermost.dump"

docker run --rm --volumes-from "${MATTERMOST_CONTAINER}:ro" \
  -v "${BACKUP_DIR}:/backup" alpine:3.20 \
  tar -czf /backup/mattermost-files.tar.gz \
  /mattermost/config /mattermost/data /mattermost/plugins \
  /mattermost/client/plugins /mattermost/bleve-indexes

if [[ -n "${BOT_CONTAINER}" ]]; then
  docker run --rm --volumes-from "${BOT_CONTAINER}:ro" \
    -v "${BACKUP_DIR}:/backup" alpine:3.20 \
    tar -czf /backup/ai-file-bot-data.tar.gz /app/data
fi

install -m 600 "${ENV_FILE}" "${BACKUP_DIR}/env"
if [[ -d "${PROJECT_DIR}/volumes/web/cert" ]]; then
  tar -czf "${BACKUP_DIR}/certificates.tar.gz" \
    -C "${PROJECT_DIR}/volumes/web" cert
fi

(
  cd "${BACKUP_DIR}"
  sha256sum ./* >SHA256SUMS
)

echo "备份完成: ${BACKUP_DIR}"
echo "请将该目录复制到独立磁盘、NAS 或对象存储，并按文档执行恢复演练。"
