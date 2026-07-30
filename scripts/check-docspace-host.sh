#!/usr/bin/env bash

set -u

minimum_cpus="${DOCSPACE_MIN_CPUS:-6}"
minimum_memory_gb="${DOCSPACE_MIN_MEMORY_GB:-12}"
minimum_swap_gb="${DOCSPACE_MIN_SWAP_GB:-6}"
minimum_disk_gb="${DOCSPACE_MIN_DISK_GB:-40}"
check_path="${DOCSPACE_CHECK_PATH:-/}"

failures=0
warnings=0

pass() {
  printf '[PASS] %s\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1"
  warnings=$((warnings + 1))
}

fail() {
  printf '[FAIL] %s\n' "$1"
  failures=$((failures + 1))
}

if [ "$(uname -s)" = "Linux" ]; then
  pass "Operating system is Linux"
else
  fail "Operating system must be Linux"
fi

architecture="$(uname -m)"
case "$architecture" in
  x86_64|amd64)
    pass "Architecture is amd64 ($architecture)"
    ;;
  *)
    fail "Architecture must be amd64; detected $architecture"
    ;;
esac

cpu_count="$(getconf _NPROCESSORS_ONLN 2>/dev/null || nproc)"
if [ "$cpu_count" -ge "$minimum_cpus" ]; then
  pass "CPU count: $cpu_count (minimum $minimum_cpus)"
else
  fail "CPU count: $cpu_count (minimum $minimum_cpus)"
fi

memory_kib="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
minimum_memory_kib=$((minimum_memory_gb * 1024 * 1024))
memory_gb="$(awk -v value="$memory_kib" 'BEGIN {printf "%.1f", value / 1024 / 1024}')"
if [ "$memory_kib" -ge "$minimum_memory_kib" ]; then
  pass "Memory: ${memory_gb} GiB (minimum ${minimum_memory_gb} GiB)"
else
  fail "Memory: ${memory_gb} GiB (minimum ${minimum_memory_gb} GiB)"
fi

swap_kib="$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo)"
minimum_swap_kib=$((minimum_swap_gb * 1024 * 1024))
swap_gb="$(awk -v value="$swap_kib" 'BEGIN {printf "%.1f", value / 1024 / 1024}')"
if [ "$swap_kib" -ge "$minimum_swap_kib" ]; then
  pass "Swap: ${swap_gb} GiB (minimum ${minimum_swap_gb} GiB)"
else
  fail "Swap: ${swap_gb} GiB (minimum ${minimum_swap_gb} GiB)"
fi

if [ -d "$check_path" ]; then
  disk_available_kib="$(df -Pk "$check_path" | awk 'NR == 2 {print $4}')"
  minimum_disk_kib=$((minimum_disk_gb * 1024 * 1024))
  disk_available_gb="$(awk -v value="$disk_available_kib" 'BEGIN {printf "%.1f", value / 1024 / 1024}')"
  if [ "$disk_available_kib" -ge "$minimum_disk_kib" ]; then
    pass "Free disk at $check_path: ${disk_available_gb} GiB (minimum ${minimum_disk_gb} GiB)"
  else
    fail "Free disk at $check_path: ${disk_available_gb} GiB (minimum ${minimum_disk_gb} GiB)"
  fi
else
  fail "Disk check path does not exist: $check_path"
fi

if command -v docker >/dev/null 2>&1; then
  pass "Docker command is installed"
  if docker info >/dev/null 2>&1; then
    pass "Docker daemon is available"
  else
    fail "Docker daemon is unavailable to the current user"
  fi

  if docker compose version >/dev/null 2>&1; then
    pass "Docker Compose plugin is installed"
  else
    fail "Docker Compose plugin is not installed"
  fi
else
  fail "Docker is not installed"
fi

if command -v ss >/dev/null 2>&1; then
  for port in 80 443; do
    if ss -H -ltn | awk '{print $4}' | grep -Eq ":${port}$"; then
      warn "TCP port $port is already in use"
    else
      pass "TCP port $port is available"
    fi
  done
else
  warn "The ss command is unavailable; ports 80 and 443 were not checked"
fi

printf '\nSummary: %s failure(s), %s warning(s)\n' "$failures" "$warnings"

if [ "$failures" -gt 0 ]; then
  exit 1
fi
