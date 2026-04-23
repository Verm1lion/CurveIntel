#!/bin/sh
set -eu

if [ "${1:-}" = "uvicorn" ]; then
    echo "[entrypoint] Running alembic upgrade head"
    alembic upgrade head
fi

exec "$@"
