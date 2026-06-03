#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="dev"
INSTALL="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --install)
      INSTALL="true"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: ./scripts/start-frontend.sh [--env dev|staging|prod] [--install]"
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

cd "$ROOT_DIR/frontend"

if [[ "$INSTALL" == "true" ]]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo "Starting frontend with environment '$ENVIRONMENT'..."
npm run dev
