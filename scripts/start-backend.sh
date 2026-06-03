#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="dev"
RUN_MIGRATIONS="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --migrate)
      RUN_MIGRATIONS="true"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: ./scripts/start-backend.sh [--env dev|staging|prod] [--migrate]"
      exit 1
      ;;
  esac
done

if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "prod" ]]; then
  echo "Invalid environment: $ENVIRONMENT"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.$ENVIRONMENT"
if [[ ! -f "$ENV_FILE" ]]; then
  ENV_FILE="$ROOT_DIR/.env"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "No env file found. Expected '$ROOT_DIR/.env.$ENVIRONMENT' or '$ROOT_DIR/.env'. Create one from '.env.example' first."
  exit 1
fi

echo "Loading env from $ENV_FILE"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

cd "$ROOT_DIR/backend"

PYTHON_CMD="python"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_CMD=".venv/bin/python"
fi

if [[ "$RUN_MIGRATIONS" == "true" ]]; then
  echo "Running Alembic migrations..."
  "$PYTHON_CMD" -m alembic upgrade head
fi

echo "Starting backend with environment '$ENVIRONMENT'..."
"$PYTHON_CMD" -m uvicorn app.main:app --reload --port 8000
