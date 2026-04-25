# Development

This document describes how to run Wikiddle locally.

## Prerequisites

- Python 3.x
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
ENV=dev WIKI_DB_PATH=../data/wiki.db fastapi dev
```

`ENV=dev` opens CORS to all origins. CORS (Cross-Origin Resource Sharing) is a browser security mechanism that prevents a web page from making requests to a different domain than the one that served it. This protects users from malicious websites silently making requests to other sites on their behalf. In development, the frontend and backend run on different ports, which counts as different origins — so CORS needs to be disabled locally.

## Frontend

Serve the frontend locally:

```bash
cd frontend/
python3 -m http.server 3000
```

## Tests

Run from the root of the project:

```bash
python -m pytest
```

Unit tests (`tests/test_main.py`) mock the database and can be run without it. Integration tests (`tests/test_integration.py`) require the database to be present at `data/wiki.db`.
