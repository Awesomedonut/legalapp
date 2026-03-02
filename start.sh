#!/usr/bin/env bash
set -euo pipefail

cd unfair_tos_web
exec gunicorn app:app --bind "0.0.0.0:${PORT:-8080}" --workers 2 --threads 4 --timeout 120
