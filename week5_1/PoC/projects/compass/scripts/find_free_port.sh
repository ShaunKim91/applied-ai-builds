#!/usr/bin/env bash
# Portable free-port scanner — works on macOS/Linux bash and Windows Git
# Bash (both ship a real bash with /dev/tcp support), no extra tools needed.
#
# Usable two ways:
#   source scripts/find_free_port.sh      # exposes is_port_free() / find_free_port()
#   ./scripts/find_free_port.sh 8760      # prints the first free port >= 8760

is_port_free() {
  local port="$1"
  if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
    exec 3<&- 3>&- 2>/dev/null
    return 1 # connection succeeded => something is already listening
  fi
  return 0 # connection failed => port is free
}

find_free_port() {
  local start="${1:-8760}"
  local max=$((start + 200))
  local port=$start
  while [ "$port" -le "$max" ]; do
    if is_port_free "$port"; then
      echo "$port"
      return 0
    fi
    port=$((port + 1))
  done
  echo "ERROR: no free port found in range $start-$max" >&2
  return 1
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  find_free_port "${1:-8760}"
fi
