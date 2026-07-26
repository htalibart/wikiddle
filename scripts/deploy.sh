#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIRECTORY="/var/www/wikiddle"
TEMPORARY_ROOT=""
TEST_DIRECTORY=""
WORKTREE_CREATED=false
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

    if [ "$WORKTREE_CREATED" = true ]; then
        git -C "$PROJECT_DIRECTORY" worktree remove --force "$TEST_DIRECTORY" 2>/dev/null || true
    fi

    if [ -n "$TEMPORARY_ROOT" ]; then
        rm -rf "$TEMPORARY_ROOT"
    fi
}

trap cleanup EXIT

cd "$PROJECT_DIRECTORY"

echo "Fetching origin/main..."
git fetch origin main

WIKI_VERSION="$(git show origin/main:config/wikiddle.service | sed -n 's/^Environment="WIKI_VERSION=\([^"]*\)"$/\1/p')"

if [ -z "$WIKI_VERSION" ]; then
    echo "WIKI_VERSION could not be read from config/wikiddle.service"
    exit 1
fi

if [ ! -f "$PROJECT_DIRECTORY/data/db/wiki/v${WIKI_VERSION}/en.db" ]; then
    echo "Missing database: data/db/wiki/v${WIKI_VERSION}/en.db"
    exit 1
fi

if [ ! -f "$PROJECT_DIRECTORY/data/db/wiki/v${WIKI_VERSION}/fr.db" ]; then
    echo "Missing database: data/db/wiki/v${WIKI_VERSION}/fr.db"
    exit 1
fi

echo "Database version v${WIKI_VERSION} is available"

if git diff --quiet HEAD origin/main -- config/Caddyfile.prod; then
    CADDY_CHANGED=false
else
    CADDY_CHANGED=true
fi

echo "Creating temporary worktree..."
TEMPORARY_ROOT="$(mktemp -d /tmp/wikiddle-deploy-XXXXXX)"
TEST_DIRECTORY="$TEMPORARY_ROOT/worktree"

git worktree add --detach "$TEST_DIRECTORY" origin/main
WORKTREE_CREATED=true

echo "Creating temporary Python environment..."
python3 -m venv "$TEST_DIRECTORY/venv"
"$TEST_DIRECTORY/venv/bin/pip" install -r "$TEST_DIRECTORY/backend/requirements.txt" pytest pytest-playwright
"$TEST_DIRECTORY/venv/bin/python" -m playwright install firefox

echo "Installing and building temporary frontend..."
npm --prefix "$TEST_DIRECTORY/frontend" ci
npm --prefix "$TEST_DIRECTORY/frontend" run build

echo "Starting temporary backend..."
setsid env \
    ENV=dev \
    WIKI_DB_DIR="$PROJECT_DIRECTORY/data/db/wiki/" \
    WIKI_VERSION="$WIKI_VERSION" \
    GAMES_DB="$PROJECT_DIRECTORY/data/db/games/v2.db" \
    ADMIN_TOKEN=dev \
    bash -c "cd '$TEST_DIRECTORY/backend' && exec '$TEST_DIRECTORY/venv/bin/fastapi' run --port 8001" \
    > /tmp/wikiddle-backend-e2e.log 2>&1 &

BACKEND_PID=$!
BACKEND_PGID="$(ps -o pgid= -p "$BACKEND_PID" | tr -d ' ')"

echo "Starting temporary frontend..."
setsid env \
    VITE_API_TARGET=http://127.0.0.1:8001 \
    npm --prefix "$TEST_DIRECTORY/frontend" run dev -- --host 127.0.0.1 --port 5174 \
    > /tmp/wikiddle-frontend-e2e.log 2>&1 &

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

echo "Running E2E tests..."
E2E_BASE_URL=http://127.0.0.1:5174 \
    "$TEST_DIRECTORY/venv/bin/python" -m pytest \
    "$TEST_DIRECTORY/tests/test_e2e.py" \
    --browser firefox

echo "E2E tests passed"

echo "Updating production code..."
git pull --ff-only origin main

echo "Installing production Python requirements..."
venv/bin/pip install -r backend/requirements.txt

echo "Building production frontend..."
npm --prefix frontend ci
npm --prefix frontend run build

echo "Restarting Wikiddle..."
sudo systemctl daemon-reload
sudo systemctl restart wikiddle
sudo systemctl is-active --quiet wikiddle

if [ "$CADDY_CHANGED" = true ]; then
    echo "Caddy configuration changed, restarting Caddy..."
    sudo systemctl restart caddy
fi

echo "Waiting for production API..."

for i in {1..30}; do
    if curl --fail --silent http://127.0.0.1:8000/openapi.json > /dev/null; then
        echo "Production API is responding"
        break
    fi

    if [ "$i" -eq 30 ]; then
        echo "Production API failed to start"
        exit 1
    fi

    sleep 1
done

echo "Deployment completed successfully"
