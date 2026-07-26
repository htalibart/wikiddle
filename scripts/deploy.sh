#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIRECTORY="/var/www/wikiddle"
BACKEND_PID=""
BACKEND_PGID=""
FRONTEND_PID=""
FRONTEND_PGID=""

cleanup() {
    if [ -n "$FRONTEND_PGID" ]; then
        kill -- "-$FRONTEND_PGID" 2>/dev/null || true
    fi

    if [ -n "$BACKEND_PGID" ]; then
        kill -- "-$BACKEND_PGID" 2>/dev/null || true
    fi

    if [ -n "$FRONTEND_PID" ]; then
        wait "$FRONTEND_PID" 2>/dev/null || true
    fi

    if [ -n "$BACKEND_PID" ]; then
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT

cd "$PROJECT_DIRECTORY"

git fetch origin main

WIKI_VERSION="$(git show origin/main:config/wikiddle.service | sed -n 's/^Environment="WIKI_VERSION=\([^"]*\)"$/\1/p')"

test -n "$WIKI_VERSION"
test -f "data/db/wiki/v${WIKI_VERSION}/en.db"
test -f "data/db/wiki/v${WIKI_VERSION}/fr.db"

echo "Database version v${WIKI_VERSION} is available"
echo "Pulling main..."

git pull --ff-only origin main

echo "Installing pip requirements..."
venv/bin/pip install -r backend/requirements.txt

echo "Building frontend..."
npm --prefix frontend ci
npm --prefix frontend run build

echo "Running temporary backend for tests..."
setsid env ENV=dev WIKI_DB_DIR=../data/db/wiki/ WIKI_VERSION="$WIKI_VERSION" GAMES_DB=../data/db/games/v2.db ADMIN_TOKEN=dev bash -c 'cd backend && exec ../venv/bin/fastapi dev --port 8001' > /tmp/wikiddle-backend-e2e.log 2>&1 &
BACKEND_PID=$!
BACKEND_PGID="$(ps -o pgid= -p "$BACKEND_PID" | tr -d ' ')"

echo "Running temporary frontend for tests..."
setsid env VITE_API_TARGET=http://127.0.0.1:8001 npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174 > /tmp/wikiddle-frontend-e2e.log 2>&1 &
FRONTEND_PID=$!
FRONTEND_PGID="$(ps -o pgid= -p "$FRONTEND_PID" | tr -d ' ')"

echo "Waiting for temporary servers..."

for i in {1..30}; do
    if curl --fail --silent http://127.0.0.1:8001/openapi.json > /dev/null &&
       curl --fail --silent http://127.0.0.1:5174 > /dev/null; then
        echo "Temporary backend and frontend are ready"
        break
    fi

    if [ "$i" -eq 30 ]; then
        echo "Temporary backend or frontend failed to start"
        cat /tmp/wikiddle-backend-e2e.log
        cat /tmp/wikiddle-frontend-e2e.log
        exit 1
    fi

    sleep 1
done


echo "Running end-to-end tests..."
E2E_BASE_URL=http://127.0.0.1:5174 venv/bin/python -m pytest tests/test_e2e.py --browser firefox

echo "Restarting Wikiddle..."
sudo systemctl daemon-reload
sudo systemctl restart wikiddle
sudo systemctl is-active --quiet wikiddle

echo "Deployment successful"
