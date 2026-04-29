#!/bin/bash
set -e

if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Applying database migrations..."
    alembic upgrade head
fi

exec "$@"
