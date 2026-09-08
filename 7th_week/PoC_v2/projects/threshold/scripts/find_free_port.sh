#!/usr/bin/env bash
# Sourced by setup.sh/run.sh. Defines is_port_free() and find_free_port().
is_port_free() {
  local port="$1"
  ! (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null
}

find_free_port() {
  local start="${1:-8790}"
  local port="$start"
  for _ in $(seq 1 50); do
    if is_port_free "$port"; then
      echo "$port"
      return 0
    fi
    port=$((port + 1))
  done
  echo "Could not find a free port starting from $start" >&2
  return 1
}
