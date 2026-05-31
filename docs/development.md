# Development
This document describes how to run Wikiddle locally.

## Prerequisites
- Python 3.x
- Node.js 24+

## Backend
Create a virtual environment and install dependencies:
```bash
cd backend/
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```
Run the development server:
```bash
cd backend/
ENV=dev WIKI_DB_DIR=../data/db/wiki/ WIKI_VERSION=2 GAMES_DB=../data/db/games/v1.db ADMIN_TOKEN=dev fastapi dev
```
`ENV=dev` opens CORS to all origins. CORS (Cross-Origin Resource Sharing) is a browser security mechanism that prevents a web page from making requests to a different domain than the one that served it. This protects users from malicious websites silently making requests to other sites on their behalf. In development, the frontend and backend run on different ports, which counts as different origins — so CORS needs to be disabled locally.

To manually trigger the daily refresh:
```bash
curl -s -X POST -H "Authorization: Bearer dev" "http://127.0.0.1:8000/api/admin/refresh"
```

## Frontend

The frontend is a plain HTML/CSS/JS app using ES modules, bundled with [Vite](https://vite.dev). Vite serves two purposes:

- **In development** — it provides a local dev server with hot reload, and proxies `/api` requests to the backend
- **In production** — it bundles the JS files into `dist/`, which Caddy serves

### Initial setup (already done, documented for reference)

Install Node.js 24:
```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v
```

Create `package.json` from the project root:
```bash
npm init -y
```

Install Vite:
```bash
npm install --save-dev vite
```

Add the following scripts to `package.json`:
```json
"scripts": {
  "dev": "cd frontend && vite",
  "build": "cd frontend && vite build"
}
```

Install the frontend npm packages (tom-select and canvas-confetti):
```bash
npm install tom-select canvas-confetti
```

Create `frontend/vite.config.js` to proxy `/api` requests to the backend in development:
```js
export default {
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000'
    }
  }
}
```

`package.json`, `package-lock.json`, and `vite.config.js` are versioned in the repo. `node_modules/` — the directory where npm installs the actual package files — is not, because it is large and can be fully reproduced from `package.json`.

### Running locally

Install packages listed in `package.json` into `node_modules/`:
```bash
npm install
```

Re-run `npm install` whenever `package.json` changes (e.g. after a `git pull` that adds or updates a dependency). You do not need to re-run it when your own JS files change — Vite picks those up automatically.

To add a new dependency:
```bash
npm install <package>         # runtime dependency
npm install --save-dev <package>  # dev-only dependency (linters, bundlers, etc.)
```

This updates `package.json` and `package-lock.json` — commit both.

Run the development server:
```bash
npm run dev
```

The site will be available at `http://localhost:5173`. Make sure the backend is running first.

### Testing the production build locally

To test an environment closer to production, build the frontend and serve it with Caddy:

```bash
npm run build
```

Then, stop the system Caddy service if it is running:
```bash
sudo systemctl stop caddy
```

Serve the built frontend with the local Caddy config from the project root:
```bash
caddy run --config config/Caddyfile.dev
```

The site will be available at `http://localhost:8080`. Unlike `npm run dev`, changes to JS files are not picked up automatically (re-run `npm run build` each time).

## Tests
For unit tests and integration tests, run from the root of the project:

```bash
python -m pytest
```
Unit tests (`tests/test_main.py`) mock the database and can be run without it. Integration tests (`tests/test_integration.py`) require the database to be present at `data/wiki.db`.


For end-to-end tests with Firefox, first install Playwright:

```bash 
pip install pytest-playwright
playwright install firefox
```

then:

```bash
python -m pytest tests/test_e2e.py --browser firefox
```

Or to run with Chromium (the default):

```bash 
playwright install chromium
python -m pytest tests/test_e2e.py
```



## Documentation
```bash
npx jsdoc frontend/*.js -d docs/jsdoc
```

## Linter
For Python, it's simple, install `ruff`:
```bash
pip install ruff
```
then:
```bash
ruff check backend/
```
It was added to pre-commit hooks (`.git/hooks/pre-commit`) and to CI (`.github/workflows/ci.yml`).

For JavaScript, to install ESLint, we need to install Node >= 20:
```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v
```
Then:
```bash
npx eslint frontend/
```
It was added to pre-commit hooks (`.git/hooks/pre-commit`) and to CI (`.github/workflows/ci.yml`).
