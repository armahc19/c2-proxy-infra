#!/bin/sh
# render/entrypoint.sh — start only what this container's ROLE needs.
# Render web services bind a single $PORT, so the collector and the proxy
# must never both try to claim it (see Dockerfile for the port layout).
set -eu

case "${ROLE:-both}" in
  collector)
    exec uvicorn collector_api:app --host 0.0.0.0 --port "${PORT}"
    ;;
  proxy)
    exec python3 proxy_fallback.py
    ;;
  both)
    uvicorn collector_api:app --host 127.0.0.1 --port "${COLLECTOR_PORT}" &
    exec python3 proxy_fallback.py
    ;;
  *)
    echo "entrypoint: unknown ROLE '${ROLE}' (use: both | proxy | collector)" >&2
    exit 2
    ;;
esac
