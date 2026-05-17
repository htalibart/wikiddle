# Development
This document describes how to run Wikiddle locally.

## Prerequisites
- Python 3.x
- Caddy
- A local copy of the database at `data/wiki.db`

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
ENV=dev WIKI_DB_DIR=../data/db GAMES_DB=../data/games.db ADMIN_TOKEN=dev fastapi dev
```
`ENV=dev` opens CORS to all origins. CORS (Cross-Origin Resource Sharing) is a browser security mechanism that prevents a web page from making requests to a different domain than the one that served it. This protects users from malicious websites silently making requests to other sites on their behalf. In development, the frontend and backend run on different ports, which counts as different origins — so CORS needs to be disabled locally.

To manually trigger the daily refresh:
```bash
curl "http://localhost:8080/api/admin/refresh?token=dev"
```

## Frontend
First, stop the system Caddy service if it is running:
```bash
sudo systemctl stop caddy
```
Then serve the frontend with the local Caddy config from the project root:
```bash
caddy run --config config/Caddyfile.dev
```
The site will be available at `http://localhost:8080`.

## Updating External Dependencies

External scripts and stylesheets are loaded from jsdelivr with [Subresource Integrity (SRI)](https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity) hashes to prevent tampering.

To update a dependency:
1. Find the latest version:
```bash
   curl https://cdn.jsdelivr.net/npm/${package}/package.json | grep '"version"'
```
2. For each file of the package loaded in `frontend/index.html`, replace the version number in the URL with the new one (e.g. `tom-select@2.5.0` -> `tom-select@2.6.0`)
3. Paste each updated URL into https://srihash.org and copy the generated `integrity` attribute back into `frontend/index.html`

## Tests
Run from the root of the project:
```bash
python -m pytest
```
Unit tests (`tests/test_main.py`) mock the database and can be run without it. Integration tests (`tests/test_integration.py`) require the database to be present at `data/wiki.db`.


## Documentation
```bash
npx jsdoc frontend/app.js -d docs/jsdoc
```
