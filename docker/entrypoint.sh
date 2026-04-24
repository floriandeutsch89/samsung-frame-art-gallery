#!/bin/sh
set -e

# Optional: Run migrations or init tasks here if needed
# python -m alembic upgrade head

# Start the application
exec uvicorn src.main:app --host 0.0.0.0 --port 8080
