
# ENYARD Admin (Backend + Frontend)

## Backend (FastAPI)
- Location: `backend/`
- Install:
  ```bash
  pip install -r backend/requirements.txt
  ```
- Run:
  ```bash
  uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --reload
  ```
- Env (optional): `DB_HOST, DB_USER, DB_PASS, DB_NAME`

## Frontend
- Location: `frontend/index.html`
- Open `index.html` in your browser.
- It expects backend at `http://localhost:8000`. Edit the `API` const in the file if you run backend elsewhere.
